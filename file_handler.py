import pandas as pd
import io
from database import save_ropa_record
from audit_logger import log_audit_event
import openpyxl
from werkzeug.utils import secure_filename
from datetime import datetime
import json

def process_uploaded_file(file, user_email):
    """Process uploaded Excel file with all sheets and store complete structure"""
    try:
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()

        if file_extension not in ['xlsx', 'xls']:
            return "Only Excel files (.xlsx, .xls) are supported for multi-sheet processing"

        # Read all sheets from Excel file
        excel_data = read_all_excel_sheets(file)
        if not excel_data:
            return "No valid data found in Excel file"

        # Store the complete Excel structure in database
        result = store_excel_data_in_database(excel_data, user_email, filename)

        log_audit_event('Excel File Processed', user_email, f'Processed multi-sheet Excel file: {filename}')
        return result

    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return f"Error processing file: {str(e)}"

def read_all_excel_sheets(file):
    """Read all sheets from Excel file and preserve structure"""
    try:
        # Get all sheet names
        xl_file = pd.ExcelFile(file)
        sheet_names = xl_file.sheet_names

        excel_data = {
            'sheets': {},
            'metadata': {
                'total_sheets': len(sheet_names),
                'sheet_names': sheet_names,
                'upload_timestamp': datetime.now().isoformat()
            }
        }

        print(f"Found {len(sheet_names)} sheets: {sheet_names}")

        # Read each sheet
        for sheet_name in sheet_names:
            try:
                # Read sheet with multiple strategies
                sheet_data = read_sheet_with_fallback(file, sheet_name)
                if sheet_data is not None and not sheet_data.empty:
                    # Store data with original column names preserved exactly as uploaded
                    excel_data['sheets'][sheet_name] = {
                        'data': sheet_data.to_dict('records'),
                        'columns': list(sheet_data.columns),  # Keep exact original column names
                        'shape': sheet_data.shape,
                        'has_data': True
                    }
                    print(f"Successfully read sheet '{sheet_name}' with shape {sheet_data.shape}")
                else:
                    excel_data['sheets'][sheet_name] = {
                        'data': [],
                        'columns': [],
                        'shape': (0, 0),
                        'has_data': False,
                        'error': 'No data found'
                    }
                    print(f"No data found in sheet '{sheet_name}'")
            except Exception as e:
                print(f"Error reading sheet '{sheet_name}': {str(e)}")
                excel_data['sheets'][sheet_name] = {
                    'data': [],
                    'columns': [],
                    'shape': (0, 0),
                    'has_data': False,
                    'error': str(e)
                }

        return excel_data

    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        return None

def read_sheet_with_fallback(file, sheet_name):
    """Read sheet with multiple fallback strategies"""
    strategies = [
        {'header': 0},  # First row as header
        {'header': 1},  # Second row as header
        {'header': None},  # No header
        {'header': 0, 'skiprows': 1},  # Skip first row, second as header
    ]

    for strategy in strategies:
        try:
            file.seek(0)  # Reset file pointer
            df = pd.read_excel(file, sheet_name=sheet_name, **strategy)

            # Clean the dataframe
            df = df.dropna(how='all')  # Remove completely empty rows
            df = df.loc[:, ~df.columns.duplicated()]  # Remove duplicate columns

            if not df.empty:
                # Keep original column names EXACTLY as they are - no cleaning or modification
                df.columns = [str(col) for col in df.columns]
                return df
        except Exception as e:
            continue

    return pd.DataFrame()

def store_excel_data_in_database(excel_data, user_email, filename):
    """Store complete Excel data structure in database"""
    from models import ROPARecord, ExcelFileData, ExcelSheetData, User
    from app import db

    try:
        # Get or create user
        user = User.query.filter_by(email=user_email).first()
        if not user:
            user = User(
                email=user_email,
                password_hash='system_upload',
                role='Privacy Officer',
                department='System'
            )
            db.session.add(user)
            db.session.commit()

        # Create Excel file record
        excel_file_record = ExcelFileData(
            filename=filename,
            uploaded_by=user.id,
            total_sheets=excel_data['metadata']['total_sheets'],
            sheet_names=json.dumps(excel_data['metadata']['sheet_names']),
            upload_timestamp=datetime.now(),
            file_metadata=json.dumps(excel_data['metadata'])
        )
        db.session.add(excel_file_record)
        db.session.flush()  # Get the ID

        records_created = 0
        sheets_processed = 0

        # Process each sheet
        for sheet_name, sheet_info in excel_data['sheets'].items():
            if not sheet_info['has_data']:
                continue

            # Store sheet metadata
            excel_sheet_record = ExcelSheetData(
                excel_file_id=excel_file_record.id,
                sheet_name=sheet_name,
                columns=json.dumps(sheet_info['columns']),
                row_count=sheet_info['shape'][0],
                column_count=sheet_info['shape'][1],
                sheet_data=json.dumps(sheet_info['data'])
            )
            db.session.add(excel_sheet_record)
            sheets_processed += 1

            # Try to extract ROPA records from sheet if it looks like ROPA data
            if is_ropa_sheet(sheet_name, sheet_info):
                ropa_records = extract_ropa_from_sheet_data(sheet_info['data'], user.id)
                for record_data in ropa_records:
                    try:
                        record = ROPARecord(**record_data)
                        db.session.add(record)
                        records_created += 1
                    except Exception as e:
                        print(f"Error creating ROPA record: {str(e)}")

        db.session.commit()

        return f"Successfully processed Excel file with {sheets_processed} sheets. Created {records_created} ROPA records from identifiable ROPA sheets."

    except Exception as e:
        db.session.rollback()
        print(f"Error storing Excel data: {str(e)}")
        return f"Error storing Excel data: {str(e)}"

