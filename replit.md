# ROPA Management System

## Overview
A Record of Processing Activities (ROPA) management system for GDPR compliance. Helps Privacy Officers and Privacy Champions manage data processing records, conduct risk assessments, and maintain audit-ready documentation.

## Tech Stack
- **Language:** Python 3.11
- **Framework:** Flask 3.x
- **ORM:** SQLAlchemy with Flask-SQLAlchemy
- **Database:** SQLite (`instance/ropa_system.db`)
- **Auth:** Flask-Login + Werkzeug password hashing
- **Data Processing:** Pandas + Openpyxl (Excel import/export)
- **Server:** Gunicorn
- **Frontend:** Jinja2 templates + vanilla JS + custom CSS

## Project Structure
- `app.py` — Main Flask application (routes, business logic)
- `main.py` — Entry point (imports app, runs on 0.0.0.0:5000)
- `models.py` — SQLAlchemy database models
- `database.py` — Raw SQLite helpers and initialization
- `audit_logger.py` — Audit event logging
- `automation.py` — Auto-classification and risk assessment
- `export_utils.py` — Excel/PDF export utilities
- `file_handler.py` — Excel file upload handling
- `template_generator.py` — ROPA template generation
- `subscription.py` — Subscription/trial management
- `utils.py` — Shared utility functions
- `templates/` — Jinja2 HTML templates
- `static/` — CSS, JS, images
- `uploads/` — Uploaded file storage

## Running the App
- Workflow: `gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`
- Port: 5000

## Key Features
- User roles: Privacy Officer (admin) and Privacy Champion (department)
- ROPA record creation, editing, review, and approval workflow
- Excel import/export
- Audit logging
- Subscription model with 7-day free trial
- Custom tabs and fields on ROPA records
- Auto-classification and risk assessment
