"""
GDPR ROPA Automation Module
Implements automation features based on the provided automation document
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from database import get_db_connection
from audit_logger import log_audit_event, log_security_event, AuditEventTypes
from utils import get_predefined_options

class ROPAAutomation:
    
    @staticmethod
    def pre_populate_organization_data():
        """Pre-populate common organizational data to reduce manual entry"""
        return {
            'controller_name': 'Your Organization Name',
            'controller_contact': 'dpo@yourorganization.com',
            'controller_address': 'Your Organization Address',
            'dpo_name': 'Data Protection Officer',
            'dpo_contact': 'dpo@yourorganization.com',
            'dpo_address': 'Same as Controller Address'
        }
    
    @staticmethod
    def suggest_processing_purpose(department_function, data_categories):
        """Suggest processing purposes based on department and data types"""
        suggestions = {
            'Human Resources': [
                'Employee management and payroll processing',
                'Recruitment and onboarding',
                'Performance evaluation and training',
                'Benefits administration'
            ],
            'Marketing': [
                'Customer relationship management',
                'Marketing campaigns and communications',
                'Market research and analytics',
                'Lead generation and conversion'
            ],
            'Finance': [
                'Financial reporting and accounting',
                'Invoice processing and payments',
                'Budgeting and financial planning',
                'Tax compliance and reporting'
            ],
            'Information Technology': [
                'System administration and maintenance',
                'Security monitoring and incident response',
                'Software development and testing',
                'Data backup and recovery'
            ],
            'Customer Service': [
                'Customer support and assistance',
                'Complaint handling and resolution',
                'Service delivery and improvement',
                'Customer satisfaction surveys'
            ]
        }
        
        return suggestions.get(department_function, ['General business operations'])
    
    @staticmethod
    def classify_data_automatically(data_description):
        """Automatically classify data types based on description"""
        classifications = {
            'Personal Identifiable Information (PII)': [
                'name', 'email', 'phone', 'address', 'id number'
            ],
            'Financial Data': [
                'bank account', 'credit card', 'payment', 'salary', 'invoice'
            ],
            'Health Data': [
                'medical', 'health', 'treatment', 'diagnosis', 'medication'
            ],
            'Employment Data': [
                'employee', 'job title', 'department', 'performance', 'training'
            ]
        }
        
        detected_categories = []
        data_lower = data_description.lower()
        
        for category, keywords in classifications.items():
            if any(keyword in data_lower for keyword in keywords):
                detected_categories.append(category)
        
        return detected_categories
    
    @staticmethod
    def assess_risk_level(data_categories, special_categories, third_country_transfers):
        """Automatically assess risk level for DPIA recommendations"""
        risk_score = 0
        
        # Special categories increase risk
        if special_categories and special_categories.strip():
            risk_score += 3
        
        # Third country transfers increase risk
        if third_country_transfers and third_country_transfers.strip():
            risk_score += 2
        
        # Large scale processing increases risk
        if 'large scale' in (data_categories or '').lower():
            risk_score += 2
        
        # Automated decision making increases risk
        if any(term in (data_categories or '').lower() for term in ['automated', 'profiling', 'algorithm']):
            risk_score += 2
        
        if risk_score >= 5:
            return 'High', 'DPIA Required'
        elif risk_score >= 3:
            return 'Medium', 'DPIA Recommended'
        else:
            return 'Low', 'Standard Processing'
    
    @staticmethod
    def generate_retention_suggestions(category, legal_basis):
        """Generate retention period suggestions based on category and legal basis"""
        retention_matrix = {
            'HR Management': {
                'Contract': '7 years after employment termination',
                'Legal Obligation': '7 years (tax and employment law)',
                'Legitimate Interests': '2 years after employment termination'
            },
            'Customer Management': {
                'Contract': '7 years after contract termination',
                'Consent': 'Until consent is withdrawn',
                'Legitimate Interests': '3 years after last contact'
            },
            'Marketing': {
                'Consent': 'Until consent is withdrawn',
                'Legitimate Interests': '2 years after last interaction'
            },
            'Finance': {
                'Legal Obligation': '7 years (accounting requirements)',
                'Contract': '7 years after contract completion'
            }
        }
        
        return retention_matrix.get(category, {}).get(legal_basis, 'Review and determine based on business needs')
    
    @staticmethod
    def check_review_schedules():
        """Check for ROPA records that need periodic review"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find records older than 12 months without review
        cursor.execute("""
            SELECT id, processing_activity_name, created_by, created_at
            FROM ropa_records 
            WHERE (reviewed_at IS NULL OR reviewed_at < %s)
            AND created_at < %s
            AND status = 'Approved'
        """, (datetime.now() - timedelta(days=365), datetime.now() - timedelta(days=365)))
        
        overdue_reviews = cursor.fetchall()
        conn.close()
        
        return overdue_reviews
    
    @staticmethod
    def generate_compliance_alerts():
        """Generate automated alerts for compliance issues"""
        alerts = []
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check for missing retention policies
        cursor.execute("""
            SELECT COUNT(*) FROM ropa_records 
            WHERE (retention_period IS NULL OR retention_period = '')
            AND status = 'Approved'
        """)
        missing_retention = cursor.fetchone()[0]
        
        if missing_retention > 0:
            alerts.append({
                'type': 'warning',
                'message': f'{missing_retention} approved ROPA records are missing retention policies',
                'action': 'Review and update retention information'
            })
        
        # Check for high-risk processing without DPIA
        cursor.execute("""
            SELECT COUNT(*) FROM ropa_records 
            WHERE special_categories IS NOT NULL 
            AND special_categories != ''
            AND additional_info NOT ILIKE '%DPIA%'
            AND status = 'Approved'
        """)
        missing_dpia = cursor.fetchone()[0]
        
        if missing_dpia > 0:
            alerts.append({
                'type': 'danger',
                'message': f'{missing_dpia} high-risk processing activities may require DPIA',
                'action': 'Conduct Data Protection Impact Assessment'
            })
        
        # Check for records with non-compliant data retention
        cursor.execute("""
            SELECT COUNT(*) FROM ropa_records 
            WHERE data_retained_accordance = 'false'
            AND status = 'Approved'
        """)
        non_compliant_retention = cursor.fetchone()[0]
        
        if non_compliant_retention > 0:
            alerts.append({
                'type': 'danger',
                'message': f'{non_compliant_retention} records indicate non-compliance with retention policies',
                'action': 'Review and update data retention practices'
            })
        
        conn.close()
        return alerts
    
    @staticmethod
    def auto_fill_security_measures(department_function, data_categories):
        """Auto-suggest security measures based on department and data types"""
        base_measures = [
            "Encryption at rest and in transit (AES-256)",
            "Multi-factor authentication for all users",
            "Regular security assessments and vulnerability scans",
            "Access controls and role-based permissions",
            "Regular data backups with tested recovery procedures",
            "Employee security training and awareness programs",
            "Network segmentation and firewall protection",
            "Incident response and breach notification procedures"
        ]
        
        additional_measures = {
            'Human Resources': [
                "HR data segregation and restricted access",
                "Background checks for HR personnel",
                "Secure employee file storage"
            ],
            'Finance': [
                "Financial data encryption and audit trails",
                "Segregation of duties for financial processes",
                "Regular financial security audits"
            ],
            'Information Technology': [
                "Advanced threat detection systems",
                "Security information and event management (SIEM)",
                "Regular penetration testing"
            ]
        }
        
        if 'special categories' in (data_categories or '').lower():
            base_measures.extend([
                "Special category data encryption",
                "Enhanced access logging and monitoring",
                "Data anonymization where possible"
            ])
        
        department_specific = additional_measures.get(department_function, [])
        return base_measures + department_specific

def send_review_reminders():
    """Send automated review reminders to relevant users"""
    overdue_reviews = ROPAAutomation.check_review_schedules()
    
    for record in overdue_reviews:
        record_id, activity_name, created_by, created_at = record
        log_audit_event(
            AuditEventTypes.SYSTEM_ERROR,
            'system',
            f"Review reminder: ROPA record '{activity_name}' (ID: {record_id}) requires periodic review. Last updated: {created_at}"
        )
    
    return len(overdue_reviews)

def generate_automation_dashboard_data():
    """Generate data for automation dashboard"""
    alerts = ROPAAutomation.generate_compliance_alerts()
    overdue_reviews = ROPAAutomation.check_review_schedules()
    
    return {
        'compliance_alerts': alerts,
        'overdue_reviews': len(overdue_reviews),
        'total_automations': 8,  # Number of automation features implemented
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }