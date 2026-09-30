from flask import render_template, request, redirect, url_for
import database
from config import SITE_URL, SITE_NAME, SITE_DESCRIPTION
from services.auth import current_user
from services.web_utils import safe_next_path


def register_routes(app):
    @app.get("/")
    def index():
        return render_template("index.html", site_url=SITE_URL, site_name=SITE_NAME, site_description=SITE_DESCRIPTION, checks_last_hour=database.checks_last_hour())

    @app.get("/legal")
    def legal():
        return render_template("legal.html", site_name=SITE_NAME, site_url=SITE_URL)

    @app.get("/register")
    def register():
        if current_user(): return redirect(url_for("index"))
        return render_template("auth.html", mode="register", site_name=SITE_NAME, site_url=SITE_URL)

    @app.get("/login")
    def login():
        if current_user(): return redirect(url_for("index"))
        return render_template("auth.html", mode="login", site_name=SITE_NAME, site_url=SITE_URL, next=request.args.get("next", "/"))
