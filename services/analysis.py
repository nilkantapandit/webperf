import hashlib
import ipaddress
import json
import re
import socket
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.parse import urljoin, urlparse

import requests

import database
from config import ANALYSIS_CACHE_HOURS
from services.web_utils import normalized_host, validate_url

CATEGORY_META = {
    "performance": {"label": "Performance", "class": "performance", "icon": "⚡"},
    "accessibility": {"label": "Accessibility", "class": "accessibility", "icon": "♿"},
    "best-practices": {"label": "Best Practices", "class": "best-practices", "icon": "◈"},
    "seo": {"label": "SEO", "class": "seo", "icon": "⌕"},
}

FRIENDLY_GUIDANCE = {
    "server-response-time": ("Your website is taking longer than expected to start responding. Visitors may see a blank or slow-loading page while the server prepares the content.", "This can be caused by slow hosting, busy servers, database work, or a website that has to do too much before sending the first response.", "Check hosting and server load, optimize slow database or application work, and consider caching or a CDN where appropriate."),
    "uses-optimized-images": ("Some images are heavier than they need to be, so visitors have to download more data before the page feels ready.", "Images are often uploaded at a higher quality or size than the page actually needs.", "Resize images to the size they are displayed, use WebP or AVIF where suitable, compress them, and lazy-load images that are lower on the page."),
    "uses-long-cache-ttl": ("Your browser is not being told to keep some static files for long enough. Repeat visitors may download the same files again.", "CSS, JavaScript and image files may have short or missing cache settings.", "Set sensible browser cache durations for versioned static files so returning visitors can reuse them."),
    "render-blocking-resources": ("Some CSS or JavaScript is delaying the moment when visitors can see useful content.", "The browser has to download and process certain files before it can finish displaying the page.", "Remove unnecessary files, defer non-essential JavaScript and optimize critical CSS so the main content can appear sooner."),
    "uses-text-compression": ("Text files such as HTML, CSS and JavaScript are larger than necessary while being sent to visitors.", "The server is not fully using compression such as Brotli or Gzip for text responses.", "Enable Brotli or Gzip compression for HTML, CSS, JavaScript, JSON and other text-based responses."),
    "largest-contentful-paint": ("The largest important piece of content is taking too long to appear.", "Slow server responses, large images, render-blocking files or too much work before the main content appears can delay it.", "Improve server response time, prioritize the main image or content, reduce blocking resources and avoid unnecessary work during initial loading."),
    "cumulative-layout-shift": ("Parts of the page move around while the page is loading. This can make the site feel unstable and can cause accidental clicks.", "Images, ads, fonts or other content may be loading without reserved space.", "Reserve space for images and embeds, avoid inserting content above existing content, and make font loading predictable."),
    "total-blocking-time": ("The browser is spending too much time busy with JavaScript before it can respond smoothly to visitors.", "Large scripts, third-party tools or too much JavaScript work can keep the main browser thread busy.", "Reduce JavaScript, split large bundles, defer non-essential code and review third-party scripts."),
    "interaction-to-next-paint": ("The page can feel slow when visitors click, tap or type.", "Long JavaScript tasks can prevent the browser from responding quickly to user actions.", "Reduce long-running JavaScript tasks, simplify event handlers and delay work that is not needed immediately."),
    "image-delivery-insight": ("Some images could be delivered more efficiently, which can make the page feel faster.", "Large image files, inefficient formats or images that are bigger than their displayed size can increase download time.", "Compress and resize images, use modern formats and serve appropriately sized images for each device."),
    "forced-reflow-insight": ("The browser has to stop and recalculate the page layout while JavaScript is running. Repeating this can make scrolling and loading less smooth.", "JavaScript may be reading layout information immediately after changing the page, forcing the browser to recalculate styles and positions.", "Batch DOM changes, avoid repeatedly reading layout values during updates, and move non-essential work away from the critical loading path."),
    "meta-description": ("Search engines may not have a clear description to show with your page in search results.", "The page is missing a useful meta description or it is not being recognized correctly.", "Add a short, unique description that explains what the page offers and matches its main content."),
    "link-text": ("Some links may not clearly tell visitors or search engines where they lead.", "Links such as 'click here' or empty links provide little context.", "Use short, descriptive link text that makes the destination clear without needing surrounding context."),
    "image-alt": ("Some images do not have helpful alternative text. This can make important visual information harder to understand for people using screen readers.", "Alternative text is often missed when images are added or generated dynamically.", "Add concise descriptions to meaningful images and use empty alt text for purely decorative images."),
    "color-contrast": ("Some text may be difficult to read because its color does not stand out enough from the background.", "Design colors can look fine visually while still being difficult to read for some visitors.", "Increase contrast between text and its background and check important text against accessibility contrast guidelines."),
    "label": ("Some form fields may not clearly tell visitors what information they should enter, especially when assistive technology is used.", "A field can look labelled visually but still be missing a proper connection between the label and the input.", "Give each form field a clear visible label and make sure the label is correctly associated with its input."),
    "is-on-https": ("Your website is not fully using a secure HTTPS connection.", "The site may not have a valid SSL/TLS configuration or some resources may still be served insecurely.", "Use a valid HTTPS certificate and make sure internal resources and redirects use HTTPS."),
}


