# GDPR ROPA Management System

## Overview
A GDPR Record of Processing Activities (ROPA) management system for organizations to document and manage their data processing activities in compliance with GDPR requirements.

## Tech Stack
- **Backend:** Python 3.11 with Flask web framework
- **Database:** SQLite (via SQLAlchemy ORM + direct sqlite3)
- **Frontend:** Jinja2 HTML templates, Bootstrap CSS, vanilla JavaScript
- **Auth:** Flask-Login with Werkzeug password hashing
- **Data:** Pandas + Openpyxl for Excel import/export
- **Production Server:** Gunicorn

## Project Structure
- `app.py` - Main Flask application (routes, logic)
- `main.py` - Entry point (runs Flask dev server on 0.0.0.0:5000)
- `models.py` - SQLAlchemy models (User, ROPARecord, AuditLog, etc.)
- `database.py` - SQLite initialization and helper functions
- `automation.py` - Auto-classification, risk assessment
- `export_utils.py` - Excel/CSV export utilities
- `file_handler.py` - File upload processing
- `template_generator.py` - ROPA template generation
- `templates/` - Jinja2 HTML templates
- `static/` - CSS, JS, images
- `instance/` - SQLite database file (ropa_system.db)
- `uploads/` - Uploaded files directory

## Running the Application
- **Development:** `python main.py` (port 5000, debug mode)
- **Production:** `gunicorn --bind=0.0.0.0:5000 --reuse-port main:app`

## Key Features
- User roles: Privacy Champion (department) and Privacy Officer (admin)
- ROPA record CRUD with custom fields/tabs
- Auto-classification of personal data categories
- Privacy risk assessment (High/Medium/Low)
- Excel import/export
- Comprehensive audit logging
- Session-based authentication with consent tracking

## Environment Variables
- `SESSION_SECRET` - Flask secret key (defaults to dev key if not set)
