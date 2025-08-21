
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

def generate_ropa_template():
    """Generate Controller Processing Activities Register template matching the provided format"""
    try:
        # Get existing data to populate template
        existing_data = get_all_ropa_data_for_template()

        # Create workbook and worksheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Controller Processing Activities Register"

        # Define the exact column structure from the image
        columns_structure = [
            # Controller Details section
            ("Name", "controller_name"),
            ("Address", "controller_address"), 
            ("Contact Details", "controller_contact"),
            
            # Data Protection Officer section
            ("Name", "dpo_name"),
            ("Address", "dpo_address"),
            ("Contact Details", "dpo_contact"),
            
            # Representative Details section  
            ("Name", "representative_name"),
            ("Address", "representative_address"),
            ("Contact Details", "representative_contact"),
            
            # Processing Details
            ("Detail the department or function responsible for the processing", "department_function"),
            ("Describe the purpose of the processing", "processing_purpose"),
            ("Describe the categories of data subjects", "data_subjects"),
            ("Describe the categories of personal data", "data_categories"),
            ("If possible, envisaged time limits for erasure of different categories of data", "retention_period"),
            ("Categories of recipients to whom personal data has/will be disclosed", "recipients"),
            ("If possible, description of technical & organisational security measures", "security_measures"),
            ("Legal Basis for Processing", "legal_basis"),
            ("Is Data Protection Impact Assessment (DPIA) Required", "dpia_required"),
            ("Any information questions", "additional_info")
        ]

        # Create the header structure
        # Row 1: Main section headers
        ws.merge_cells('A1:C1')  # Controller Details
        ws['A1'] = 'Controller Details'
        ws.merge_cells('D1:F1')  # Data Protection Officer
        ws['D1'] = 'Data Protection Officer'
        ws.merge_cells('G1:I1')  # Representative Details
        ws['G1'] = 'Representative Details (if applicable)'
        ws.merge_cells('J1:T1')  # Processing Details
        ws['J1'] = 'Processing Details'

        # Style the main headers
        for cell_range in ['A1:C1', 'D1:F1', 'G1:I1', 'J1:T1']:
            for row in ws[cell_range]:
                for cell in row:
                    cell.font = Font(bold=True, color="FFFFFF", size=11)
                    cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    cell.border = Border(
                        left=Side(style='thin'),
                        right=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )

        # Row 2: Sub-headers (Name, Address, Contact Details for each section, then processing details)
        headers = [col[0] for col in columns_structure]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col_idx, value=header)
            cell.font = Font(bold=True, color="FFFFFF", size=10)
            cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

        # Set row heights
        ws.row_dimensions[1].height = 25
        ws.row_dimensions[2].height = 60

        # Set column widths based on content
        column_widths = [25, 35, 30, 25, 35, 30, 25, 35, 30, 40, 40, 35, 40, 30, 35, 45, 25, 15, 30]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width

        # Add existing data if available
        start_row = 3
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

                    # Debug: Print first record's controller data to verify it's being read correctly
                    if row_idx == start_row and db_field in ['controller_name', 'controller_contact', 'controller_address']:
                        print(f"DEBUG Template: {db_field} = '{value}'")

                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.border = Border(
                        left=Side(style='thin'),
                        right=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )
                    cell.alignment = Alignment(wrap_text=True, vertical='top')
                    cell.font = Font(name="Calibri", size=10, color="1F1F1F")

                    # Apply alternating row colors
                    fill_color = "FFFFFF" if row_idx % 2 == 1 else "F2F2F2"
                    cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")

                ws.row_dimensions[row_idx].height = 30

            # Add empty rows for data entry after existing data
            next_empty_row = start_row + len(existing_data)
            for row_idx in range(next_empty_row, next_empty_row + 10):
                fill_color = "FFFFFF" if row_idx % 2 == 1 else "F2F2F2"
                fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
                for col_idx in range(1, len(columns_structure) + 1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    cell.border = Border(
                        left=Side(style='thin'),
                        right=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )
                    cell.fill = fill
                    cell.font = Font(name="Calibri", size=10, color="1F1F1F")
                    cell.alignment = Alignment(wrap_text=True, vertical='top')
                ws.row_dimensions[row_idx].height = 30

        else:
            # If no existing data, just add empty rows for data entry
            for row_idx in range(start_row, start_row + 20):
                fill_color = "FFFFFF" if row_idx % 2 == 1 else "F2F2F2"
                fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
                for col_idx in range(1, len(columns_structure) + 1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    cell.border = Border(
                        left=Side(style='thin'),
                        right=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )
                    cell.fill = fill
                    cell.font = Font(name="Calibri", size=10, color="1F1F1F")
                    cell.alignment = Alignment(wrap_text=True, vertical='top')
                ws.row_dimensions[row_idx].height = 30

        # Add footer
        footer_row = ws.max_row + 2
        footer_cell = ws.cell(row=footer_row, column=1)
        footer_cell.value = "Controller Processing Activities Register - GDPR Compliance Template"
        footer_cell.font = Font(name="Calibri", size=9, color="4472C4", italic=True, bold=True)
        footer_cell.alignment = Alignment(horizontal='center')
        ws.merge_cells(f'A{footer_row}:{get_column_letter(len(columns_structure))}{footer_row}')

        # Save to temporary file
        temp_dir = tempfile.mkdtemp()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Controller_Processing_Activities_Register_{timestamp}.xlsx"
        file_path = os.path.join(temp_dir, filename)

        wb.save(file_path)
        print(f"Template saved to: {file_path}")

        return file_path

    except Exception as e:
        print(f"Error during template generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
