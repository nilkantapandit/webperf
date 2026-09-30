# WebPerf Diagnostics v20

## Changes
- Refactored the ~950-line `app.py` into a small application entry point plus focused route/service modules.
- Kept existing Flask endpoint names unchanged so templates and frontend JavaScript do not need a route migration.
- Added `config.py` as the single environment/configuration layer.
- Split business logic into:
  - `services/web_utils.py` — URL, host and CSRF helpers
  - `services/analysis.py` — PageSpeed parsing, caching and automatic industry classification
  - `services/competitors.py` — Serper/Brave/Google Places discovery and relevance filtering
  - `services/auth.py` — current user and access decorators
  - `services/emailer.py` — SMTP contact mail
- Split HTTP routes into focused modules under `routes/`.
- Competitor discovery cache key bumped to v4 and backend now retains up to 12 filtered competitors so the existing frontend "Show more results" control can actually reveal more than the first six when available.
- Slightly increased comparison typography for readability without changing the table/grid dimensions.

## Important
- Existing `.env` remains in the project directory.
- Existing database behavior is preserved; set `DATABASE_PATH` in `.env` if you want a persistent database outside each extracted application folder.
- Do not delete an existing working `webperf.db` until you have confirmed which database v20 is using.
