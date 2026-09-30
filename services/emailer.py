import smtplib
from email.message import EmailMessage
from config import SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_USE_TLS, CONTACT_TO_EMAIL, CONTACT_FROM_EMAIL


def smtp_configured():
    return bool(SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD and CONTACT_TO_EMAIL)


def send_contact_email(payload: dict):
    if not smtp_configured():
        raise RuntimeError("Contact email is not configured yet. Add the SMTP settings to your .env file.")
    msg = EmailMessage()
    msg["Subject"] = f"Website optimization request — {payload['website']}"
    msg["From"] = CONTACT_FROM_EMAIL or SMTP_USERNAME
    msg["To"] = CONTACT_TO_EMAIL
    msg["Reply-To"] = payload["email"]
    msg.set_content("A new website optimization request was submitted.\n\n" + "\n".join([
        f"Name: {payload['name']}", f"Email: {payload['email']}", f"Website: {payload['website']}", f"Help requested: {payload['helpWith']}", "", f"Message:\n{payload.get('message') or 'No additional message provided.'}"
    ]))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        if SMTP_USE_TLS: server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