def is_ropa_sheet(sheet_name, sheet_info):
    """Determine if a sheet contains ROPA data"""
    sheet_name_lower = sheet_name.lower()
    
    # Expanded ROPA keywords including common variations
    ropa_sheet_keywords = [
        'ropa', 'record', 'processing', 'activities', 'register', 'controller', 'processor',
        'activity', 'data protection', 'gdpr', 'privacy', 'personal data'
    ]

    # Check sheet name for ROPA indicators
    if any(keyword in sheet_name_lower for keyword in ropa_sheet_keywords):
        print(f"Sheet '{sheet_name}' identified as ROPA sheet by name")
        return True

    # Check column names for ROPA indicators
    columns = [str(col).lower() for col in sheet_info['columns']]
    ropa_column_keywords = [
        'processing', 'controller', 'data', 'purpose', 'legal', 'retention', 'security',
        'activity', 'name', 'department', 'contact', 'address', 'dpo', 'subjects',
        'categories', 'recipients', 'basis', 'measures', 'period'
    ]

    matches = sum(1 for keyword in ropa_column_keywords if any(keyword in col for col in columns))
    
    # Lower threshold for better detection
    if matches >= 2:
        print(f"Sheet '{sheet_name}' identified as ROPA sheet by columns (matches: {matches})")
        return True
        
    # Additional check: if sheet has reasonable amount of data and looks structured
    if len(sheet_info['columns']) >= 5 and sheet_info['shape'][0] > 1:
        # Check if any columns contain typical ROPA field patterns
        typical_patterns = ['name', 'purpose', 'controller', 'data', 'legal']
        pattern_matches = sum(1 for pattern in typical_patterns if any(pattern in col for col in columns))
        
        if pattern_matches >= 2:
            print(f"Sheet '{sheet_name}' identified as potential ROPA sheet by structure")
            return True

    print(f"Sheet '{sheet_name}' not identified as ROPA sheet")
    return False

