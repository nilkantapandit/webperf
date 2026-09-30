import re
import smtplib
from flask import jsonify, request, current_app
from services.emailer import send_contact_email
from services.web_utils import validate_url


def register_routes(app):
    @app.post("/api/contact")
    def contact():
        try:
            body=request.get_json(silent=True) or {}; name=str(body.get("name","")).strip(); email=str(body.get("email","")).strip(); website=validate_url(body.get("website")); help_with=str(body.get("helpWith","Not sure yet")).strip() or "Not sure yet"; message=str(body.get("message","")).strip()
            if body.get("ageConfirmed") is not True: raise ValueError("Please confirm that you are 18 or older before sending a request.")
            if not name or len(name)<2: raise ValueError("Please enter your name.")
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email): raise ValueError("Please enter a valid email address.")
            send_contact_email({"name":name,"email":email,"website":website,"helpWith":help_with,"message":message})
            return jsonify({"ok":True,"message":"Request received. We will get back to you shortly."})
        except ValueError as exc: return jsonify({"error":str(exc)}),400
        except RuntimeError as exc: return jsonify({"error":str(exc)}),503
        except (smtplib.SMTPException,OSError): current_app.logger.exception("Contact email failed"); return jsonify({"error":"We could not send your request right now. Please try again later."}),502
        except Exception as exc: current_app.logger.exception("Contact request failed"); return jsonify({"error":f"Could not send the request: {exc}"}),500
