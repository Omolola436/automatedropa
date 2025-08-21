import pandas as pd
import io
from database import save_ropa_record
from audit_logger import log_audit_event
import openpyxl
from werkzeug.utils import secure_filename

def process_uploaded_file(file, user_email):
    """Process uploaded Excel or CSV file containing ROPA data"""
    try:
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()

        # Read the file based on extension with improved header detection
        if file_extension in ['xlsx', 'xls']:
            # Try reading with different header rows to find the actual data
            df = None
            header_row_found = 0
            
            # First, try to read the entire file to understand its structure
            try:
                full_df = pd.read_excel(file, header=None, engine='openpyxl')
                print(f"Full file shape: {full_df.shape}")
                print(f"First few rows of raw data:")
                print(full_df.head(10))
                
                # Look for the row that contains the most meaningful headers
                best_header_row = 0
                max_meaningful_cols = 0
                
                for row_idx in range(min(10, len(full_df))):  # Check first 10 rows
                    row_values = full_df.iloc[row_idx].values
                    meaningful_cols = 0
                    for val in row_values:
                        if pd.notna(val) and isinstance(val, str) and len(val.strip()) > 2:
                            # Check if it looks like a header (contains common ROPA terms)
                            val_lower = val.lower()
                            if any(term in val_lower for term in ['processing', 'activity', 'controller', 'data', 'purpose', 'legal', 'category', 'subject', 'retention', 'security']):
                                meaningful_cols += 1
                    
                    if meaningful_cols > max_meaningful_cols:
                        max_meaningful_cols = meaningful_cols
                        best_header_row = row_idx
                
                print(f"Best header row found at index: {best_header_row} with {max_meaningful_cols} meaningful columns")
                
                # Read with the best header row
                file.seek(0)  # Reset file pointer
                df = pd.read_excel(file, header=best_header_row, engine='openpyxl')
                header_row_found = best_header_row
                
            except Exception as e:
                print(f"Error with smart header detection: {e}")
                # Fallback to simple reading
                file.seek(0)
                df = pd.read_excel(file, engine='openpyxl')
        elif file_extension == 'csv':
            df = pd.read_csv(file)
        else:
            raise ValueError("Unsupported file format")

        print(f"Original columns in uploaded file: {list(df.columns)}")
        print(f"DataFrame shape: {df.shape}")
        print(f"First few rows preview:")
        print(df.head())

        # Clean the dataframe - remove completely empty rows
        df = df.dropna(how='all')

        # Standardize column names to match our schema
        df = standardize_columns(df)

        print(f"Standardized columns: {list(df.columns)}")

        # Smart detection of processing activity name
        if 'processing_activity_name' not in df.columns:
            # Try to find a suitable column that could be the processing activity name
            potential_name_columns = [col for col in df.columns if any(keyword in col.lower() for keyword in ['name', 'activity', 'process', 'title', 'function', 'department'])]

            if potential_name_columns:
                # Use the first potential column as processing activity name
                df['processing_activity_name'] = df[potential_name_columns[0]]
                print(f"Using column '{potential_name_columns[0]}' as processing_activity_name")
            else:
                # If no clear name column, create one from department + purpose or similar
                if 'department_function' in df.columns and 'processing_purpose' in df.columns:
                    df['processing_activity_name'] = df['department_function'].astype(str) + ' - ' + df['processing_purpose'].astype(str)
                    print("Created processing_activity_name from department_function and processing_purpose")
                elif 'department_function' in df.columns:
                    df['processing_activity_name'] = df['department_function']
                    print("Using department_function as processing_activity_name")
                else:
                    available_columns = list(df.columns)
                    raise ValueError(f"Could not find a suitable column for 'Processing Activity Name'. Available columns: {available_columns}. Please ensure your file has a column with the activity name/title.")

        # Process each row and save to database
        records_processed = 0
        from database import save_ropa_record

        for index, row in df.iterrows():
            # Convert row to dict and handle NaN values
            row_dict = row.to_dict()
            for key, value in row_dict.items():
                if pd.isna(value):
                    row_dict[key] = ''
                else:
                    row_dict[key] = str(value).strip()

            # Special handling for multi-column controller data
            # Look for multiple Name, Address, Contact columns and consolidate them
            controller_names = []
            controller_addresses = []
            controller_contacts = []
            
            for key, value in row_dict.items():
                if key.startswith('controller_name') and value.strip():
                    controller_names.append(value.strip())
                elif key.startswith('controller_address') and value.strip():
                    controller_addresses.append(value.strip())
                elif key.startswith('controller_contact') and value.strip():
                    controller_contacts.append(value.strip())
            
            # If we found multiple controller entries, use the first non-empty one
            if controller_names:
                row_dict['controller_name'] = controller_names[0]
            if controller_addresses:
                row_dict['controller_address'] = controller_addresses[0]
            if controller_contacts:
                row_dict['controller_contact'] = controller_contacts[0]

            # Generate a meaningful processing activity name if empty
            processing_name = row_dict.get('processing_activity_name', '').strip()
            if not processing_name or processing_name in ['nan', 'None']:
                # Try to create from other fields
                dept = row_dict.get('department_function', '').strip()
                purpose = row_dict.get('processing_purpose', '').strip()
                category = row_dict.get('category', '').strip()

                if dept and purpose:
                    processing_name = f"{dept} - {purpose}"
                elif dept:
                    processing_name = f"{dept} Processing Activity"
                elif purpose:
                    processing_name = purpose
                elif category:
                    processing_name = f"{category} Processing"
                else:
                    processing_name = f"Processing Activity {index + 1}"

            record_data = {
                'processing_activity_name': processing_name,
                'category': row_dict.get('category', ''),
                'description': row_dict.get('description', ''),
                'department_function': row_dict.get('department_function', ''),
                'controller_name': row_dict.get('controller_name', ''),
                'controller_contact': row_dict.get('controller_contact', ''),
                'controller_address': row_dict.get('controller_address', ''),
                'dpo_name': row_dict.get('dpo_name', ''),
                'dpo_contact': row_dict.get('dpo_contact', ''),
                'dpo_address': row_dict.get('dpo_address', ''),
                'processor_name': row_dict.get('processor_name', ''),
                'processor_contact': row_dict.get('processor_contact', ''),
                'processor_address': row_dict.get('processor_address', ''),
                'representative_name': row_dict.get('representative_name', ''),
                'representative_contact': row_dict.get('representative_contact', ''),
                'representative_address': row_dict.get('representative_address', ''),
                'processing_purpose': row_dict.get('processing_purpose', ''),
                'legal_basis': row_dict.get('legal_basis', ''),
                'legitimate_interests': row_dict.get('legitimate_interests', ''),
                'data_categories': row_dict.get('data_categories', ''),
                'special_categories': row_dict.get('special_categories', ''),
                'data_subjects': row_dict.get('data_subjects', ''),
                'recipients': row_dict.get('recipients', ''),
                'third_country_transfers': row_dict.get('third_country_transfers', ''),
                'safeguards': row_dict.get('safeguards', ''),
                'retention_period': row_dict.get('retention_period', ''),
                'deletion_procedures': row_dict.get('deletion_procedures', ''),
                'security_measures': row_dict.get('security_measures', ''),
                'breach_likelihood': row_dict.get('breach_likelihood', ''),
                'breach_impact': row_dict.get('breach_impact', ''),
                'risk_level': row_dict.get('risk_level', ''),
                'dpia_required': row_dict.get('dpia_required', ''),
                'dpia_outcome': row_dict.get('dpia_outcome', ''),
                'status': 'Draft'  # Always set uploaded records as Draft
            }

            # Skip rows that have no meaningful data
            has_data = any(value.strip() for value in [
                record_data['processing_activity_name'],
                record_data['department_function'],
                record_data['processing_purpose'],
                record_data['controller_name'],
                record_data['data_categories']
            ])

            if not has_data:
                print(f"Skipping empty row {index + 1}")
                continue

            print(f"Processing record {index + 1}: {record_data['processing_activity_name']}")

            # Save to database using SQLAlchemy models
            try:
                from models import ROPARecord, User
                from app import db
                from datetime import datetime

                # Get user
                user = User.query.filter_by(email=user_email).first()
                if not user:
                    print(f"User not found: {user_email}, creating system user")
                    user = User(
                        email=user_email,
                        password_hash='system_upload',
                        role='Privacy Officer',
                        department='System'
                    )
                    db.session.add(user)
                    db.session.commit()

                # Get all valid columns from database
                import sqlalchemy
                inspector = sqlalchemy.inspect(db.engine)
                valid_columns = [col['name'] for col in inspector.get_columns('ropa_records')]
                
                # Create record with all valid fields from the data
                record_fields = {}
                
                # Add standard fields
                for field in valid_columns:
                    if field not in ['id', 'created_at', 'updated_at']:
                        if field == 'created_by':
                            record_fields[field] = user.id
                        elif field == 'status':
                            record_fields[field] = 'Draft'
                        elif field == 'dpia_required':
                            record_fields[field] = record_data.get(field, '') == 'Yes'
                        else:
                            record_fields[field] = record_data.get(field, '')

                # Create record with all fields
                record = ROPARecord(**record_fields)

                db.session.add(record)
                db.session.commit()

                records_processed += 1
                print(f"Saved record with ID: {record.id}")

            except Exception as e:
                db.session.rollback()
                print(f"Failed to save record: {record_data['processing_activity_name']} - Error: {str(e)}")

        if records_processed == 0:
            return "No valid records found in the file. Please check that your file contains data in the correct format."

        return f"Successfully processed {records_processed} records from {len(df)} total rows"

    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return f"Error processing file: {str(e)}"

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

