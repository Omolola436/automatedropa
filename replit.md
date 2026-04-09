# ROPA Management System

## Overview
A Record of Processing Activities (ROPA) management system for GDPR/NDPA compliance. Helps Privacy Officers and Privacy Champions manage data processing records, conduct risk assessments, and maintain audit-ready documentation.

## Tech Stack
- **Language:** Python 3.11
- **Framework:** Flask 3.x
- **ORM:** SQLAlchemy with Flask-SQLAlchemy
- **Database:** SQLite (`instance/ropa_system.db`)
- **Auth:** Flask-Login + Werkzeug password hashing
- **Data Processing:** Pandas + Openpyxl (Excel import/export)
- **Server:** Gunicorn
- **Frontend:** Jinja2 templates + vanilla JS + Bootstrap 5

## Project Structure
- `app.py` — Main Flask application (routes, business logic)
- `main.py` — Entry point (imports app, runs on 0.0.0.0:5000)
- `models.py` — SQLAlchemy database models
- `database.py` — Raw SQLite helpers and initialization
- `subscription.py` — Tier config and feature gates
- `health_engine.py` — Compliance scoring, alerting, ROPA health checks, vendor risk
- `audit_logger.py` — Audit event logging
- `automation.py` — Auto-classification and risk assessment
- `export_utils.py` — Excel/PDF export utilities
- `file_handler.py` — Excel file upload handling
- `template_generator.py` — ROPA template generation
- `utils.py` — Shared utility functions
- `templates/` — Jinja2 HTML templates
- `static/` — CSS, JS, images
- `uploads/` — Uploaded file storage

## Running the App
- Workflow: `gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`
- Port: 5000

## Tier System
| Tier | Price | Key Features |
|------|-------|-------------|
| Trial | Free / 7d | Up to 3 activities, basic template |
| Starter | $29/mo | Export (Excel/PDF), manual entry |
| Growth | $99/mo | Dashboard, version history, basic alerts, risk flagging, multi-user |
| Enterprise | $299/mo | Full automation, compliance scoring, health engine, vendor tracking, audit logs, DPIA triggers, all alerts |

## Key Features by Tier

### Enterprise-Only Features (has_compliance_score, has_health_engine, has_vendor_tracking, has_dpia_triggers)
- **Compliance Score Engine**: Per-record field-completeness score (0–100%). Labels: Excellent (90+), Good (70+), Needs Attention (50+), Critical (<50)
- **ROPA Health Engine**: Automated background checks — detects high-risk activities, missing legal basis, records not reviewed in 12+ months, third-party transfer risks
- **Vendor Tracking**: Track third-party vendors, auto-flag non-adequate countries, contract expiry alerts (30-day warning)
- **Compliance Report**: Per-record and org-wide score dashboard at `/compliance-report`

### Growth + Enterprise Features (has_alerts, has_risk_engine)
- **In-App Notifications**: Bell icon in navbar with unread count. Alert types: 🔴 High-risk, 🟡 Missing legal basis, 🔵 Review due, 🟣 New activity submitted, ⚠️ Third-party risk
- **Notification Centre**: `/notifications` page with mark-read/mark-all-read
- **Risk Flagging**: Risk engine checks during activity creation and editing

## Models
- `User` — Accounts with role (Privacy Officer / Privacy Champion) and subscription tier
- `ROPARecord` — Core ROPA data with 30+ compliance fields
- `Notification` — In-app alerts (Growth+)
- `Vendor` / `VendorActivity` — Third-party tracking (Enterprise)
- `AuditLog` — Immutable event log
- `ROPAVersionHistory` — Change snapshots (Growth+)
- `CustomTab` / `ApprovedCustomField` / `ROPACustomData` — Custom field system
- `ExcelFileData` / `ExcelSheetData` — Uploaded file storage

## Key Routes
- `/` — Landing / dashboard redirect
- `/pricing` — Public pricing page (all 4 tiers)
- `/subscription` — Tier management (Privacy Officer only)
- `/compliance-report` — Compliance score report (Enterprise)
- `/notifications` — In-app notification centre (Growth+)
- `/health-check` (POST) — Run ROPA health engine (Enterprise)
- `/vendors` — Vendor tracking (Enterprise)
- `/vendors/add`, `/vendors/edit/<id>`, `/vendors/delete/<id>` — Vendor CRUD
