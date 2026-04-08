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

## Subscription System
- **Tiers**: Trial (7 days free), Starter ($29/mo, 3 activities), Growth ($99/mo, 15 activities), Enterprise ($299/mo, unlimited)
- **Feature gating**: Activity limits enforced on add; Audit Logs locked to Enterprise; Version History for Growth+
- **Version History**: Snapshots saved on record edit for Growth/Enterprise users
- **Subscription Management**: Privacy Officers manage user tiers at `/subscription`
- **Pricing Page**: Public page at `/pricing` with full feature comparison table
- **Trial tracking**: 7-day countdown shown in navbar; expired trial blocks new activities
- **Tier badge**: Shown in navbar for all logged-in users
- Key files: `subscription.py` (tier config & helpers), `templates/pricing.html`, `templates/subscription_manage.html`, `templates/version_history.html`

## Environment Variables
- `SESSION_SECRET` - Flask secret key (defaults to dev key if not set)