def detect_and_add_new_columns(df):
    """Detect new columns not in database and add them dynamically"""
    try:
        from models import ROPARecord
        from app import db
        import sqlalchemy
        
        # Get existing column names from the actual database table
        inspector = sqlalchemy.inspect(db.engine)
        existing_columns = [col['name'] for col in inspector.get_columns('ropa_records')]
        
        # Clean uploaded column names - preserve original names but make them database-friendly
        original_columns = list(df.columns)
        df_columns = []
        column_mapping = {}
        
        for col in original_columns:
            # More aggressive cleaning for database compatibility
            clean_col = str(col).lower().strip()
            clean_col = clean_col.replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '')
            clean_col = clean_col.replace('/', '_').replace('&', '_and_').replace('%', '_percent_')
            clean_col = clean_col.replace('?', '').replace('!', '').replace('@', '_at_')
            clean_col = clean_col.replace('#', '_hash_').replace('$', '_dollar_').replace('^', '_')
            clean_col = clean_col.replace('*', '_star_').replace('+', '_plus_').replace('=', '_equals_')
            clean_col = clean_col.replace('[', '').replace(']', '').replace('{', '').replace('}', '')
            clean_col = clean_col.replace('|', '_or_').replace('\\', '_').replace(':', '_')
            clean_col = clean_col.replace(';', '_').replace('"', '').replace("'", '')
            clean_col = clean_col.replace('<', '_lt_').replace('>', '_gt_').replace(',', '_')
            clean_col = clean_col.replace('.', '_').replace('`', '').replace('~', '_')
            
            # Remove multiple underscores and clean up
            while '__' in clean_col:
                clean_col = clean_col.replace('__', '_')
            clean_col = clean_col.strip('_')
            
            # Ensure it doesn't start with a number
            if clean_col and clean_col[0].isdigit():
                clean_col = 'col_' + clean_col
                
            df_columns.append(clean_col)
            column_mapping[col] = clean_col
        
        # Find new columns that don't exist in database
        new_columns = []
        excluded_columns = ['id', 'unnamed_0', 'unnamed_1', 'index', '']
        
        for col in df_columns:
            if col and col not in existing_columns and col not in excluded_columns:
                # Don't create duplicate columns for controller data variations
                if not any(col.startswith(base) for base in ['controller_name', 'controller_address', 'controller_contact']):
                    new_columns.append(col)
        
        # Add new columns to database table if any found
        if new_columns:
            print(f"Found {len(new_columns)} new columns to add: {new_columns}")
            
            # Add columns to database table dynamically
            for col_name in new_columns:
                try:
                    # Use proper SQLAlchemy syntax for newer versions
                    with db.engine.connect() as conn:
                        conn.execute(sqlalchemy.text(f"ALTER TABLE ropa_records ADD COLUMN `{col_name}` TEXT"))
                        conn.commit()
                    print(f"Added new column to database: {col_name}")
                except Exception as e:
                    print(f"Column {col_name} might already exist or error: {e}")
            
        # Rename DataFrame columns to match database columns
        df = df.rename(columns=column_mapping)
        
        return df, new_columns
        
    except Exception as e:
        print(f"Error detecting new columns: {str(e)}")
        return df, []