def score_value(category: dict) -> int | None:
    score = category.get("score")
    return round(float(score) * 100) if isinstance(score, (int, float)) else None


def score_label(score: int | None) -> str:
    if score is None: return "Unavailable"
    if score >= 90: return "Good"
    if score >= 50: return "Needs attention"
    return "Needs work"


def score_class(score: int | None) -> str:
    if score is None: return "neutral"
    if score >= 90: return "good"
    if score >= 50: return "warn"
    return "poor"


def friendly_key(audit: dict) -> str:
    haystack = f"{(audit.get('id') or '').lower()} {(audit.get('title') or '').lower()}"
    for key in FRIENDLY_GUIDANCE:
        if key in haystack: return key
    return ""


def audit_to_issue(audit: dict, category: str) -> dict | None:
    if audit.get("scoreDisplayMode") in {"notApplicable", "manual", "informative"}: return None
    score = audit.get("score")
    if score is None or score >= 0.9: return None
    title = audit.get("title") or audit.get("id", "Website check")
    raw_description = audit.get("description", "")
    details = audit.get("details") or {}
    numeric = details.get("overallSavingsMs") or details.get("overallSavingsBytes")
    severity = "high" if score < 0.5 else "medium" if score < 0.9 else "low"
    guidance = FRIENDLY_GUIDANCE.get(friendly_key(audit))
    if guidance:
        meaning, why, improve = guidance
    else:
        meaning = "This check found something that may be making the website slower, harder to use, or harder to discover."
        why = "Lighthouse detected a condition that did not meet its recommended threshold. The exact cause depends on how the website is built and hosted."
        improve = "Review the affected page or resource, make the recommended change, then run the check again to confirm the improvement."
    return {"id": audit.get("id"), "title": title, "description": meaning, "whyItHappens": why, "howToImprove": improve, "technicalDescription": raw_description, "severity": severity, "category": category, "displayValue": audit.get("displayValue"), "savings": numeric}


