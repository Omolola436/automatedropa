
"""
ROPA Template Generator with Custom Fields Support
"""
import pandas as pd
import tempfile
import os
import json
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows
from custom_tab_automation import get_approved_custom_fields_by_category

def generate_ropa_template():
    """Generate Excel template for ROPA data collection matching the uploaded format"""
    
    # Create workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Record of Processing Activities"
    
    # Get approved custom fields
    try:
        custom_fields = get_approved_custom_fields_by_category()
    except:
        custom_fields = {}
    
    # Define headers matching the uploaded document structure
    headers = [
        ("Processing Activity Name", "Name of the processing activity"),
        ("Category", "Category of processing activity"),
        ("Description", "Description of the processing activity"),
        ("Data Controller", "Name of the data controller"),
        ("Contact Details", "Contact details of the controller"),
        ("Controller Address", "Address of the controller"),
        ("DPO Name", "Data Protection Officer name"),
        ("DPO Contact", "DPO contact details"),
        ("Purpose of Processing", "Purpose and justification for processing"),
        ("Legal Basis", "Legal basis under GDPR (Art. 6)"),
        ("Legitimate Interests", "Details if legal basis is legitimate interests"),
        ("Categories of Personal Data", "Types of personal data processed"),
        ("Special Categories", "Special categories of personal data (Art. 9)"),
        ("Data Subjects", "Categories of data subjects"),
        ("Recipients", "Recipients or categories of recipients"),
        ("Third Country Transfers", "Transfers to third countries or international organizations"),
        ("Safeguards", "Appropriate safeguards for transfers"),
        ("Retention Period", "Retention period for personal data"),
        ("Retention Criteria", "Criteria for determining retention period"),
        ("Technical Measures", "Technical security measures"),
        ("Organizational Measures", "Organizational security measures"),
        ("Source of Data", "Source of personal data"),
        ("Data Subject Rights", "Information about data subject rights"),
        ("Additional Information", "Any additional relevant information")
    ]
    
    # Add approved custom fields to headers
    for category, fields in custom_fields.items():
        for field in fields:
            field_header = f"{category} - {field['field_name']}"
            field_desc = f"Custom field: {field['field_name']}"
            if field['is_required']:
                field_desc += " (REQUIRED)"
            headers.append((field_header, field_desc))
    
    # Style definitions
    title_font = Font(bold=True, size=14, color="FFFFFF")
    title_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, size=11, color="000000")
    header_fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
    required_fill = PatternFill(start_color="FFD700", end_color="FFD700", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'), 
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Add title
    ws['A1'] = "RECORD OF PROCESSING ACTIVITIES"
    ws['A1'].font = title_font
    ws['A1'].fill = title_fill
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.merge_cells('A1:X1')
    ws.row_dimensions[1].height = 30
    
    # Add subtitle
    ws['A2'] = "GDPR Article 30 Compliance Template"
    ws['A2'].font = Font(bold=True, size=12)
    ws['A2'].alignment = Alignment(horizontal='center')
    ws.merge_cells('A2:X2')
    ws.row_dimensions[2].height = 25
    
    # Add instructions
    instructions = [
        "",
        "Instructions for completing this Record of Processing Activities:",
        "1. Complete all fields marked as REQUIRED",
        "2. Provide detailed information for each processing activity",
        "3. Ensure legal basis is clearly identified under GDPR Article 6",
        "4. Include appropriate safeguards for any third country transfers",
        "5. Save and upload this completed file back to the system",
        ""
    ]
    
    row = 3
    for instruction in instructions:
        ws[f'A{row}'] = instruction
        if instruction.startswith("Instructions"):
            ws[f'A{row}'].font = Font(bold=True, size=11)
        elif instruction.startswith(("1.", "2.", "3.", "4.", "5.")):
            ws[f'A{row}'].font = Font(size=10)
        row += 1
    
    # Add headers
    header_row = row + 1
    for col, (header, description) in enumerate(headers, 1):
        # Header cell
        cell = ws.cell(row=header_row, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        
        # Description cell
        desc_cell = ws.cell(row=header_row + 1, column=col, value=description)
        desc_cell.font = Font(size=9, italic=True)
        desc_cell.border = border
        desc_cell.alignment = Alignment(wrap_text=True, vertical='center')
        
        # Highlight required fields
        if any(req in header for req in ["Processing Activity Name", "Data Controller", "Purpose of Processing", "Legal Basis", "Categories of Personal Data", "Data Subjects", "Recipients", "Retention Period"]):
            desc_cell.fill = required_fill
    
    # Add example data row
    example_row = header_row + 2
    example_data = [
        "Employee Human Resources Management",  # Processing Activity Name
        "Human Resources",  # Category
        "Processing of employee personal data for HR administration, payroll, benefits, and performance management",  # Description
        "Your Company Name Ltd",  # Data Controller
        "hr@yourcompany.com, +44 123 456 7890",  # Contact Details
        "123 Business Street, London, UK, SW1A 1AA",  # Controller Address
        "Jane Smith",  # DPO Name
        "dpo@yourcompany.com, +44 123 456 7891",  # DPO Contact
        "Human resources management, payroll processing, employee benefits administration",  # Purpose of Processing
        "Article 6(1)(b) - Performance of contract",  # Legal Basis
        "",  # Legitimate Interests
        "Name, email, phone number, address, employee ID, salary, bank details, performance data",  # Categories of Personal Data
        "",  # Special Categories
        "Current employees, former employees, job applicants",  # Data Subjects
        "HR department, payroll provider, pension scheme administrators",  # Recipients
        "",  # Third Country Transfers
        "",  # Safeguards
        "7 years after employment termination",  # Retention Period
        "Legal obligations and legitimate business interests",  # Retention Criteria
        "Access controls, encryption, secure servers, regular backups",  # Technical Measures
        "Staff training, data protection policies, incident response procedures",  # Organizational Measures
        "Employee application forms, employment contracts, direct from employees",  # Source of Data
        "Access, rectification, erasure, portability, restriction of processing",  # Data Subject Rights
        "Regular review and updates as required by GDPR"  # Additional Information
    ]
    
    # Fill example data
    for col, value in enumerate(example_data, 1):
        if col <= len(headers):
            cell = ws.cell(row=example_row, column=col, value=value)
            cell.border = border
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            # Light blue fill for example row
            cell.fill = PatternFill(start_color="F0F8FF", end_color="F0F8FF", fill_type="solid")
    
    # Set row heights
    ws.row_dimensions[header_row].height = 40
    ws.row_dimensions[header_row + 1].height = 60
    ws.row_dimensions[example_row].height = 80
    
    # Add additional worksheets for reference
    
    # Legal Basis Reference Sheet
    legal_basis_ws = wb.create_sheet("Legal Basis Reference")
    legal_basis_data = [
        ("Article", "Legal Basis", "Description", "Examples"),
        ("6(1)(a)", "Consent", "Individual has given clear consent", "Marketing emails, newsletters, optional services"),
        ("6(1)(b)", "Contract", "Processing necessary for contract performance", "Employee records, customer orders, service delivery"),
        ("6(1)(c)", "Legal Obligation", "Required by law", "Tax records, regulatory reporting, statutory obligations"),
        ("6(1)(d)", "Vital Interests", "Protecting someone's life", "Medical emergencies, health and safety incidents"),
        ("6(1)(e)", "Public Task", "Performing official functions", "Government services, public sector duties"),
        ("6(1)(f)", "Legitimate Interests", "Legitimate business interests", "Fraud prevention, direct marketing, security")
    ]
    
    for row, (article, basis, desc, examples) in enumerate(legal_basis_data, 1):
        legal_basis_ws.cell(row=row, column=1, value=article)
        legal_basis_ws.cell(row=row, column=2, value=basis)
        legal_basis_ws.cell(row=row, column=3, value=desc)
        legal_basis_ws.cell(row=row, column=4, value=examples)
        
        if row == 1:  # Header row
            for col in range(1, 5):
                cell = legal_basis_ws.cell(row=row, column=col)
                cell.font = header_font
                cell.fill = header_fill
                cell.border = border
        else:
            for col in range(1, 5):
                cell = legal_basis_ws.cell(row=row, column=col)
                cell.border = border
                cell.alignment = Alignment(wrap_text=True, vertical='top')
    
    # Data Categories Reference Sheet
    categories_ws = wb.create_sheet("Data Categories Reference")
    data_categories = [
        ("Category", "Examples", "Sensitivity Level"),
        ("Identity Data", "Name, date of birth, ID numbers, photographs", "Standard"),
        ("Contact Information", "Email, phone, postal address, social media", "Standard"),
        ("Financial Data", "Bank details, payment information, salary, expenses", "High"),
        ("Employment Data", "Job title, performance reviews, disciplinary records", "Standard"),
        ("Technical Data", "IP address, login data, cookies, device information", "Standard"),
        ("Usage Data", "Website usage, application interactions, preferences", "Standard"),
        ("Location Data", "GPS coordinates, delivery addresses, travel data", "Standard"),
        ("Communication Data", "Emails, messages, call logs, meeting records", "Standard"),
        ("Health Data", "Medical records, health assessments, absence records", "Special Category"),
        ("Biometric Data", "Fingerprints, facial recognition, voice patterns", "Special Category")
    ]
    
    for row, (category, examples, sensitivity) in enumerate(data_categories, 1):
        categories_ws.cell(row=row, column=1, value=category)
        categories_ws.cell(row=row, column=2, value=examples)
        categories_ws.cell(row=row, column=3, value=sensitivity)
        
        if row == 1:  # Header row
            for col in range(1, 4):
                cell = categories_ws.cell(row=row, column=col)
                cell.font = header_font
                cell.fill = header_fill
                cell.border = border
        else:
            for col in range(1, 4):
                cell = categories_ws.cell(row=row, column=col)
                cell.border = border
                cell.alignment = Alignment(wrap_text=True, vertical='top')
                # Highlight special categories
                if sensitivity == "Special Category":
                    cell.fill = PatternFill(start_color="FFE6E6", end_color="FFE6E6", fill_type="solid")
    
    # Adjust column widths for all sheets
    from openpyxl.utils import get_column_letter
    
    # Main sheet column widths
    column_widths = {
        1: 25,   # Processing Activity Name
        2: 15,   # Category
        3: 35,   # Description
        4: 20,   # Data Controller
        5: 25,   # Contact Details
        6: 30,   # Controller Address
        7: 15,   # DPO Name
        8: 25,   # DPO Contact
        9: 30,   # Purpose of Processing
        10: 20,  # Legal Basis
        11: 25,  # Legitimate Interests
        12: 35,  # Categories of Personal Data
        13: 20,  # Special Categories
        14: 25,  # Data Subjects
        15: 25,  # Recipients
        16: 25,  # Third Country Transfers
        17: 25,  # Safeguards
        18: 20,  # Retention Period
        19: 25,  # Retention Criteria
        20: 30,  # Technical Measures
        21: 30,  # Organizational Measures
        22: 25,  # Source of Data
        23: 25,  # Data Subject Rights
        24: 25   # Additional Information
    }
    
    for col_num, width in column_widths.items():
        if col_num <= len(headers):
            column_letter = get_column_letter(col_num)
            ws.column_dimensions[column_letter].width = width
    
    # Set column widths for reference sheets
    for ref_ws in [legal_basis_ws, categories_ws]:
        for col_num in range(1, ref_ws.max_column + 1):
            column_letter = get_column_letter(col_num)
            if ref_ws == legal_basis_ws:
                widths = [8, 18, 35, 40]
            else:
                widths = [20, 40, 15]
            if col_num <= len(widths):
                ref_ws.column_dimensions[column_letter].width = widths[col_num - 1]
    
    # Save to temporary file
    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Record_of_Processing_Activities_{timestamp}.xlsx"
    file_path = os.path.join(temp_dir, filename)
    
    wb.save(file_path)
    
    return file_path
