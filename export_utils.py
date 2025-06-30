import pandas as pd
import io
import os
from datetime import datetime
from database import get_db_connection
from audit_logger import log_audit_event
import tempfile

def generate_export(user_email, user_role, export_format, include_drafts=False, include_rejected=False):
    """Generate export file and return file path and filename"""
    
    # Get filtered data
    records_df = get_filtered_ropa_data(
        user_email=user_email,
        user_role=user_role,
        include_drafts=include_drafts,
        include_rejected=include_rejected
    )
    
    if records_df.empty:
        raise Exception("No records found matching the selected criteria.")
    
    # Generate export based on format
    if export_format == 'excel':
        return generate_excel_export(records_df)
    elif export_format == 'csv':
        return generate_csv_export(records_df)
    elif export_format == 'pdf':
        return generate_pdf_export(records_df)
    else:
        raise Exception(f"Unsupported export format: {export_format}")

def get_filtered_ropa_data(user_email, user_role, include_drafts=False, include_rejected=False):
    """Get filtered ROPA data based on export criteria"""
    
    conn = get_db_connection()
    
    # Build query based on user role
    if user_role == "Privacy Champion":
        # Privacy Champions see only their own records
        base_query = "SELECT * FROM ropa_records WHERE created_by = ?"
        params = [user_email]
    else:
        # Privacy Officers and Admins see all records
        base_query = "SELECT * FROM ropa_records WHERE 1=1"
        params = []
    
    # Status filtering
    status_filters = ["'Approved'"]
    if include_drafts:
        status_filters.append("'Draft'")
    if include_rejected:
        status_filters.append("'Rejected'")
    
    status_clause = " AND status IN (" + ", ".join(status_filters) + ")"
    query = base_query + status_clause + " ORDER BY created_at DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    return df

def generate_excel_export(df):
    """Generate Excel export with multiple sheets"""
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ROPA_Export_{timestamp}.xlsx"
    file_path = os.path.join(temp_dir, filename)
    
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        # Main ROPA data sheet
        export_df = prepare_export_dataframe(df)
        export_df.to_excel(writer, sheet_name='ROPA Records', index=False)
        
        # Summary sheet
        summary_data = create_summary_data(df)
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Status breakdown sheet
        if not df.empty:
            status_breakdown = df['status'].value_counts().reset_index()
            status_breakdown.columns = ['Status', 'Count']
            status_breakdown.to_excel(writer, sheet_name='Status Breakdown', index=False)
    
    return file_path, filename

def generate_csv_export(df):
    """Generate CSV export"""
    
    export_df = prepare_export_dataframe(df)
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ROPA_Export_{timestamp}.csv"
    file_path = os.path.join(temp_dir, filename)
    
    export_df.to_csv(file_path, index=False)
    
    return file_path, filename

def generate_pdf_export(df):
    """Generate PDF report (text format)"""
    
    report_content = create_pdf_report_content(df)
    
    # Create temporary file
    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ROPA_Report_{timestamp}.txt"
    file_path = os.path.join(temp_dir, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    return file_path, filename

def prepare_export_dataframe(df):
    """Prepare dataframe for export with clean column names"""
    
    # Select and rename columns for export
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
        'legitimate_interests': 'Legitimate Interests',
        'data_categories': 'Data Categories',
        'special_categories': 'Special Categories',
        'data_subjects': 'Data Subjects',
        'recipients': 'Recipients',
        'third_country_transfers': 'Third Country Transfers',
        'safeguards': 'Safeguards',
        'retention_period': 'Retention Period',
        'retention_criteria': 'Retention Criteria',
        'security_measures': 'Security Measures',
        'status': 'Status',
        'created_by': 'Created By',
        'created_at': 'Created Date',
        'approved_by': 'Approved By',
        'approved_at': 'Approved Date'
    }
    
    # Select available columns
    available_columns = {k: v for k, v in export_columns.items() if k in df.columns}
    
    export_df = df[list(available_columns.keys())].copy()
    export_df = export_df.rename(columns=available_columns)
    
    # Clean up date columns
    date_columns = ['Created Date', 'Approved Date']
    for col in date_columns:
        if col in export_df.columns:
            export_df[col] = pd.to_datetime(export_df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    
    return export_df

def create_summary_data(df):
    """Create summary statistics for export"""
    
    summary = []
    
    # Basic statistics
    summary.append({"Metric": "Total Records", "Value": len(df)})
    summary.append({"Metric": "Approved Records", "Value": len(df[df['status'] == 'Approved'])})
    summary.append({"Metric": "Pending Review", "Value": len(df[df['status'] == 'Pending Review'])})
    summary.append({"Metric": "Draft Records", "Value": len(df[df['status'] == 'Draft'])})
    
    # Export information
    summary.append({"Metric": "Export Date", "Value": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    
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
Approved Records: {len(df[df['status'] == 'Approved']) if not df.empty else 0}
Pending Review: {len(df[df['status'] == 'Pending Review']) if not df.empty else 0}
Draft Records: {len(df[df['status'] == 'Draft']) if not df.empty else 0}

Compliance Rate: {(len(df[df['status'] == 'Approved']) / len(df) * 100):.1f}% if not df.empty else 0%

========================================
RECORDS BY CATEGORY
========================================
"""
    
    if not df.empty and 'category' in df.columns:
        category_counts = df['category'].value_counts()
        for category, count in category_counts.items():
            report += f"{category}: {count} records\n"
    
    report += f"""

========================================
RECORDS BY LEGAL BASIS
========================================
"""
    
    if not df.empty and 'legal_basis' in df.columns:
        legal_basis_counts = df['legal_basis'].value_counts()
        for basis, count in legal_basis_counts.items():
            report += f"{basis}: {count} records\n"
    
    report += f"""

========================================
DETAILED RECORDS
========================================

"""
    
    # Add first 10 records as examples
    if not df.empty:
        for idx, record in df.head(10).iterrows():
            report += f"""
Record: {record.get('processing_activity_name', 'N/A')}
Category: {record.get('category', 'N/A')}
Status: {record.get('status', 'N/A')}
Legal Basis: {record.get('legal_basis', 'N/A')}
Created: {record.get('created_at', 'N/A')}
----------------------------------------
"""
        
        if len(df) > 10:
            report += f"\n... and {len(df) - 10} more records (see complete data in Excel/CSV export)\n"
    
    return report
