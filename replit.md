# ROPA Management System

## Overview
A Records of Processing Activities (ROPA) management system to help organizations manage data processing activities in compliance with GDPR and other privacy regulations.

## Tech Stack
- **Backend:** Python 3.11 + Flask
- **Frontend:** Jinja2 server-side rendered HTML templates + vanilla CSS/JS
- **Database:** SQLAlchemy ORM with SQLite (file: `instance/ropa_system.db`)
- **Auth:** Flask-Login + Werkzeug password hashing
- **Data:** Pandas + OpenPyXL for Excel import/export

## Project Structure
- `app.py` — Main Flask application and route definitions (~2100 lines)
- `main.py` — Entry point (runs on `0.0.0.0:5000`)
- `models.py` — SQLAlchemy database models
- `database.py` — DB initialization and connection helpers
- `automation.py` — Auto-classification and risk assessment
- `export_utils.py` — Excel/ROPA export utilities
- `file_handler.py` — Uploaded file processing
- `health_engine.py` — Compliance scoring
- `subscription.py` — Tier-based feature gating (Trial/Growth/Enterprise)
- `audit_logger.py` — Security and user event logging
- `templates/` — Jinja2 HTML templates
- `static/` — CSS, JS, and image assets
- `uploads/` — User-uploaded files (runtime)
- `instance/` — SQLite database (runtime)

## Running the App
```bash
python main.py
```
Runs on `http://0.0.0.0:5000`

## Deployment
Configured for Replit autoscale deployment via Gunicorn:
```
gunicorn --bind=0.0.0.0:5000 --reuse-port main:app
```

## Key Features
- Multi-role dashboards: Privacy Officers (admins) and Privacy Champions (contributors)
- Wizard-based ROPA record creation
- Excel import/export
- Subscription tiers (Trial, Growth, Enterprise)
- Compliance scoring and health checks
- Audit logging
- Vendor management
- Custom tabs/fields per organization