def standardize_columns(df):
    """Standardize column names to match database schema and handle new columns"""

    # Handle multi-header Excel files by flattening column names
    if hasattr(df.columns, 'nlevels') and df.columns.nlevels > 1:
        df.columns = [' '.join(str(col).strip() for col in col_tuple).strip() for col_tuple in df.columns.values]

    # Clean column names first
    df.columns = [str(col).strip() for col in df.columns]
    
    # First detect and add any new columns to database
    df, new_columns = detect_and_add_new_columns(df)

    # Column mapping from various formats to our standard
    column_mapping = {
        # Basic Information - Enhanced mapping
        'processing activity name': 'processing_activity_name',
        'activity name': 'processing_activity_name',
        'name': 'processing_activity_name',
        'processing activity': 'processing_activity_name',
        'activity': 'processing_activity_name',
        'record name': 'processing_activity_name',
        'ropa name': 'processing_activity_name',
        'title': 'processing_activity_name',
        'process name': 'processing_activity_name',
        'processing name': 'processing_activity_name',
        'name of processing activity': 'processing_activity_name',
        'name of activity': 'processing_activity_name',
        'activity title': 'processing_activity_name',
        'process title': 'processing_activity_name',

        # Department/Function mapping
        'department/function': 'department_function',
        'department function': 'department_function',
        'department': 'department_function',
        'function': 'department_function',
        'business function': 'department_function',
        'detail the department or function responsible for the processing': 'department_function',

        # Purpose mapping
        'purpose': 'processing_purpose',
        'purpose of processing': 'processing_purpose',
        'processing purpose': 'processing_purpose',
        'purpose?': 'processing_purpose',
        'describe the purpose of the processing': 'processing_purpose',

        # Categories mapping
        'categories of data': 'data_categories',
        'data categories': 'data_categories',
        'personal data': 'data_categories',
        'categories of personal data': 'data_categories',
        'describe the categories of personal data': 'data_categories',

        # Data subjects mapping
        'data subjects': 'data_subjects',
        'categories of data subjects': 'data_subjects',
        'describe the categories of data subjects': 'data_subjects',

        # Special categories mapping
        'categories of personal data (sensitive)': 'special_categories',
        'special categories of personal data': 'special_categories',
        'special categories': 'special_categories',
        'sensitive data': 'special_categories',

        # Retention mapping
        'retention period': 'retention_period',
        'retention': 'retention_period',
        'data retention': 'retention_period',
        'if possible, envisaged time limits for erasure of different categories of data': 'retention_period',

        # Recipients mapping
        'recipients': 'recipients',
        'third parties': 'recipients',
        'data recipients': 'recipients',
        'categories of recipients to whom personal data has/will be disclosed': 'recipients',

        # Security mapping
        'security measures used': 'security_measures',
        'security measures': 'security_measures',
        'technical measures': 'security_measures',
        'organisational measures': 'security_measures',
        'if possible, description of technical & organisational security measures  (e.g. pseudonymisation, encryption, codes of conduct etc)': 'security_measures',

        # Controller mapping - Multiple approaches to capture controller info
        'controller': 'controller_name',
        'controller name': 'controller_name',
        'data controller': 'controller_name',
        'name & contact details of the controller': 'controller_name',
        'name:': 'controller_name',  # Handle "Name:" column from Excel
        'name': 'controller_name',   # Handle "Name" column
        
        # Controller address mapping
        'controller address': 'controller_address',
        'address:': 'controller_address',  # Handle "Address:" column from Excel
        'address': 'controller_address',   # Handle "Address" column
        
        # Controller contact mapping
        'controller contact': 'controller_contact',
        'contact details:': 'controller_contact',  # Handle "Contact Details:" column from Excel
        'contact details': 'controller_contact',   # Handle "Contact Details" column
        'contact': 'controller_contact',

        # Legal basis mapping
        'legal basis for processing': 'legal_basis',
        'legal basis': 'legal_basis',
        'lawful basis': 'legal_basis',

        # DPIA mapping
        'is data protection impact assessment (dpia) required?': 'dpia_required',
        'dpia required': 'dpia_required',
        'data protection impact assessment': 'dpia_required',

        # Safeguards mapping
        'safeguards & measures': 'safeguards',
        'safeguards': 'safeguards',
        'protection measures': 'safeguards',

        # Category (general)
        'category': 'category',
        'description': 'description',
    }

    # Normalize column names (lowercase, remove extra spaces)
    df.columns = [str(col).lower().strip() for col in df.columns]

    # Apply mapping
    df = df.rename(columns=column_mapping)

    # Fill missing columns with empty strings
    required_columns = [
        'processing_activity_name', 'category', 'description',
        'department_function', 'controller_name', 'controller_contact', 'controller_address',
        'dpo_name', 'dpo_contact', 'dpo_address',
        'processor_name', 'processor_contact', 'processor_address',
        'representative_name', 'representative_contact', 'representative_address',
        'processing_purpose', 'legal_basis', 'legitimate_interests',
        'data_categories', 'special_categories', 'data_subjects',
        'recipients', 'third_country_transfers', 'safeguards',
        'retention_period', 'retention_criteria', 'deletion_procedures',
        'security_measures', 'breach_likelihood', 'breach_impact',
        'risk_level', 'dpia_required', 'dpia_outcome', 'additional_info'
    ]

    for col in required_columns:
        if col not in df.columns:
            df[col] = ''

    return df

