"""WebPerf Diagnostics application entry point.

Routes and business logic live in services/ and routes/. Keep this file small:
it should mainly configure Flask, security hooks, shared template state, and route registration.
"""
import secrets
from flask import Flask, jsonify, g, request

import database
from config import *
from services.auth import current_user
from services.web_utils import ensure_csrf_token, verify_csrf
from routes import pages, auth, admin, api_analysis, api_competitors, api_payments, api_contact, system

# config.py loads .env before database.py is imported, so DATABASE_PATH is stable.
database.init_db()

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
app.secret_key = FLASK_SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
    SESSION_COOKIE_NAME="__Host-webperf_session" if SESSION_COOKIE_SECURE else "webperf_session",
)


@app.before_request
def security_before_request():
    ensure_csrf_token()
    g.csp_nonce = secrets.token_urlsafe(18)
    if request.method == "POST" and request.path != "/api/payment/webhook":
        if not verify_csrf():
            if request.path.startswith("/api/"):
                return jsonify({"error":"Security check failed. Refresh the page and try again."}), 403
            return "Security check failed. Refresh the page and try again.", 403


@app.after_request
def security_headers(response):
    nonce = getattr(g, "csp_nonce", "")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' https://unpkg.com https://checkout.razorpay.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://checkout.razorpay.com https://api.razorpay.com; "
        "frame-src https://checkout.razorpay.com https://api.razorpay.com; "
        "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
    )
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.path.startswith("/api/") or request.path in {"/login","/register","/admin","/admin/login"}:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.context_processor
def inject_state():
    user = current_user()
    payment_configured = bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)
    webperf_state = {
        "authenticated": user is not None,
        "premium": bool(user and user["premium_unlocked"]),
        "email": user["email"] if user else "",
        "paymentConfigured": payment_configured,
        "premiumPrice": PREMIUM_DISPLAY_PRICE,
    }
    return {
        "current_user": user,
        "premium_price": PREMIUM_DISPLAY_PRICE,
        "payment_configured": payment_configured,
        "webperf_state": {**webperf_state, "csrfToken": ensure_csrf_token()},
        "csrf_token": ensure_csrf_token(),
        "legal_contact_email": LEGAL_CONTACT_EMAIL,
        "business_name": BUSINESS_NAME,
        "business_address": BUSINESS_ADDRESS,
        "competitor_provider": COMPETITOR_PROVIDER,
        "csp_nonce": getattr(g, "csp_nonce", ""),
    }


# Route modules register their original endpoint names, so existing templates/JS keep working.
pages.register_routes(app)
auth.register_routes(app)
admin.register_routes(app)
api_analysis.register_routes(app)
api_competitors.register_routes(app)
api_payments.register_routes(app)
api_contact.register_routes(app)
system.register_routes(app)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=FLASK_DEBUG)
