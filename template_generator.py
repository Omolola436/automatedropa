"""
ROPA Template Generator
"""
import pandas as pd
import tempfile
import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows

def generate_ropa_template():
    """Generate Excel template for ROPA data collection"""
    
    # Create workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "ROPA Template"
    
    # Define headers and their descriptions
    headers = [
        ("Processing Activity Name", "Name of the processing activity (REQUIRED)"),
        ("Category", "Category of processing (e.g., HR, Marketing, Sales)"),
        ("Description", "Detailed description of the processing activity (REQUIRED)"),
        ("Department/Function", "Department or business function responsible"),
        ("Controller Name", "Name of the data controller (REQUIRED)"),  
        ("Controller Contact", "Contact details of the controller (REQUIRED)"),
        ("Controller Address", "Address of the controller (REQUIRED)"),
        ("DPO Name", "Data Protection Officer name"),
        ("DPO Contact", "DPO contact details"),
        ("DPO Address", "DPO address"),
        ("Processor Name", "Name of data processor (if applicable)"),
        ("Processor Contact", "Processor contact details"),
        ("Processor Address", "Processor address"),
        ("Representative Name", "EU representative name (if applicable)"),
        ("Representative Contact", "Representative contact details"),
        ("Representative Address", "Representative address"),
        ("Purpose of Processing", "Purpose and legal justification (REQUIRED)"),
        ("Legal Basis", "Legal basis under GDPR (REQUIRED)"),
        ("Legitimate Interests", "Details if legal basis is legitimate interests"),
        ("Data Categories", "Categories of personal data processed (REQUIRED)"),
        ("Special Categories", "Special categories of personal data"),
        ("Data Subjects", "Categories of data subjects (REQUIRED)"),
        ("Recipients", "Categories of recipients (REQUIRED)"),
        ("Third Country Transfers", "Details of transfers to third countries"),
        ("Safeguards", "Safeguards for third country transfers"),
        ("Retention Period", "How long data is kept (REQUIRED)"),
        ("Retention Criteria", "Criteria for determining retention period"),
        ("Security Measures", "Technical and organizational security measures (REQUIRED)"),
        ("Additional Information", "Any additional relevant information")
    ]
    
    # Style definitions
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    required_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'), 
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Add title
    ws['A1'] = "GDPR ROPA Data Collection Template"
    ws['A1'].font = Font(bold=True, size=16)
    ws.merge_cells('A1:D1')
    
    # Add instructions
    instructions = [
        "Instructions:",
        "1. Fill in all REQUIRED fields (highlighted in yellow)",
        "2. Provide as much detail as possible for accurate ROPA records",
        "3. Use the dropdown values where provided",
        "4. Save and upload this file back to the system when complete",
        ""
    ]
    
    row = 3
    for instruction in instructions:
        ws[f'A{row}'] = instruction
        if instruction.startswith("Instructions:"):
            ws[f'A{row}'].font = Font(bold=True)
        row += 1
    
    # Add headers
    header_row = row + 1
    for col, (header, description) in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(wrap_text=True, vertical='center')
        
        # Add description in second row
        desc_cell = ws.cell(row=header_row + 1, column=col, value=description)
        desc_cell.border = border
        desc_cell.alignment = Alignment(wrap_text=True, vertical='center')
        
        # Highlight required fields
        if "(REQUIRED)" in description:
            desc_cell.fill = required_fill
    
    # Add example data row
    example_row = header_row + 2
    example_data = [
        "Employee Data Management",  # Processing Activity Name
        "Human Resources",  # Category
        "Processing of employee personal data for HR management purposes",  # Description
        "HR",  # Department/Function
        "Your Company Ltd",  # Controller Name
        "hr@yourcompany.com",  # Controller Contact
        "123 Business Street, City, Country",  # Controller Address
        "Jane Doe",  # DPO Name
        "dpo@yourcompany.com",  # DPO Contact
        "123 Business Street, City, Country",  # DPO Address
        "",  # Processor Name
        "",  # Processor Contact
        "",  # Processor Address
        "",  # Representative Name
        "",  # Representative Contact
        "",  # Representative Address
        "Human Resources Management",  # Purpose of Processing
        "Contract",  # Legal Basis
        "",  # Legitimate Interests
        "Contact Information, Identity Data, Employment Data",  # Data Categories
        "",  # Special Categories
        "Employees, Job Applicants",  # Data Subjects
        "HR Department, Payroll Provider",  # Recipients
        "",  # Third Country Transfers
        "",  # Safeguards
        "7 years after employment ends",  # Retention Period
        "Legal requirement and business necessity",  # Retention Criteria
        "Access controls, encryption, regular backups",  # Security Measures
        "Standard HR processing activities"  # Additional Information
    ]
    
    for col, value in enumerate(example_data, 1):
        cell = ws.cell(row=example_row, column=col, value=value)
        cell.border = border
        if col <= len(headers):
            # Light blue fill for example row
            cell.fill = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
    
    # Add legal basis options sheet
    legal_basis_ws = wb.create_sheet("Legal Basis Options")
    legal_basis_options = [
        ("Legal Basis", "Description", "When to Use"),
        ("Consent", "Individual has given clear consent", "Marketing, optional services"),
        ("Contract", "Processing necessary for contract performance", "Employee data, customer orders"),
        ("Legal Obligation", "Required by law", "Tax records, regulatory reporting"),
        ("Vital Interests", "Protecting someone's life", "Medical emergencies"),
        ("Public Task", "Performing official functions", "Government agencies"),
        ("Legitimate Interests", "Legitimate business interests", "Fraud prevention, direct marketing")
    ]
    
    for row, (basis, desc, when) in enumerate(legal_basis_options, 1):
        legal_basis_ws.cell(row=row, column=1, value=basis)
        legal_basis_ws.cell(row=row, column=2, value=desc)
        legal_basis_ws.cell(row=row, column=3, value=when)
        
        if row == 1:  # Header row
            for col in range(1, 4):
                cell = legal_basis_ws.cell(row=row, column=col)
                cell.font = header_font
                cell.fill = header_fill
    
    # Add data categories sheet
    categories_ws = wb.create_sheet("Data Categories")
    data_categories = [
        ("Category", "Examples"),
        ("Contact Information", "Name, email, phone, address"),
        ("Identity Data", "Name, date of birth, ID numbers"),
        ("Employment Data", "Job title, salary, performance reviews"),
        ("Financial Data", "Bank details, payment information"),
        ("Technical Data", "IP address, login data, cookies"),
        ("Usage Data", "Website usage, app interactions"),
        ("Marketing Data", "Preferences, marketing responses"),
        ("Location Data", "GPS coordinates, delivery addresses"),
        ("Communication Data", "Emails, messages, call logs"),
        ("Transaction Data", "Purchase history, billing records")
    ]
    
    for row, (category, examples) in enumerate(data_categories, 1):
        categories_ws.cell(row=row, column=1, value=category)
        categories_ws.cell(row=row, column=2, value=examples)
        
        if row == 1:  # Header row
            for col in range(1, 3):
                cell = categories_ws.cell(row=row, column=col)
                cell.font = header_font
                cell.fill = header_fill
    
    # Adjust column widths - handle merged cells properly
    from openpyxl.utils import get_column_letter
    for ws_name in [ws, legal_basis_ws, categories_ws]:
        for col_num in range(1, ws_name.max_column + 1):
            max_length = 0
            column_letter = get_column_letter(col_num)
            
            for row_num in range(1, ws_name.max_row + 1):
                cell = ws_name.cell(row=row_num, column=col_num)
                # Skip merged cells by checking if it's part of a merged range
                skip_cell = False
                for merged_range in ws_name.merged_cells.ranges:
                    if cell.coordinate in merged_range:
                        skip_cell = True
                        break
                
                if skip_cell:
                    continue
                    
                try:
                    if cell.value and len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)  # Cap at 50 chars
            if adjusted_width > 0:
                ws_name.column_dimensions[column_letter].width = adjusted_width
    
    # Save to temporary file
    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ROPA_Template_{timestamp}.xlsx"
    file_path = os.path.join(temp_dir, filename)
    
    wb.save(file_path)
    
    return file_path
