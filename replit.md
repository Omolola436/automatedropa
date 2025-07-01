# GDPR ROPA System

## Overview

This is a comprehensive GDPR Record of Processing Activities (ROPA) management system built with Flask and SQLite. The system enables organizations to manage their data processing activities in compliance with GDPR requirements through a web-based interface with role-based access control, automated features, and comprehensive audit logging.

## System Architecture

The application follows a traditional Flask MVC architecture with a modular design:

- **Web Framework**: Flask with server-side rendering using Jinja2 templates
- **Database**: SQLite for data persistence with potential for PostgreSQL migration
- **Frontend**: Bootstrap 5 with custom CSS and JavaScript for responsive UI
- **Authentication**: Session-based authentication with role-based access control
- **File Processing**: Pandas for Excel/CSV import/export functionality

## Key Components

### Backend Architecture
- **Flask Application** (`app.py`): Main application entry point with route handlers
- **Database Layer** (`database.py`): SQLite operations and data models
- **Authentication**: Session-based user management with password hashing
- **File Processing** (`file_handler.py`): Upload and processing of ROPA data files
- **Export System** (`export_utils.py`): Multi-format data export (Excel, CSV, PDF)
- **Audit System** (`audit_logger.py`): Comprehensive activity logging for compliance
- **Automation Engine** (`automation.py`): Smart suggestions and auto-classification

### Frontend Architecture
- **Template System**: Jinja2 templates with Bootstrap 5 for responsive design
- **Static Assets**: Custom CSS and JavaScript for enhanced user experience
- **Form Handling**: Multi-step ROPA forms with progress tracking
- **Dashboard**: Role-specific dashboards with statistics and charts

### Data Models
The system uses SQLite with the following core tables:
- **users**: User accounts with roles and departments
- **ropa_records**: GDPR processing activity records with comprehensive fields
- **audit_logs**: Security and activity audit trail

### Role-Based Access Control
- **Privacy Champions**: Create and manage department-specific ROPA records
- **Privacy Officers**: Full system access including approvals and audit logs
- **Department-based filtering**: Users see only relevant records based on their role

## Data Flow

1. **User Registration/Login**: Users register with role assignment and authenticate via sessions
2. **ROPA Creation**: Step-by-step form completion with automated suggestions
3. **Approval Workflow**: Privacy Officers review and approve/reject submissions
4. **File Import/Export**: Bulk operations using Excel/CSV templates
5. **Audit Trail**: All activities logged with IP addresses and timestamps

## External Dependencies

### Python Libraries
- **Flask**: Web framework and routing
- **Pandas**: Data manipulation and file processing
- **OpenPyXL**: Excel file handling
- **Werkzeug**: Security utilities and file handling
- **SQLAlchemy**: Database abstraction (prepared for PostgreSQL migration)
- **Plotly**: Dashboard visualizations and charts

### Frontend Libraries
- **Bootstrap 5**: UI framework with dark theme support
- **Font Awesome**: Icon library for enhanced UX
- **jQuery**: DOM manipulation and AJAX functionality

### File Processing
- **Excel/CSV Import**: Automated parsing with error handling
- **Template Generation**: Dynamic Excel template creation
- **Multi-format Export**: PDF, Excel, and CSV export options

## Deployment Strategy

The system is designed for flexible deployment:

### Local Development
- SQLite database for easy setup
- Flask development server
- No external dependencies required

### Production Considerations
- Database migration path to PostgreSQL using SQLAlchemy
- Environment-based configuration
- Session secret management
- File upload security measures
- Audit log retention policies

### Security Features
- Password hashing with Werkzeug
- Session-based authentication
- CSRF protection ready
- IP address logging
- File upload validation
- SQL injection prevention

## Changelog

- June 30, 2025. Initial setup
- June 30, 2025. Completed Replit migration:
  - Migrated from legacy Flask structure to modern Flask-SQLAlchemy
  - Removed all hardcoded demo accounts - users must register
  - Implemented proper role-based access with Flask-Login
  - Fixed approval workflow: Privacy Champions save drafts/submit for review → Privacy Officers approve
  - Added downloadable templates and bulk upload functionality
  - Maintained audit logging and security features
  - Fresh SQLite database with no pre-existing accounts
- July 1, 2025. Enhanced Custom Tab Automation:
  - Implemented dynamic custom field system with approval workflow
  - Added automatic integration of approved fields into existing ROPA records
  - Custom fields auto-included in downloadable templates
  - Enhanced export/import functionality for round-trip editing
  - Organized custom fields into 9 categories: Basic Info, Controller, DPO, Processor, Processing, Data, Recipients, Retention, Security
  - Fixed dashboard card clickability and improved UI for light theme
  - Removed PostgreSQL references, using SQLite only

## User Preferences

Preferred communication style: Simple, everyday language.