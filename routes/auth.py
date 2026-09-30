import re
from flask import render_template, request, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import database
from config import SITE_NAME, SITE_URL
from services.auth import current_user
from services.web_utils import safe_next_path


def register_routes(app):
    @app.post("/register")
    def register_post():
        if current_user(): return redirect(url_for("index"))
        email = request.form.get("email", "").strip().lower(); password = request.form.get("password", "")
        if request.form.get("age_confirmed") != "1":
            return render_template("auth.html", mode="register", error="This service is intended for people aged 18 or older.", site_name=SITE_NAME, site_url=SITE_URL, next=request.form.get("next", "/")), 400
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            return render_template("auth.html", mode="register", error="Enter a valid email address.", site_name=SITE_NAME, site_url=SITE_URL, next=request.form.get("next", "/")), 400
        if len(password) < 8:
            return render_template("auth.html", mode="register", error="Your password must be at least 8 characters.", site_name=SITE_NAME, site_url=SITE_URL, next=request.form.get("next", "/")), 400
        try: user_id = database.create_user(email, generate_password_hash(password))
        except Exception:
            return render_template("auth.html", mode="register", error="An account with that email already exists.", site_name=SITE_NAME, site_url=SITE_URL, next=request.form.get("next", "/")), 400
        session.clear(); session["user_id"] = user_id
        return redirect(safe_next_path(request.form.get("next")))

    @app.post("/login")
    def login_post():
        email = request.form.get("email", "").strip().lower(); password = request.form.get("password", "")
        user = database.get_user_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("auth.html", mode="login", error="Email or password is incorrect.", site_name=SITE_NAME, site_url=SITE_URL, next=request.form.get("next", "/")), 401
        session.clear(); session["user_id"] = user["id"]
        return redirect(safe_next_path(request.form.get("next")))

    @app.post("/logout")
    def logout():
        session.pop("user_id", None)
        return redirect(url_for("index"))
