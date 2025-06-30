# GDPR ROPA System - Local Setup Guide

A comprehensive GDPR Record of Processing Activities (ROPA) management system using Flask and SQLite for easy local deployment.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Quick Start

1. **Download all project files** to your local directory

2. **Install dependencies:**
```bash
pip install flask flask-login flask-wtf jinja2 openpyxl pandas plotly sqlalchemy werkzeug wtforms
```

3. **Run the application:**
```bash
python app.py
```

4. **Access the system:**
   - Open your browser to `http://localhost:5000`
   - Register as either:
     - **Privacy Champion**: Can create and edit ROPA records in their department
     - **Privacy Officer**: Can approve records and access all system features

## System Features

### Core Functionality
- Complete GDPR ROPA record management
- Role-based access control (Privacy Champions/Officers)  
- Department-based record filtering for Privacy Champions
- Editable records with approval workflow

### Automation Features
- Auto-fill organization data (controller, DPO details)
- Smart data classification based on description keywords
- Processing purpose suggestions by department
- Automatic risk assessment with DPIA alerts
- Security measures auto-suggestions
- Real-time form progress tracking

### Security & Compliance
- Comprehensive audit logging with IP tracking
- Error handling with detailed logging
- Form validation and data integrity checks
- GDPR compliance scoring

### File Management
- Excel/CSV file upload for bulk ROPA import (Privacy Officers only)
- Export to PDF, Excel, and CSV formats
- File validation and error reporting

## User Roles

The system uses a simple two-role structure:

### Privacy Champion
- Create new ROPA records
- Edit records in their department or created by them
- Submit records for Privacy Officer review
- View dashboard with their records
- Cannot access audit logs or user management

### Privacy Officer  
- All Privacy Champion permissions
- Approve/reject ROPA records
- Upload bulk ROPA files
- Access security audit logs (exclusive access)
- Manage users and system settings
- View automation dashboard
- Manage all records across departments

## Database

The system uses SQLite (`ropa_system.db`) which is created automatically on first run. No additional database setup required.

## File Structure

```
├── app.py                 # Main Flask application
├── database.py           # SQLite database functions
├── audit_logger.py       # Security audit logging
├── automation.py         # ROPA automation features
├── file_handler.py       # File upload/processing
├── export_utils.py       # Data export functionality
├── utils.py              # Utility functions
├── templates/            # HTML templates
├── uploads/              # File upload directory
└── ropa_system.db        # SQLite database (created automatically)
```

## Support

The system includes comprehensive error handling and audit logging. Check the audit logs through the Privacy Officer dashboard for troubleshooting.