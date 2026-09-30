import hashlib
import hmac
import secrets
import requests
from flask import jsonify, request, current_app
import database
from config import *
from services.auth import current_user, login_required


def register_routes(app):
    @app.post("/api/payment/order")
    @login_required
    def create_payment_order():
        user=current_user()
        if user["premium_unlocked"]: return jsonify({"alreadyUnlocked":True})
        if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET: return jsonify({"error":"Payments are not configured yet. Add the Razorpay test/live keys to your .env file."}),503
        receipt=f"cp_{user['id']}_{secrets.token_hex(5)}"; payload={"amount":PREMIUM_AMOUNT_MINOR,"currency":PREMIUM_CURRENCY,"receipt":receipt,"notes":{"user_id":str(user["id"]),"product":PREMIUM_NAME}}
        try:
            response=requests.post(f"{RAZORPAY_API_URL}/orders",auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET),json=payload,timeout=20)
            if response.status_code >= 400:
                try: message=response.json().get("error",{}).get("description") or "Razorpay could not create the order."
                except ValueError: message="Razorpay could not create the order."
                return jsonify({"error":message}),502
            order=response.json(); database.create_purchase(user["id"],order["id"],PREMIUM_AMOUNT_MINOR,PREMIUM_CURRENCY)
            return jsonify({"key":RAZORPAY_KEY_ID,"orderId":order["id"],"amount":PREMIUM_AMOUNT_MINOR,"currency":PREMIUM_CURRENCY,"name":SITE_NAME,"email":user["email"],"description":PREMIUM_NAME})
        except requests.RequestException: return jsonify({"error":"We could not reach the payment service. Please try again."}),502

    @app.post("/api/payment/verify")
    @login_required
    def verify_payment():
        body=request.get_json(silent=True) or {}; order_id=str(body.get("razorpay_order_id","")).strip(); payment_id=str(body.get("razorpay_payment_id","")).strip(); signature=str(body.get("razorpay_signature","")).strip()
        if not order_id or not payment_id or not signature: return jsonify({"error":"Payment verification details are incomplete."}),400
        purchase=database.get_purchase_by_order(order_id); user=current_user()
        if not purchase or purchase["user_id"] != user["id"]: return jsonify({"error":"This payment does not belong to your account."}),403
        expected=hmac.new(RAZORPAY_KEY_SECRET.encode(),f"{order_id}|{payment_id}".encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,signature): return jsonify({"error":"Payment verification failed."}),400
        database.mark_purchase_paid(order_id,payment_id); return jsonify({"ok":True,"premiumUnlocked":True})

    @app.post("/api/payment/webhook")
    def payment_webhook():
        if not RAZORPAY_WEBHOOK_SECRET: return jsonify({"error":"Webhook secret is not configured."}),503
        raw=request.get_data(); signature=request.headers.get("X-Razorpay-Signature",""); expected=hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(),raw,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,signature): return jsonify({"error":"Invalid webhook signature."}),400
        payload=request.get_json(silent=True) or {}; event=payload.get("event",""); payment=((payload.get("payload") or {}).get("payment") or {}).get("entity") or {}; order_id=payment.get("order_id")
        if event == "payment.captured" and order_id: database.mark_purchase_paid(order_id,payment.get("id",""))
        elif event == "payment.failed" and order_id:
            purchase=database.get_purchase_by_order(order_id)
            if purchase:
                with database.connect() as conn: conn.execute("UPDATE purchases SET status = 'failed', updated_at = ? WHERE order_id = ?",(database.utc_now(),order_id))
        return jsonify({"ok":True})

    @app.post("/api/dev/unlock")
    @login_required
    def dev_unlock():
        if not DEV_PREMIUM_UNLOCK: return jsonify({"error":"Developer unlock is disabled."}),404
        database.set_premium(current_user()["id"],True); return jsonify({"ok":True,"premiumUnlocked":True})
