import streamlit as st
import pandas as pd
from datetime import datetime
from database import save_ropa_record, get_ropa_records, update_ropa_status
from audit_logger import log_audit_event
from utils import get_predefined_options

def create_ropa_form(user_email, user_role):
    """Create new ROPA record form with tabbed interface"""
    
    # Initialize form data in session state
    if 'ropa_form_data' not in st.session_state:
        st.session_state.ropa_form_data = {}
    
    # Tab interface matching the screenshot
    tabs = st.tabs([
        "📋 Basic Information",
        "🏢 Controller Details", 
        "👤 DPO Details",
        "⚙️ Processor Details",
        "👥 Representative Details",
        "📊 Processing Details",
        "📂 Data Categories",
        "📤 Recipients & Transfers",
        "📅 Retention",
        "🔒 Security",
        "ℹ️ Additional Info"
    ])
    
    with tabs[0]:  # Basic Information
        st.subheader("📋 Basic Information")
        
        col1, col2 = st.columns(2)
        with col1:
            activity_name = st.text_input("Processing Activity Name*", 
                                        value=st.session_state.ropa_form_data.get('processing_activity_name', ''))
        with col2:
            category = st.selectbox("Category*", 
                                  get_predefined_options('categories'),
                                  index=get_index_for_value(get_predefined_options('categories'), 
                                                          st.session_state.ropa_form_data.get('category', '')))
        
        description = st.text_area("Description*", 
                                 value=st.session_state.ropa_form_data.get('description', ''),
                                 help="Provide a detailed description of the processing activity.",
                                 height=100)
        
        # Save to session state
        st.session_state.ropa_form_data.update({
            'processing_activity_name': activity_name,
            'category': category,
            'description': description
        })
    
    with tabs[1]:  # Controller Details
        st.subheader("🏢 Controller Details")
        
        col1, col2 = st.columns(2)
        with col1:
            controller_name = st.text_input("Controller Name*",
                                          value=st.session_state.ropa_form_data.get('controller_name', ''))
            controller_contact = st.text_input("Controller Contact*",
                                             value=st.session_state.ropa_form_data.get('controller_contact', ''))
        with col2:
            controller_address = st.text_area("Controller Address*",
                                            value=st.session_state.ropa_form_data.get('controller_address', ''),
                                            height=100)
        
        st.session_state.ropa_form_data.update({
            'controller_name': controller_name,
            'controller_contact': controller_contact,
            'controller_address': controller_address
        })
    
    with tabs[2]:  # DPO Details
        st.subheader("👤 Data Protection Officer Details")
        
        col1, col2 = st.columns(2)
        with col1:
            dpo_name = st.text_input("DPO Name",
                                   value=st.session_state.ropa_form_data.get('dpo_name', ''))
            dpo_contact = st.text_input("DPO Contact",
                                      value=st.session_state.ropa_form_data.get('dpo_contact', ''))
        with col2:
            dpo_address = st.text_area("DPO Address",
                                     value=st.session_state.ropa_form_data.get('dpo_address', ''),
                                     height=100)
        
        st.session_state.ropa_form_data.update({
            'dpo_name': dpo_name,
            'dpo_contact': dpo_contact,
            'dpo_address': dpo_address
        })
    
    with tabs[3]:  # Processor Details
        st.subheader("⚙️ Processor Details")
        
        col1, col2 = st.columns(2)
        with col1:
            processor_name = st.text_input("Processor Name",
                                         value=st.session_state.ropa_form_data.get('processor_name', ''))
            processor_contact = st.text_input("Processor Contact",
                                            value=st.session_state.ropa_form_data.get('processor_contact', ''))
        with col2:
            processor_address = st.text_area("Processor Address",
                                           value=st.session_state.ropa_form_data.get('processor_address', ''),
                                           height=100)
        
        st.session_state.ropa_form_data.update({
            'processor_name': processor_name,
            'processor_contact': processor_contact,
            'processor_address': processor_address
        })
    
    with tabs[4]:  # Representative Details
        st.subheader("👥 Representative Details")
        
        col1, col2 = st.columns(2)
        with col1:
            representative_name = st.text_input("Representative Name",
                                              value=st.session_state.ropa_form_data.get('representative_name', ''))
            representative_contact = st.text_input("Representative Contact",
                                                  value=st.session_state.ropa_form_data.get('representative_contact', ''))
        with col2:
            representative_address = st.text_area("Representative Address",
                                                value=st.session_state.ropa_form_data.get('representative_address', ''),
                                                height=100)
        
        st.session_state.ropa_form_data.update({
            'representative_name': representative_name,
            'representative_contact': representative_contact,
            'representative_address': representative_address
        })
    
    with tabs[5]:  # Processing Details
        st.subheader("📊 Processing Details")
        
        processing_purpose = st.text_area("Purpose of Processing*",
                                        value=st.session_state.ropa_form_data.get('processing_purpose', ''),
                                        height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            legal_basis = st.selectbox("Legal Basis*",
                                     get_predefined_options('legal_basis'),
                                     index=get_index_for_value(get_predefined_options('legal_basis'),
                                                             st.session_state.ropa_form_data.get('legal_basis', '')))
        with col2:
            legitimate_interests = st.text_area("Legitimate Interests (if applicable)",
                                              value=st.session_state.ropa_form_data.get('legitimate_interests', ''),
                                              height=100)
        
        st.session_state.ropa_form_data.update({
            'processing_purpose': processing_purpose,
            'legal_basis': legal_basis,
            'legitimate_interests': legitimate_interests
        })
    
    with tabs[6]:  # Data Categories
        st.subheader("📂 Data Categories")
        
        data_categories = st.multiselect("Categories of Personal Data*",
                                       get_predefined_options('data_categories'),
                                       default=st.session_state.ropa_form_data.get('data_categories', '').split(', ') if st.session_state.ropa_form_data.get('data_categories') else [])
        
        special_categories = st.multiselect("Special Categories of Personal Data",
                                          get_predefined_options('special_categories'),
                                          default=st.session_state.ropa_form_data.get('special_categories', '').split(', ') if st.session_state.ropa_form_data.get('special_categories') else [])
        
        data_subjects = st.multiselect("Categories of Data Subjects*",
                                     get_predefined_options('data_subjects'),
                                     default=st.session_state.ropa_form_data.get('data_subjects', '').split(', ') if st.session_state.ropa_form_data.get('data_subjects') else [])
        
        st.session_state.ropa_form_data.update({
            'data_categories': ', '.join(data_categories),
            'special_categories': ', '.join(special_categories),
            'data_subjects': ', '.join(data_subjects)
        })
    
    with tabs[7]:  # Recipients & Transfers
        st.subheader("📤 Recipients & Transfers")
        
        recipients = st.text_area("Categories of Recipients*",
                                value=st.session_state.ropa_form_data.get('recipients', ''),
                                height=100)
        
        col1, col2 = st.columns(2)
        with col1:
            third_country_transfers = st.text_area("Third Country Transfers",
                                                 value=st.session_state.ropa_form_data.get('third_country_transfers', ''),
                                                 height=100)
        with col2:
            safeguards = st.text_area("Appropriate Safeguards",
                                    value=st.session_state.ropa_form_data.get('safeguards', ''),
                                    height=100)
        
        st.session_state.ropa_form_data.update({
            'recipients': recipients,
            'third_country_transfers': third_country_transfers,
            'safeguards': safeguards
        })
    
    with tabs[8]:  # Retention
        st.subheader("📅 Retention")
        
        col1, col2 = st.columns(2)
        with col1:
            retention_period = st.text_input("Retention Period*",
                                           value=st.session_state.ropa_form_data.get('retention_period', ''))
        with col2:
            retention_criteria = st.text_area("Retention Criteria*",
                                            value=st.session_state.ropa_form_data.get('retention_criteria', ''),
                                            height=100)
        
        st.session_state.ropa_form_data.update({
            'retention_period': retention_period,
            'retention_criteria': retention_criteria
        })
    
    with tabs[9]:  # Security
        st.subheader("🔒 Security")
        
        security_measures = st.text_area("Technical and Organisational Security Measures*",
                                       value=st.session_state.ropa_form_data.get('security_measures', ''),
                                       height=120)
        
        col1, col2 = st.columns(2)
        with col1:
            breach_likelihood = st.selectbox("Data Breach Likelihood",
                                           ["Low", "Medium", "High"],
                                           index=["Low", "Medium", "High"].index(st.session_state.ropa_form_data.get('breach_likelihood', 'Low')))
        with col2:
            breach_impact = st.selectbox("Data Breach Impact",
                                       ["Low", "Medium", "High"],
                                       index=["Low", "Medium", "High"].index(st.session_state.ropa_form_data.get('breach_impact', 'Low')))
        
        st.session_state.ropa_form_data.update({
            'security_measures': security_measures,
            'breach_likelihood': breach_likelihood,
            'breach_impact': breach_impact
        })
    
    with tabs[10]:  # Additional Info
        st.subheader("ℹ️ Additional Information")
        
        additional_info = st.text_area("Additional Information",
                                     value=st.session_state.ropa_form_data.get('additional_info', ''),
                                     height=120,
                                     help="Any additional relevant information about this processing activity.")
        
        st.session_state.ropa_form_data.update({
            'additional_info': additional_info
        })
    
    # Form submission buttons
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.ropa_form_data = {}
            st.session_state.current_page = "dashboard"
            st.rerun()
    
    with col2:
        if st.button("💾 Save as Draft", use_container_width=True):
            if validate_required_fields(st.session_state.ropa_form_data, draft=True):
                save_ropa_draft(user_email)
    
    with col3:
        if st.button("✅ Submit for Review", use_container_width=True):
            if validate_required_fields(st.session_state.ropa_form_data):
                submit_for_review(user_email)

def validate_required_fields(data, draft=False):
    """Validate required fields"""
    required_fields = [
        'processing_activity_name', 'category', 'description',
        'controller_name', 'controller_contact', 'controller_address'
    ]
    
    if not draft:
        required_fields.extend([
            'processing_purpose', 'legal_basis', 'data_categories',
            'data_subjects', 'recipients', 'retention_period',
            'retention_criteria', 'security_measures'
        ])
    
    missing_fields = []
    for field in required_fields:
        if not data.get(field, '').strip():
            missing_fields.append(field.replace('_', ' ').title())
    
    if missing_fields:
        st.error(f"Please fill in the following required fields: {', '.join(missing_fields)}")
        return False
    
    return True

def save_ropa_draft(user_email):
    """Save ROPA record as draft"""
    try:
        record_id = save_ropa_record(st.session_state.ropa_form_data, user_email)
        
        log_audit_event("ROPA Draft Saved", user_email, 
                       f"ROPA record saved as draft: {st.session_state.ropa_form_data.get('processing_activity_name', 'Unknown')}")
        
        st.success("✅ ROPA record saved as draft successfully!")
        st.session_state.ropa_form_data = {}
        
    except Exception as e:
        st.error(f"❌ Error saving ROPA record: {str(e)}")
        log_audit_event("ROPA Save Error", user_email, f"Error saving ROPA draft: {str(e)}")

def submit_for_review(user_email):
    """Submit ROPA record for review"""
    try:
        # Set status to pending review
        st.session_state.ropa_form_data['status'] = 'Pending Review'
        record_id = save_ropa_record(st.session_state.ropa_form_data, user_email)
        
        log_audit_event("ROPA Submitted for Review", user_email,
                       f"ROPA record submitted for review: {st.session_state.ropa_form_data.get('processing_activity_name', 'Unknown')}")
        
        st.success("✅ ROPA record submitted for review successfully!")
        st.session_state.ropa_form_data = {}
        
    except Exception as e:
        st.error(f"❌ Error submitting ROPA record: {str(e)}")
        log_audit_event("ROPA Submit Error", user_email, f"Error submitting ROPA: {str(e)}")

def view_ropa_records(user_email, user_role):
    """View and manage ROPA records"""
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox("Filter by Status", 
                                   ["All", "Draft", "Pending Review", "Approved", "Rejected"])
    
    with col2:
        if user_role in ["Privacy Officer", "Admin"]:
            show_all = st.checkbox("Show All Records", value=user_role == "Admin")
        else:
            show_all = False
    
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Get records based on filters
    filter_status = None if status_filter == "All" else status_filter
    records_df = get_ropa_records(
        user_email=None if show_all else user_email,
        role=user_role,
        status=filter_status
    )
    
    if records_df.empty:
        st.info("No ROPA records found matching the current filters.")
        return
    
    # Display records
    for index, record in records_df.iterrows():
        with st.expander(f"📋 {record['processing_activity_name']} - {record['status']}", expanded=False):
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Category:** {record['category']}")
                st.write(f"**Created by:** {record['created_by']}")
                st.write(f"**Created:** {record['created_at']}")
            
            with col2:
                st.write(f"**Status:** {record['status']}")
                if record['reviewed_by']:
                    st.write(f"**Reviewed by:** {record['reviewed_by']}")
                if record['approved_by']:
                    st.write(f"**Approved by:** {record['approved_by']}")
            
            with col3:
                st.write(f"**Legal Basis:** {record['legal_basis']}")
                st.write(f"**Data Categories:** {record['data_categories']}")
            
            st.write(f"**Description:** {record['description']}")
            
            # Action buttons based on role and status
            action_col1, action_col2, action_col3 = st.columns(3)
            
            if user_role == "Privacy Officer" and record['status'] == "Pending Review":
                with action_col1:
                    if st.button(f"✅ Approve", key=f"approve_{record['id']}"):
                        update_ropa_status(record['id'], "Approved", user_email)
                        log_audit_event("ROPA Approved", user_email, 
                                       f"ROPA record approved: {record['processing_activity_name']}")
                        st.success("Record approved successfully!")
                        st.rerun()
                
                with action_col2:
                    if st.button(f"❌ Reject", key=f"reject_{record['id']}"):
                        update_ropa_status(record['id'], "Rejected", user_email)
                        log_audit_event("ROPA Rejected", user_email,
                                       f"ROPA record rejected: {record['processing_activity_name']}")
                        st.warning("Record rejected!")
                        st.rerun()
            
            if record['created_by'] == user_email and record['status'] in ["Draft", "Rejected"]:
                with action_col3:
                    if st.button(f"✏️ Edit", key=f"edit_{record['id']}"):
                        st.info("Edit functionality would load the record into the form for modification.")

def get_index_for_value(options, value):
    """Get index of value in options list"""
    try:
        return options.index(value) if value in options else 0
    except (ValueError, IndexError):
        return 0
