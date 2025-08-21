import os
import logging
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import tempfile
from datetime import datetime
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///ropa_system.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Import models and initialize db
from models import db
import models

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

with app.app_context():
    # Initialize database with proper schema
    from database import init_database
    init_database()
    # Create all SQLAlchemy tables
    db.create_all()

# Import utility functions after app context
from automation import auto_classify_data, suggest_processing_purpose, assess_risk, suggest_security_measures
from utils import get_predefined_options, validate_required_fields
from database import get_db_connection, get_user_department
from export_utils import generate_export
from file_handler import process_uploaded_file
from template_generator import generate_ropa_template

@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))

# Import enhanced audit logging functions
from audit_logger import log_audit_event, log_security_event, get_client_ip

@app.route('/')
def index():
    """Redirect to appropriate dashboard based on user role"""
    if current_user.is_authenticated:
        if current_user.role == 'Privacy Officer':
            return redirect(url_for('privacy_officer_dashboard'))
        else:
            return redirect(url_for('privacy_champion_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = models.User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            log_audit_event('Login Success', email, 'User logged in successfully')
            return redirect(url_for('index'))
        else:
            log_audit_event('Login Failed', email, 'Failed login attempt')
            flash('Invalid email or password', 'error')

    return render_template('login.html')

@app.route('/register')
def register():
    """Redirect to login - public registration disabled"""
    flash('Registration is restricted. Please contact your Privacy Officer for account access.', 'info')
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    log_audit_event('Logout', current_user.email, 'User logged out')
    logout_user()
    return redirect(url_for('login'))

@app.route('/privacy-champion-dashboard')
@login_required
def privacy_champion_dashboard():
    """Privacy Champion dashboard"""
    if current_user.role not in ['Privacy Champion', 'Privacy Officer']:
        abort(403)

    # Get user's ROPA records
    records = models.ROPARecord.query.filter_by(created_by=current_user.id).all()

    # Statistics
    total_records = len(records)
    draft_records = len([r for r in records if r.status == 'Draft'])
    pending_records = len([r for r in records if r.status == 'Under Review'])
    approved_records = len([r for r in records if r.status == 'Approved'])

    return render_template('privacy_champion_dashboard.html', 
                         records=records,
                         total_records=total_records,
                         draft_records=draft_records,
                         pending_records=pending_records,
                         approved_records=approved_records)

@app.route('/privacy-officer-dashboard')
@login_required
def privacy_officer_dashboard():
    """Privacy Officer dashboard"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    # Get all ROPA records
    all_records = models.ROPARecord.query.all()
    pending_records = models.ROPARecord.query.filter_by(status='Under Review').all()
    draft_records = models.ROPARecord.query.filter_by(status='Draft').all()

    # Statistics
    total_records = len(all_records)
    pending_count = len(pending_records)
    draft_count = len(draft_records)
    approved_records = len([r for r in all_records if r.status == 'Approved'])

    return render_template('privacy_officer_dashboard.html',
                         all_records=all_records,
                         pending_records=pending_records,
                         draft_records=draft_records,
                         total_records=total_records,
                         pending_count=pending_count,
                         draft_count=draft_count,
                         approved_records=approved_records)

@app.route('/add-activity', methods=['GET', 'POST'])
@login_required
def add_activity():
    """Add new ROPA activity"""
    if request.method == 'POST':
        # Create new ROPA record
        record = models.ROPARecord(
            processing_activity_name=request.form['processing_activity_name'],
            category=request.form.get('category'),
            description=request.form.get('description'),
            department_function=request.form.get('department_function'),
            controller_name=request.form.get('controller_name'),
            controller_contact=request.form.get('controller_contact'),
            controller_address=request.form.get('controller_address'),
            processing_purpose=request.form.get('processing_purpose'),
            legal_basis=request.form.get('legal_basis'),
            data_categories=request.form.get('data_categories'),
            data_subjects=request.form.get('data_subjects'),
            retention_period=request.form.get('retention_period'),
            security_measures=request.form.get('security_measures'),
            created_by=current_user.id
        )

        # Check the action type from the form
        action = request.form.get('action', 'submit')
        if action == 'draft':
            record.status = 'Draft'
            message = 'ROPA record saved as draft'
        elif action == 'submit':
            record.status = 'Under Review'
            message = 'ROPA record submitted for review'
        elif action == 'approve' and current_user.role == 'Privacy Officer':
            record.status = 'Approved'
            message = 'ROPA record created and approved'
        else:
            record.status = 'Under Review'
            message = 'ROPA record submitted for review'

        db.session.add(record)
        db.session.commit()

        # Process custom tabs if any were created
        custom_tab_counter = 1
        while f'custom_tab_name_{custom_tab_counter}' in request.form:
            tab_name = request.form.get(f'custom_tab_name_{custom_tab_counter}')
            tab_description = request.form.get(f'custom_tab_description_{custom_tab_counter}')
            tab_processes = request.form.get(f'custom_tab_processes_{custom_tab_counter}')

            if tab_name and tab_processes:  # Only create if required fields are filled
                custom_tab = models.CustomTab(
                    tab_name=tab_name,
                    tab_description=tab_description,
                    processes=tab_processes,
                    created_by=current_user.id,
                    ropa_record_id=record.id
                )
                db.session.add(custom_tab)

            custom_tab_counter += 1

        db.session.commit()

        log_audit_event('ROPA Created', current_user.email, f'Created ROPA record: {record.processing_activity_name}')
        flash(message, 'success')
        return redirect(url_for('privacy_champion_dashboard'))

    options = get_predefined_options()
    return render_template('add_activity.html', options=options)

@app.route('/edit-activity/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit_activity(record_id):
    """Edit existing ROPA activity"""
    record = models.ROPARecord.query.get_or_404(record_id)

    # Check permissions
    if current_user.role == 'Privacy Champion' and record.created_by != current_user.id:
        abort(403)

    if request.method == 'POST':
        # Update record fields
        record.processing_activity_name = request.form['processing_activity_name']
        record.category = request.form.get('category')
        record.description = request.form.get('description')
        record.department_function = request.form.get('department_function')
        record.controller_name = request.form.get('controller_name')
        record.controller_contact = request.form.get('controller_contact')
        record.controller_address = request.form.get('controller_address')
        record.processing_purpose = request.form.get('processing_purpose')
        record.legal_basis = request.form.get('legal_basis')
        record.data_categories = request.form.get('data_categories')
        record.data_subjects = request.form.get('data_subjects')
        record.retention_period = request.form.get('retention_period')
        record.security_measures = request.form.get('security_measures')
        record.updated_at = datetime.utcnow()

        # Check if saving as draft or submitting for review
        if 'save_draft' in request.form:
            record.status = 'Draft'
            message = 'ROPA record updated and saved as draft'
        else:
            record.status = 'Under Review'
            message = 'ROPA record updated and submitted for review'

        db.session.commit()

        log_audit_event('ROPA Updated', current_user.email, f'Updated ROPA record: {record.processing_activity_name}')
        flash(message, 'success')
        return redirect(url_for('privacy_champion_dashboard'))

    options = get_predefined_options()
    return render_template('ropa_edit.html', record=record, options=options)

@app.route('/view-activity/<int:record_id>')
@login_required
def view_activity(record_id):
    """View ROPA activity details"""
    record = models.ROPARecord.query.get_or_404(record_id)

    # Check permissions
    if current_user.role == 'Privacy Champion' and record.created_by != current_user.id:
        abort(403)

    # Get custom tabs for this record
    custom_tabs = models.CustomTab.query.filter_by(ropa_record_id=record.id).all()
    return render_template('ropa_view.html', record=record, custom_tabs=custom_tabs)

@app.route('/update-status/<int:record_id>/<status>', methods=['POST'])
@login_required
def update_status(record_id, status):
    """Update ROPA record status (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    record = models.ROPARecord.query.get_or_404(record_id)
    record.status = status
    record.reviewed_by = current_user.id
    record.reviewed_at = datetime.utcnow()

    if 'comments' in request.form:
        record.review_comments = request.form['comments']

    # If approved, integrate custom activities into main ROPA record
    if status == 'Approved':
        integrate_custom_activities(record)

    db.session.commit()

    log_audit_event('ROPA Status Updated', current_user.email, f'Updated status of ROPA {record.processing_activity_name} to {status}')
    flash(f'ROPA record status updated to {status}', 'success')
    return redirect(url_for('privacy_officer_dashboard'))

@app.route('/delete-activity/<int:record_id>', methods=['POST'])
@login_required
def delete_activity(record_id):
    """Delete ROPA activity"""
    record = models.ROPARecord.query.get_or_404(record_id)

    # Check permissions
    if current_user.role == 'Privacy Champion' and record.created_by != current_user.id:
        abort(403)

    record_name = record.processing_activity_name
    db.session.delete(record)
    db.session.commit()

    log_audit_event('ROPA Deleted', current_user.email, f'Deleted ROPA record: {record_name}')
    flash('ROPA record deleted successfully', 'success')
    return redirect(url_for('privacy_champion_dashboard'))

@app.route('/download-template')
@login_required
def download_template():
    """Download ROPA template (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    try:
        template_path = generate_ropa_template()
        log_audit_event('Template Downloaded', current_user.email, 'Downloaded ROPA template')
        return send_file(template_path, as_attachment=True, download_name='ROPA_Template.xlsx')
    except Exception as e:
        flash(f'Error generating template: {str(e)}', 'error')
        return redirect(url_for('privacy_officer_dashboard'))

@app.route('/upload-file', methods=['GET', 'POST'])
@login_required
def upload_file():
    """Upload and process ROPA file (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            try:
                result = process_uploaded_file(file, current_user.email)
                log_audit_event('File Uploaded', current_user.email, f'Uploaded and processed file: {filename}')
                flash(f'File processed successfully: {result}', 'success')
            except Exception as e:
                log_audit_event('File Upload Error', current_user.email, f'Error processing file {filename}: {str(e)}')
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Invalid file type. Please upload Excel or CSV files only.', 'error')

    return render_template('file_upload.html')

@app.route('/export-data')
@login_required
def export_data():
    """Export ROPA data"""
    export_format = request.args.get('format', 'excel')
    include_drafts = request.args.get('include_drafts') == 'true'
    include_rejected = request.args.get('include_rejected') == 'true'

    try:
        file_path, filename = generate_export(current_user.email, current_user.role, export_format, include_drafts, include_rejected)
        log_audit_event('Data Exported', current_user.email, f'Exported data in {export_format} format')
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        flash(f'Error generating export: {str(e)}', 'error')
        if current_user.role == 'Privacy Officer':
            return redirect(url_for('privacy_officer_dashboard'))
        else:
            return redirect(url_for('privacy_champion_dashboard'))

@app.route('/audit-logs')
@login_required
def audit_logs():
    """View audit logs (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        log_security_event('Unauthorized Access', current_user.email, 
                          f'Attempted to access audit logs without Privacy Officer role')
        abort(403)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    # Use enhanced audit log retrieval
    from audit_logger import get_audit_logs
    logs_data = get_audit_logs(page=page, per_page=per_page)

    log_audit_event('Audit Logs Viewed', current_user.email, 
                   f'Accessed audit logs page {page}')

    return render_template('audit_logs.html', logs=logs_data)

@app.route('/user-management')
@login_required
def user_management():
    """User management page (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    users = models.User.query.all()
    return render_template('user_management.html', users=users)

@app.route('/add-user', methods=['POST'])
@login_required
def add_user():
    """Add new user (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    department = request.form['department']

    # Validation
    if not all([email, password, role, department]):
        flash('All fields are required', 'error')
        return redirect(url_for('user_management'))

    if len(password) < 6:
        flash('Password must be at least 6 characters long', 'error')
        return redirect(url_for('user_management'))

    if role not in ['Privacy Champion', 'Privacy Officer']:
        flash('Invalid role selected', 'error')
        return redirect(url_for('user_management'))

    # Check if user already exists
    if models.User.query.filter_by(email=email).first():
        flash('Email already registered', 'error')
        return redirect(url_for('user_management'))

    try:
        # Create new user
        user = models.User(
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            department=department
        )
        db.session.add(user)
        db.session.commit()

        log_audit_event('User Created by Admin', current_user.email, f'Created user: {email} with role: {role}')
        flash(f'User {email} created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {str(e)}', 'error')

    return redirect(url_for('user_management'))

@app.route('/edit-user/<int:user_id>', methods=['POST'])
@login_required
def edit_user(user_id):
    """Edit user (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    user = models.User.query.get_or_404(user_id)

    # Don't allow editing own account through this interface
    if user.id == current_user.id:
        flash('Cannot edit your own account through this interface', 'error')
        return redirect(url_for('user_management'))

    email = request.form['email']
    role = request.form['role']
    department = request.form['department']
    new_password = request.form.get('new_password', '').strip()

    # Validation
    if not all([email, role, department]):
        flash('Email, role, and department are required', 'error')
        return redirect(url_for('user_management'))

    if role not in ['Privacy Champion', 'Privacy Officer']:
        flash('Invalid role selected', 'error')
        return redirect(url_for('user_management'))

    # Check if email is taken by another user
    existing_user = models.User.query.filter_by(email=email).first()
    if existing_user and existing_user.id != user.id:
        flash('Email already taken by another user', 'error')
        return redirect(url_for('user_management'))

    try:
        old_email = user.email
        user.email = email
        user.role = role
        user.department = department

        if new_password:
            if len(new_password) < 6:
                flash('Password must be at least 6 characters long', 'error')
                return redirect(url_for('user_management'))
            user.password_hash = generate_password_hash(new_password)

        db.session.commit()

        log_audit_event('User Updated by Admin', current_user.email, 
                       f'Updated user: {old_email} -> {email}, role: {role}')
        flash(f'User {email} updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user: {str(e)}', 'error')

    return redirect(url_for('user_management'))

@app.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete user (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    user = models.User.query.get_or_404(user_id)

    # Don't allow deleting own account
    if user.id == current_user.id:
        flash('Cannot delete your own account', 'error')
        return redirect(url_for('user_management'))

    try:
        user_email = user.email
        db.session.delete(user)
        db.session.commit()

        log_audit_event('User Deleted by Admin', current_user.email, f'Deleted user: {user_email}')
        flash(f'User {user_email} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')

    return redirect(url_for('user_management'))

# API endpoints for automation features
@app.route('/api/auto-classify', methods=['POST'])
@login_required
def api_auto_classify():
    """API endpoint for auto-classification"""
    data = request.get_json()
    description = data.get('description', '')
    classification = auto_classify_data(description)
    return jsonify({'classification': classification})

@app.route('/api/suggest-purpose', methods=['POST'])
@login_required
def api_suggest_purpose():
    """API endpoint for purpose suggestion"""
    data = request.get_json()
    department = data.get('department', '')
    category = data.get('category', '')
    suggestion = suggest_processing_purpose(department, category)
    return jsonify({'suggestion': suggestion})

@app.route('/api/assess-risk', methods=['POST'])
@login_required
def api_assess_risk():
    """API endpoint for risk assessment"""
    data = request.get_json()
    data_categories = data.get('data_categories', '')
    special_categories = data.get('special_categories', '')
    risk_assessment = assess_risk(data_categories, special_categories)
    return jsonify({'risk_assessment': risk_assessment})

@app.route('/api/suggest-security', methods=['POST'])
@login_required
def api_suggest_security():
    """API endpoint for security measures suggestion"""
    data = request.get_json()
    data_categories = data.get('data_categories', '')
    risk_level = data.get('risk_level', 'Medium')
    suggestions = suggest_security_measures(data_categories, risk_level)
    return jsonify({'suggestions': suggestions})

def integrate_custom_activities(record):
    """Integrate approved custom activities into main ROPA record"""
    import json

    # Get all custom tabs for this record
    custom_tabs = models.CustomTab.query.filter_by(ropa_record_id=record.id).all()

    if not custom_tabs:
        return

    # Collect all processes from custom tabs
    all_processes = []
    for tab in custom_tabs:
        if tab.processes:
            try:
                processes = json.loads(tab.processes)
                if isinstance(processes, list):
                    all_processes.extend(processes)
            except (json.JSONDecodeError, TypeError):
                continue

    if not all_processes:
        return

    # Merge process information into main ROPA record
    # Collect unique purposes, data categories, etc.
    purposes = set()
    data_categories = set()
    recipients = set()
    security_measures = set()

    # Parse existing values
    if record.processing_purpose:
        purposes.add(record.processing_purpose.strip())
    if record.data_categories:
        data_categories.update([cat.strip() for cat in record.data_categories.split(';') if cat.strip()])
    if record.recipients:
        recipients.update([rec.strip() for rec in record.recipients.split(';') if rec.strip()])
    if record.security_measures:
        security_measures.update([sec.strip() for sec in record.security_measures.split(';') if sec.strip()])

    # Add custom process information
    for process in all_processes:
        if process.get('purpose'):
            purposes.add(process['purpose'].strip())
        if process.get('data_category'):
            data_categories.add(process['data_category'].strip())
        if process.get('recipients'):
            recipients.add(process['recipients'].strip())
        if process.get('security_measures'):
            security_measures.add(process['security_measures'].strip())

    # Update record with merged information
    record.processing_purpose = '; '.join(sorted(purposes)) if purposes else record.processing_purpose
    record.data_categories = '; '.join(sorted(data_categories)) if data_categories else record.data_categories
    record.recipients = '; '.join(sorted(recipients)) if recipients else record.recipients
    record.security_measures = '; '.join(sorted(security_measures)) if security_measures else record.security_measures

    # Mark custom tabs as integrated by deleting them (they're now part of main record)
    for tab in custom_tabs:
        db.session.delete(tab)

    log_audit_event('Custom Activities Integrated', record.creator.email, 
                   f'Integrated {len(all_processes)} custom activities into ROPA {record.processing_activity_name}')

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls', 'csv'}


@app.route('/custom-tabs')
@login_required
def custom_tabs():
    """Manage custom tabs"""
    if current_user.role == 'Privacy Officer':
        # Privacy Officers see pending custom tabs for review
        from custom_tab_automation import get_pending_custom_tabs
        pending_tabs = get_pending_custom_tabs()
        return render_template('custom_tabs_admin.html', pending_tabs=pending_tabs)
    else:
        # Privacy Champions see their custom tab submissions
        custom_tabs = models.CustomTab.query.filter_by(created_by=current_user.id).all()
        return render_template('custom_tabs.html', custom_tabs=custom_tabs)


@app.route('/add-custom-field', methods=['GET', 'POST'])
@login_required
def add_custom_field():
    """Add new custom field"""
    if current_user.role not in ['Privacy Champion', 'Privacy Officer']:
        abort(403)

    if request.method == 'POST':
        try:
            custom_tab = models.CustomTab()
            custom_tab.tab_category = request.form.get('tab_category')
            custom_tab.field_name = request.form.get('field_name')
            custom_tab.field_description = request.form.get('field_description')
            custom_tab.field_type = request.form.get('field_type', 'text')
            custom_tab.is_required = 'is_required' in request.form
            custom_tab.created_by = current_user.id
            custom_tab.status = 'Draft'

            # Handle field options for select fields
            if custom_tab.field_type == 'select':
                options = request.form.get('field_options', '').split('\n')
                options = [opt.strip() for opt in options if opt.strip()]
                custom_tab.field_options = json.dumps(options)

            db.session.add(custom_tab)
            db.session.commit()

            from audit_logger import log_audit_event
            log_audit_event(
                "CUSTOM_FIELD_CREATED",
                current_user.email,
                f"Created custom field '{custom_tab.field_name}' in category '{custom_tab.tab_category}'"
            )

            flash('Custom field created successfully!', 'success')
            return redirect(url_for('custom_tabs'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating custom field: {str(e)}', 'error')

    # Define the available categories
    categories = ['Basic Info', 'Controller', 'DPO', 'Processor', 'Processing', 'Data', 'Recipients', 'Retention', 'Security']
    return render_template('add_custom_field.html', categories=categories)


@app.route('/submit-custom-field/<int:field_id>')
@login_required
def submit_custom_field(field_id):
    """Submit custom field for review"""
    custom_tab = models.CustomTab.query.get_or_404(field_id)

    if custom_tab.created_by != current_user.id:
        abort(403)

    from custom_tab_automation import submit_custom_tab_for_review
    result = submit_custom_tab_for_review(field_id)

    if result['success']:
        flash('Custom field submitted for review!', 'success')
    else:
        flash(result['message'], 'error')

    return redirect(url_for('custom_tabs'))


@app.route('/approve-custom-field/<int:field_id>', methods=['POST'])
@login_required
def approve_custom_field(field_id):
    """Approve custom field (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    from custom_tab_automation import approve_custom_tab
    comments = request.form.get('comments', '')
    result = approve_custom_tab(field_id, current_user.id, comments)

    if result['success']:
        flash('Custom field approved and integrated into all existing ROPA records!', 'success')
    else:
        flash(result['message'], 'error')

    return redirect(url_for('custom_tabs'))


@app.route('/reject-custom-field/<int:field_id>', methods=['POST'])
@login_required
def reject_custom_field(field_id):
    """Reject custom field (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    from custom_tab_automation import reject_custom_tab
    comments = request.form.get('comments', 'No reason provided')
    result = reject_custom_tab(field_id, current_user.id, comments)

    if result['success']:
        flash('Custom field rejected.', 'warning')
    else:
        flash(result['message'], 'error')

    return redirect(url_for('custom_tabs'))


@app.route('/ropa-form')
@login_required
def ropa_form():
    """Display ROPA form with custom fields"""
    from custom_tab_automation import get_approved_custom_fields_by_category
    try:
        custom_fields = get_approved_custom_fields_by_category()
    except:
        custom_fields = {}

    return render_template('ropa_form.html', custom_fields=custom_fields)

@app.route('/ropa/<int:id>')
@login_required
def view_ropa(id):
    """View ROPA record with custom fields"""
    record = models.ROPARecord.query.get_or_404(id)

    # Check permissions
    if current_user.role == 'Privacy Champion' and record.created_by != current_user.id:
        abort(403)

    # Get custom fields and their data for this record
    from custom_tab_automation import get_approved_custom_fields_by_category, get_custom_data_for_record
    try:
        custom_fields = get_approved_custom_fields_by_category()
        custom_data = get_custom_data_for_record(record.id)
    except:
        custom_fields = {}
        custom_data = {}

    return render_template('ropa_view.html', record=record, custom_fields=custom_fields, custom_data=custom_data)

@app.route('/ropa/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_ropa(id):
    """Edit ROPA record with custom fields"""
    record = models.ROPARecord.query.get_or_404(id)

    # Check permissions
    if current_user.role == 'Privacy Champion' and record.created_by != current_user.id:
        abort(403)

    # Get custom fields and their data
    from custom_tab_automation import get_approved_custom_fields_by_category, get_custom_data_for_record, update_custom_data_for_record
    try:
        custom_fields = get_approved_custom_fields_by_category()
        custom_data = get_custom_data_for_record(record.id)
    except:
        custom_fields = {}
        custom_data = {}

    if request.method == 'POST':
        # Update record fields
        record.processing_activity_name = request.form.get('processing_activity_name')
        record.category = request.form.get('category')
        record.description = request.form.get('description')
        record.department_function = request.form.get('department_function')
        record.controller_name = request.form.get('controller_name')
        record.controller_contact = request.form.get('controller_contact')
        record.controller_address = request.form.get('controller_address')
        record.processing_purpose = request.form.get('processing_purpose')
        record.legal_basis = request.form.get('legal_basis')
        record.data_categories = request.form.get('data_categories')
        record.data_subjects = request.form.get('data_subjects')
        record.retention_period = request.form.get('retention_period')
        record.security_measures = request.form.get('security_measures')

        # Handle custom fields
        custom_updates = {}
        for category, fields in custom_fields.items():
            for field in fields:
                field_name = f"custom_field_{field['id']}"
                if field_name in request.form:
                    custom_updates[field['id']] = request.form.get(field_name, '')

        try:
            db.session.commit()

            # Update custom field data
            if custom_updates:
                update_custom_data_for_record(record.id, custom_updates)

            flash('ROPA record updated successfully!', 'success')

            # Log the update
            log_audit_event(
                "ROPA_UPDATED",
                f"user_{current_user.id}",
                f"Updated ROPA record '{record.processing_activity_name}' (ID: {record.id}) with custom fields"
            )

            return redirect(url_for('view_ropa', id=record.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating record: {str(e)}', 'error')

    return render_template('ropa_edit.html', record=record, custom_fields=custom_fields, custom_data=custom_data)


@app.route('/view-ropa')
@login_required
def view_ropa_records():
    # Get filter parameters
    status_filter = request.args.get('status', 'All')

    # Build query based on user role
    conn = get_db_connection()

    if current_user.role == "Privacy Champion":
        # Privacy Champions see their own records AND approved records they can edit (in their department)
        user_dept = get_user_department(current_user.email)
        if status_filter == 'All':
            query = """SELECT * FROM ropa_records 
                      WHERE (created_by = ? OR (status = 'Approved' AND department_function = ?))
                      ORDER BY created_at DESC"""
            params = [current_user.id, user_dept]
        else:
            query = """SELECT * FROM ropa_records 
                      WHERE (created_by = ? OR (status = 'Approved' AND department_function = ?)) 
                      AND status = ? ORDER BY created_at DESC"""
            params = [current_user.id, user_dept, status_filter]
    else:
        # Privacy Officers and Admins see all records
        if status_filter == 'All':
            query = "SELECT * FROM ropa_records ORDER BY created_at DESC"
            params = []
        else:
            query = "SELECT * FROM ropa_records WHERE status = ? ORDER BY created_at DESC"
            params = [status_filter]

    cursor = conn.cursor()

    # Debug the exact query being executed
    print(f"DEBUG: Executing query: {query}")
    print(f"DEBUG: With params: {params}")

    try:
        cursor.execute(query, params)
        records = cursor.fetchall()

        # Convert to list of dictionaries
        columns = [
            'id', 'processing_activity_name', 'category', 'description', 'department_function',
            'controller_name', 'controller_contact', 'controller_address', 'dpo_name', 'dpo_contact',
            'dpo_address', 'processor_name', 'processor_contact', 'processor_address',
            'representative_name', 'representative_contact', 'representative_address',
            'processing_purpose', 'legal_basis', 'legitimate_interests', 'data_categories', 'special_categories',
            'data_subjects', 'recipients', 'third_country_transfers', 'safeguards',
            'retention_period', 'retention_criteria', 'retention_justification', 'security_measures',
            'breach_likelihood', 'breach_impact', 'dpia_required', 'additional_info',
            'international_transfers', 'status', 'created_by', 'created_at', 'updated_at', 'updated_by',
            'reviewed_by', 'reviewed_at', 'approved_by', 'approved_at'
        ]

        records_list = []
        for record in records:
            record_dict = dict(zip(columns, record))
            records_list.append(record_dict)

        print(f"DEBUG: Found {len(records_list)} records")
        for record in records_list:
            print(f"DEBUG: Record - ID: {record['id']}, Name: {record['processing_activity_name']}, Status: {record['status']}, Created by: {record['created_by']}")

    except Exception as e:
        print(f"DEBUG: Error executing query: {str(e)}")
        records_list = []
    finally:
        conn.close()

    return render_template('view_ropa.html', records=records_list, status_filter=status_filter)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)