def parse_pagespeed(data: dict, url: str, strategy: str) -> dict:
    lighthouse = data.get("lighthouseResult") or {}
    categories = lighthouse.get("categories") or {}
    audits = lighthouse.get("audits") or {}
    scores = {
        "performance": score_value(categories.get("performance", {})),
        "accessibility": score_value(categories.get("accessibility", {})),
        "bestPractices": score_value(categories.get("best-practices", {})),
        "seo": score_value(categories.get("seo", {})),
    }
    core_ids = ["first-contentful-paint", "largest-contentful-paint", "total-blocking-time", "cumulative-layout-shift", "speed-index", "interaction-to-next-paint"]
    vitals = []
    for audit_id in core_ids:
        audit = audits.get(audit_id)
        if not audit: continue
        pct = round(float(audit["score"]) * 100) if isinstance(audit.get("score"), (int, float)) else None
        vitals.append({"id": audit_id, "title": audit.get("title", audit_id), "value": audit.get("displayValue", "—"), "score": audit.get("score"), "numericValue": audit.get("numericValue"), "scoreClass": score_class(pct)})
    issues = []
    for source_category, output_category in {"performance":"performance", "accessibility":"accessibility", "best-practices":"best-practices", "seo":"seo"}.items():
        category = categories.get(source_category) or {}
        seen = set()
        for ref in category.get("auditRefs") or []:
            audit_id = ref.get("id")
            if not audit_id or audit_id in seen: continue
            seen.add(audit_id)
            issue = audit_to_issue(audits.get(audit_id, {}), output_category)
            if issue: issues.append(issue)
    severity_order = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda item: (severity_order[item["severity"]], item["category"], item["title"]))
    performance = scores["performance"]
    failing_vitals = [v for v in vitals if v.get("score") is not None and v["score"] < 0.9 and v["id"] in {"largest-contentful-paint", "total-blocking-time", "cumulative-layout-shift", "interaction-to-next-paint"}]
    return {"url": url, "strategy": strategy, "scores": scores, "overall": performance, "overallLabel": score_label(performance), "overallClass": score_class(performance), "vitals": vitals, "coreWebVitalsFailing": bool(failing_vitals), "issues": issues[:24], "issueCounts": {"critical": sum(1 for i in issues if i["severity"] == "high"), "warnings": sum(1 for i in issues if i["severity"] == "medium"), "passed": sum(1 for i in audits.values() if isinstance(i, dict) and i.get("score") == 1)}, "fetchTime": lighthouse.get("fetchTime"), "finalUrl": lighthouse.get("finalUrl") or url, "pageTitle": lighthouse.get("title") or "", "environment": lighthouse.get("environment", {}), "rawVersion": lighthouse.get("lighthouseVersion")}


def cache_key_for_analysis(url, strategy):
    return hashlib.sha256(f"{normalized_host(url)}|{strategy}".encode()).hexdigest()


def get_cached_analysis(url, strategy):
    row = database.get_cache(cache_key_for_analysis(url, strategy), "analysis_cache")
    return json.loads(row["result_json"]) if row else None


def cache_analysis(result):
    expires = datetime.now(timezone.utc) + timedelta(hours=ANALYSIS_CACHE_HOURS)
    database.set_analysis_cache(cache_key_for_analysis(result["url"], result["strategy"]), result, expires.isoformat())


