import pandas as pd
import io
import os
from datetime import datetime
from audit_logger import log_audit_event
import tempfile
import json

def generate_export(user_email, user_role, export_format, include_drafts=False, include_rejected=False):
    """Generate export file with enhanced multi-sheet support"""

    if export_format == 'excel_complete':
        # New complete Excel export with all sheets
        from file_handler import export_excel_with_all_sheets
        return export_excel_with_all_sheets(user_email, user_role, include_updates=True)
    elif export_format == 'excel':
        return generate_excel_export_enhanced(user_email, user_role, include_drafts, include_rejected)
    elif export_format == 'csv':
        return generate_csv_export(user_email, user_role, include_drafts, include_rejected)
    elif export_format == 'pdf':
        return generate_pdf_export(user_email, user_role, include_drafts, include_rejected)
    else:
        raise Exception(f"Unsupported export format: {export_format}")

def generate_excel_export_enhanced(user_email, user_role, include_drafts=False, include_rejected=False):
    """Generate enhanced Excel export with original sheets and updates"""
    from models import ExcelFileData, ExcelSheetData, ROPARecord, User
    from app import db

    try:
        user = User.query.filter_by(email=user_email).first()
        if not user:
            raise Exception("User not found")

        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ROPA_Enhanced_Export_{timestamp}.xlsx"
        file_path = os.path.join(temp_dir, filename)

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Export current ROPA records
            records_df = get_filtered_ropa_data(user_email, user_role, include_drafts, include_rejected)
            if not records_df.empty:
                export_df = prepare_export_dataframe(records_df)
                export_df.to_excel(writer, sheet_name='Current_ROPA_Records', index=False)

            # Export original Excel sheets if user has uploaded files
            if user_role == 'Privacy Officer':
                excel_files = ExcelFileData.query.all()
            else:
                excel_files = ExcelFileData.query.filter_by(uploaded_by=user.id).all()

            for excel_file in excel_files:
                sheets = ExcelSheetData.query.filter_by(excel_file_id=excel_file.id).all()
                for sheet in sheets:
                    try:
                        sheet_data = json.loads(sheet.sheet_data)
                        if sheet_data:
                            df = pd.DataFrame(sheet_data)
                            sheet_name = f"Original_{sheet.sheet_name}"[:31]  # Excel limit
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                    except Exception as e:
                        print(f"Error exporting sheet {sheet.sheet_name}: {str(e)}")

            # Add summary sheet
            summary_data = create_enhanced_summary_data(records_df, excel_files)
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Export_Summary', index=False)

        return file_path, filename

    except Exception as e:
        print(f"Error generating enhanced Excel export: {str(e)}")
        raise e

def get_filtered_ropa_data(user_email, user_role, include_drafts=False, include_rejected=False):
    """Get filtered ROPA data for export"""
    from models import ROPARecord, User
    from app import db

    try:
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return pd.DataFrame()

        # Build query based on user role
        if user_role == 'Privacy Champion':
            query = ROPARecord.query.filter_by(created_by=user.id)
        else:
            query = ROPARecord.query

        # Status filtering
        status_filters = ['Approved', 'Under Review']
        if include_drafts:
            status_filters.append('Draft')
        if include_rejected:
            status_filters.append('Rejected')

        # Apply status filter
        records = query.filter(ROPARecord.status.in_(status_filters)).order_by(ROPARecord.created_at.desc()).all()

        # Convert to DataFrame
        if not records:
            return pd.DataFrame()

        records_data = []
        for record in records:
            creator = User.query.get(record.created_by)
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
                'processing_purpose': record.processing_purpose,
                'legal_basis': record.legal_basis,
                'data_categories': record.data_categories,
                'data_subjects': record.data_subjects,
                'recipients': record.recipients,
                'retention_period': record.retention_period,
                'security_measures': record.security_measures,
                'status': record.status,
                'created_by': creator.email if creator else 'Unknown',
                'created_at': record.created_at,
                'updated_at': record.updated_at
            }
            records_data.append(record_dict)

        return pd.DataFrame(records_data)

    except Exception as e:
        print(f"Error getting filtered ROPA data: {str(e)}")
        return pd.DataFrame()

