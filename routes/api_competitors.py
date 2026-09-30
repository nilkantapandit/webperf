import requests
from flask import jsonify, request, current_app
from config import COMPETITOR_CACHE_DAYS
from services.auth import premium_required
from services.competitors import discover_competitors
from services.web_utils import validate_url


def register_routes(app):
    @app.post("/api/competitors")
    @premium_required
    def competitors():
        try:
            body=request.get_json(silent=True) or {}; website=validate_url(body.get("website")); region=str(body.get("region","")).strip(); industry=str(body.get("industry","")).strip()
            return jsonify({"results":discover_competitors(website,region,industry),"region":region,"industry":industry,"cachedForDays":COMPETITOR_CACHE_DAYS})
        except ValueError as exc: return jsonify({"error":str(exc)}),400
        except RuntimeError as exc: return jsonify({"error":str(exc)}),503
        except requests.Timeout: return jsonify({"error":"Competitor search took too long. Please try again."}),504
        except requests.RequestException: return jsonify({"error":"We could not reach the competitor search service right now."}),502
        except Exception as exc: current_app.logger.exception("Competitor discovery failed"); return jsonify({"error":f"Competitor search failed: {exc}"}),500
