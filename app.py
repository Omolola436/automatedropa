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
application=app
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
from subscription import (get_user_effective_tier, get_tier_config,
                          get_trial_days_remaining, can_add_activity, has_feature,
                          TIER_CONFIG)
from health_engine import (calculate_compliance_score, calculate_org_compliance_score,
                           run_health_checks, notify_new_activity, check_vendor_alerts)

# Subscription + notification context processor
@app.context_processor
def inject_subscription():
    if current_user.is_authenticated:
        tier = get_user_effective_tier(current_user)
        config = get_tier_config(tier)
        trial_days = get_trial_days_remaining(current_user)
        unread_notifications = 0
        if config.get('has_alerts'):
            try:
                unread_notifications = models.Notification.query.filter_by(
                    user_id=current_user.id, is_read=False
                ).count()
            except Exception:
                unread_notifications = 0
        return dict(
            sub_tier=tier,
            sub_config=config,
            sub_trial_days=trial_days,
            unread_notifications=unread_notifications,
            now_date=datetime.utcnow(),
        )
    return dict(sub_tier=None, sub_config={}, sub_trial_days=None, unread_notifications=0, now_date=datetime.utcnow())

# Add custom Jinja filters
@app.template_filter('from_json')
def from_json_filter(json_str):
    """Custom Jinja filter to parse JSON strings"""
    try:
        if isinstance(json_str, str):
            return json.loads(json_str)
        return json_str
    except (ValueError, TypeError):
        return []

def cleanup_duplicate_sheets():
    """Remove duplicate Excel sheets from database, keeping only the first occurrence"""
    try:
        # Get all Excel files
        excel_files = models.ExcelFileData.query.all()
        total_deleted = 0
        
        for file in excel_files:
            # Track sheet names we've seen for this file
            seen_sheet_names = set()
            sheets_to_delete = []
            
            # Go through sheets in order of creation (earliest first)
            for sheet in sorted(file.sheets, key=lambda s: s.id):
                if sheet.sheet_name in seen_sheet_names:
                    # This is a duplicate, mark for deletion
                    sheets_to_delete.append(sheet)
                    total_deleted += 1
                else:
                    # First occurrence, keep it
                    seen_sheet_names.add(sheet.sheet_name)
            
            # Delete the duplicate sheets
            for sheet in sheets_to_delete:
                db.session.delete(sheet)
        
        db.session.commit()
        return total_deleted
    except Exception as e:
        db.session.rollback()
        print(f"Error cleaning up duplicate sheets: {str(e)}")
        return 0

