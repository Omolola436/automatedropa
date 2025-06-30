import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify, abort
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import tempfile
from datetime import datetime
import pandas as pd

# Import our modules
from database import (
    init_database, authenticate_user, get_user_role, create_user, 
    get_all_users, save_ropa_record, get_ropa_records, get_ropa_record_by_id,
    update_ropa_record, delete_ropa_record, update_ropa_status, get_user_department
)
from audit_logger import log_audit_event, get_audit_logs
from export_utils import generate_export
from file_handler import process_uploaded_file
from template_generator import generate_ropa_template
from automation import auto_classify_data, suggest_processing_purpose, assess_risk, suggest_security_measures
from utils import get_predefined_options, validate_required_fields, get_client_ip

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-change-in-production")

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
init_database()

@app.before_request
def require_login():
    """Require login for all routes except login and register"""
    allowed_routes = ['login', 'register', 'static']
    if request.endpoint not in allowed_routes and 'user_email' not in session:
        return redirect(url_for('login'))

@app.route('/')
def index():
    """Redirect to appropriate dashboard based on user role"""
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_role = session.get('user_role', 'Privacy Champion')
    if user_role == 'Privacy Officer':
        return redirect(url_for('privacy_officer_dashboard'))
    else:
        return redirect(url_for('privacy_champion_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if authenticate_user(email, password):
            session['user_email'] = email
            session['user_role'] = get_user_role(email)
            session['user_department'] = get_user_department(email)
            
            log_audit_event('Login Success', email, get_client_ip(request), 'User successfully logged in')
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            log_audit_event('Login Failed', email, get_client_ip(request), 'Login failed: Invalid credentials')
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']
        department = request.form['department']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if create_user(email, password, role, department):
            log_audit_event('User Registration', email, get_client_ip(request), f'New user registered with role: {role}')
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email already exists', 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """User logout"""
    if 'user_email' in session:
        log_audit_event('Logout', session['user_email'], get_client_ip(request), 'User logged out')
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/privacy_champion_dashboard')
def privacy_champion_dashboard():
    """Privacy Champion dashboard"""
    if session.get('user_role') not in ['Privacy Champion', 'Privacy Officer']:
        abort(403)
    
    user_email = session['user_email']
    user_role = session['user_role']
    
    # Get user's ROPA records
    records_df = get_ropa_records(user_email=user_email, role=user_role)
    
    # Convert to list of dictionaries for template
    records = records_df.to_dict('records') if not records_df.empty else []
    
    # Get summary statistics
    total_records = len(records)
    approved_records = len([r for r in records if r.get('status') == 'Approved'])
    pending_records = len([r for r in records if r.get('status') == 'Pending Review'])
    draft_records = len([r for r in records if r.get('status') == 'Draft'])
    
    return render_template('privacy_champion_dashboard.html',
                         records=records,
                         total_records=total_records,
                         approved_records=approved_records,
                         pending_records=pending_records,
                         draft_records=draft_records)

@app.route('/privacy_officer_dashboard')
def privacy_officer_dashboard():
    """Privacy Officer dashboard"""
    if session.get('user_role') != 'Privacy Officer':
        abort(403)
    
    # Get all ROPA records
    records_df = get_ropa_records()
    records = records_df.to_dict('records') if not records_df.empty else []
    
    # Get summary statistics
    total_records = len(records)
    approved_records = len([r for r in records if r.get('status') == 'Approved'])
    pending_records = len([r for r in records if r.get('status') == 'Pending Review'])
    draft_records = len([r for r in records if r.get('status') == 'Draft'])
    rejected_records = len([r for r in records if r.get('status') == 'Rejected'])
    
    # Get recent audit logs
    audit_logs = get_audit_logs(limit=10)
    
    return render_template('privacy_officer_dashboard.html',
                         records=records,
                         total_records=total_records,
                         approved_records=approved_records,
                         pending_records=pending_records,
                         draft_records=draft_records,
                         rejected_records=rejected_records,
                         audit_logs=audit_logs)

@app.route('/add_activity', methods=['GET', 'POST'])
def add_activity():
    """Add new ROPA activity"""
    if request.method == 'POST':
        try:
            # Collect form data
            form_data = {
                'processing_activity_name': request.form.get('processing_activity_name', ''),
                'category': request.form.get('category', ''),
                'description': request.form.get('description', ''),
                'department_function': request.form.get('department_function', ''),
                'controller_name': request.form.get('controller_name', ''),
                'controller_contact': request.form.get('controller_contact', ''),
                'controller_address': request.form.get('controller_address', ''),
                'dpo_name': request.form.get('dpo_name', ''),
                'dpo_contact': request.form.get('dpo_contact', ''),
                'dpo_address': request.form.get('dpo_address', ''),
                'processor_name': request.form.get('processor_name', ''),
                'processor_contact': request.form.get('processor_contact', ''),
                'processor_address': request.form.get('processor_address', ''),
                'representative_name': request.form.get('representative_name', ''),
                'representative_contact': request.form.get('representative_contact', ''),
                'representative_address': request.form.get('representative_address', ''),
                'processing_purpose': request.form.get('processing_purpose', ''),
                'legal_basis': request.form.get('legal_basis', ''),
                'legitimate_interests': request.form.get('legitimate_interests', ''),
                'data_categories': ', '.join(request.form.getlist('data_categories')),
                'special_categories': ', '.join(request.form.getlist('special_categories')),
                'data_subjects': ', '.join(request.form.getlist('data_subjects')),
                'recipients': request.form.get('recipients', ''),
                'third_country_transfers': request.form.get('third_country_transfers', ''),
                'international_transfers': request.form.get('international_transfers', ''),
                'safeguards': request.form.get('safeguards', ''),
                'retention_period': request.form.get('retention_period', ''),
                'retention_criteria': request.form.get('retention_criteria', ''),
                'retention_justification': request.form.get('retention_justification', ''),
                'security_measures': request.form.get('security_measures', ''),
                'breach_likelihood': request.form.get('breach_likelihood', 'Medium'),
                'breach_impact': request.form.get('breach_impact', 'Medium'),
                'dpia_required': request.form.get('dpia_required', 'No'),
                'additional_info': request.form.get('additional_info', ''),
                'status': request.form.get('status', 'Draft')
            }
            
            # Validate required fields
            validation_result = validate_required_fields(form_data)
            if not validation_result['valid']:
                flash(f'Validation failed: {", ".join(validation_result["missing_fields"])}', 'error')
                return render_template('ropa_form.html', 
                                     form_data=form_data,
                                     predefined_options=get_predefined_options())
            
            # Save record
            record_id = save_ropa_record(form_data, session['user_email'])
            
            if record_id:
                log_audit_event('ROPA Record Created', session['user_email'], get_client_ip(request),
                              f'Created new ROPA record: {form_data["processing_activity_name"]}')
                flash('ROPA record created successfully!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Error creating ROPA record', 'error')
                
        except Exception as e:
            logging.error(f"Error creating ROPA record: {str(e)}")
            flash('An error occurred while creating the record', 'error')
    
    # GET request - show form
    return render_template('ropa_form.html', 
                         form_data={},
                         predefined_options=get_predefined_options())

@app.route('/edit_activity/<int:record_id>', methods=['GET', 'POST'])
def edit_activity(record_id):
    """Edit existing ROPA activity"""
    user_email = session['user_email']
    user_role = session['user_role']
    
    # Get the record with access control
    record = get_ropa_record_by_id(record_id, user_email, user_role)
    if not record:
        flash('Record not found or access denied', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Collect form data
            form_data = {
                'processing_activity_name': request.form.get('processing_activity_name', ''),
                'category': request.form.get('category', ''),
                'description': request.form.get('description', ''),
                'department_function': request.form.get('department_function', ''),
                'controller_name': request.form.get('controller_name', ''),
                'controller_contact': request.form.get('controller_contact', ''),
                'controller_address': request.form.get('controller_address', ''),
                'dpo_name': request.form.get('dpo_name', ''),
                'dpo_contact': request.form.get('dpo_contact', ''),
                'dpo_address': request.form.get('dpo_address', ''),
                'processor_name': request.form.get('processor_name', ''),
                'processor_contact': request.form.get('processor_contact', ''),
                'processor_address': request.form.get('processor_address', ''),
                'representative_name': request.form.get('representative_name', ''),
                'representative_contact': request.form.get('representative_contact', ''),
                'representative_address': request.form.get('representative_address', ''),
                'processing_purpose': request.form.get('processing_purpose', ''),
                'legal_basis': request.form.get('legal_basis', ''),
                'legitimate_interests': request.form.get('legitimate_interests', ''),
                'data_categories': ', '.join(request.form.getlist('data_categories')),
                'special_categories': ', '.join(request.form.getlist('special_categories')),
                'data_subjects': ', '.join(request.form.getlist('data_subjects')),
                'recipients': request.form.get('recipients', ''),
                'third_country_transfers': request.form.get('third_country_transfers', ''),
                'international_transfers': request.form.get('international_transfers', ''),
                'safeguards': request.form.get('safeguards', ''),
                'retention_period': request.form.get('retention_period', ''),
                'retention_criteria': request.form.get('retention_criteria', ''),
                'retention_justification': request.form.get('retention_justification', ''),
                'security_measures': request.form.get('security_measures', ''),
                'breach_likelihood': request.form.get('breach_likelihood', 'Medium'),
                'breach_impact': request.form.get('breach_impact', 'Medium'),
                'dpia_required': request.form.get('dpia_required', 'No'),
                'additional_info': request.form.get('additional_info', ''),
                'status': request.form.get('status', record['status'])
            }
            
            # Validate required fields
            validation_result = validate_required_fields(form_data)
            if not validation_result['valid']:
                flash(f'Validation failed: {", ".join(validation_result["missing_fields"])}', 'error')
                return render_template('ropa_edit.html', 
                                     record=record,
                                     form_data=form_data,
                                     predefined_options=get_predefined_options())
            
            # Update record
            if update_ropa_record(record_id, form_data, session['user_email']):
                log_audit_event('ROPA Record Updated', session['user_email'], get_client_ip(request),
                              f'Updated ROPA record: {form_data["processing_activity_name"]}')
                flash('ROPA record updated successfully!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Error updating ROPA record', 'error')
                
        except Exception as e:
            logging.error(f"Error updating ROPA record: {str(e)}")
            flash('An error occurred while updating the record', 'error')
    
    return render_template('ropa_edit.html', 
                         record=record,
                         predefined_options=get_predefined_options())

@app.route('/view_activity/<int:record_id>')
def view_activity(record_id):
    """View ROPA activity details"""
    user_email = session['user_email']
    user_role = session['user_role']
    
    record = get_ropa_record_by_id(record_id, user_email, user_role)
    if not record:
        flash('Record not found or access denied', 'error')
        return redirect(url_for('index'))
    
    return render_template('ropa_view.html', record=record)

@app.route('/update_status/<int:record_id>/<status>')
def update_status(record_id, status):
    """Update ROPA record status (Privacy Officer only)"""
    if session.get('user_role') != 'Privacy Officer':
        abort(403)
    
    valid_statuses = ['Approved', 'Rejected', 'Pending Review']
    if status not in valid_statuses:
        flash('Invalid status', 'error')
        return redirect(url_for('privacy_officer_dashboard'))
    
    try:
        if update_ropa_status(record_id, status, session['user_email']):
            log_audit_event('ROPA Status Updated', session['user_email'], get_client_ip(request),
                          f'Updated record {record_id} status to {status}')
            flash(f'Record status updated to {status}', 'success')
        else:
            flash('Error updating record status', 'error')
    except Exception as e:
        logging.error(f"Error updating status: {str(e)}")
        flash('An error occurred while updating status', 'error')
    
    return redirect(url_for('privacy_officer_dashboard'))

@app.route('/delete_activity/<int:record_id>')
def delete_activity(record_id):
    """Delete ROPA activity"""
    user_email = session['user_email']
    user_role = session['user_role']
    
    # Check if user has permission to delete
    record = get_ropa_record_by_id(record_id, user_email, user_role)
    if not record:
        flash('Record not found or access denied', 'error')
        return redirect(url_for('index'))
    
    try:
        if delete_ropa_record(record_id):
            log_audit_event('ROPA Record Deleted', session['user_email'], get_client_ip(request),
                          f'Deleted ROPA record: {record["processing_activity_name"]}')
            flash('ROPA record deleted successfully!', 'success')
        else:
            flash('Error deleting ROPA record', 'error')
    except Exception as e:
        logging.error(f"Error deleting record: {str(e)}")
        flash('An error occurred while deleting the record', 'error')
    
    return redirect(url_for('index'))

@app.route('/download_template')
def download_template():
    """Download ROPA template (Privacy Officer only)"""
    if session.get('user_role') != 'Privacy Officer':
        abort(403)
    
    try:
        template_path = generate_ropa_template()
        log_audit_event('Template Downloaded', session['user_email'], get_client_ip(request),
                       'Downloaded ROPA template')
        return send_file(template_path, as_attachment=True, 
                        download_name='ROPA_Template.xlsx',
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        logging.error(f"Error generating template: {str(e)}")
        flash('Error generating template', 'error')
        return redirect(url_for('privacy_officer_dashboard'))

@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():
    """Upload and process ROPA file (Privacy Officer only)"""
    if session.get('user_role') != 'Privacy Officer':
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
            try:
                filename = secure_filename(file.filename)
                results = process_uploaded_file(file, session['user_email'])
                
                log_audit_event('File Uploaded', session['user_email'], get_client_ip(request),
                              f'Uploaded file: {filename} - {results.get("success_count", 0)} successful, {results.get("error_count", 0)} failed')
                
                flash(f'File processed successfully! {results.get("success_count", 0)} records imported, {results.get("error_count", 0)} errors', 'success')
                return redirect(url_for('privacy_officer_dashboard'))
                
            except Exception as e:
                logging.error(f"Error processing file: {str(e)}")
                log_audit_event('File Upload Error', session['user_email'], get_client_ip(request),
                              f'Upload failed: {str(e)}')
                flash('Error processing file', 'error')
        else:
            flash('Invalid file type. Please upload Excel or CSV files only.', 'error')
    
    return render_template('file_upload.html')

@app.route('/export_data')
def export_data():
    """Export ROPA data"""
    export_format = request.args.get('format', 'excel')
    include_drafts = request.args.get('include_drafts') == 'true'
    include_rejected = request.args.get('include_rejected') == 'true'
    
    try:
        file_path, filename = generate_export(
            user_email=session['user_email'],
            user_role=session['user_role'],
            export_format=export_format,
            include_drafts=include_drafts,
            include_rejected=include_rejected
        )
        
        log_audit_event('Data Exported', session['user_email'], get_client_ip(request),
                       f'Exported data in {export_format} format')
        
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logging.error(f"Error exporting data: {str(e)}")
        flash('Error exporting data', 'error')
        return redirect(url_for('index'))

@app.route('/audit_logs')
def audit_logs():
    """View audit logs (Privacy Officer only)"""
    if session.get('user_role') != 'Privacy Officer':
        abort(403)
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    logs = get_audit_logs(page=page, per_page=per_page)
    
    return render_template('audit_logs.html', logs=logs)

@app.route('/api/auto_classify', methods=['POST'])
def api_auto_classify():
    """API endpoint for auto-classification"""
    description = request.json.get('description', '')
    category = auto_classify_data(description)
    return jsonify({'category': category})

@app.route('/api/suggest_purpose', methods=['POST'])
def api_suggest_purpose():
    """API endpoint for purpose suggestion"""
    department = request.json.get('department', '')
    category = request.json.get('category', '')
    purpose = suggest_processing_purpose(department, category)
    return jsonify({'purpose': purpose})

@app.route('/api/assess_risk', methods=['POST'])
def api_assess_risk():
    """API endpoint for risk assessment"""
    data_categories = request.json.get('data_categories', [])
    special_categories = request.json.get('special_categories', [])
    risk = assess_risk(data_categories, special_categories)
    return jsonify(risk)

@app.route('/api/suggest_security', methods=['POST'])
def api_suggest_security():
    """API endpoint for security measures suggestion"""
    data_categories = request.json.get('data_categories', [])
    risk_level = request.json.get('risk_level', 'Medium')
    measures = suggest_security_measures(data_categories, risk_level)
    return jsonify({'measures': measures})

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
