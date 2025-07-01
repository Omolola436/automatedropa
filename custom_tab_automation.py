"""
Custom Tab Automation for GDPR ROPA System
Handles automatic integration of approved custom fields into templates and existing ROPA records
"""

import json
from datetime import datetime
from models import db, CustomTab, ApprovedCustomField, ROPACustomData, ROPARecord
from audit_logger import log_audit_event


def approve_custom_tab(custom_tab_id, privacy_officer_id, comments=None):
    """
    Approve a custom tab and automatically integrate it into the system
    """
    try:
        # Get the custom tab
        custom_tab = CustomTab.query.get(custom_tab_id)
        if not custom_tab:
            return {"success": False, "message": "Custom tab not found"}
        
        # Update status to approved
        custom_tab.status = 'Approved'
        custom_tab.reviewed_by = privacy_officer_id
        custom_tab.reviewed_at = datetime.utcnow()
        custom_tab.review_comments = comments
        
        # Create approved custom field record
        approved_field = ApprovedCustomField()
        approved_field.custom_tab_id = custom_tab.id
        approved_field.field_name = custom_tab.field_name
        approved_field.tab_category = custom_tab.tab_category
        approved_field.field_type = custom_tab.field_type
        approved_field.field_options = custom_tab.field_options
        approved_field.is_required = custom_tab.is_required
        
        db.session.add(approved_field)
        db.session.commit()
        
        # Auto-integrate into existing ROPA records
        integrate_field_into_existing_records(approved_field.id)
        
        # Log the approval
        log_audit_event(
            "CUSTOM_TAB_APPROVED",
            f"privacy_officer_{privacy_officer_id}",
            f"Approved custom field '{custom_tab.field_name}' in category '{custom_tab.tab_category}'"
        )
        
        return {"success": True, "message": "Custom tab approved and integrated successfully"}
        
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Error approving custom tab: {str(e)}"}


def integrate_field_into_existing_records(approved_field_id):
    """
    Automatically add approved custom field to all existing ROPA records
    """
    try:
        approved_field = ApprovedCustomField.query.get(approved_field_id)
        if not approved_field:
            return
        
        # Get all existing ROPA records
        existing_records = ROPARecord.query.all()
        
        for record in existing_records:
            # Check if this field already exists for this record
            existing_data = ROPACustomData.query.filter_by(
                ropa_record_id=record.id,
                custom_field_id=approved_field_id
            ).first()
            
            if not existing_data:
                # Create new custom data entry with empty value
                custom_data = ROPACustomData()
                custom_data.ropa_record_id = record.id
                custom_data.custom_field_id = approved_field_id
                custom_data.field_value = ""  # Empty value for existing records
                db.session.add(custom_data)
        
        db.session.commit()
        
        log_audit_event(
            "CUSTOM_FIELD_INTEGRATED",
            "system",
            f"Integrated custom field '{approved_field.field_name}' into {len(existing_records)} existing ROPA records"
        )
        
    except Exception as e:
        db.session.rollback()
        print(f"Error integrating field into existing records: {str(e)}")


def get_approved_custom_fields_by_category():
    """
    Get all approved custom fields organized by category
    """
    approved_fields = ApprovedCustomField.query.all()
    
    categories = {
        'Basic Info': [],
        'Controller': [],
        'DPO': [],
        'Processor': [],
        'Processing': [],
        'Data': [],
        'Recipients': [],
        'Retention': [],
        'Security': []
    }
    
    for field in approved_fields:
        if field.tab_category in categories:
            categories[field.tab_category].append({
                'id': field.id,
                'field_name': field.field_name,
                'field_type': field.field_type,
                'field_options': json.loads(field.field_options) if field.field_options else [],
                'is_required': field.is_required
            })
    
    return categories


def get_custom_data_for_record(ropa_record_id):
    """
    Get all custom field data for a specific ROPA record
    """
    custom_data = db.session.query(ROPACustomData, ApprovedCustomField).join(
        ApprovedCustomField, ROPACustomData.custom_field_id == ApprovedCustomField.id
    ).filter(ROPACustomData.ropa_record_id == ropa_record_id).all()
    
    result = {}
    for data, field in custom_data:
        if field.tab_category not in result:
            result[field.tab_category] = {}
        
        result[field.tab_category][field.field_name] = {
            'value': data.field_value,
            'field_type': field.field_type,
            'field_options': json.loads(field.field_options) if field.field_options else [],
            'is_required': field.is_required
        }
    
    return result


def update_custom_data_for_record(ropa_record_id, custom_data_updates):
    """
    Update custom field data for a ROPA record
    """
    try:
        for field_id, value in custom_data_updates.items():
            # Find existing custom data entry
            custom_data = ROPACustomData.query.filter_by(
                ropa_record_id=ropa_record_id,
                custom_field_id=field_id
            ).first()
            
            if custom_data:
                custom_data.field_value = value
                custom_data.updated_at = datetime.utcnow()
            else:
                # Create new entry if it doesn't exist
                custom_data = ROPACustomData()
                custom_data.ropa_record_id = ropa_record_id
                custom_data.custom_field_id = field_id
                custom_data.field_value = value
                db.session.add(custom_data)
        
        db.session.commit()
        return {"success": True}
        
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": str(e)}


def reject_custom_tab(custom_tab_id, privacy_officer_id, comments):
    """
    Reject a custom tab submission
    """
    try:
        custom_tab = CustomTab.query.get(custom_tab_id)
        if not custom_tab:
            return {"success": False, "message": "Custom tab not found"}
        
        custom_tab.status = 'Rejected'
        custom_tab.reviewed_by = privacy_officer_id
        custom_tab.reviewed_at = datetime.utcnow()
        custom_tab.review_comments = comments
        
        db.session.commit()
        
        log_audit_event(
            "CUSTOM_TAB_REJECTED",
            f"privacy_officer_{privacy_officer_id}",
            f"Rejected custom field '{custom_tab.field_name}' - Reason: {comments}"
        )
        
        return {"success": True, "message": "Custom tab rejected"}
        
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Error rejecting custom tab: {str(e)}"}


def get_pending_custom_tabs():
    """
    Get all custom tabs pending review
    """
    return CustomTab.query.filter_by(status='Pending Review').all()


def submit_custom_tab_for_review(custom_tab_id):
    """
    Submit a custom tab for Privacy Officer review
    """
    try:
        custom_tab = CustomTab.query.get(custom_tab_id)
        if not custom_tab:
            return {"success": False, "message": "Custom tab not found"}
        
        custom_tab.status = 'Pending Review'
        custom_tab.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        log_audit_event(
            "CUSTOM_TAB_SUBMITTED",
            f"user_{custom_tab.created_by}",
            f"Submitted custom field '{custom_tab.field_name}' for review"
        )
        
        return {"success": True, "message": "Custom tab submitted for review"}
        
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Error submitting custom tab: {str(e)}"}