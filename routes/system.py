from flask import jsonify, current_app
import database
from config import *
from services.emailer import smtp_configured


def register_routes(app):
    @app.get("/api/health")
    def health():
        return jsonify({"status":"ok","pagespeed_key_configured":bool(API_KEY),"smtp_configured":smtp_configured(),"google_places_configured":bool(GOOGLE_PLACES_API_KEY),"competitor_provider":COMPETITOR_PROVIDER,"brave_search_configured":bool(BRAVE_SEARCH_API_KEY),"serper_configured":bool(SERPER_API_KEY),"payments_configured":bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET),"database":str(database.DB_PATH)})

    @app.get("/robots.txt")
    def robots_txt():
        return current_app.response_class(f"User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /admin\nDisallow: /login\nDisallow: /register\nDisallow: /static/\n\nSitemap: {SITE_URL}/sitemap.xml\n",mimetype="text/plain")

    @app.get("/sitemap.xml")
    def sitemap_xml():
        return current_app.response_class(f'''<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{SITE_URL}/</loc></url><url><loc>{SITE_URL}/legal</loc></url></urlset>''',mimetype="application/xml")

    @app.get("/llms.txt")
    def llms_txt():
        content=f"""# {SITE_NAME}\n\n> {SITE_DESCRIPTION}\n\n{SITE_NAME} checks public websites with Google PageSpeed Insights and explains performance, accessibility, SEO and best-practice findings in plain language. Premium users can unlock competitor discovery and side-by-side website comparisons.\n\n## Main page\n- [Website checker]({SITE_URL}/)\n\n## Notes\n- Free audits are generated on demand.\n- Competitor analysis is a paid feature.\n- Results can vary with device, network, server and page conditions.\n"""
        return current_app.response_class(content,mimetype="text/plain")
