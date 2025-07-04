"""
Utility functions for Privacy ROPA system
"""

def get_predefined_options():
    """Get predefined options for form fields"""
    
    return {
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
        
        'departments': [
            "HR",
            "IT", 
            "Marketing",
            "Sales",
            "Finance",
            "Legal",
            "Operations",
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

def validate_required_fields(form_data, draft=False):
    """Validate required fields in ROPA form"""
    
    required_fields = [
        'processing_activity_name',
        'controller_name', 
        'processing_purpose',
        'legal_basis',
        'data_categories',
        'data_subjects',
        'retention_period'
    ]
    
    # Less strict validation for drafts
    if draft:
        required_fields = ['processing_activity_name']
    
    missing_fields = []
    
    for field in required_fields:
        value = form_data.get(field, '')
        if not value or not str(value).strip():
            missing_fields.append(field.replace('_', ' ').title())
    
    return {
        'valid': len(missing_fields) == 0,
        'missing_fields': missing_fields
    }

def get_client_ip(request):
    """Get client IP address from request"""
    # Check for forwarded IP first (in case of proxy)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def format_datetime(dt_string):
    """Format datetime string for display"""
    try:
        from datetime import datetime
        if isinstance(dt_string, str):
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        else:
            dt = dt_string
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return str(dt_string)

def calculate_compliance_score(record):
    """Calculate compliance score for a ROPA record"""
    score = 0
    max_score = 10
    
    # Required fields check (50% of score)
    required_fields = [
        'processing_activity_name', 'controller_name', 'processing_purpose',
        'legal_basis', 'data_categories', 'data_subjects', 'retention_period'
    ]
    
    filled_required = sum(1 for field in required_fields if record.get(field, '').strip())
    score += (filled_required / len(required_fields)) * 5
    
    # Additional important fields (30% of score)
    important_fields = ['security_measures', 'dpo_name', 'recipients']
    filled_important = sum(1 for field in important_fields if record.get(field, '').strip())
    score += (filled_important / len(important_fields)) * 3
    
    # Special considerations (20% of score)
    if record.get('legal_basis') == 'Legitimate Interests' and record.get('legitimate_interests', '').strip():
        score += 1
    
    if record.get('third_country_transfers', '').strip() and record.get('safeguards', '').strip():
        score += 1
    
    return min(score, max_score)
