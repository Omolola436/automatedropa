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

### Session 3 (Latest)
- **Step 1 simplified**: Removed Processor/Joint Controller radio buttons; Step 1 now shows a static "Data Controller" badge with a hidden input `entity_type=Controller`
- **Step 2 new fields**: Added Special Categories textarea, Representative card (name/contact/address), DPIA Required select, DPIA Outcome textarea (conditionally shown when DPIA Required = Yes or Under Assessment)
- **Risk auto-override**: `dpia_required` is forced to `Yes` when both `breach_likelihood` and `breach_impact` are `High`; otherwise uses the manual `dpia_required_field` selection
- **app.py**: `save_step_data` and `generate_ropa_records` now save `special_categories`, `representative_name/contact/address`, `dpia_outcome`, `dpia_required`, and `controller_country`
- **database.py**: Added ALTER TABLE migrations for `controller_country`, `special_categories`, `representative_name`, `representative_contact`, `representative_address`, `dpia_outcome`
- **export_utils.py**: Added new columns to both data extraction and column mapping (controller_country, special_categories, representative_name/contact/address, dpia_outcome)
- **base.html sidebar**: Custom Fields link is now locked (shows padlock + "Pro" badge linking to /subscription) for trial tier users; visible normally for paid tiers

## Session 2 Changes (Prior)
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
