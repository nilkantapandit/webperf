"""Central application configuration loaded from .env."""
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
COMPETITOR_PROVIDER = os.getenv("COMPETITOR_PROVIDER", "serper").strip().lower()
GOOGLE_PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
SERPER_SEARCH_URL = "https://google.serper.dev/search"

PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
API_KEY = os.getenv("GOOGLE_PAGESPEED_API_KEY", "").strip()
DEFAULT_STRATEGY = os.getenv("PAGESPEED_STRATEGY", "mobile").strip().lower()

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").strip().lower() == "true"
CONTACT_TO_EMAIL = os.getenv("CONTACT_TO_EMAIL", "").strip()
CONTACT_FROM_EMAIL = os.getenv("CONTACT_FROM_EMAIL", SMTP_USERNAME).strip()
SITE_URL = os.getenv("SITE_URL", "https://www.example.com").strip().rstrip("/")
SITE_NAME = os.getenv("SITE_NAME", "WebPerf Diagnostics").strip()
SITE_DESCRIPTION = os.getenv("SITE_DESCRIPTION", "Free website speed, SEO, accessibility and best-practices checker with plain-English recommendations.").strip()

COMPETITOR_CACHE_DAYS = int(os.getenv("COMPETITOR_CACHE_DAYS", "7"))
ANALYSIS_CACHE_HOURS = int(os.getenv("ANALYSIS_CACHE_HOURS", "6"))

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()
RAZORPAY_API_URL = "https://api.razorpay.com/v1"
PREMIUM_AMOUNT_MINOR = int(os.getenv("PREMIUM_AMOUNT_MINOR", "9900"))
PREMIUM_CURRENCY = os.getenv("PREMIUM_CURRENCY", "INR").strip().upper()
PREMIUM_DISPLAY_PRICE = os.getenv("PREMIUM_DISPLAY_PRICE", "₹99").strip()
PREMIUM_NAME = os.getenv("PREMIUM_NAME", "Competitor Report").strip()
DEV_PREMIUM_UNLOCK = os.getenv("DEV_PREMIUM_UNLOCK", "false").strip().lower() == "true"

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
LEGAL_CONTACT_EMAIL = os.getenv("LEGAL_CONTACT_EMAIL", CONTACT_TO_EMAIL or CONTACT_FROM_EMAIL or "hello@example.com").strip()
BUSINESS_NAME = os.getenv("BUSINESS_NAME", SITE_NAME).strip()
BUSINESS_ADDRESS = os.getenv("BUSINESS_ADDRESS", "Update this address before launch.").strip()

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-change-this-secret")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
DATABASE_PATH = os.getenv("DATABASE_PATH", "").strip()
PORT = int(os.getenv("PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
