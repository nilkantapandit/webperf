import hmac
from flask import render_template, request, redirect, session, url_for
import database
from config import ADMIN_EMAIL, ADMIN_PASSWORD, SITE_NAME
from services.auth import admin_required


def register_routes(app):
    @app.get("/admin/login")
    def admin_login():
        if session.get("admin_authenticated"): return redirect(url_for("admin"))
        return render_template("admin_login.html", site_name=SITE_NAME, error=None)

    @app.post("/admin/login")
    def admin_login_post():
        email = request.form.get("email", "").strip().lower(); password = request.form.get("password", "")
        if not ADMIN_EMAIL or not ADMIN_PASSWORD or email != ADMIN_EMAIL or not hmac.compare_digest(password, ADMIN_PASSWORD):
            return render_template("admin_login.html", site_name=SITE_NAME, error="Invalid admin credentials."), 401
        session.clear(); session["admin_authenticated"] = True
        return redirect(url_for("admin"))

    @app.post("/admin/logout")
    def admin_logout():
        session.pop("admin_authenticated", None)
        return redirect(url_for("admin_login"))

    @app.get("/admin")
    @admin_required
    def admin():
        return render_template("admin.html", site_name=SITE_NAME, stats=database.stats(), users=database.list_users(), purchases=database.list_purchases())

    @app.post("/admin/users/<int:user_id>/premium")
    @admin_required
    def admin_toggle_premium(user_id):
        database.set_premium(user_id, request.form.get("enabled") == "1")
        return redirect(url_for("admin"))