@app.route('/')
def index():
    """Landing page for visitors; dashboard redirect for authenticated users"""
    if current_user.is_authenticated:
        if current_user.role == 'Privacy Officer':
            return redirect(url_for('privacy_officer_dashboard'))
        else:
            return redirect(url_for('privacy_champion_dashboard'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        consent = request.form.get('consent')

        # Check consent
        if not consent:
            flash('You must provide consent to use the system', 'error')
            return render_template('login.html')

        user = models.User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            # Clear any leftover wizard session data from a previous user
            session.pop('wizard_data', None)
            log_audit_event('Login Success', email, 'User logged in successfully with consent')
            return redirect(url_for('index'))
        else:
            log_audit_event('Login Failed', email, 'Failed login attempt')
            flash('Invalid email or password', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Open registration — each new signup creates a Privacy Officer (org admin) on a free trial"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        organisation = request.form.get('organisation', '')

        if not all([email, password, confirm_password]):
            flash('All fields are required.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')

        if models.User.query.filter_by(email=email).first():
            flash('An account with that email already exists.', 'error')
            return render_template('register.html')

        try:
            user = models.User(
                email=email,
                password_hash=generate_password_hash(password),
                role='Privacy Officer',
                department=organisation or 'General',
                subscription_tier='trial',
                trial_start_date=datetime.utcnow(),
            )
            db.session.add(user)
            db.session.commit()

            login_user(user)
            log_audit_event('New Account Created', email, 'New organisation signed up for free trial')
            flash('Welcome! Your 7-day free trial has started.', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error creating account: {str(e)}', 'error')

    return render_template('register.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password requests"""
    if request.method == 'POST':
        email = request.form['email']
        user = models.User.query.filter_by(email=email).first()

        if user:
            # Generate reset token
            import secrets
            import hashlib
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            # Set token expiry (24 hours from now)
            from datetime import datetime, timedelta
            user.reset_token = token_hash
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
            db.session.commit()

            # In a production app, you would send an email here
            # For now, we'll flash the reset link
            reset_url = url_for('reset_password', token=token, _external=True)

            log_audit_event('Password Reset Requested', email, 'User requested password reset')
            flash(f'Password reset instructions would be sent to {email}. For development: {reset_url}', 'info')
        else:
            # Don't reveal whether email exists or not for security
            flash('If an account with that email exists, password reset instructions will be sent.', 'info')
            log_audit_event('Password Reset Failed', email, 'Password reset requested for non-existent email')

        return redirect(url_for('login'))

    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token"""
    import hashlib
    from datetime import datetime

    # Hash the token to match what's stored in database
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Find user with valid token
    user = models.User.query.filter_by(reset_token=token_hash).first()

    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        flash('Invalid or expired reset token. Please request a new password reset.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Validation
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('reset_password.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html')

        # Update password and clear reset token
        user.password_hash = generate_password_hash(password)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()

        log_audit_event('Password Reset Completed', user.email, 'User successfully reset password')
        flash('Your password has been reset successfully. You can now log in with your new password.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

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

    # Get current tier and plan name
    current_tier = get_user_effective_tier(current_user)
    current_tier_config = get_tier_config(current_tier)

    return render_template('privacy_champion_dashboard.html', 
                         records=records,
                         total_records=total_records,
                         draft_records=draft_records,
                         pending_records=pending_records,
                         approved_records=approved_records,
                         current_tier_name=current_tier_config.get('name'),
                         current_tier=current_tier,
                         tiers=TIER_CONFIG)

@app.route('/privacy-officer-dashboard')
@login_required
def privacy_officer_dashboard():
    if current_user.role != 'Privacy Officer':
        abort(403)

    try:
        # Get all records for the current user's organization (same department)
        all_records = models.ROPARecord.query.join(models.User, models.ROPARecord.created_by == models.User.id).filter(models.User.department == current_user.department).all()

        # Calculate status counts
        status_counts = {}
        for record in all_records:
            status_counts[record.status] = status_counts.get(record.status, 0) + 1

        # Get recent records (last 10) for the organization
        recent_records = []
        try:
            recent_records_list = models.ROPARecord.query.join(models.User, models.ROPARecord.created_by == models.User.id).filter(models.User.department == current_user.department).order_by(models.ROPARecord.created_at.desc()).limit(10).all()

            for record in recent_records_list:
                try:
                    creator = models.User.query.get(record.created_by)
                    creator_email = creator.email if creator else f'User ID {record.created_by}'
                    recent_records.append({
                        'processing_activity_name': record.processing_activity_name,
                        'status': record.status,
                        'created_at': record.created_at,
                        'created_by': creator_email
                    })
                except Exception as e:
                    print(f"Error processing record {record.id}: {str(e)}")
                    continue
        except Exception as e:
            print(f"Error getting recent records: {str(e)}")
            recent_records = []

        # Get records by status for template sections
        draft_records = [r for r in all_records if r.status == 'Draft']
        pending_records = [r for r in all_records if r.status == 'Under Review']
        rejected_records = [r for r in all_records if r.status == 'Rejected']

        # Get counts
        pending_count = len(pending_records)
        draft_count = len(draft_records)
        rejected_count = len(rejected_records)

        # Convert all records to list of dicts for template
        records_list = []
        for record in all_records:
            creator = models.User.query.get(record.created_by)
            creator_email = creator.email if creator else f'User ID {record.created_by}'

            records_list.append({
                'id': record.id,
                'processing_activity_name': record.processing_activity_name,
                'category': record.category,
                'description': record.description,
                'department_function': record.department_function,
                'status': record.status,
                'created_by': creator_email,
                'created_at': record.created_at,
                'creator': creator
            })

        print(f"DEBUG: Privacy Officer Dashboard - Total records: {len(all_records)}")
        print(f"DEBUG: Status counts: {status_counts}")
        print(f"DEBUG: Pending count: {pending_count} (type: {type(pending_count)})")

        # Compliance score (Enterprise only)
        org_compliance = None
        tier = get_user_effective_tier(current_user)
        if get_tier_config(tier).get('has_compliance_score'):
            org_compliance = calculate_org_compliance_score(all_records)

        # Unread notifications (Growth+)
        recent_notifications = []
        if get_tier_config(tier).get('has_alerts'):
            recent_notifications = models.Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).order_by(models.Notification.created_at.desc()).limit(5).all()

        # Get current tier and plan name
        current_tier = get_user_effective_tier(current_user)
        current_tier_config = get_tier_config(current_tier)

        return render_template('privacy_officer_dashboard.html',
                             total_records=len(all_records),
                             pending_reviews=pending_count,
                             pending_records=pending_records,
                             pending_count=pending_count,
                             approved_records=status_counts.get('Approved', 0),
                             draft_records=draft_records,
                             draft_count=draft_count,
                             rejected_records=rejected_count,
                             recent_records=recent_records,
                             records=records_list,
                             status_counts=status_counts,
                             org_compliance=org_compliance,
                             recent_notifications=recent_notifications,
                             tiers=TIER_CONFIG,
                             current_tier_name=current_tier_config.get('name'),
                             current_tier=current_tier)

    except Exception as e:
        print(f"Error in privacy_officer_dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('privacy_officer_dashboard.html',
                             total_records=0,
                             pending_reviews=0,
                             pending_records=[],
                             pending_count=0,
                             approved_records=0,
                             draft_records=[],
                             draft_count=0,
                             rejected_records=0,
                             recent_records=[],
                             records=[],
                             status_counts={},
                             org_compliance=None,
                             recent_notifications=[])


@app.route('/add-activity', methods=['GET', 'POST'])
@login_required
def add_activity():
    """Add new ROPA activity with step-by-step wizard"""
    # Enforce activity limit based on subscription tier
    tier = get_user_effective_tier(current_user)
    if tier == 'expired':
        flash('Your free trial has expired. Please upgrade to continue adding activities.', 'error')
        return redirect(url_for('pricing'))

    config = get_tier_config(tier)
    current_count = models.ROPARecord.query.filter_by(created_by=current_user.id).count()
    if not can_add_activity(current_user, current_count):
        flash(
            f'You have reached the limit of {config["max_activities"]} processing activities for your '
            f'{config["name"]} plan. Please upgrade to add more.',
            'error'
        )
        return redirect(url_for('pricing'))

    # Initialize wizard data in session if not exists
    if 'wizard_data' not in session:
        session['wizard_data'] = {
            'step': 1,
            'organization': {},
            'activity_form': {}
        }

    wizard_data = session['wizard_data']
    # Ensure new keys exist for sessions created before this version
    wizard_data.setdefault('activity_form', {})
    wizard_data.setdefault('organization', {})

    if request.method == 'POST':
        action = request.form.get('action', 'next')

        if action == 'next':
            step = int(request.form.get('current_step', 1))
            save_step_data(step, request.form, wizard_data)
            wizard_data['step'] = min(step + 1, 3)

        elif action == 'back':
            step = int(request.form.get('current_step', 1))
            save_step_data(step, request.form, wizard_data)
            wizard_data['step'] = max(step - 1, 1)

        elif action == 'generate':
            # Final step - generate ROPA records and export to Excel
            step = int(request.form.get('current_step', 1))
            save_step_data(step, request.form, wizard_data)

            # Generate ROPA records based on wizard data
            records_created = generate_ropa_records(wizard_data, current_user)

            # Clear wizard data
            session.pop('wizard_data', None)

            flash(f'Successfully created {records_created} ROPA record(s). Downloading your Excel file...', 'success')
            # Redirect to Excel export so file downloads immediately
            return redirect(url_for('export_data', format='excel'))

        session.modified = True

    return render_template(
        'create_ropa_wizard.html',
        wizard_data=wizard_data,
        current_step=wizard_data.get('step', 1),
        activity_count=current_count,
        max_activities=config['max_activities'],
        sub_tier=current_user.subscription_tier
    )


def save_step_data(step, form, wizard_data):
    """Save form data for the current step"""
    if step == 1:  # Organization Overview + DPO
        wizard_data['organization'] = {
            'name': form.get('org_name'),
            'industry': form.get('industry'),
            'country': form.get('country'),
            'employee_count': form.get('employee_count'),
            'controller_contact': form.get('controller_contact', ''),
            'controller_address': form.get('controller_address', ''),
            'dpo_name': form.get('dpo_name'),
            'dpo_contact': form.get('dpo_contact'),
            'dpo_address': form.get('dpo_address')
        }
    elif step == 2:  # Processing Activity Details
        wizard_data['activity_form'] = {
            'activity_name': form.get('activity_name', ''),
            'department_function': form.get('department_function', ''),
            'processing_purpose': form.get('processing_purpose', ''),
            'data_subjects': form.get('data_subjects', ''),
            'data_categories': form.get('data_categories', ''),
            'retention_period': form.get('retention_period', ''),
            'recipients': form.get('recipients', ''),
            'security_measures': form.get('security_measures', ''),
            'legal_basis': form.get('legal_basis', ''),
            'crossborder_transfer': form.get('crossborder_transfer', ''),
            'recipient_details': form.get('recipient_details', ''),
            'safeguards': form.get('safeguards', ''),
            'retained_in_accordance': form.get('retained_in_accordance', ''),
            'reasons_not_adhering': form.get('reasons_not_adhering', ''),
            'notes_comments': form.get('notes_comments', '')
        }


def generate_ropa_records(wizard_data, user):
    """Generate ROPA records based on wizard data"""
    records_created = 0
    af = wizard_data.get('activity_form', {})
    org = wizard_data.get('organization', {})

    activity_name = af.get('activity_name') or 'Unnamed Activity'

    # Build deletion_procedures from retention policy answers
    retained = af.get('retained_in_accordance', '')
    reasons = af.get('reasons_not_adhering', '')
    if retained == 'No' and reasons:
        deletion_procedures = f"Not in accordance with policy. Reason: {reasons}"
    else:
        deletion_procedures = f"In accordance with policy: {retained}" if retained else ''

    record_data = {
        'processing_activity_name': activity_name,
        'created_by': user.id,
        'category': org.get('industry', 'General'),
        'description': af.get('notes_comments', ''),
        'department_function': af.get('department_function', ''),

        # Controller information (from org step)
        'controller_name': org.get('name', ''),
        'controller_contact': org.get('controller_contact', ''),
        'controller_address': org.get('controller_address', ''),

        # DPO information
        'dpo_name': org.get('dpo_name', ''),
        'dpo_contact': org.get('dpo_contact', ''),
        'dpo_address': org.get('dpo_address', ''),

        # Processor / recipient details
        'processor_name': af.get('recipient_details', ''),
        'processor_contact': '',
        'processor_address': '',

        # Processing details from activity form
        'processing_purpose': af.get('processing_purpose', ''),
        'legal_basis': af.get('legal_basis', ''),
        'legitimate_interests': af.get('reasons_not_adhering', ''),
        'data_subjects': af.get('data_subjects', ''),
        'data_categories': af.get('data_categories', ''),
        'special_categories': '',
        'recipients': af.get('recipients', ''),
        'third_country_transfers': af.get('crossborder_transfer', ''),
        'safeguards': af.get('safeguards', ''),
        'retention_period': af.get('retention_period', ''),
        'deletion_procedures': deletion_procedures,
        'security_measures': af.get('security_measures', ''),

        'status': 'Under Review'
    }

    record = models.ROPARecord(**record_data)
    db.session.add(record)
    records_created += 1

    # Trigger notifications and health checks
    try:
        if has_feature(user, 'has_alerts'):
            officers = models.User.query.filter_by(role='Privacy Officer').all()
            notify_new_activity(record, user, officers, db, models.Notification)
    except Exception:
        pass

    try:
        if has_feature(user, 'has_health_engine'):
            run_health_checks([record], user, db, models.Notification)
    except Exception:
        pass

    db.session.commit()
    return records_created


def suggest_legal_basis(activity):
    """Suggest legal basis based on activity type"""
    suggestions = {
        'marketing': 'Consent',
        'hr': 'Contract',
        'customer_onboarding': 'Contract',
        'analytics': 'Legitimate interest'
    }
    
    activity_lower = activity.lower()
    for key, basis in suggestions.items():
        if key in activity_lower:
            return basis
    
    return 'Legitimate interest'  # Default


def assess_risk_level(activity, wizard_data):
    """Assess risk level based on activity and data"""
    risk_factors = []
    
    # Check for sensitive data
    data_categories = wizard_data.get('data_categories', [])
    if 'Health data (sensitive)' in data_categories:
        risk_factors.append('sensitive_data')
    
    # Check for international transfers
    if wizard_data.get('transfers', {}).get('international_transfers') == 'yes':
        risk_factors.append('international_transfer')
    
    # Check for third parties
    if wizard_data.get('third_parties'):
        risk_factors.append('third_party_sharing')
    
    if len(risk_factors) >= 2:
        return 'High'
    elif len(risk_factors) == 1:
        return 'Medium'
    else:
        return 'Low'

@app.route('/edit-activity/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit_activity(record_id):
    """Edit existing ROPA activity in Excel format"""
    record = models.ROPARecord.query.get_or_404(record_id)

    # Check permissions
    if current_user.role == 'Privacy Champion' and record.created_by != current_user.id:
        abort(403)

    if request.method == 'POST':
        # Update all record fields from Excel-like form
        record.processing_activity_name = request.form.get('processing_activity_name', '')
        record.category = request.form.get('category', '')
        record.description = request.form.get('description', '')
        record.department_function = request.form.get('department_function', '')
        record.controller_name = request.form.get('controller_name', '')
        record.controller_contact = request.form.get('controller_contact', '')
        record.controller_address = request.form.get('controller_address', '')
        record.dpo_name = request.form.get('dpo_name', '')
        record.dpo_contact = request.form.get('dpo_contact', '')
        record.dpo_address = request.form.get('dpo_address', '')
        record.processor_name = request.form.get('processor_name', '')
        record.processor_contact = request.form.get('processor_contact', '')
        record.processor_address = request.form.get('processor_address', '')
        record.processing_purpose = request.form.get('processing_purpose', '')
        record.legal_basis = request.form.get('legal_basis', '')
        record.legitimate_interests = request.form.get('legitimate_interests', '')
        
        # Handle checkbox groups for data categories and subjects
        if request.form.getlist('data_categories'):
            record.data_categories = ', '.join(request.form.getlist('data_categories'))
        else:
            record.data_categories = ''
            
        if request.form.getlist('special_categories'):
            record.special_categories = ', '.join(request.form.getlist('special_categories'))
        else:
            record.special_categories = ''
            
        if request.form.getlist('data_subjects'):
            record.data_subjects = ', '.join(request.form.getlist('data_subjects'))
        else:
            record.data_subjects = ''
            
        record.recipients = request.form.get('recipients', '')
        record.third_country_transfers = request.form.get('third_country_transfers', '')
        
        # Handle checkbox groups for safeguards and security measures
        if request.form.getlist('safeguards'):
            record.safeguards = ', '.join(request.form.getlist('safeguards'))
        else:
            record.safeguards = ''
            
        if request.form.getlist('security_measures'):
            record.security_measures = ', '.join(request.form.getlist('security_measures'))
        else:
            record.security_measures = ''
            
        record.retention_period = request.form.get('retention_period', '')
        record.deletion_procedures = request.form.get('deletion_procedures', '')
        record.breach_likelihood = request.form.get('breach_likelihood', '')
        record.breach_impact = request.form.get('breach_impact', '')
        record.risk_level = request.form.get('risk_level', '')
        record.dpia_required = bool(int(request.form.get('dpia_required', '0')))
        record.dpia_outcome = request.form.get('dpia_outcome', '')
        
        # Handle status update
        if request.form.get('status'):
            record.status = request.form.get('status')
        
        record.updated_at = datetime.utcnow()

        try:
            db.session.commit()

            # Save version history snapshot for Growth+ tiers
            if has_feature(current_user, 'has_version_history'):
                try:
                    snapshot = json.dumps({
                        'processing_activity_name': record.processing_activity_name,
                        'category': record.category,
                        'description': record.description,
                        'legal_basis': record.legal_basis,
                        'risk_level': record.risk_level,
                        'status': record.status,
                    })
                    history = models.ROPAVersionHistory(
                        ropa_record_id=record.id,
                        changed_by=current_user.id,
                        change_summary=f'Updated by {current_user.email}',
                        snapshot=snapshot,
                    )
                    db.session.add(history)
                    db.session.commit()
                except Exception:
                    pass

            log_audit_event('ROPA Updated', current_user.email, f'Updated ROPA record: {record.processing_activity_name}')

            # Run health engine for Enterprise users after edit
            try:
                if has_feature(current_user, 'has_health_engine'):
                    run_health_checks([record], current_user, db, models.Notification)
            except Exception:
                pass

            flash('ROPA record updated successfully in Excel format', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating record: {str(e)}', 'error')
            print(f"Error updating record: {str(e)}")

    options = get_predefined_options()
    return render_template('ropa_edit_excel.html', record=record, options=options)

@app.route('/view-activity/<int:record_id>')
@login_required
def view_activity(record_id):
    """View ROPA activity details in Excel format"""
    record = models.ROPARecord.query.get_or_404(record_id)

    # Check permissions
    if current_user.role == 'Privacy Champion' and record.created_by != current_user.id:
        abort(403)

    # Get custom fields and their data for this record
    from custom_tab_automation import get_approved_custom_fields_by_category
    from custom_tab_automation import get_custom_data_for_record
    try:
        custom_fields = get_approved_custom_fields_by_category()
        custom_data = get_custom_data_for_record(record.id)
    except:
        custom_fields = {}
        custom_data = {}

    return render_template('ropa_view_excel.html', record=record, custom_fields=custom_fields, custom_data=custom_data)

@app.route('/view-all-ropa-excel')
@login_required
def view_all_ropa_excel():
    """View all uploaded ROPA files in Excel format (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)
    
    # Clean up any duplicate sheets in the database first
    deleted_count = cleanup_duplicate_sheets()
    if deleted_count > 0:
        print(f"Cleaned up {deleted_count} duplicate sheets")
    
    # Get all uploaded Excel files with their sheet data
    uploaded_files = models.ExcelFileData.query.order_by(models.ExcelFileData.upload_timestamp.desc()).all()
    # Provide a fallback display name for unnamed sheets (A, B, C...)
    import string
    for file in uploaded_files:
        for idx, sheet in enumerate(file.sheets):
            raw_name = (sheet.sheet_name or '').strip()
            lower_raw = raw_name.lower()
            # Treat empty, generic 'unnamed' or patterns like 'unnamed: 0' as missing
            if not raw_name or lower_raw.startswith('unnamed') or lower_raw in ['nan', 'none']:
                letter = string.ascii_uppercase[idx % 26]
                suffix = '' if idx < 26 else str((idx // 26))
                sheet.display_name = f"{letter}{suffix}"
            else:
                sheet.display_name = raw_name

    generated_records = models.ROPARecord.query.order_by(models.ROPARecord.updated_at.desc()).all()
    log_audit_event('View Uploaded ROPA Excel', current_user.email, 'Viewed all uploaded ROPA files in Excel format')
    return render_template('view_all_ropa_excel.html', uploaded_files=uploaded_files, generated_records=generated_records, current_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/edit-all-ropa-excel', methods=['GET', 'POST'])
@login_required
def edit_all_ropa_excel():
    """Edit all uploaded ROPA files in Excel format (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)
    
    if request.method == 'POST':
        try:
            import json
            updated_count = 0
            
            # Get all form data
            form_data = request.form.to_dict()
            
            # Process each sheet update - check new_row FIRST because _new_row_ contains _row_
            for key, value in form_data.items():
                # Process new rows data FIRST (more specific pattern)
                if key.startswith('sheet_') and '_new_row_' in key and '_col_' in key:
                    # Parse sheet_ID_new_row_X_col_Y format
                    parts = key.replace('sheet_', '').split('_')
                    if len(parts) >= 5 and value.strip():  # Only process if value is not empty
                        try:
                            sheet_id = int(parts[0])
                            new_row_idx = int(parts[3])
                            col_name = '_'.join(parts[5:])
                        except (ValueError, IndexError):
                            continue
                        
                        # Get the sheet and add new data
                        sheet = models.ExcelSheetData.query.get(sheet_id)
                        if sheet:
                            sheet_data = json.loads(sheet.sheet_data)
                            
                            # Initialize new rows dictionary if needed
                            if not hasattr(sheet, '_new_rows'):
                                sheet._new_rows = {}
                            if new_row_idx not in sheet._new_rows:
                                # Create new row with all columns from original structure
                                if sheet_data and len(sheet_data) > 0:
                                    sheet._new_rows[new_row_idx] = {col: '' for col in sheet_data[0].keys()}
                                else:
                                    sheet._new_rows[new_row_idx] = {}
                            
                            # Set the value for this column in the new row
                            sheet._new_rows[new_row_idx][col_name] = value
                
                # Process existing data rows (less specific pattern)
                elif key.startswith('sheet_') and '_row_' in key and '_col_' in key:
                    # Parse sheet_ID_row_X_col_Y format
                    parts = key.replace('sheet_', '').split('_')
                    if len(parts) >= 4:
                        try:
                            sheet_id = int(parts[0])
                            row_idx = int(parts[2])
                            col_name = '_'.join(parts[4:])  # Join remaining parts for column name
                        except (ValueError, IndexError):
                            continue
                        
                        # Get the sheet and update the data
                        sheet = models.ExcelSheetData.query.get(sheet_id)
                        if sheet:
                            sheet_data = json.loads(sheet.sheet_data)
                            if row_idx < len(sheet_data) and col_name in sheet_data[row_idx]:
                                sheet_data[row_idx][col_name] = value
                                sheet.sheet_data = json.dumps(sheet_data)
                                db.session.add(sheet)  # Ensure the sheet is tracked
                                updated_count += 1
            
            # Add completed new rows to sheet data
            for sheet_id, sheet in [(s.id, s) for s in models.ExcelSheetData.query.all() if hasattr(s, '_new_rows')]:
                sheet_data = json.loads(sheet.sheet_data)
                for new_row_idx, new_row_data in sheet._new_rows.items():
                    # Only add rows that have at least one non-empty value
                    if any(v.strip() for v in new_row_data.values() if v):
                        sheet_data.append(new_row_data)
                        updated_count += 1
                
                # Update sheet with new data
                sheet.sheet_data = json.dumps(sheet_data)
                sheet.row_count = len(sheet_data)
            
            db.session.commit()
            log_audit_event('Edit Uploaded ROPA Excel', current_user.email, f'Updated {updated_count} uploaded file fields')
            flash(f'Successfully updated {updated_count} uploaded file fields!', 'success')
            
            # Redirect to view all to show the updated data
            return redirect(url_for('view_all_ropa_excel'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating uploaded files: {str(e)}', 'error')
            print(f"Error updating uploaded files: {str(e)}")
    
    # Get all uploaded Excel files with their sheet data for editing
    # Clean up any duplicate sheets in the database first
    deleted_count = cleanup_duplicate_sheets()
    if deleted_count > 0:
        print(f"Cleaned up {deleted_count} duplicate sheets")
    
    uploaded_files = models.ExcelFileData.query.order_by(models.ExcelFileData.upload_timestamp.desc()).all()
    # Provide a fallback display name for unnamed sheets (A, B, C...)
    import string
    def excel_col_label(index):
        # Convert 0-based index to Excel-style column labels: 0->A, 25->Z, 26->AA
        label = ''
        i = index
        while True:
            label = chr((i % 26) + 65) + label
            i = i // 26 - 1
            if i < 0:
                break
        return label

    for file in uploaded_files:
        for idx, sheet in enumerate(file.sheets):
            raw_name = (sheet.sheet_name or '').strip()
            lower_raw = raw_name.lower()
            if not raw_name or lower_raw.startswith('unnamed') or lower_raw in ['nan', 'none']:
                letter = string.ascii_uppercase[idx % 26]
                suffix = '' if idx < 26 else str((idx // 26))
                sheet.display_name = f"{letter}{suffix}"
            else:
                sheet.display_name = raw_name

            # Build display column labels mapping for this sheet
            try:
                sheet_data = json.loads(sheet.sheet_data) if sheet.sheet_data else []
            except Exception:
                sheet_data = []

            columns = []
            if sheet_data and isinstance(sheet_data, list) and len(sheet_data) > 0:
                columns = list(sheet_data[0].keys())
            else:
                # fall back to stored columns JSON
                try:
                    columns = json.loads(sheet.columns) if sheet.columns else []
                except Exception:
                    columns = []

            display_columns = {}
            for c_idx, col in enumerate(columns):
                col_name = (col or '').strip()
                lcol = col_name.lower()
                if not col_name or lcol.startswith('unnamed') or lcol in ['nan', 'none']:
                    display_columns[col] = excel_col_label(c_idx)
                else:
                    display_columns[col] = col_name

            sheet.display_columns = display_columns

    generated_records = models.ROPARecord.query.order_by(models.ROPARecord.updated_at.desc()).all()
    return render_template('edit_all_ropa_excel.html', uploaded_files=uploaded_files, generated_records=generated_records)

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
        import traceback
        print(f"Template generation error: {str(e)}")
        traceback.print_exc()
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
                # Process the uploaded file
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
    if not has_feature(current_user, 'has_export'):
        flash('Export functionality is not available on your current plan. Please upgrade to access Excel/PDF downloads.', 'error')
        return redirect(url_for('pricing'))
    try:
        export_format = request.args.get('format', 'excel')
        include_drafts = request.args.get('include_drafts') == 'true'
        include_rejected = request.args.get('include_rejected') == 'true'

        # Special handling for complete Excel export
        if export_format == 'excel':
            export_format = 'excel_complete'  # Use the enhanced export

        file_path, filename = generate_export(
            current_user.email, 
            current_user.role, 
            export_format,
            include_drafts,
            include_rejected
        )

        # Get information about what was exported for user feedback
        from models import ExcelFileData, User
        user = User.query.filter_by(email=current_user.email).first()
        if user:
            if current_user.role == 'Privacy Officer':
                excel_files = ExcelFileData.query.all()
            else:
                excel_files = ExcelFileData.query.filter_by(uploaded_by=user.id).all()

            if excel_files:
                sheet_info = []
                for excel_file in excel_files:
                    sheet_names = json.loads(excel_file.sheet_names)
                    sheet_info.extend(sheet_names)

                flash(f"Export successful! Included {len(excel_files)} original file(s) with sheets: {', '.join(sheet_info[:10])}{'...' if len(sheet_info) > 10 else ''}", "success")
            else:
                flash("Export successful! Included system ROPA records.", "success")

        log_audit_event('Data Export', current_user.email, f'Exported data in {export_format} format with original sheet preservation')

        return send_file(file_path, as_attachment=True, download_name=filename)

    except Exception as e:
        flash(f'Error generating export: {str(e)}', 'error')
        if current_user.role == 'Privacy Officer':
            return redirect(url_for('privacy_officer_dashboard'))
        else:
            return redirect(url_for('privacy_champion_dashboard'))

@app.route('/export-complete-excel')
@login_required
def export_complete_excel():
    """Export complete Excel file with all original sheets plus updates"""
    try:
        from file_handler import export_excel_with_all_sheets
        file_path, filename = export_excel_with_all_sheets(current_user.email, current_user.role, include_updates=True)
        log_audit_event('Complete Excel Exported', current_user.email, 'Exported complete Excel with all sheets and updates')
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        flash(f'Error generating complete Excel export: {str(e)}', 'error')
        if current_user.role == 'Privacy Officer':
            return redirect(url_for('privacy_officer_dashboard'))
        else:
            return redirect(url_for('privacy_champion_dashboard'))

@app.route('/view-saved-ropa')
@login_required
def view_saved_ropa():
    """View saved ROPA records (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)
    
    try:
        # Get all ROPA records for the current user's organization
        saved_records = models.ROPARecord.query.join(models.User, models.ROPARecord.created_by == models.User.id).filter(models.User.department == current_user.department).order_by(models.ROPARecord.updated_at.desc()).all()
        
        log_audit_event('View Saved ROPA', current_user.email, 'Viewed saved ROPA records')
        return render_template('view_saved_ropa.html', 
                             saved_records=saved_records,
                             total_saved=len(saved_records),
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        flash(f'Error loading saved ROPA records: {str(e)}', 'error')
        return redirect(url_for('privacy_officer_dashboard'))

@app.route('/system-help')
@login_required
def system_help():
    """System help and error guidance (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    # Check if user has access to help & support (not trial)
    tier = get_user_effective_tier(current_user)
    if tier == 'trial':
        flash('Help & Support is available on paid plans. Please upgrade for access to troubleshooting guides and system monitoring.', 'error')
        return redirect(url_for('pricing'))
    
    try:
        # Get recent error logs and common issues
        import traceback
        from audit_logger import get_recent_errors
        
        # Get system status information
        system_status = {
            'total_users': models.User.query.count(),
            'total_records': models.ROPARecord.query.count(),
            'upload_files': models.ExcelFileData.query.count(),
            'recent_logins': models.User.query.filter(models.User.last_login.isnot(None)).count(),
        }
        
        # Common troubleshooting tips
        troubleshooting_tips = [
            {
                'issue': 'Excel Upload Errors',
                'solution': 'Ensure Excel files are in .xlsx or .xls format with proper headers. Check that sheet names don\'t contain special characters.',
                'icon': 'fas fa-file-excel text-warning'
            },
            {
                'issue': 'Login Issues',
                'solution': 'Verify email and password are correct. Ensure consent checkbox is checked. Contact administrator if account is locked.',
                'icon': 'fas fa-sign-in-alt text-info'
            },
            {
                'issue': 'ROPA Record Creation Fails',
                'solution': 'Required fields must be filled. Check that processing activity name is unique. Verify user has proper permissions.',
                'icon': 'fas fa-file-alt text-danger'
            },
            {
                'issue': 'Export Problems',
                'solution': 'Check that records exist to export. Verify browser allows file downloads. Try different export formats.',
                'icon': 'fas fa-download text-success'
            },
            {
                'issue': 'Performance Issues',
                'solution': 'Large Excel files may take time to process. Close unnecessary browser tabs. Clear browser cache if needed.',
                'icon': 'fas fa-tachometer-alt text-primary'
            }
        ]
        
        log_audit_event('System Help Accessed', current_user.email, 'Accessed system help and troubleshooting')
        return render_template('system_help.html', 
                             system_status=system_status,
                             troubleshooting_tips=troubleshooting_tips,
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        flash(f'Error loading system help: {str(e)}', 'error')
        return redirect(url_for('privacy_officer_dashboard'))


@app.route('/audit-logs')
@login_required
def audit_logs():
    """View audit logs (Privacy Officer + Enterprise tier only)"""
    if current_user.role != 'Privacy Officer':
        log_security_event('Unauthorized Access', current_user.email, 
                          f'Attempted to access audit logs without Privacy Officer role')
        abort(403)

    if not has_feature(current_user, 'has_audit_logs'):
        flash('Audit Logs are available on the Enterprise plan. Please upgrade to access this feature.', 'error')
        return redirect(url_for('pricing'))

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
    """User management page (Privacy Officer + Growth/Enterprise only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    if not has_feature(current_user, 'has_multi_user'):
        flash('Multi-user management is available on the Growth and Enterprise plans. Please upgrade to add team members.', 'error')
        return redirect(url_for('pricing'))

    users = models.User.query.all()
    return render_template('user_management.html', users=users)

@app.route('/add-user', methods=['POST'])
@login_required
def add_user():
    """Add new user (Privacy Officer + Growth/Enterprise only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    if not has_feature(current_user, 'has_multi_user'):
        flash('Multi-user management is available on the Growth and Enterprise plans.', 'error')
        return redirect(url_for('pricing'))

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
    """Edit user (Privacy Officer + Growth/Enterprise only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)
    if not has_feature(current_user, 'has_multi_user'):
        flash('Multi-user management is available on the Growth and Enterprise plans.', 'error')
        return redirect(url_for('pricing'))

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
    """Delete user (Privacy Officer + Growth/Enterprise only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)
    if not has_feature(current_user, 'has_multi_user'):
        flash('Multi-user management is available on the Growth and Enterprise plans.', 'error')
        return redirect(url_for('pricing'))

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

# API endpoints for automation features — gated by subscription tier
@app.route('/api/auto-classify', methods=['POST'])
@login_required
def api_auto_classify():
    """Auto-classification — Enterprise only"""
    if not has_feature(current_user, 'has_automation'):
        return jsonify({'error': 'upgrade_required', 'message': 'Full automation is available on the Enterprise plan.'}), 403
    data = request.get_json()
    description = data.get('description', '')
    classification = auto_classify_data(description)
    return jsonify({'classification': classification})

@app.route('/api/suggest-purpose', methods=['POST'])
@login_required
def api_suggest_purpose():
    """Purpose suggestion — Enterprise only"""
    if not has_feature(current_user, 'has_automation'):
        return jsonify({'error': 'upgrade_required', 'message': 'Full automation is available on the Enterprise plan.'}), 403
    data = request.get_json()
    department = data.get('department', '')
    category = data.get('category', '')
    suggestion = suggest_processing_purpose(department, category)
    return jsonify({'suggestion': suggestion})

@app.route('/api/assess-risk', methods=['POST'])
@login_required
def api_assess_risk():
    """Risk assessment — Growth+ (basic risk flagging)"""
    if not has_feature(current_user, 'has_dashboard'):
        return jsonify({'error': 'upgrade_required', 'message': 'Risk assessment is available on the Growth and Enterprise plans.'}), 403
    data = request.get_json()
    data_categories = data.get('data_categories', '')
    special_categories = data.get('special_categories', '')
    risk_assessment = assess_risk(data_categories, special_categories)
    return jsonify({'risk_assessment': risk_assessment})

@app.route('/api/suggest-security', methods=['POST'])
@login_required
def api_suggest_security():
    """Security suggestions — Enterprise only"""
    if not has_feature(current_user, 'has_automation'):
        return jsonify({'error': 'upgrade_required', 'message': 'Full automation is available on the Enterprise plan.'}), 403
    data = request.get_json()
    data_categories = data.get('data_categories', '')
    risk_level = data.get('risk_level', 'Medium')
    suggestions = suggest_security_measures(data_categories, risk_level)
    return jsonify({'suggestions': suggestions})

@app.route('/api/check-privacy-officer')
def api_check_privacy_officer():
    """API endpoint to check if Privacy Officer exists"""
    privacy_officer_exists = models.User.query.filter_by(role='Privacy Officer').first() is not None
    return jsonify({'exists': privacy_officer_exists})

def integrate_custom_activities(record):
    """Integrate approved custom field data into main ROPA record"""
    try:
        # Get custom field data for this record
        from custom_tab_automation import get_custom_data_for_record
        custom_data = get_custom_data_for_record(record.id)

        if not custom_data:
            return

        # Log the integration attempt
        log_audit_event('Custom Activities Integration', current_user.email, 
                       f'Integrated custom field data into ROPA {record.processing_activity_name}')

    except Exception as e:
        # If custom field integration fails, just log it and continue
        print(f"Custom field integration error: {str(e)}")
        log_audit_event('Custom Activities Integration Error', current_user.email, 
                       f'Error integrating custom fields for ROPA {record.processing_activity_name}: {str(e)}')

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
    from custom_tab_automation import submit_custom_tab_for_review
    result = submit_custom_tab_for_review(field_id)

    if result['success']:
        flash('Custom field submitted successfully for Privacy Officer review!', 'success')
    else:
        flash(f'Error submitting custom field: {result["message"]}', 'error')

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
    from custom_tab_automation import get_approved_custom_fields_by_category
    from custom_tab_automation import get_custom_data_for_record
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
    from custom_tab_automation import get_approved_custom_fields_by_category
    from custom_tab_automation import get_custom_data_for_record
    from custom_tab_automation import update_custom_data_for_record
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
def view_all_ropa():
    # Get filter parameters
    status_filter = request.args.get('status', 'All')

    # Build query based on user role using SQLAlchemy models
    if current_user.role == "Privacy Champion":
        # Privacy Champions see their own records AND approved records they can edit (in their department)
        if status_filter == 'All':
            query = models.ROPARecord.query.filter(
                db.or_(
                    models.ROPARecord.created_by == current_user.id,
                    db.and_(
                        models.ROPARecord.status == 'Approved',
                        models.ROPARecord.department_function == current_user.department
                    )
                )
            )
        else:
            query = models.ROPARecord.query.filter(
                db.and_(
                    db.or_(
                        models.ROPARecord.created_by == current_user.id,
                        db.and_(
                            models.ROPARecord.status == 'Approved',
                            models.ROPARecord.department_function == current_user.department
                        )
                    ),
                    models.ROPARecord.status == status_filter
                )
            )
    else:
        # Privacy Officers and Admins see all records
        if status_filter == 'All':
            query = models.ROPARecord.query
        else:
            query = models.ROPARecord.query.filter(models.ROPARecord.status == status_filter)

    records = query.order_by(models.ROPARecord.created_at.desc()).all()

    print(f"DEBUG: Found {len(records)} records for user {current_user.email} (role: {current_user.role})")

    # Convert to list of dictionaries for template compatibility
    records_list = []
    for record in records:
        creator = models.User.query.get(record.created_by)
        creator_email = creator.email if creator else 'Unknown'

        record_dict = {
            'id': record.id,
            'processing_activity_name': record.processing_activity_name,
            'category': record.category,
            'description': record.description,
            'department_function': record.department_function,
            'controller_name': record.controller_name,
            'controller_contact': record.controller_contact,
            'controller_address': record.controller_address,
            'dpo_name': record.dpo_name,
            'dpo_contact': record.dpo_contact,
            'dpo_address': record.dpo_address,
            'processor_name': record.processor_name,
            'processor_contact': record.processor_contact,
            'processor_address': record.processor_address,
            'representative_name': record.representative_name,
            'representative_contact': record.representative_contact,
            'representative_address': record.representative_address,
            'processing_purpose': record.processing_purpose,
            'legal_basis': record.legal_basis,
            'legitimate_interests': record.legitimate_interests,
            'data_categories': record.data_categories,
            'special_categories': record.special_categories,
            'data_subjects': record.data_subjects,
            'recipients': record.recipients,
            'third_country_transfers': record.third_country_transfers,
            'safeguards': record.safeguards,
            'retention_period': record.retention_period,
            'security_measures': record.security_measures,
            'breach_likelihood': record.breach_likelihood,
            'breach_impact': record.breach_impact,
            'risk_level': record.risk_level,
            'dpia_required': record.dpia_required,
            'dpia_outcome': record.dpia_outcome,
            'status': record.status,
            'created_by': creator_email,
            'created_at': record.created_at,
            'updated_at': record.updated_at
        }
        records_list.append(record_dict)

    return render_template('ropa_view.html', 
                         records=records_list, 
                         current_status=status_filter,
                         user_role=current_user.role)


@app.route('/pricing')
def pricing():
    """Public pricing page"""
    return render_template('pricing.html', tiers=TIER_CONFIG)


@app.route('/test_tier/<tier>')
def test_tier(tier):
    """Test a subscription tier - preview without login required"""
    if tier not in TIER_CONFIG:
        abort(404)
    session['test_tier'] = tier
    session['test_mode'] = True
    flash(f'Testing {TIER_CONFIG[tier]["name"]} plan. You can now see what users on this plan experience.', 'info')
    return redirect(url_for('test_tier_preview', tier=tier))


@app.route('/test-tier-preview/<tier>')
def test_tier_preview(tier):
    """Public preview of a subscription tier"""
    if tier not in TIER_CONFIG:
        abort(404)
    
    tier_config = TIER_CONFIG[tier]
    
    return render_template('test_tier_preview.html', 
                         tier=tier,
                         tier_config=tier_config,
                         tiers=TIER_CONFIG)


@app.route('/exit_test_mode')
@login_required
def exit_test_mode():
    """Exit test mode and return to actual subscription tier"""
    if 'test_tier' in session:
        del session['test_tier']
        flash('Exited test mode. Returned to your actual subscription tier.', 'info')
    return redirect(url_for('privacy_officer_dashboard'))


@app.route('/subscription')
@login_required
def subscription():
    """Subscription management page (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)
    users = models.User.query.all()
    return render_template('subscription_manage.html', users=users, tiers=TIER_CONFIG)


@app.route('/subscription/update/<int:user_id>', methods=['POST'])
@login_required
def update_subscription(user_id):
    """Update a user's subscription tier (Privacy Officer only)"""
    if current_user.role != 'Privacy Officer':
        abort(403)

    user = models.User.query.get_or_404(user_id)
    new_tier = request.form.get('tier')
    if new_tier not in TIER_CONFIG:
        flash('Invalid subscription tier.', 'error')
        return redirect(url_for('subscription'))

    user.subscription_tier = new_tier
    if new_tier != 'trial':
        user.subscription_start_date = datetime.utcnow()
    db.session.commit()

    log_audit_event('Subscription Updated', current_user.email,
                    f'Updated {user.email} subscription to {new_tier}')
    flash(f'{user.email} subscription updated to {TIER_CONFIG[new_tier]["name"]}.', 'success')
    return redirect(url_for('subscription'))


@app.route('/version-history/<int:record_id>')
@login_required
def version_history(record_id):
    """View version history for a ROPA record (Growth+ only)"""
    if not has_feature(current_user, 'has_version_history'):
        flash('Version History is available on the Growth and Enterprise plans. Please upgrade to access this feature.', 'error')
        return redirect(url_for('pricing'))

    record = models.ROPARecord.query.get_or_404(record_id)

    if current_user.role == 'Privacy Champion' and record.created_by != current_user.id:
        abort(403)

    history = models.ROPAVersionHistory.query.filter_by(
        ropa_record_id=record_id
    ).order_by(models.ROPAVersionHistory.changed_at.desc()).all()

    return render_template('version_history.html', record=record, history=history)


@app.route('/notifications')
@login_required
def notifications():
    """View all in-app notifications (Growth+ only)"""
    if not has_feature(current_user, 'has_alerts'):
        flash('In-app alerts are available on the Growth and Enterprise plans.', 'error')
        return redirect(url_for('pricing'))

    all_notifications = models.Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(models.Notification.created_at.desc()).limit(100).all()

    return render_template('notifications.html', notifications=all_notifications)


@app.route('/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = models.Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        abort(403)
    notif.is_read = True
    db.session.commit()
    return redirect(request.referrer or url_for('notifications'))


@app.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    models.Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications'))


@app.route('/health-check', methods=['POST'])
@login_required
def run_health_check():
    """Manually trigger the ROPA Health Engine (Enterprise only)"""
    if not has_feature(current_user, 'has_health_engine'):
        flash('The ROPA Health Engine is an Enterprise feature. Please upgrade.', 'error')
        return redirect(url_for('pricing'))

    if current_user.role == 'Privacy Officer':
        records = models.ROPARecord.query.all()
    else:
        records = models.ROPARecord.query.filter_by(created_by=current_user.id).all()

    alerts_created = run_health_checks(records, current_user, db, models.Notification)

    # Also check vendors
    vendors = models.Vendor.query.filter_by(created_by=current_user.id).all()
    vendor_alerts = check_vendor_alerts(vendors, current_user, db, models.Notification)

    total = alerts_created + vendor_alerts
    if total:
        flash(f'Health check complete — {total} new alert(s) created. Check your notifications.', 'warning')
    else:
        flash('Health check complete — no new issues found.', 'success')

    return redirect(request.referrer or url_for('privacy_officer_dashboard'))


@app.route('/compliance-report')
@login_required
def compliance_report():
    """View per-record compliance scores (Enterprise only)"""
    if not has_feature(current_user, 'has_compliance_score'):
        flash('Compliance Scoring is an Enterprise feature. Please upgrade to access it.', 'error')
        return redirect(url_for('pricing'))

    if current_user.role == 'Privacy Officer':
        records = models.ROPARecord.query.all()
    else:
        records = models.ROPARecord.query.filter_by(created_by=current_user.id).all()

    scored_records = []
    for record in records:
        score_data = calculate_compliance_score(record)
        scored_records.append({
            'record': record,
            'score': score_data,
        })

    scored_records.sort(key=lambda x: x['score']['score'])
    org_compliance = calculate_org_compliance_score(records)

    return render_template('compliance_report.html',
                           scored_records=scored_records,
                           org_compliance=org_compliance)


@app.route('/vendors')
@login_required
def vendors():
    """Vendor tracking page (Enterprise only)"""
    if not has_feature(current_user, 'has_vendor_tracking'):
        flash('Vendor Tracking is an Enterprise feature. Please upgrade to access it.', 'error')
        return redirect(url_for('pricing'))

    all_vendors = models.Vendor.query.order_by(models.Vendor.name).all()
    return render_template('vendors.html', vendors=all_vendors)


@app.route('/vendors/add', methods=['GET', 'POST'])
@login_required
def add_vendor():
    """Add a vendor (Enterprise only)"""
    if not has_feature(current_user, 'has_vendor_tracking'):
        flash('Vendor Tracking is an Enterprise feature.', 'error')
        return redirect(url_for('pricing'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Vendor name is required.', 'error')
            return render_template('vendors_form.html', vendor=None)

        expiry_str = request.form.get('contract_expiry', '').strip()
        contract_expiry = None
        if expiry_str:
            try:
                contract_expiry = datetime.strptime(expiry_str, '%Y-%m-%d')
            except ValueError:
                pass

        country = request.form.get('country', '').strip()
        from health_engine import SAFE_COUNTRIES
        risk = 'Low' if country in SAFE_COUNTRIES else ('High' if country else 'Unknown')

        vendor = models.Vendor(
            name=name,
            country=country,
            services=request.form.get('services', ''),
            contract_expiry=contract_expiry,
            risk_level=risk,
            created_by=current_user.id,
        )
        db.session.add(vendor)
        db.session.commit()

        # Run vendor alerts immediately
        check_vendor_alerts([vendor], current_user, db, models.Notification)

        log_audit_event('Vendor Added', current_user.email, f'Added vendor: {name}')
        flash(f'Vendor "{name}" added successfully.', 'success')
        return redirect(url_for('vendors'))

    return render_template('vendors_form.html', vendor=None)


@app.route('/vendors/edit/<int:vendor_id>', methods=['GET', 'POST'])
@login_required
def edit_vendor(vendor_id):
    """Edit a vendor (Enterprise only)"""
    if not has_feature(current_user, 'has_vendor_tracking'):
        flash('Vendor Tracking is an Enterprise feature.', 'error')
        return redirect(url_for('pricing'))

    vendor = models.Vendor.query.get_or_404(vendor_id)

    if request.method == 'POST':
        vendor.name = request.form.get('name', vendor.name).strip()
        vendor.country = request.form.get('country', '').strip()
        vendor.services = request.form.get('services', '')

        expiry_str = request.form.get('contract_expiry', '').strip()
        if expiry_str:
            try:
                vendor.contract_expiry = datetime.strptime(expiry_str, '%Y-%m-%d')
            except ValueError:
                vendor.contract_expiry = None
        else:
            vendor.contract_expiry = None

        from health_engine import SAFE_COUNTRIES
        vendor.risk_level = 'Low' if vendor.country in SAFE_COUNTRIES else ('High' if vendor.country else 'Unknown')
        vendor.updated_at = datetime.utcnow()
        db.session.commit()

        log_audit_event('Vendor Updated', current_user.email, f'Updated vendor: {vendor.name}')
        flash(f'Vendor "{vendor.name}" updated.', 'success')
        return redirect(url_for('vendors'))

    return render_template('vendors_form.html', vendor=vendor)


@app.route('/vendors/delete/<int:vendor_id>', methods=['POST'])
@login_required
def delete_vendor(vendor_id):
    """Delete a vendor (Enterprise only)"""
    if not has_feature(current_user, 'has_vendor_tracking'):
        abort(403)

    vendor = models.Vendor.query.get_or_404(vendor_id)
    name = vendor.name
    db.session.delete(vendor)
    db.session.commit()
    flash(f'Vendor "{name}" deleted.', 'success')
    return redirect(url_for('vendors'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)