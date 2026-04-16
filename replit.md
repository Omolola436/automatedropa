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
