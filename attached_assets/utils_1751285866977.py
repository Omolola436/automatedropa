import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

def get_predefined_options(option_type):
    """Get predefined options for form fields"""
    
    options = {
        'categories': [
            "Human Resources",
            "Marketing",
            "Sales",
            "Customer Service",
            "IT Security",
            "Finance",
            "Operations",
            "Legal",
            "Research & Development",
            "Training",
            "Administration"
        ],
        
        'legal_basis': [
            "Consent",
            "Contract",
            "Legal Obligation",
            "Vital Interests",
            "Public Task",
            "Legitimate Interests"
        ],
        
        'data_categories': [
            "Contact Information",
            "Identity Data",
            "Employment Data",
            "Financial Data",
            "Technical Data",
            "Usage Data",
            "Marketing Data",
            "Profile Data",
            "Location Data",
            "Communication Data",
            "Transaction Data",
            "Behavioral Data"
        ],
        
        'special_categories': [
            "Racial or Ethnic Origin",
            "Political Opinions",
            "Religious or Philosophical Beliefs",
            "Trade Union Membership",
            "Genetic Data",
            "Biometric Data",
            "Health Data",
            "Sex Life or Sexual Orientation",
            "Criminal Convictions"
        ],
        
        'data_subjects': [
            "Employees",
            "Job Applicants",
            "Customers",
            "Prospects",
            "Suppliers",
            "Visitors",
            "Website Users",
            "Newsletter Subscribers",
            "Former Employees",
            "Students",
            "Patients",
            "Members"
        ]
    }
    
    return options.get(option_type, [])

def format_datetime(dt_string):
    """Format datetime string for display"""
    try:
        dt = pd.to_datetime(dt_string)
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return dt_string

def calculate_retention_deadline(created_date, retention_period):
    """Calculate retention deadline based on creation date and period"""
    try:
        created = pd.to_datetime(created_date)
        
        # Parse retention period (simplified)
        if 'year' in retention_period.lower():
            years = int(''.join(filter(str.isdigit, retention_period)) or 1)
            deadline = created + timedelta(days=years * 365)
        elif 'month' in retention_period.lower():
            months = int(''.join(filter(str.isdigit, retention_period)) or 1)
            deadline = created + timedelta(days=months * 30)
        elif 'day' in retention_period.lower():
            days = int(''.join(filter(str.isdigit, retention_period)) or 1)
            deadline = created + timedelta(days=days)
        else:
            # Default to 7 years if unclear
            deadline = created + timedelta(days=7 * 365)
        
        return deadline
    except:
        return None

def get_risk_level(breach_likelihood, breach_impact):
    """Calculate risk level based on likelihood and impact"""
    risk_matrix = {
        ('Low', 'Low'): 'Low',
        ('Low', 'Medium'): 'Low',
        ('Low', 'High'): 'Medium',
        ('Medium', 'Low'): 'Low',
        ('Medium', 'Medium'): 'Medium',
        ('Medium', 'High'): 'High',
        ('High', 'Low'): 'Medium',
        ('High', 'Medium'): 'High',
        ('High', 'High'): 'High'
    }
    
    return risk_matrix.get((breach_likelihood, breach_impact), 'Medium')

def validate_email(email):
    """Simple email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_record_id():
    """Generate unique record ID"""
    from datetime import datetime
    import random
    import string
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ROPA-{timestamp}-{random_suffix}"

def check_gdpr_compliance(record_data):
    """Check GDPR compliance of a ROPA record"""
    issues = []
    recommendations = []
    
    # Required fields check
    required_fields = [
        'processing_activity_name',
        'controller_name',
        'processing_purpose',
        'legal_basis',
        'data_categories',
        'data_subjects',
        'retention_period',
        'security_measures'
    ]
    
    for field in required_fields:
        field_value = record_data.get(field, '') or ''
        if not field_value.strip():
            issues.append(f"Missing required field: {field.replace('_', ' ').title()}")
    
    # Legal basis validation
    legal_basis = record_data.get('legal_basis', '') or ''
    legitimate_interests = record_data.get('legitimate_interests', '') or ''
    if legal_basis == 'Legitimate Interests' and not legitimate_interests.strip():
        issues.append("Legitimate interests must be specified when using this legal basis")
    
    # Special categories check
    special_categories = record_data.get('special_categories', '') or ''
    if special_categories.strip():
        if legal_basis not in ['Consent', 'Legal Obligation', 'Vital Interests']:
            recommendations.append("Special categories require explicit consent or specific legal basis")
    
    # Third country transfers
    third_country_transfers = record_data.get('third_country_transfers', '') or ''
    safeguards = record_data.get('safeguards', '') or ''
    if third_country_transfers.strip():
        if not safeguards.strip():
            issues.append("Third country transfers require appropriate safeguards")
    
    # Retention period validation
    retention_period = record_data.get('retention_period', '') or ''
    retention = retention_period.strip()
    if retention and 'indefinite' in retention.lower():
        recommendations.append("Indefinite retention periods should be avoided under GDPR")
    
    # Risk assessment
    likelihood = record_data.get('breach_likelihood', 'Medium')
    impact = record_data.get('breach_impact', 'Medium')
    risk_level = get_risk_level(likelihood, impact)
    
    if risk_level == 'High':
        recommendations.append("High-risk processing may require Data Protection Impact Assessment (DPIA)")
    
    return {
        'compliant': len(issues) == 0,
        'issues': issues,
        'recommendations': recommendations,
        'risk_level': risk_level
    }

def create_progress_indicator(current_step, total_steps):
    """Create a progress indicator for multi-step forms"""
    progress = current_step / total_steps
    
    st.progress(progress)
    st.caption(f"Step {current_step} of {total_steps}")

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def get_user_preferences():
    """Get user preferences from session state"""
    if 'user_preferences' not in st.session_state:
        st.session_state.user_preferences = {
            'theme': 'dark',
            'notifications': True,
            'auto_save': True,
            'export_format': 'excel'
        }
    
    return st.session_state.user_preferences

def save_user_preferences(preferences):
    """Save user preferences to session state"""
    st.session_state.user_preferences = preferences

def create_backup_data():
    """Create backup of important session data"""
    backup_data = {
        'form_data': st.session_state.get('ropa_form_data', {}),
        'user_email': st.session_state.get('user_email', ''),
        'current_page': st.session_state.get('current_page', 'dashboard'),
        'timestamp': datetime.now().isoformat()
    }
    
    return backup_data

def restore_backup_data(backup_data):
    """Restore session data from backup"""
    if backup_data:
        st.session_state.ropa_form_data = backup_data.get('form_data', {})
        st.session_state.current_page = backup_data.get('current_page', 'dashboard')
