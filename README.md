# WebPerf Diagnostics v20

A Flask website audit and premium competitor benchmarking application.

## Project structure

```text
app.py                    Flask setup, security hooks, shared template state
config.py                 .env loading and application configuration
database.py               SQLite persistence
services/
  web_utils.py            URL, host and CSRF helpers
  analysis.py             PageSpeed parsing, cache, industry classification
  competitors.py          Competitor discovery and relevance filtering
  auth.py                 Authentication/access decorators
  emailer.py              SMTP contact email
routes/
  pages.py                Public pages
  auth.py                 Registration/login/logout
  admin.py                Admin panel
  api_analysis.py         Audit, profile and competitor PageSpeed APIs
  api_competitors.py      Competitor discovery API
  api_payments.py         Razorpay APIs
  api_contact.py          Contact API
  system.py               Health, robots, sitemap and llms routes
static/
templates/
```

## Run

```powershell
.\run.bat
```

After changing `.env`, fully stop and restart the server. `/api/health` reports which integrations are configured without exposing secrets.