def extract_ropa_from_sheet_data(sheet_data, user_id):
    """Extract ROPA records from sheet data"""
    ropa_records = []

    for row in sheet_data:
        # Convert row to ROPA record format
        record_data = {
            'processing_activity_name': '',
            'status': 'Draft',
            'created_by': user_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        # Map Excel columns to ROPA fields
        column_mapping = get_column_mapping()

        for excel_col, value in row.items():
            excel_col_lower = str(excel_col).lower()
            for ropa_field, excel_patterns in column_mapping.items():
                if any(pattern in excel_col_lower for pattern in excel_patterns):
                    record_data[ropa_field] = str(value) if pd.notna(value) else ''
                    break

        # Ensure required fields have values
        if not record_data['processing_activity_name']:
            # Generate from available data
            name_parts = []
            if record_data.get('department_function'):
                name_parts.append(record_data['department_function'])
            if record_data.get('processing_purpose'):
                name_parts.append(record_data['processing_purpose'])

            record_data['processing_activity_name'] = ' - '.join(name_parts) or f'Processing Activity {len(ropa_records) + 1}'

        # Only add if it has meaningful data
        if any(record_data.get(field, '').strip() for field in ['controller_name', 'processing_purpose', 'data_categories']):
            ropa_records.append(record_data)

    return ropa_records

def get_column_mapping():
    """Get mapping between Excel columns and ROPA fields"""
    return {
        'processing_activity_name': ['activity', 'name', 'process', 'title'],
        'category': ['category', 'type'],
        'description': ['description', 'detail'],
        'department_function': ['department', 'function', 'responsible'],
        'controller_name': ['controller', 'name'],
        'controller_contact': ['controller contact', 'contact'],
        'controller_address': ['controller address', 'address'],
        'processing_purpose': ['purpose', 'reason'],
        'legal_basis': ['legal', 'basis', 'lawful'],
        'data_categories': ['data categories', 'personal data', 'data types'],
        'data_subjects': ['data subjects', 'subjects'],
        'retention_period': ['retention', 'period', 'time'],
        'security_measures': ['security', 'measures', 'protection'],
        'recipients': ['recipients', 'third parties'],
        'dpo_name': ['dpo', 'protection officer'],
        'dpo_contact': ['dpo contact'],
        'dpo_address': ['dpo address']
    }

def export_excel_with_all_sheets(user_email, user_role, include_updates=True):
    """Export Excel file with all original sheets plus updates"""
    from models import ExcelFileData, ExcelSheetData, ROPARecord, User
    from app import db
    import tempfile
    import os

    try:
        # Get user's uploaded files
        user = User.query.filter_by(email=user_email).first()
        if not user:
            raise Exception("User not found")

        # Get the most recent Excel file uploaded by user or all files for Privacy Officer
        if user_role == 'Privacy Officer':
            excel_files = ExcelFileData.query.order_by(ExcelFileData.upload_timestamp.desc()).all()
        else:
            excel_files = ExcelFileData.query.filter_by(uploaded_by=user.id).order_by(ExcelFileData.upload_timestamp.desc()).all()

        if not excel_files:
            raise Exception("No Excel files found to export")

        # Create new Excel file with all sheets
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Complete_ROPA_Export_{timestamp}.xlsx"
        file_path = os.path.join(temp_dir, filename)

        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            sheets_written = 0

            for excel_file in excel_files:
                # Get all sheets for this file
                sheets = ExcelSheetData.query.filter_by(excel_file_id=excel_file.id).all()

                for sheet in sheets:
                    try:
                        # Load original sheet data
                        sheet_data = json.loads(sheet.sheet_data)
                        df = pd.DataFrame(sheet_data)

                        if not df.empty:
                            # Write original sheet
                            sheet_name = f"{sheet.sheet_name}_{excel_file.id}"
                            if len(sheet_name) > 31:  # Excel sheet name limit
                                sheet_name = sheet_name[:31]

                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                            sheets_written += 1
                    except Exception as e:
                        print(f"Error writing sheet {sheet.sheet_name}: {str(e)}")

            # Add updated ROPA records sheet
            if include_updates:
                try:
                    if user_role == 'Privacy Officer':
                        ropa_records = ROPARecord.query.all()
                    else:
                        ropa_records = ROPARecord.query.filter_by(created_by=user.id).all()

                    if ropa_records:
                        ropa_data = []
                        for record in ropa_records:
                            record_dict = {
                                'Processing Activity Name': record.processing_activity_name,
                                'Category': record.category,
                                'Description': record.description,
                                'Department/Function': record.department_function,
                                'Controller Name': record.controller_name,
                                'Controller Contact': record.controller_contact,
                                'Controller Address': record.controller_address,
                                'DPO Name': record.dpo_name,
                                'DPO Contact': record.dpo_contact,
                                'Processing Purpose': record.processing_purpose,
                                'Legal Basis': record.legal_basis,
                                'Data Categories': record.data_categories,
                                'Data Subjects': record.data_subjects,
                                'Recipients': record.recipients,
                                'Retention Period': record.retention_period,
                                'Security Measures': record.security_measures,
                                'Status': record.status,
                                'Created Date': record.created_at.strftime('%Y-%m-%d %H:%M:%S') if record.created_at else '',
                                'Updated Date': record.updated_at.strftime('%Y-%m-%d %H:%M:%S') if record.updated_at else ''
                            }
                            ropa_data.append(record_dict)

                        ropa_df = pd.DataFrame(ropa_data)
                        ropa_df.to_excel(writer, sheet_name='Updated_ROPA_Records', index=False)
                        sheets_written += 1
                except Exception as e:
                    print(f"Error adding ROPA records sheet: {str(e)}")

        return file_path, filename

    except Exception as e:
        print(f"Error exporting Excel with all sheets: {str(e)}")
        raise e

# Keep existing functions for backward compatibility
def parse_excel_file(uploaded_file):
    """Legacy function - now uses multi-sheet reader"""
    excel_data = read_all_excel_sheets(uploaded_file)
    if excel_data and excel_data['sheets']:
        # Return first sheet with data for backward compatibility
        for sheet_name, sheet_info in excel_data['sheets'].items():
            if sheet_info['has_data']:
                return pd.DataFrame(sheet_info['data'])
    return pd.DataFrame()

def standardize_columns(df):
    """Standardize column names for ROPA processing"""
    column_mapping = {
        'processing activity name': 'processing_activity_name',
        'activity name': 'processing_activity_name',
        'name': 'processing_activity_name',
        'controller': 'controller_name',
        'controller name': 'controller_name',
        'purpose': 'processing_purpose',
        'processing purpose': 'processing_purpose',
        'data categories': 'data_categories',
        'categories of data': 'data_categories',
        'data subjects': 'data_subjects',
        'retention': 'retention_period',
        'retention period': 'retention_period',
        'security measures': 'security_measures',
        'legal basis': 'legal_basis',
        'department': 'department_function',
        'department function': 'department_function'
    }

    # Normalize column names
    df.columns = [str(col).lower().strip() for col in df.columns]

    # Apply mapping
    df = df.rename(columns=column_mapping)

    return df