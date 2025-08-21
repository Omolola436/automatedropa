import pandas as pd
import io
from database import save_ropa_record
from audit_logger import log_audit_event
import openpyxl

def process_uploaded_file(file, user_email):
    """Process uploaded ROPA file and return results"""

    try:
        # Parse the file based on extension
        if file.filename.lower().endswith('.xlsx'):
            df = parse_excel_file(file)
        else:
            df = parse_csv_file(file)

        if df is not None and not df.empty:
            # Import records
            results = import_ropa_records(df, user_email, overwrite_existing=False)
            return results
        else:
            return {"success_count": 0, "error_count": 1, "message": "No valid data found in file"}

    except Exception as e:
        return {"success_count": 0, "error_count": 1, "message": str(e)}

def parse_excel_file(uploaded_file):
    """Parse Excel file and extract ROPA data"""
    try:
        # Try to read multiple sheets
        xl_file = pd.ExcelFile(uploaded_file)

        # Look for common sheet names
        sheet_names = xl_file.sheet_names
        target_sheet = None

        # Common ROPA sheet names
        ropa_keywords = ['ropa', 'record', 'processing', 'activities', 'register']

        for sheet in sheet_names:
            if any(keyword in sheet.lower() for keyword in ropa_keywords):
                target_sheet = sheet
                break

        # If no specific sheet found, use the first one
        if target_sheet is None:
            target_sheet = sheet_names[0]

        # Read the sheet
        df = pd.read_excel(uploaded_file, sheet_name=target_sheet)

        # Clean and standardize column names
        df = standardize_columns(df)

        return df

    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        return None

def parse_csv_file(uploaded_file):
    """Parse CSV file and extract ROPA data"""
    try:
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding=encoding)
                df = standardize_columns(df)
                return df
            except UnicodeDecodeError:
                continue

        print("Could not decode the CSV file. Please ensure it's properly encoded.")
        return None

    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        return None

def standardize_columns(df):
    """Standardize column names to match database schema"""

    # Handle multi-header Excel files by flattening column names
    if hasattr(df.columns, 'nlevels') and df.columns.nlevels > 1:
        df.columns = [' '.join(col).strip() for col in df.columns.values]

    # Column mapping from various formats to our standard
    column_mapping = {
        # Basic Information
        'processing activity name': 'processing_activity_name',
        'activity name': 'processing_activity_name',
        'name': 'processing_activity_name',
        'processing activity': 'processing_activity_name',
        'activity': 'processing_activity_name',
        'record name': 'processing_activity_name',
        'category': 'category',
        'description': 'description',
        'department': 'department_function',
        'department function': 'department_function',
        'department/function': 'department_function',
        'function': 'department_function',
        'business function': 'department_function',

        # Controller Details - Enhanced mapping for various formats
        'controller name': 'controller_name',
        'controller': 'controller_name',
        'data controller': 'controller_name',
        'controller details name': 'controller_name',
        'controller contact': 'controller_contact',
        'controller address': 'controller_address',
        'address': 'controller_address',
        'controller details address': 'controller_address',
        'contact details': 'controller_contact',
        'controller details contact details': 'controller_contact',

        # DPO Details
        'dpo name': 'dpo_name',
        'data protection officer': 'dpo_name',
        'data protection officer name': 'dpo_name',
        'dpo contact': 'dpo_contact',
        'dpo address': 'dpo_address',

        # Processing Details
        'purpose': 'processing_purpose',
        'purpose of processing': 'processing_purpose',
        'legal basis': 'legal_basis',
        'lawful basis': 'legal_basis',
        'legitimate interests': 'legitimate_interests',

        # Data Categories
        'data categories': 'data_categories',
        'categories of data': 'data_categories',
        'personal data': 'data_categories',
        'special categories': 'special_categories',
        'data subjects': 'data_subjects',
        'categories of data subjects': 'data_subjects',

        # Recipients and Transfers
        'recipients': 'recipients',
        'third country transfers': 'third_country_transfers',
        'international transfers': 'third_country_transfers',
        'safeguards': 'safeguards',

        # Retention
        'retention period': 'retention_period',
        'retention': 'retention_period',
        'retention criteria': 'retention_criteria',

        # Security
        'security measures': 'security_measures',
        'technical measures': 'security_measures',
        'organisational measures': 'security_measures',

        # Additional
        'additional information': 'additional_info',
        'notes': 'additional_info',
        'comments': 'additional_info'
    }

    # Normalize column names (lowercase, remove extra spaces)
    df.columns = [str(col).lower().strip() for col in df.columns]

    # Apply mapping
    df = df.rename(columns=column_mapping)

    # Fill missing columns with empty strings
    required_columns = [
        'processing_activity_name', 'category', 'description',
        'controller_name', 'controller_contact', 'controller_address',
        'dpo_name', 'dpo_contact', 'dpo_address',
        'processor_name', 'processor_contact', 'processor_address',
        'representative_name', 'representative_contact', 'representative_address',
        'processing_purpose', 'legal_basis', 'legitimate_interests',
        'data_categories', 'special_categories', 'data_subjects',
        'recipients', 'third_country_transfers', 'safeguards',
        'retention_period', 'retention_criteria', 'security_measures',
        'breach_likelihood', 'breach_impact', 'additional_info'
    ]

    for col in required_columns:
        if col not in df.columns:
            df[col] = ''

    return df

def import_ropa_records(df, user_email, overwrite_existing=False):
    """Import ROPA records into the database"""

    success_count = 0
    error_count = 0
    total_records = len(df)

    for idx, row in df.iterrows():
        try:
            # Convert row to dictionary and clean data
            record_data = row.to_dict()

            # Clean and validate data
            for key, value in record_data.items():
                if pd.isna(value):
                    record_data[key] = ''
                else:
                    record_data[key] = str(value).strip()

            # Ensure we have a processing activity name (required field)
            if not record_data.get('processing_activity_name', '').strip():
                # Generate a default name based on available data
                default_name = f"Processing Activity {idx + 1}"
                if record_data.get('category', '').strip():
                    default_name = f"{record_data['category']} - Activity {idx + 1}"
                elif record_data.get('department_function', '').strip():
                    default_name = f"{record_data['department_function']} - Activity {idx + 1}"
                record_data['processing_activity_name'] = default_name

            # Set status as Draft so records are visible
            record_data['status'] = 'Draft'
            
            # Save record
            record_id = save_ropa_record(record_data, user_email)

            if record_id:
                success_count += 1
                log_audit_event("ROPA Record Imported", user_email, "",
                               f"Imported ROPA record: {record_data.get('processing_activity_name', 'Unknown')}")
            else:
                error_count += 1

        except Exception as e:
            error_count += 1
            print(f"Error importing record {idx + 1}: {str(e)}")

    # Log overall import results
    log_audit_event("ROPA Bulk Import", user_email, "",
                   f"Bulk import completed: {success_count} successful, {error_count} failed")

    return {
        "success_count": success_count,
        "error_count": error_count,
        "total_count": total_records
    }