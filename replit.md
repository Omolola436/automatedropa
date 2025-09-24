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
- **Environment**: Replit environment configured
- **Dependencies**: Python packages installed via pyproject.toml
- **Database**: SQLite database with automated schema creation
- **Entry Point**: main.py runs Flask app on 0.0.0.0:5000

## Recent Changes
- 2025-01-24: Initial GitHub import setup for Replit environment

## User Preferences
- Uses SQLite for development database
- Follows Flask best practices for web application structure
- Uses Bootstrap for frontend styling