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
- Horizontal-scrolling Excel-style table with frozen Column A (view & edit)
- Click-to-edit cells in the ROPA data table with save-to-database
- View Saved Data page shows edited files with timestamps
- Email notifications via EmailJS (welcome on signup, upgrade reminder on limit)
- Admin: All Users view (superadmin only, user ID=1 or SUPERADMIN_EMAIL env var)
- Admin: Activity Tracker — full audit log browser with filters
- User activity tracked silently via audit_logs table

## Admin Access
The superadmin panel (All Users + Activity Tracker) is accessible to:
- The first registered user (user ID=1), OR
- Any user whose email matches the `SUPERADMIN_EMAIL` environment variable

## Email (EmailJS)
Configured via secrets: EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, EMAILJS_PUBLIC_KEY
- Welcome/confirmation email sent on every new registration
- Upgrade reminder email sent once when a user hits their activity limit
