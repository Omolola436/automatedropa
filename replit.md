# ROPA Management System

## Overview
A Record of Processing Activities (ROPA) Management System designed to help organizations manage their data processing records in compliance with data protection regulations (e.g., GDPR).

## Tech Stack
- **Backend**: Python 3.11 + Flask
- **Database**: SQLite (stored in `instance/ropa_system.db`)
- **ORM**: SQLAlchemy via Flask-SQLAlchemy
- **Auth**: Flask-Login with Werkzeug password hashing
- **Data Processing**: Pandas + Openpyxl for Excel import/export
- **Production Server**: Gunicorn
- **Templates**: Jinja2 (server-side rendering)

## Features
- User roles: Privacy Officers (admins) and Privacy Champions (contributors)
- ROPA Wizard: step-by-step tool to create processing activity records
- Excel upload/export for ROPA data
- Compliance scoring and risk health engine
- Subscription tiers: Trial, Growth, Enterprise
- Comprehensive audit logging

## Project Structure
- `app.py` — Main Flask application, routes, and configuration
- `main.py` — Development server entry point (runs on 0.0.0.0:5000)
- `models.py` — SQLAlchemy database models
- `database.py` — Database initialization and raw SQLite utilities
- `automation.py` — Risk assessment and auto-classification logic
- `health_engine.py` — Compliance scoring and health checks
- `export_utils.py` — Excel and data export logic
- `file_handler.py` — Uploaded file processing
- `template_generator.py` — ROPA template generation
- `subscription.py` — Feature tier management
- `audit_logger.py` — Security and event audit logging
- `email_utils.py` — Email notifications
- `templates/` — Jinja2 HTML templates
- `static/` — CSS and JavaScript assets
- `instance/` — SQLite database file
- `uploads/` — Uploaded files directory

## Running the App
- Development: `python main.py` (runs on port 5000)
- Production: `gunicorn --bind=0.0.0.0:5000 --reuse-port main:app`

## Environment Variables
- `SESSION_SECRET` — Flask secret key (defaults to dev key if not set)
- `SUPERADMIN_EMAIL` — Email address for the platform superadmin