def import_ropa_records(df, user_email, overwrite_existing=False):
    """Import ROPA records into the database"""
    from models import User, ROPARecord
    from app import db
    from datetime import datetime

    success_count = 0
    error_count = 0
    total_records = len(df)

    # Get the user ID from email
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return {
            "success_count": 0,
            "error_count": total_records,
            "total_count": total_records,
            "message": "User not found"
        }

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

            # Create new ROPA record using SQLAlchemy model
            record = ROPARecord(
                processing_activity_name=record_data.get('processing_activity_name', ''),
                category=record_data.get('category', ''),
                description=record_data.get('description', ''),
                department_function=record_data.get('department_function', ''),
                controller_name=record_data.get('controller_name', ''),
                controller_contact=record_data.get('controller_contact', ''),
                controller_address=record_data.get('controller_address', ''),
                dpo_name=record_data.get('dpo_name', ''),
                dpo_contact=record_data.get('dpo_contact', ''),
                dpo_address=record_data.get('dpo_address', ''),
                processor_name=record_data.get('processor_name', ''),
                processor_contact=record_data.get('processor_contact', ''),
                processor_address=record_data.get('processor_address', ''),
                representative_name=record_data.get('representative_name', ''),
                representative_contact=record_data.get('representative_contact', ''),
                representative_address=record_data.get('representative_address', ''),
                processing_purpose=record_data.get('processing_purpose', ''),
                legal_basis=record_data.get('legal_basis', ''),
                legitimate_interests=record_data.get('legitimate_interests', ''),
                data_categories=record_data.get('data_categories', ''),
                special_categories=record_data.get('special_categories', ''),
                data_subjects=record_data.get('data_subjects', ''),
                recipients=record_data.get('recipients', ''),
                third_country_transfers=record_data.get('third_country_transfers', ''),
                safeguards=record_data.get('safeguards', ''),
                retention_period=record_data.get('retention_period', ''),
                retention_criteria=record_data.get('retention_criteria', ''),
                retention_justification=record_data.get('retention_justification', ''),
                security_measures=record_data.get('security_measures', ''),
                breach_likelihood=record_data.get('breach_likelihood', ''),
                breach_impact=record_data.get('breach_impact', ''),
                dpia_required=record_data.get('dpia_required', ''),
                additional_info=record_data.get('additional_info', ''),
                international_transfers=record_data.get('international_transfers', ''),
                status='Draft',  # Set as Draft so it shows in Privacy Champion dashboard
                created_by=user.id,  # Use user ID, not email
                created_at=datetime.utcnow()
            )

            db.session.add(record)
            db.session.commit()

            success_count += 1
            log_audit_event("ROPA Record Imported", user_email,
                           f"Imported ROPA record: {record_data.get('processing_activity_name', 'Unknown')}")

        except Exception as e:
            db.session.rollback()
            error_count += 1
            print(f"Error importing record {idx + 1}: {str(e)}")

    # Log overall import results
    log_audit_event("ROPA Bulk Import", user_email,
                   f"Bulk import completed: {success_count} successful, {error_count} failed")

    return {
        "success_count": success_count,
        "error_count": error_count,
        "total_count": total_records
    }