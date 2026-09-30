import hmac
import secrets
from urllib.parse import urlparse
from flask import request, session


def validate_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("Enter a website address.")
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or "." not in parsed.hostname:
        raise ValueError("Enter a valid website address, for example example.com")
    if parsed.username or parsed.password:
        raise ValueError("Website addresses cannot contain usernames or passwords.")
    if len(parsed.hostname) > 253:
        raise ValueError("That website address is too long.")
    return value


def safe_next_path(value: str | None) -> str:
    value = (value or "/").strip()
    if not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/"
    return value


def ensure_csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def verify_csrf() -> bool:
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRFToken") or request.form.get("csrf_token")
    return bool(expected and supplied and hmac.compare_digest(expected, supplied))


def normalized_host(url):
    return (urlparse(url).hostname or "").lower().replace("www.", "")
