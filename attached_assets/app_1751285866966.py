from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import pandas as pd
import os
import json
from datetime import datetime
import hashlib
from audit_logger import log_audit_event, AuditEventTypes, log_error_event, get_client_ip
from database import (
    init_database, get_db_connection, authenticate_user, get_user_role, 
    create_user, get_all_users, save_ropa_record, get_ropa_records, 
    update_ropa_status, get_dashboard_stats, get_user_department,
    get_ropa_record_by_id, update_ropa_record
)
from utils import get_predefined_options, check_gdpr_compliance
from file_handler import process_uploaded_file
from export_utils import generate_export
import plotly.graph_objects as go
import plotly.utils

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
# login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize database
init_database()

class User(UserMixin):
    def __init__(self, id, email, role, department):
        self.id = id
        self.email = email
        self.role = role
        self.department = department

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, role, department FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email and password:
            # Regular login
            conn = get_db_connection()
            cursor = conn.cursor()
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            cursor.execute("""
                SELECT id, email, role, department FROM users 
                WHERE email = ? AND password_hash = ? AND role IN ('Privacy Champion', 'Privacy Officer')
            """, (email, password_hash))
            user_data = cursor.fetchone()
            
            if user_data:
                # Update last login
                cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_data[0],))
                conn.commit()
                conn.close()
                
                user = User(user_data[0], user_data[1], user_data[2], user_data[3])
                login_user(user)
                log_audit_event(AuditEventTypes.LOGIN_SUCCESS, user.email, "User successfully logged in")
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                conn.close()
                log_audit_event(AuditEventTypes.LOGIN_FAILED, email, "Login failed: Invalid credentials")
                flash('Invalid email or password', 'error')
        else:
            flash('Please enter both email and password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        department = request.form.get('department')
        
        # Validation
        if not all([email, password, confirm_password, role, department]):
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        if role not in ['Privacy Champion', 'Privacy Officer']:
            flash('Invalid role selected', 'error')
            return render_template('register.html')
        
        # Check if email already exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create account
        try:
            password_hash = hashlib.sha256(str(password).encode('utf-8')).hexdigest()
            cursor.execute("""
                INSERT INTO users (email, password_hash, role, department)
                VALUES (?, ?, ?, ?)
            """, (email, password_hash, role, department))
            
            conn.commit()
            conn.close()
            
            log_audit_event(AuditEventTypes.USER_CREATED, email, f"User registered with role: {role}")
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash(f'Error creating account: {str(e)}', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    log_audit_event(AuditEventTypes.LOGOUT, current_user.email, "User logged out")
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get dashboard statistics
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total records
    cursor.execute("SELECT COUNT(*) FROM ropa_records")
    total_records = cursor.fetchone()[0]
    
    # Records by status
    cursor.execute("SELECT status, COUNT(*) FROM ropa_records GROUP BY status")
    status_data = dict(cursor.fetchall())
    
    # Recent activity
    if current_user.role == "Privacy Champion":
        cursor.execute("""
            SELECT processing_activity_name, status, created_at
            FROM ropa_records 
            WHERE created_by = ?
            ORDER BY created_at DESC 
            LIMIT 5
        """, (current_user.email,))
    else:
        cursor.execute("""
            SELECT processing_activity_name, status, created_at
            FROM ropa_records 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
    
    recent_activity = cursor.fetchall()
    
    # Records pending review for Privacy Officers
    pending_records = []
    if current_user.role in ["Privacy Officer", "Admin"]:
        cursor.execute("""
            SELECT id, processing_activity_name, created_by, created_at
            FROM ropa_records 
            WHERE status = 'Pending Review'
            ORDER BY created_at ASC
            LIMIT 5
        """)
        pending_records = cursor.fetchall()
    
    conn.close()
    
    # Create status chart
    if status_data:
        labels = list(status_data.keys())
        values = list(status_data.values())
        
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
        fig.update_layout(
            title="ROPA Status Distribution",
            font=dict(color='white'),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        chart_json = None
    
    stats = {
        'total_records': total_records,
        'approved': status_data.get('Approved', 0),
        'pending': status_data.get('Pending Review', 0),
        'draft': status_data.get('Draft', 0),
        'rejected': status_data.get('Rejected', 0)
    }
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_activity=recent_activity,
                         pending_records=pending_records,
                         chart_json=chart_json)

@app.route('/ropa/new')
@login_required
def new_ropa():
    # Only Privacy Officers can create new ROPA records
    if current_user.role != "Privacy Officer":
        flash('Only Privacy Officers can create new ROPA records. Privacy Champions can edit existing approved records.', 'error')
        return redirect(url_for('view_ropa'))
    return render_template('ropa_form_enhanced.html')

@app.route('/ropa/save', methods=['POST'])
@login_required
def save_ropa():
    # Only Privacy Officers can create new ROPA records
    if current_user.role != "Privacy Officer":
        flash('Only Privacy Officers can create new ROPA records.', 'error')
        return redirect(url_for('view_ropa'))
    
    try:
        # Get form data including new fields
        form_data = request.form.to_dict()
        
        # Convert boolean field to string for database storage
        form_data['data_retained_accordance'] = str(request.form.get('data_retained_accordance') == 'true')
        
        # Determine if saving as draft or submitting for review
        is_draft = request.form.get('save_as_draft') == 'true'
        
        # Set status based on user role and action
        if is_draft:
            form_data['status'] = 'Draft'
        else:
            # Privacy Champions submit for review, Privacy Officers can approve directly
            if current_user.role == "Privacy Champion":
                form_data['status'] = 'Pending Review'
            else:
                form_data['status'] = 'Approved'
        
        # Validate required fields for submission (not for drafts)
        if not is_draft:
            required_fields = [
                'processing_activity_name', 'category', 'description', 'department_function',
                'controller_name', 'controller_contact', 'processing_purpose', 
                'legal_basis', 'data_categories', 'data_subjects', 'retention_period',
                'security_measures', 'data_retained_accordance'
            ]
            
            missing_fields = []
            for field in required_fields:
                if not form_data.get(field, '').strip():
                    missing_fields.append(field.replace('_', ' ').title())
            
            if missing_fields:
                flash(f'Please fill in the following required fields: {", ".join(missing_fields)}', 'error')
                return redirect(url_for('new_ropa'))
        
        # Save to database using the enhanced save function
        from database import save_ropa_record
        record_id = save_ropa_record(form_data, current_user.email)
        
        # Log the appropriate audit event
        if is_draft:
            log_audit_event(AuditEventTypes.ROPA_CREATED, current_user.email, 
                          f"ROPA record saved as draft: {form_data.get('processing_activity_name', 'Unknown')}")
            flash('ROPA record saved as draft successfully!', 'success')
        elif current_user.role == "Privacy Champion":
            log_audit_event(AuditEventTypes.ROPA_SUBMITTED, current_user.email,
                          f"ROPA record submitted for review: {form_data.get('processing_activity_name', 'Unknown')}")
            flash('ROPA record submitted for Privacy Officer review successfully!', 'success')
        else:
            log_audit_event(AuditEventTypes.ROPA_APPROVED, current_user.email,
                          f"ROPA record approved by Privacy Officer: {form_data.get('processing_activity_name', 'Unknown')}")
            flash('ROPA record created and approved successfully!', 'success')
        
        return redirect(url_for('view_ropa'))
        
    except Exception as e:
        flash(f'Error saving ROPA record: {str(e)}', 'error')
        log_audit_event(AuditEventTypes.SYSTEM_ERROR, current_user.email, f"Error saving ROPA: {str(e)}")
        return redirect(url_for('new_ropa'))

@app.route('/ropa/view')
@login_required
def view_ropa():
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
            params = [current_user.email, user_dept]
        else:
            query = """SELECT * FROM ropa_records 
                      WHERE (created_by = ? OR (status = 'Approved' AND department_function = ?)) 
                      AND status = ? ORDER BY created_at DESC"""
            params = [current_user.email, user_dept, status_filter]
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
        records_data = cursor.fetchall()
        print(f"DEBUG: Query executed successfully, fetched {len(records_data)} rows")
    except Exception as e:
        print(f"DEBUG: Query execution failed: {e}")
        records_data = []
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    
    # Convert to list of dictionaries for template
    records = []
    for row in records_data:
        record_dict = dict(zip(columns, row))
        records.append(record_dict)
    
    conn.close()
    

    
    return render_template('view_ropa.html', records=records, status_filter=status_filter)

@app.route('/ropa/<int:record_id>')
@login_required
def view_ropa_detail(record_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user can access this record
    if current_user.role == "Privacy Champion":
        user_dept = get_user_department(current_user.email)
        cursor.execute("""SELECT * FROM ropa_records 
                         WHERE id = ? AND (created_by = ? OR (status = 'Approved' AND department_function = ?))""", 
                      (record_id, current_user.email, user_dept))
    else:
        cursor.execute("SELECT * FROM ropa_records WHERE id = ?", (record_id,))
    
    record = cursor.fetchone()
    conn.close()
    
    if not record:
        flash('Record not found or access denied', 'error')
        return redirect(url_for('view_ropa'))
    
    # Convert to dictionary
    columns = [
        'id', 'processing_activity_name', 'category', 'description',
        'controller_name', 'controller_contact', 'controller_address',
        'dpo_name', 'dpo_contact', 'dpo_address',
        'processor_name', 'processor_contact', 'processor_address',
        'representative_name', 'representative_contact', 'representative_address',
        'processing_purpose', 'legal_basis', 'legitimate_interests',
        'data_categories', 'special_categories', 'data_subjects',
        'recipients', 'third_country_transfers', 'safeguards',
        'retention_period', 'retention_criteria', 'security_measures',
        'breach_likelihood', 'breach_impact', 'additional_info',
        'status', 'created_by', 'created_at', 'updated_at',
        'reviewed_by', 'reviewed_at', 'approved_by', 'approved_at'
    ]
    
    record_dict = dict(zip(columns, record))
    
    # Check GDPR compliance
    compliance = check_gdpr_compliance(record_dict)
    
    # Check if user can edit this record
    user_dept = get_user_department(current_user.email)
    can_edit = (current_user.role == "Privacy Officer" or 
                record_dict['created_by'] == current_user.email or 
                (current_user.role == "Privacy Champion" and record_dict.get('department_function') == user_dept))
    
    return render_template('ropa_detail.html', record=record_dict, compliance=compliance, can_edit=can_edit)

@app.route('/ropa/edit/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit_ropa(record_id):
    # Get record with access control
    record = get_ropa_record_by_id(record_id, current_user.email, current_user.role)
    if not record:
        flash('Record not found or access denied', 'error')
        return redirect(url_for('view_ropa'))
    
    # Check if user can edit this record
    user_dept = get_user_department(current_user.email)
    can_edit = (current_user.role == "Privacy Officer" or 
                record['created_by'] == current_user.email or 
                (current_user.role == "Privacy Champion" and record['department_function'] == user_dept and record['status'] == 'Approved'))
    
    if not can_edit:
        flash('You do not have permission to edit this record', 'error')
        return redirect(url_for('view_ropa'))
    
    if request.method == 'POST':
        try:
            # Log the edit attempt
            log_audit_event("ROPA Updated", current_user.email, 
                          f"Updated ROPA record ID: {record_id} - {request.form.get('processing_activity_name', 'Unknown')}", 
                          get_client_ip())
            
            # Update the record
            if update_ropa_record(record_id, request.form.to_dict(), current_user.email):
                flash('ROPA record updated successfully and submitted for review', 'success')
                return redirect(url_for('view_ropa'))
            else:
                flash('Error updating ROPA record', 'error')
                
        except Exception as e:
            # Log the error
            log_error_event("ROPA Update Error", current_user.email, 
                          f"Failed to update ROPA record ID: {record_id}", str(e))
            flash('An error occurred while updating the record', 'error')
    
    return render_template('edit_ropa.html', record=record)

@app.route('/ropa/add-activity', methods=['GET', 'POST'])
@login_required
def add_activity():
    if current_user.role != 'Privacy Champion':
        flash('Only Privacy Champions can add new activities.', 'error')
        return redirect(url_for('dashboard'))
    
    department = current_user.department

    if request.method == 'POST':
        # Collect basic fields
        form_data = {
            'processing_activity_name': request.form.get('processing_activity_name'),
            'category': request.form.get('category', ''),
            'description': request.form.get('description', ''),
            'department_function': department,
            # Optional/default fields
            'controller_name': '',
            'controller_contact': '',
            'controller_address': '',
            'dpo_name': '',
            'dpo_contact': '',
            'dpo_address': '',
            'processor_name': '',
            'processor_contact': '',
            'processor_address': '',
            'representative_name': '',
            'representative_contact': '',
            'representative_address': '',
            'processing_purpose': '',
            'legal_basis': '',
            'legitimate_interests': '',
            'data_categories': '',
            'special_categories': '',
            'data_subjects': '',
            'recipients': '',
            'third_country_transfers': '',
            'safeguards': '',
            'retention_period': '',
            'retention_criteria': '',
            'retention_justification': '',
            'security_measures': '',
            'breach_likelihood': '',
            'breach_impact': '',
            'dpia_required': '',
            'additional_info': '',
            'international_transfers': '',
            'status': 'Draft'
        }

        # ✅ Validation
        if not form_data['processing_activity_name']:
            flash('Processing Activity Name is required.', 'error')
            return render_template('add_activity.html', department=department)

        # ✅ Save and Audit Log
        save_ropa_record(form_data, current_user.email)
        log_audit_event(
            AuditEventTypes.ROPA_CREATED,
            current_user.email,
            f"New activity added: {form_data['processing_activity_name']}"
        )

        flash('Activity submitted as draft. Privacy Officers can review it later.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_activity.html', department=department)


@app.route('/ropa/<int:record_id>/status', methods=['POST'])
@login_required
def update_ropa_status(record_id):
    if current_user.role not in ["Privacy Officer", "Admin"]:
        flash('Access denied. Only Privacy Officers and Admins can review records.', 'error')
        return redirect(url_for('view_ropa'))
    
    new_status = request.form.get('status')
    comments = request.form.get('comments', '')
    
    if new_status not in ['Approved', 'Rejected', 'Under Review']:
        flash('Invalid status', 'error')
        return redirect(url_for('view_ropa_detail', record_id=record_id))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get record name for logging
    cursor.execute("SELECT processing_activity_name FROM ropa_records WHERE id = ?", (record_id,))
    result = cursor.fetchone()
    record_name = result[0] if result else "Unknown"
    
    # Update status
    if new_status == "Approved":
        cursor.execute("""
            UPDATE ropa_records 
            SET status = ?, approved_by = ?, approved_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, current_user.email, record_id))
        log_audit_event(AuditEventTypes.ROPA_APPROVED, current_user.email, f"Approved ROPA: {record_name}")
    elif new_status == "Rejected":
        cursor.execute("""
            UPDATE ropa_records 
            SET status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, current_user.email, record_id))
        log_audit_event(AuditEventTypes.ROPA_REJECTED, current_user.email, f"Rejected ROPA: {record_name}. Comments: {comments}")
    else:  # Under Review
        cursor.execute("""
            UPDATE ropa_records 
            SET status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, current_user.email, record_id))
        log_audit_event(AuditEventTypes.ROPA_UPDATED, current_user.email, f"Updated ROPA status to Under Review: {record_name}")
    
    conn.commit()
    conn.close()
    
    flash(f'Record status updated to {new_status}', 'success')
    return redirect(url_for('view_ropa_detail', record_id=record_id))