def generate_csv_export(user_email, user_role, include_drafts=False, include_rejected=False):
    """Generate CSV export"""
    records_df = get_filtered_ropa_data(user_email, user_role, include_drafts, include_rejected)

    if records_df.empty:
        raise Exception("No records found for export")

    export_df = prepare_export_dataframe(records_df)

    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ROPA_Export_{timestamp}.csv"
    file_path = os.path.join(temp_dir, filename)

    export_df.to_csv(file_path, index=False)
    return file_path, filename

def generate_pdf_export(user_email, user_role, include_drafts=False, include_rejected=False):
    """Generate PDF report"""
    records_df = get_filtered_ropa_data(user_email, user_role, include_drafts, include_rejected)

    report_content = create_pdf_report_content(records_df)

    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ROPA_Report_{timestamp}.txt"
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(report_content)

    return file_path, filename

def prepare_export_dataframe(df):
    """Prepare dataframe for export with clean column names"""
    if df.empty:
        return df

    export_columns = {
        'processing_activity_name': 'Processing Activity Name',
        'category': 'Category',
        'description': 'Description',
        'department_function': 'Department/Function',
        'controller_name': 'Controller Name',
        'controller_contact': 'Controller Contact',
        'controller_address': 'Controller Address',
        'dpo_name': 'DPO Name',
        'dpo_contact': 'DPO Contact',
        'processing_purpose': 'Purpose of Processing',
        'legal_basis': 'Legal Basis',
        'data_categories': 'Data Categories',
        'data_subjects': 'Data Subjects',
        'recipients': 'Recipients',
        'retention_period': 'Retention Period',
        'security_measures': 'Security Measures',
        'status': 'Status',
        'created_by': 'Created By',
        'created_at': 'Created Date',
        'updated_at': 'Updated Date'
    }

    # Select available columns
    available_columns = {k: v for k, v in export_columns.items() if k in df.columns}

    export_df = df[list(available_columns.keys())].copy()
    export_df = export_df.rename(columns=available_columns)

    # Clean up date columns
    date_columns = ['Created Date', 'Updated Date']
    for col in date_columns:
        if col in export_df.columns:
            export_df[col] = pd.to_datetime(export_df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

    return export_df

def create_enhanced_summary_data(records_df, excel_files):
    """Create enhanced summary with original file information"""
    summary = []

    # Basic statistics
    summary.append({"Metric": "Total ROPA Records", "Value": len(records_df)})
    if not records_df.empty:
        summary.append({"Metric": "Approved Records", "Value": len(records_df[records_df['status'] == 'Approved'])})
        summary.append({"Metric": "Pending Review", "Value": len(records_df[records_df['status'] == 'Under Review'])})
        summary.append({"Metric": "Draft Records", "Value": len(records_df[records_df['status'] == 'Draft'])})

    # Excel file information
    summary.append({"Metric": "Original Excel Files", "Value": len(excel_files)})

    for excel_file in excel_files:
        summary.append({"Metric": f"File: {excel_file.filename}", "Value": f"Uploaded: {excel_file.upload_timestamp.strftime('%Y-%m-%d %H:%M')}"})
        summary.append({"Metric": f"Sheets in {excel_file.filename}", "Value": excel_file.total_sheets})

    summary.append({"Metric": "Export Generated", "Value": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

    return summary

def create_pdf_report_content(df):
    """Create text content for PDF report"""
    report = f"""
GDPR ROPA COMPLIANCE REPORT
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

========================================
EXECUTIVE SUMMARY
========================================

Total ROPA Records: {len(df)}
"""

    if not df.empty:
        report += f"""Approved Records: {len(df[df['status'] == 'Approved'])}
Pending Review: {len(df[df['status'] == 'Under Review'])}
Draft Records: {len(df[df['status'] == 'Draft'])}

Compliance Rate: {(len(df[df['status'] == 'Approved']) / len(df) * 100):.1f}%
"""

    report += """
========================================
RECORDS BY CATEGORY
========================================
"""

    if not df.empty and 'category' in df.columns:
        category_counts = df['category'].value_counts()
        for category, count in category_counts.items():
            report += f"{category}: {count} records\n"

    return report