def _public_host(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    addresses = {info[4][0] for info in infos}
    if not addresses: return False
    for address in addresses:
        try: ip = ipaddress.ip_address(address)
        except ValueError: return False
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified: return False
    return True


def _extract_homepage_signals(website_url: str) -> tuple[str, str, str]:
    current = validate_url(website_url)
    headers = {"User-Agent": "WebPerfDiagnostics/1.0 (+website profiling)"}
    for _ in range(3):
        parsed = urlparse(current)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or not _public_host(parsed.hostname): return "", "", ""
        response = requests.get(current, headers=headers, timeout=(4, 8), allow_redirects=False, stream=True)
        if response.is_redirect or response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            response.close()
            if not location: break
            current = validate_url(urljoin(current, location))
            continue
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "text/html" not in content_type:
            response.close(); return "", "", ""
        chunks, total = [], 0
        try:
            for chunk in response.iter_content(chunk_size=16384, decode_unicode=False):
                if not chunk: continue
                remaining = 500_000 - total
                if remaining <= 0: break
                chunk = chunk[:remaining]; chunks.append(chunk); total += len(chunk)
                if total >= 500_000: break
        finally: response.close()
        html = b"".join(chunks).decode(response.encoding or "utf-8", errors="ignore")
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
        title = unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", title_match.group(1)))).strip() if title_match else ""
        descriptions = []
        for match in re.finditer(r"<meta\b[^>]*(?:name|property)=[\"'](?:description|og:description)[\"'][^>]*>", html, flags=re.I):
            content = re.search(r"content=[\"'](.*?)[\"']", match.group(0), flags=re.I | re.S)
            if content: descriptions.append(unescape(re.sub(r"\s+", " ", content.group(1))).strip())
        body = re.sub(r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>|<noscript\b[^>]*>.*?</noscript>", " ", html, flags=re.I | re.S)
        text = unescape(re.sub(r"<[^>]+>", " ", body)); text = re.sub(r"\s+", " ", text).strip()[:12000]
        return title, " ".join(descriptions)[:1200], text
    return "", "", ""


def classify_website(website_url: str, page_title: str = "", page_description: str = "", page_text: str = "") -> dict:
    host = normalized_host(website_url)
    title = str(page_title or "").strip(); description = str(page_description or "").strip(); text = str(page_text or "").strip()
    haystack = f"{host} {title} {description} {text}".lower().replace("-", " ").replace("_", " ")
    keyword_groups = {
        "Telecommunications": ["telecom", "telecommunications", "mobile network", "mobile service", "mobile operator", "sim card", "5g", "4g", "broadband", "fiber internet", "wireless network", "network services", "network software", "communications technology"],
        "Digital Marketing Agency": ["digital marketing", "seo agency", "marketing agency", "social media marketing", "performance marketing", "seo services", "digital agency", "marketing services", "content marketing", "advertising agency"],
        "Software / SaaS": ["software", "saas", "platform", "cloud software", "enterprise software", "api", "developer platform", "technology company", "software solution", "software platform"],
        "E-commerce / Retail": ["shop", "shopping", "online store", "ecommerce", "e commerce", "buy online", "products", "retail", "cart", "checkout"],
        "Banking / Financial Services": ["bank", "banking", "credit", "loan", "finance", "financial services", "insurance", "investment", "wealth management", "fintech"],
        "Healthcare": ["hospital", "healthcare", "clinic", "medical", "doctor", "health", "pharmacy", "patient", "healthcare provider"],
        "Education": ["school", "college", "university", "education", "learning", "courses", "training", "academy", "students"],
        "Real Estate": ["real estate", "property", "properties", "homes for sale", "apartments", "realty", "property management", "commercial real estate"],
        "Travel / Hospitality": ["hotel", "resort", "travel", "tourism", "flights", "holiday", "vacation", "hospitality", "booking"],
        "Professional Services": ["consulting", "consultancy", "law firm", "accounting", "legal services", "professional services", "advisory", "consulting firm"],
    }
    def has_signal(keyword: str) -> bool:
        phrase = re.sub(r"\s+", " ", keyword.lower().strip())
        if not phrase: return False
        if " " in phrase: return phrase in haystack
        return bool(re.search(rf"\b{re.escape(phrase)}\b", haystack))
    scores = {industry: sum(1 for keyword in keywords if has_signal(keyword)) for industry, keywords in keyword_groups.items()}
    best_industry = max(scores, key=scores.get) if scores else "General Business"
    best_score = scores.get(best_industry, 0)
    if best_score == 0:
        return {"industry": "General Business", "confidence": "low", "reason": "We couldn't identify a specific business category from the public homepage yet. You can change it if needed."}
    confidence = "high" if best_score >= 4 else "medium" if best_score >= 2 else "low"
    source = "the website title, description and homepage content" if (description or text) else "the website title and domain name"
    return {"industry": best_industry, "confidence": confidence, "reason": f"Detected from {source}. No additional search credit was used for classification."}
