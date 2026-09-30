from functools import wraps
from flask import jsonify, redirect, request, session, url_for
import database
from services.web_utils import safe_next_path


def current_user():
    user_id = session.get("user_id")
    return database.get_user_by_id(user_id) if user_id else None


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith("/api/"): return jsonify({"error":"Please sign in to continue.","loginRequired":True}),401
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped


def premium_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user or not user["premium_unlocked"]:
            return jsonify({"error":"Competitor analysis is a paid feature. Unlock the Competitor Report to continue.","premiumRequired":True}),402
        return fn(*args, **kwargs)
    return wrapped


def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapped
