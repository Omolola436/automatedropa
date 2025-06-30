import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import DeclarativeBase
import tempfile
from datetime import datetime
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///ropa_system.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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
    # Import models here to ensure they're registered
    import models
    db.create_all()

# Import utility functions after app context
from automation import auto_classify_data, suggest_processing_purpose, assess_risk, suggest_security_measures
from utils import get_predefined_options, validate_required_fields
from export_utils import generate_export
from file_handler import process_uploaded_file
from template_generator import generate_ropa_template

@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))

def get_client_ip():
    """Get client IP address from request"""
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR']

def log_audit_event(event_type, user_email, description, ip_address=None):
    """Log an audit event"""
    if ip_address is None:
        ip_address = get_client_ip()
    
    audit_log = models.AuditLog(
        event_type=event_type,
        user_email=user_email,
        ip_address=ip_address,
        description=description
    )
    db.session.add(audit_log)
    db.session.commit()

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        department = request.form.get('department', '')
        
        # Check if user already exists
        if models.User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create new user
        user = models.User(
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            department=department
        )
        db.session.add(user)
        db.session.commit()
        
        log_audit_event('User Registration', email, f'New user registered with role: {role}')
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

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
    
    # Statistics
    total_records = len(all_records)
    pending_count = len(pending_records)
    approved_records = len([r for r in all_records if r.status == 'Approved'])
    
    return render_template('privacy_officer_dashboard.html',
                         all_records=all_records,
                         pending_records=pending_records,
                         total_records=total_records,
                         pending_count=pending_count,
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
        
        # Check if saving as draft or submitting for review
        if 'save_draft' in request.form:
            record.status = 'Draft'
            message = 'ROPA record saved as draft'
        else:
            record.status = 'Under Review'
            message = 'ROPA record submitted for review'
        
        db.session.add(record)
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
    
    return render_template('ropa_view.html', record=record)

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
        return redirect(url_for('privacy_champion_dashboard'))

@app.route('/audit-logs')
@login_required
def audit_logs():
    """View audit logs (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)
    
    page = request.args.get('page', 1, type=int)
    logs = models.AuditLog.query.order_by(models.AuditLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('audit_logs.html', logs=logs)

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

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls', 'csv'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)