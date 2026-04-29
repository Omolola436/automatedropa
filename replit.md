# DataProcess Flow (ROPA System)

Flask-based ROPA (Records of Processing Activities) management application by 3Consulting.

## Stack
- Python 3.11
- Flask 3.x with Flask-Login, Flask-SQLAlchemy, Flask-Dance
- SQLite database (`ropa_system.db`)
- Pandas / openpyxl for export utilities
- Gunicorn for production

## Project Layout
- `main.py` — entry point that loads `.env` and runs the Flask app on `0.0.0.0:5000`.
- `app.py` — main Flask application (routes, login, config).
- `models.py` — SQLAlchemy models.
- `database.py` / `fix_*.py` / `migrate_db.py` — database initialization and migrations.
- `automation.py`, `health_engine.py`, `audit_logger.py`, `subscription.py` — business logic.
- `template_generator.py`, `export_utils.py`, `file_handler.py`, `email_utils.py`, `utils.py` — supporting modules.
- `templates/`, `static/` — Jinja templates and static assets.
- `uploads/` — user file uploads.

## Replit Setup
- Workflow `Start application` runs `python main.py` on port 5000 (webview).
- Deployment target: `autoscale` running `gunicorn --bind=0.0.0.0:5000 --reuse-port main:app`.

## Environment Variables (optional)
- `SESSION_SECRET` — Flask session secret (defaults to a dev key if unset).
- Email/OAuth credentials are read from environment via `python-dotenv` if a `.env` file is present.
