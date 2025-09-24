# GDPR ROPA Management System

## Overview
This is a Flask-based web application for managing GDPR Records of Processing Activities (ROPA). The system provides role-based access control for Privacy Officers and Privacy Champions to manage data processing activities and ensure GDPR compliance.

## Project Architecture
- **Backend**: Flask web framework with SQLAlchemy ORM
- **Database**: SQLite for development (with support for PostgreSQL)
- **Frontend**: HTML templates with Bootstrap styling
- **Authentication**: Flask-Login for session management
- **File Processing**: Pandas and OpenPyXL for Excel file handling

## Core Features
- User registration/authentication with role-based access
- ROPA record creation, editing, and approval workflow
- Custom field management for extended data collection
- Excel file import/export functionality
- Audit logging for compliance tracking
- Risk assessment and DPIA management

## User Roles
- **Privacy Officer**: Administrative access, can approve/reject records, manage users
- **Privacy Champion**: Can create and edit own department's ROPA records

## Current Setup Status
- **Environment**: Fully configured for Replit environment
- **Dependencies**: All Python packages installed and verified working
- **Database**: SQLite database initialized with sample data (3 users, 3 ROPA records)
- **Entry Point**: main.py runs Flask app on 0.0.0.0:5000
- **Workflow**: Flask App workflow configured and running on port 5000
- **Deployment**: Production deployment configured with Gunicorn
- **Frontend**: JavaScript table search functionality fixed

## Recent Changes
- 2025-09-24: Completed GitHub import setup for Replit environment
  - Fixed Flask application workflow configuration
  - Verified all dependencies are properly installed
  - Tested database connectivity and data integrity
  - Fixed JavaScript DOM manipulation error in table search
  - Configured production deployment with Gunicorn on autoscale
  - Verified web interface loads correctly with no console errors

## User Preferences
- Uses SQLite for development database
- Follows Flask best practices for web application structure
- Uses Bootstrap for frontend styling