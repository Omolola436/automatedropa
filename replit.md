# ROPA System

Flask-based ROPA (Records of Processing Activities) management application for GDPR compliance.

## Stack
- **Language:** Python 3.11
- **Framework:** Flask 3.x
- **Database:** SQLite (instance/ropa_system.db via Flask-SQLAlchemy)
- **Auth:** Flask-Login, Flask-Dance (OAuth)
- **ORM:** SQLAlchemy
- **Export:** openpyxl, pandas
- **Production Server:** Gunicorn

## Project Structure
- `app.py` — Main Flask application (routes, views, ~2500 lines)
- `main.py` — Entry point (loads dotenv, runs app on 0.0.0.0:5000)
- `models.py` — SQLAlchemy models
- `database.py` — SQLite helpers and schema initialization
- `templates/` — Jinja2 HTML templates
- `static/` — CSS, JS, logo assets
- `audit_logger.py` — Audit/security event logging
- `automation.py` — AI-assisted classification and risk assessment
- `export_utils.py` — Excel/CSV export utilities
- `file_handler.py` — File upload processing
- `health_engine.py` — Compliance scoring
- `subscription.py` — Tier/subscription management
- `template_generator.py` — ROPA template generation
- `email_utils.py` — Email notifications
- `uploads/` — User-uploaded files
- `instance/` — SQLite database file location

## Running the App
- **Dev:** `python main.py` (port 5000, host 0.0.0.0)
- **Production:** `gunicorn --bind=0.0.0.0:5000 --reuse-port main:app`

## Workflow
- **Start application** — `python main.py`, port 5000 (webview)

## Deployment
- Target: autoscale
- Run: `gunicorn --bind=0.0.0.0:5000 --reuse-port main:app`

## Environment Variables
- `SESSION_SECRET` — Flask session secret key (defaults to dev key if not set)
- Any OAuth credentials for Flask-Dance integrations
