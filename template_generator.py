
import os
import tempfile
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd
import openpyxl

def get_all_database_columns():
    """Get all columns from the ROPARecord table dynamically"""
    try:
        from app import db
        import sqlalchemy

        # Use inspector to get actual database columns (including dynamically added ones)
        inspector = sqlalchemy.inspect(db.engine)
        table_columns = inspector.get_columns('ropa_records')
        columns = [col['name'] for col in table_columns]

        # Filter out system columns
        excluded_columns = ['id', 'created_by', 'reviewed_by']
        return [col for col in columns if col not in excluded_columns]
    except Exception as e:
        print(f"Error getting database columns: {str(e)}")
        # Fallback to model columns if inspector fails
        try:
            from models import ROPARecord
            columns = [column.name for column in ROPARecord.__table__.columns]
            excluded_columns = ['id', 'created_by', 'reviewed_by']
            return [col for col in columns if col not in excluded_columns]
        except:
            return []

def get_all_ropa_data_for_template():
    """Get all existing ROPA records as a pandas DataFrame for template population"""
    try:
        from database import get_db_connection
        import sqlite3

        conn = get_db_connection()
        
        # Get all records directly from database using raw SQL
        query = """
        SELECT r.*, u.email as created_by_email 
        FROM ropa_records r 
        LEFT JOIN users u ON r.created_by = u.id 
        ORDER BY r.created_at DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        print(f"Found {len(df)} ROPA records for template")
        
        if df.empty:
            return pd.DataFrame()

        # Debug: Print sample data to see what we actually have
        print("Sample record data from database:")
        for col in df.columns:
            sample_value = df[col].iloc[0] if len(df) > 0 else 'No data'
            print(f"  {col}: {sample_value}")
        
        # Clean up the data
        for col in df.columns:
            if col in ['created_at', 'updated_at', 'reviewed_at', 'approved_at']:
                # Keep datetime columns as strings if they're already formatted
                df[col] = df[col].fillna('')
            elif col == 'dpia_required':
                # Convert boolean/int to Yes/No
                df[col] = df[col].apply(lambda x: 'Yes' if x in [1, True, 'Yes', 'yes'] else 'No' if x in [0, False, 'No', 'no'] else str(x) if pd.notna(x) else '')
            else:
                # Fill NaN values with empty strings and convert to string
                df[col] = df[col].fillna('').astype(str)
                # Clean up 'nan' strings
                df[col] = df[col].replace('nan', '')

        print(f"DataFrame created with {len(df)} rows and columns: {list(df.columns)}")
        return df

    except Exception as e:
        print(f"Error getting all ROPA data for template: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def read_uploaded_excel_structure(file_path):
    """Read the uploaded ROPA Excel file to understand its exact structure"""
    try:
        # Try to read the Excel file
        df = pd.read_excel(file_path, header=[0, 1])  # Read with multi-level headers
        print(f"Excel file structure:")
        print(f"Columns: {df.columns.tolist()}")
        print(f"Shape: {df.shape}")
        return df
    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        try:
            # Try with single header
            df = pd.read_excel(file_path, header=0)
            print(f"Excel file structure (single header):")
            print(f"Columns: {df.columns.tolist()}")
            print(f"Shape: {df.shape}")
            return df
        except Exception as e2:
            print(f"Error reading Excel file with single header: {str(e2)}")
            return None

def generate_ropa_template():
    """Generate Controller Processing Activities Register template exactly matching the uploaded ROPA format"""
    try:
        # First, try to read the uploaded ROPA file to understand its structure
        ropa_file_path = "attached_assets/ROPA_1755785319439.xlsx"
        reference_structure = None
        
        if os.path.exists(ropa_file_path):
            reference_structure = read_uploaded_excel_structure(ropa_file_path)
            if reference_structure is not None:
                print("Successfully read reference ROPA structure")

        # Get existing data to populate template
        existing_data = get_all_ropa_data_for_template()

        # Create workbook and worksheet
        wb = Workbook()
        ws = wb.active
        ws.title = "ROPA"  # Keep it short to match the uploaded file

        # Define the exact column structure from the uploaded ROPA file and image
        # This matches the exact format shown in your image
        columns_structure = [
            # Controller Details section (3 columns)
            ("Name", "controller_name"),
            ("Address", "controller_address"), 
            ("Contact Details", "controller_contact"),
            
            # Data Protection Officer section (3 columns)
            ("Name", "dpo_name"),
            ("Address", "dpo_address"),
            ("Contact Details", "dpo_contact"),
            
            # Representative Details section (3 columns)
            ("Name", "representative_name"),
            ("Address", "representative_address"),
            ("Contact Details", "representative_contact"),
            
            # Processing Details (11 columns to match the image exactly)
            ("Detail the department or function responsible for the processing", "department_function"),
            ("Describe the purpose of the processing", "processing_purpose"),
            ("Describe the categories of data subjects", "data_subjects"),
            ("Describe the categories of personal data", "data_categories"),
            ("If possible, envisaged time limits for erasure of different categories of data", "retention_period"),
            ("Categories of recipients to whom personal data has/will be disclosed", "recipients"),
            ("If possible, description of technical & organisational security measures (e.g. pseudonymisation, encryption, codes of conduct etc)", "security_measures"),
            ("Legal Basis for Processing", "legal_basis"),
            ("Is Data Protection Impact Assessment (DPIA) Required?", "dpia_required"),
            ("International transfers", "international_transfers"),
            ("Any other relevant information", "additional_info")
        ]

        # Create the header structure exactly as shown in the image
        # Row 1: Main section headers
        ws.merge_cells('A1:C1')  # Controller Details
        ws['A1'] = 'Controller Details'
        ws['A1'].font = Font(bold=True, color="FFFFFF", size=11)
        ws['A1'].fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        ws['A1'].alignment = Alignment(horizontal="center", vertical="center")
        ws['A1'].border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        ws.merge_cells('D1:F1')  # Data Protection Officer
        ws['D1'] = 'Data Protection Officer'
        ws['D1'].font = Font(bold=True, color="FFFFFF", size=11)
        ws['D1'].fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        ws['D1'].alignment = Alignment(horizontal="center", vertical="center")
        ws['D1'].border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        ws.merge_cells('G1:I1')  # Representative Details
        ws['G1'] = 'Representative Details (if applicable)'
        ws['G1'].font = Font(bold=True, color="FFFFFF", size=11)
        ws['G1'].fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        ws['G1'].alignment = Alignment(horizontal="center", vertical="center")
        ws['G1'].border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        # Calculate the last column letter for Processing Details
        last_col = get_column_letter(len(columns_structure))
        ws.merge_cells(f'J1:{last_col}1')  # Processing Details
        ws['J1'] = 'Processing Details'
        ws['J1'].font = Font(bold=True, color="FFFFFF", size=11)
        ws['J1'].fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        ws['J1'].alignment = Alignment(horizontal="center", vertical="center")
        ws['J1'].border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

        # Row 2: Sub-headers exactly as shown in the image
        headers = [col[0] for col in columns_structure]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col_idx, value=header)
            cell.font = Font(bold=True, color="FFFFFF", size=9)
            cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

        # Set row heights to match the image
        ws.row_dimensions[1].height = 30
        ws.row_dimensions[2].height = 80  # Taller for the detailed headers

        # Set column widths to match the proportions in the image
        column_widths = [20, 30, 25, 20, 30, 25, 20, 30, 25, 35, 35, 30, 35, 25, 30, 40, 25, 15, 25, 30]
        for i, width in enumerate(column_widths[:len(columns_structure)], 1):
            ws.column_dimensions[get_column_letter(i)].width = width

        # Add sample data row (Row 3) exactly as shown in the uploaded file
        sample_data = [
            "Trinity Pharmacy", "109 Josiah Chinamano Avenue, Harare", "",  # Controller
            "Tendai F Mataba", "13 Meadow Bank, Northwood, Mt Pleasant", "2.63775E+11",  # DPO
            "", "", "",  # Representative
            "SALES", "Processing Medication", "Customer", "Identity Data", "6", "marketing dep", "Access Control",  # Processing details
            "", "", "", ""  # Additional fields
        ]
        
        # Trim sample data to match actual columns
        sample_data = sample_data[:len(columns_structure)]
        
        for col_idx, value in enumerate(sample_data, 1):
            if col_idx <= len(columns_structure):
                cell = ws.cell(row=3, column=col_idx, value=value)
                cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
                cell.alignment = Alignment(wrap_text=True, vertical='top')
                cell.font = Font(name="Calibri", size=10)
                cell.fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

        # Add second sample row (Row 4) exactly as shown
        sample_data_2 = [
            "", "", "",  # Controller (empty in sample)
            "", "", "",  # DPO (empty in sample)
            "", "", "",  # Representative (empty in sample)
            "HR", "Staff Information", "Staff", "Identity Data, Financial Data", "5", "HR Dep", "Access Control, Data Minimization, Encryption",  # Processing details
            "", "", "", ""  # Additional fields
        ]
        
        # Trim sample data to match actual columns
        sample_data_2 = sample_data_2[:len(columns_structure)]
        
        for col_idx, value in enumerate(sample_data_2, 1):
            if col_idx <= len(columns_structure):
                cell = ws.cell(row=4, column=col_idx, value=value)
                cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
                cell.alignment = Alignment(wrap_text=True, vertical='top')
                cell.font = Font(name="Calibri", size=10)
                cell.fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

        ws.row_dimensions[3].height = 30
        ws.row_dimensions[4].height = 30

        # Add existing database data starting from row 5
        start_row = 5
        if not existing_data.empty:
            print(f"Populating template with {len(existing_data)} existing records")
            
            for row_idx, (_, row) in enumerate(existing_data.iterrows(), start_row):
                for col_idx, (header, db_field) in enumerate(columns_structure, 1):
                    # Get value from existing data, default to empty string
                    value = row.get(db_field, '') if db_field else ''

                    # Handle None values and convert to string
                    if value is None or str(value).lower() in ['nan', 'none']:
                        value = ''
                    else:
                        value = str(value).strip()

                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
                    cell.alignment = Alignment(wrap_text=True, vertical='top')
                    cell.font = Font(name="Calibri", size=10)

                    # Apply alternating row colors
                    fill_color = "FFFFFF" if row_idx % 2 == 1 else "F2F2F2"
                    cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")

                ws.row_dimensions[row_idx].height = 30

            # Add empty rows for data entry after existing data
            next_empty_row = start_row + len(existing_data)
        else:
            next_empty_row = start_row

        # Add empty rows for future data entry
        for row_idx in range(next_empty_row, next_empty_row + 20):
            fill_color = "FFFFFF" if row_idx % 2 == 1 else "F2F2F2"
            fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
            for col_idx in range(1, len(columns_structure) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
                cell.fill = fill
                cell.font = Font(name="Calibri", size=10)
                cell.alignment = Alignment(wrap_text=True, vertical='top')
            ws.row_dimensions[row_idx].height = 30

        # Save to temporary file
        temp_dir = tempfile.mkdtemp()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ROPA_{timestamp}.xlsx"
        file_path = os.path.join(temp_dir, filename)

        wb.save(file_path)
        print(f"Template saved to: {file_path}")

        return file_path

    except Exception as e:
        print(f"Error during template generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
