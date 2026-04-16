# ROPA Management System

## Overview
A Record of Processing Activities (ROPA) management system to help organizations comply with data protection regulations (GDPR). Features multi-tiered subscription model (Trial, Growth, Enterprise), role-based access control, audit logging, risk assessment, and compliance reporting.

## Tech Stack
- **Backend:** Python 3.11, Flask 3.1+
- **Database:** SQLite (local) via SQLAlchemy ORM; psycopg2-binary available for PostgreSQL in production
- **Auth:** Flask-Login, Werkzeug password hashing, Flask-Dance (OAuth)
- **Data:** Pandas, Openpyxl (Excel import/export)
- **Production Server:** Gunicorn

## Project Structure
- `app.py` — Main Flask application and route definitions (~2400 lines)
- `main.py` — Entry point (`python main.py` for dev)
- `models.py` — SQLAlchemy ORM models (User, ROPARecord, AuditLog, etc.)
- `database.py` — Database initialization and low-level SQL utilities
- `subscription.py` — Subscription tier/feature limit logic
- `audit_logger.py` — Security and event logging
- `automation.py` / `custom_tab_automation.py` — Auto-classification and risk assessment
- `email_utils.py` — Email notification helpers
- `export_utils.py` — Data export functionality
- `file_handler.py` — File upload handling
- `template_generator.py` — ROPA Excel template generation
- `templates/` — Jinja2 HTML templates
- `static/` — CSS, JS, image assets
- `instance/` — SQLite database (`ropa_system.db`)
- `uploads/` — Uploaded files

## Recent Changes
- Country/Jurisdiction dropdown in Step 1 controller now has full A-Z country list
- Legal basis options no longer show article numbers (e.g. "Consent" not "Consent (Art. 6(1)(a))")
- Entity type (Controller/Processor/Joint Controller) changed from clickable cards to clean radio buttons
- DPO Address field changed to a country dropdown (A-Z)
- Step 2 now has a "Mode of Processing" section (Processor/Controller) with conditional processor info form (name, contact, country)
- Step 2 now includes Risk Assessment questions: Likelihood of Breach, Impact of Breach, auto-calculated Risk Score badge, and DPIA trigger alert
- Step 2 footer has Save Activity and Add Another Processing Activity buttons (multi-activity support without restarting from step 1)
- Custom fields (add/view) locked for free trial users - redirects to pricing page
- Risk fields (breach_likelihood, breach_impact, risk_level, dpia_required) now exported to Excel
- Per-step FAQ accordions added to all 3 wizard steps using the provided FAQ content
- Phone number (+44 207 123 4567) added to footer and wizard header

## Running the App
```bash
python main.py
```
Runs on `0.0.0.0:5000`.

## Deployment
- Deployment target: autoscale
- Production command: `gunicorn --bind=0.0.0.0:5000 --reuse-port main:app`

## Environment Variables
- `SESSION_SECRET` — Flask session secret key (defaults to dev key if not set)
