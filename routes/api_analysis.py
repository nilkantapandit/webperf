import requests
from flask import jsonify, request, current_app
import database
from config import API_KEY, DEFAULT_STRATEGY, PAGESPEED_URL
from services.analysis import cache_analysis, classify_website, get_cached_analysis, parse_pagespeed, _extract_homepage_signals
from services.auth import premium_required
from services.web_utils import normalized_host, validate_url


def register_routes(app):
    @app.post("/api/analyze")
    def analyze():
        try:
            body = request.get_json(silent=True) or {}; url = validate_url(body.get("url")); database.record_analysis_event(normalized_host(url))
            strategy = (body.get("strategy") or DEFAULT_STRATEGY).lower()
            if strategy not in {"mobile","desktop"}: strategy = DEFAULT_STRATEGY if DEFAULT_STRATEGY in {"mobile","desktop"} else "mobile"
            cached = get_cached_analysis(url,strategy)
            if cached: return jsonify(cached)
            params={"url":url,"strategy":strategy,"category":["performance","accessibility","best-practices","seo"]}
            if API_KEY: params["key"]=API_KEY
            response=requests.get(PAGESPEED_URL,params=params,timeout=90)
            if response.status_code != 200:
                try: message=response.json().get("error",{}).get("message") or "Google PageSpeed returned an error."
                except ValueError: message="Google PageSpeed returned an error."
                return jsonify({"error":message,"status":response.status_code}),502
            result=parse_pagespeed(response.json(),url,strategy); cache_analysis(result); return jsonify(result)
        except ValueError as exc: return jsonify({"error":str(exc)}),400
        except requests.Timeout: return jsonify({"error":"The analysis took too long. Please try again in a moment."}),504
        except requests.RequestException: return jsonify({"error":"We could not reach Google PageSpeed right now. Please try again in a moment."}),502
        except Exception as exc: current_app.logger.exception("Analysis failed"); return jsonify({"error":f"Analysis failed: {exc}"}),500

    @app.post("/api/website-profile")
    @premium_required
    def website_profile():
        try:
            body=request.get_json(silent=True) or {}; website=validate_url(body.get("website")); page_title=str(body.get("pageTitle","")).strip()[:300]
            fetched_title,description,homepage_text=_extract_homepage_signals(website)
            return jsonify(classify_website(website,fetched_title or page_title,description,homepage_text))
        except ValueError as exc: return jsonify({"error":str(exc)}),400
        except RuntimeError as exc: return jsonify({"error":str(exc)}),503
        except requests.Timeout: return jsonify({"error":"Industry detection took too long. Please try again."}),504
        except requests.RequestException: return jsonify({"error":"We could not reach the search service right now."}),502
        except Exception: current_app.logger.exception("Website profile detection failed"); return jsonify({"error":"We could not detect your website type right now."}),500

    @app.post("/api/competitor-analyze")
    @premium_required
    def competitor_analyze():
        try:
            body=request.get_json(silent=True) or {}; url=validate_url(body.get("url")); strategy=(body.get("strategy") or DEFAULT_STRATEGY).lower()
            if strategy not in {"mobile","desktop"}: strategy="mobile"
            cached=get_cached_analysis(url,strategy)
            if cached: return jsonify(cached)
            params={"url":url,"strategy":strategy,"category":["performance","accessibility","best-practices","seo"]}
            if API_KEY: params["key"]=API_KEY
            response=requests.get(PAGESPEED_URL,params=params,timeout=90)
            if response.status_code != 200:
                try: message=response.json().get("error",{}).get("message") or "Google PageSpeed returned an error."
                except ValueError: message="Google PageSpeed returned an error."
                return jsonify({"error":message,"status":response.status_code}),502
            result=parse_pagespeed(response.json(),url,strategy); cache_analysis(result); return jsonify(result)
        except ValueError as exc: return jsonify({"error":str(exc)}),400
        except requests.Timeout: return jsonify({"error":"The competitor analysis took too long. Please try again."}),504
        except requests.RequestException: return jsonify({"error":"We could not reach Google PageSpeed right now."}),502
        except Exception as exc: current_app.logger.exception("Competitor analysis failed"); return jsonify({"error":f"Competitor analysis failed: {exc}"}),500
