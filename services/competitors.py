import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
import requests
import database
from config import *
from services.web_utils import normalized_host


def discover_competitors(website_url: str, region: str, industry: str) -> list[dict]:
    region = str(region or "").strip(); industry = str(industry or "").strip()
    if len(region) < 2 or len(industry) < 2:
        raise ValueError("Choose a region and enter the type of website or industry you want to compare.")
    provider = COMPETITOR_PROVIDER if COMPETITOR_PROVIDER in {"serper", "brave", "google_places"} else "serper"
    if provider == "google_places" and not GOOGLE_PLACES_API_KEY: raise RuntimeError("Google Places is not configured. Add GOOGLE_PLACES_API_KEY or choose another competitor provider for testing.")
    if provider == "brave" and not BRAVE_SEARCH_API_KEY: raise RuntimeError("Brave Search is not configured. Add BRAVE_SEARCH_API_KEY to your .env file.")
    if provider == "serper" and not SERPER_API_KEY: raise RuntimeError("Serper is not configured. Add SERPER_API_KEY to your .env file.")
    cache_key = hashlib.sha256(f"{provider}-v4|{region.lower()}|{industry.lower()}".encode()).hexdigest()
    cached = database.get_cache(cache_key, "competitor_cache")
    if cached: return json.loads(cached["results_json"])
    current_host = normalized_host(website_url); industry_lower = industry.lower()
    if "digital marketing" in industry_lower or "marketing agency" in industry_lower: search_terms = ["digital marketing agency", "marketing agency", "SEO agency"]
    elif "seo" in industry_lower: search_terms = ["SEO agency", "digital marketing agency"]
    elif "software" in industry_lower or "saas" in industry_lower: search_terms = ["software company", "SaaS company"]
    elif "real estate" in industry_lower: search_terms = ["real estate agency", "real estate company"]
    elif "health" in industry_lower: search_terms = ["healthcare provider", "medical clinic"]
    elif "education" in industry_lower: search_terms = ["education institute", "training institute"]
    elif "travel" in industry_lower or "hospitality" in industry_lower: search_terms = ["travel agency", "hotel"]
    elif "financial" in industry_lower or "banking" in industry_lower: search_terms = ["financial services company", "finance company"]
    elif "professional" in industry_lower or "consult" in industry_lower: search_terms = ["consulting firm", industry]
    else: search_terms = [industry]
    blocked_domains = ("reddit.com","quora.com","wikipedia.org","facebook.com","instagram.com","linkedin.com","youtube.com","x.com","medium.com","substack.com","clutch.co","goodfirms.co","upwork.com","fiverr.com","glassdoor.com","indeed.com","ambitionbox.com","crunchbase.com","yelp.com","tripadvisor.com","semrush.com","themanifest.com","builtincolorado.com")
    editorial_terms = ("how to","how-to","guide","list of","directory","directories","ranking","ranked","comparison","reddit","community","forum","thread","blog","course","courses","jobs","salary","marketplace","startup list","association","associations","university","college","school","you should know")
    business_terms = ("agency","company","services","solutions","consulting","consultancy","studio","firm","digital marketing","seo","marketing","software","saas","platform","ecommerce","e-commerce","technology","technologies","telecom","telecommunications","network","mobile operator")
    results_by_domain = {}
    def add_candidate(title, url, snippet, address="", maps_url="", primary_type=""):
        host = normalized_host(url) if url else ""
        if not host or host == current_host or host in results_by_domain: return
        if any(host == d or host.endswith("." + d) for d in blocked_domains): return
        title_lower = str(title or "").strip().lower(); url_lower = str(url or "").lower(); haystack = f"{title} {snippet} {url}".lower()
        if re.match(r"^\s*\d+([.)]|\s)", title_lower) or title_lower.startswith(("best ", "top ", "list of ")): return
        if any(term in title_lower for term in editorial_terms): return
        if any(marker in url_lower for marker in ("/list/","/lists/","/directory/","/directories/","/rankings/","/ranking/","/reviews/","/blog/","/article/","/articles/","/forum/")): return
        industry_terms = [x.strip() for x in re.split(r"[,|/]", industry_lower) if len(x.strip()) >= 3]
        industry_hits = sum(1 for term in industry_terms if term in haystack); business_hits = sum(1 for term in business_terms if term in haystack)
        strong_business = any(term in title_lower for term in ("agency","company","consult","studio","firm","marketing","software","telecom","technology"))
        if not industry_hits and not business_hits: return
        if business_hits < 2 and not strong_business: return
        score = industry_hits * 5 + business_hits + (4 if strong_business else 0)
        results_by_domain[host] = {"domain":host,"url":url,"title":str(title or host).strip()[:180],"address":str(address or region).strip()[:220],"googleMapsUrl":maps_url,"primaryType":primary_type,"snippet":str(snippet or address or "Business website").strip()[:280],"relevanceScore":score}
    if provider == "serper":
        term = search_terms[0]; query = f"{term} in {region}"
        response = requests.post(SERPER_SEARCH_URL, headers={"X-API-KEY":SERPER_API_KEY,"Content-Type":"application/json"}, json={"q":query,"hl":"en","num":20}, timeout=25)
        if response.status_code >= 400:
            if response.status_code in (401,403): raise RuntimeError("Serper rejected the API key (Unauthorized). Check SERPER_API_KEY in your .env file, then fully stop and restart run.bat.")
            try: message = response.json().get("message") or response.json().get("error") or "Serper returned an error."
            except ValueError: message = "Serper returned an error."
            raise RuntimeError(str(message))
        for item in (response.json().get("organic") or []): add_candidate(item.get("title"),item.get("link"),item.get("snippet"))
    elif provider == "brave":
        term = search_terms[0]; query = f"{term} in {region}"
        response = requests.get(BRAVE_SEARCH_URL, headers={"Accept":"application/json","X-Subscription-Token":BRAVE_SEARCH_API_KEY}, params={"q":query,"count":10,"search_lang":"en"}, timeout=25)
        if response.status_code >= 400:
            try: message = response.json().get("message") or response.json().get("error") or "Brave Search returned an error."
            except ValueError: message = "Brave Search returned an error."
            raise RuntimeError(str(message))
        for item in (response.json().get("web",{}).get("results") or []): add_candidate(item.get("title"),item.get("url"),item.get("description"))
    else:
        field_mask = ",".join(["places.id","places.displayName","places.formattedAddress","places.googleMapsUri","places.primaryType","places.types","places.websiteUri","places.pureServiceAreaBusiness"])
        for term in search_terms[:2]:
            payload = {"textQuery":f"{term} in {region}","pageSize":10,"includePureServiceAreaBusinesses":True,"languageCode":"en"}
            response = requests.post(GOOGLE_PLACES_URL, headers={"Content-Type":"application/json","X-Goog-Api-Key":GOOGLE_PLACES_API_KEY,"X-Goog-FieldMask":field_mask}, json=payload, timeout=25)
            if response.status_code >= 400:
                try: message = response.json().get("error",{}).get("message") or "Google Places returned an error."
                except ValueError: message = "Google Places returned an error."
                raise RuntimeError(message)
            for place in (response.json().get("places") or []):
                website = str(place.get("websiteUri") or "").strip(); display_name = ((place.get("displayName") or {}).get("text") or normalized_host(website)).strip(); types = " ".join([str(place.get("primaryType") or "")] + [str(x) for x in (place.get("types") or [])])
                add_candidate(display_name,website,place.get("formattedAddress") or region,place.get("formattedAddress") or region,place.get("googleMapsUri") or "",types)
    results = sorted(results_by_domain.values(), key=lambda item:(-item["relevanceScore"],item["title"].lower()))[:12]
    for item in results: item.pop("relevanceScore",None)
    expires = datetime.now(timezone.utc) + timedelta(days=COMPETITOR_CACHE_DAYS)
    database.set_competitor_cache(cache_key,region,industry,results,expires.isoformat())
    return results