@app.route('/upload')
@login_required
def upload_page():
    # Only Privacy Officers can upload existing ROPA files
    if current_user.role != "Privacy Officer":
        flash('Only Privacy Officers can upload existing ROPA files.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('upload_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('upload_page'))
    
    if file and file.filename and file.filename.lower().endswith(('.xlsx', '.csv')):
        try:
            # Process the uploaded file
            results = process_uploaded_file(file, current_user.email)
            
            flash(f'File processed successfully! Imported {results["success_count"]} records. {results["error_count"]} errors.', 'success')
            log_audit_event(AuditEventTypes.FILE_UPLOADED, current_user.email, 
                          f"Uploaded ROPA file: {file.filename}. Success: {results['success_count']}, Errors: {results['error_count']}")
            
            return redirect(url_for('view_ropa'))
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            log_audit_event(AuditEventTypes.SYSTEM_ERROR, current_user.email, f"Error uploading file: {str(e)}")
            return redirect(url_for('upload_page'))
    
    flash('Invalid file format. Please upload Excel (.xlsx) or CSV files only.', 'error')
    return redirect(url_for('upload_page'))

@app.route('/export')
@login_required
def export_page():
    return render_template('export.html')

@app.route('/export', methods=['POST'])
@login_required
def export_data():
    export_format = request.form.get('format')
    include_drafts = 'include_drafts' in request.form
    include_rejected = 'include_rejected' in request.form
    
    try:
        # Generate export
        file_path, filename = generate_export(current_user.email, current_user.role, 
                                            export_format, include_drafts, include_rejected)
        
        log_audit_event(AuditEventTypes.DATA_EXPORTED, current_user.email, 
                      f"Exported ROPA data in {export_format} format")
        
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        flash(f'Error generating export: {str(e)}', 'error')
        log_audit_event(AuditEventTypes.SYSTEM_ERROR, current_user.email, f"Export error: {str(e)}")
        return redirect(url_for('export_page'))

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != "Privacy Officer":
        flash('Access denied. Privacy Officer privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    df = pd.read_sql_query("""
        SELECT id, email, role, department, created_at, last_login 
        FROM users ORDER BY created_at DESC
    """, conn)
    conn.close()
    
    users = df.to_dict('records') if not df.empty else []
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
@login_required
def add_user():
    if current_user.role != "Privacy Officer":
        flash('Access denied. Privacy Officer privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    department = request.form.get('department')
    
    if not all([email, password, role, department]):
        flash('All fields are required', 'error')
        return redirect(url_for('admin_users'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Ensure password is not None before encoding
        if password is None:
            flash('Password is required', 'error')
            return redirect(url_for('admin_users'))
            
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        cursor.execute("""
            INSERT INTO users (email, password_hash, role, department)
            VALUES (?, ?, ?, ?)
        """, (email, password_hash, role, department))
        
        conn.commit()
        conn.close()
        
        log_audit_event(AuditEventTypes.USER_CREATED, current_user.email, f"Created user: {email} with role: {role}")
        flash('User created successfully!', 'success')
        
    except Exception as e:
        if 'duplicate key' in str(e).lower() or 'already exists' in str(e).lower():
            flash('Email already exists', 'error')
        else:
            flash(f'Error creating user: {str(e)}', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/audit')
@login_required
def admin_audit():
    if current_user.role != "Privacy Officer":
        flash('Access denied. Privacy Officer privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    event_type = request.args.get('event_type', 'All')
    user_email = request.args.get('user_email', '')
    limit = int(request.args.get('limit', 100))
    
    conn = get_db_connection()
    
    # Build query
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    
    if event_type != 'All':
        query += " AND event_type = ?"
        params.append(event_type)
    
    if user_email:
        query += " AND user_email LIKE ?"
        params.append(f"%{user_email}%")
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    audit_logs = df.to_dict('records') if not df.empty else []
    
    # Get event type options
    event_types = [
        'All', 'Login Success', 'Login Failed', 'ROPA Created', 
        'ROPA Approved', 'ROPA Rejected', 'File Uploaded', 'Data Exported'
    ]
    
    return render_template('admin_audit.html', 
                         audit_logs=audit_logs, 
                         event_types=event_types,
                         current_event_type=event_type,
                         current_user_email=user_email)

@app.route('/automation')
@login_required
def automation_dashboard():
    if current_user.role != "Privacy Officer":
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get automation statistics
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Count ROPA records by status for automation insights
    cursor.execute("SELECT status, COUNT(*) FROM ropa_records GROUP BY status")
    status_data = dict(cursor.fetchall())
    
    # Count records by category for automation suggestions
    cursor.execute("SELECT category, COUNT(*) FROM ropa_records WHERE category IS NOT NULL GROUP BY category")
    category_data = dict(cursor.fetchall())
    
    # Get recent automation events from audit log
    cursor.execute("""
        SELECT timestamp, event_type, description
        FROM audit_logs 
        WHERE event_type LIKE '%Auto%' OR description LIKE '%automation%'
        ORDER BY timestamp DESC 
        LIMIT 10
    """)
    automation_events = []
    for row in cursor.fetchall():
        automation_events.append({
            'timestamp': row[0],
            'event_type': row[1],
            'description': row[2]
        })
    
    conn.close()
    
    automation_stats = {
        'total_records': sum(status_data.values()) if status_data else 0,
        'auto_classified': len(category_data) if category_data else 0,
        'status_distribution': status_data,
        'category_distribution': category_data
    }
    
    return render_template('automation_dashboard.html', 
                         automation_stats=automation_stats,
                         automation_events=automation_events)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)