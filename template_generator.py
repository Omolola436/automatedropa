
import os
import tempfile
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def get_approved_custom_fields_by_category():
    """Get approved custom fields organized by category"""
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT category, field_name, field_type, is_required, options
            FROM custom_fields 
            WHERE status = 'Approved'
            ORDER BY category, field_name
        """)
        
        fields = cursor.fetchall()
        conn.close()
        
        # Organize by category
        categories = {}
        for field in fields:
            category = field[0]
            if category not in categories:
                categories[category] = []
            categories[category].append({
                'name': field[1],
                'type': field[2],
                'required': field[3],
                'options': field[4]
            })
        
        return categories
    except:
        return {}


def generate_ropa_template():
    """Generate Excel template for ROPA data collection matching the uploaded format"""
    
    # Create workbook
    wb = Workbook()
    
    # Remove default sheet
    wb.remove(wb.active)
    
    # Define styles
    title_font = Font(bold=True, size=16, color="FFFFFF")
    title_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, size=12, color="FFFFFF")
    header_fill = PatternFill(start_color="5B9BD5", end_color="5B9BD5", fill_type="solid")
    instruction_font = Font(bold=True, size=11)
    border = Border(
        left=Side(style='thin'), 
        right=Side(style='thin'), 
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Create Introduction Sheet
    intro_ws = wb.create_sheet("Introduction", 0)
    
    # Introduction content
    intro_ws['A1'] = "RECORD OF PROCESSING ACTIVITIES"
    intro_ws['A1'].font = title_font
    intro_ws['A1'].fill = title_fill
    intro_ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    intro_ws.merge_cells('A1:F1')
    intro_ws.row_dimensions[1].height = 35
    
    intro_ws['A3'] = "GDPR Article 30 Compliance Template"
    intro_ws['A3'].font = Font(bold=True, size=14)
    intro_ws['A3'].alignment = Alignment(horizontal='center')
    intro_ws.merge_cells('A3:F3')
    intro_ws.row_dimensions[3].height = 25
    
    # Instructions
    instructions = [
        "",
        "About This Template:",
        "This template is designed to help you comply with GDPR Article 30 requirements for maintaining records of processing activities.",
        "",
        "Instructions:",
        "1. This workbook contains three sheets: Introduction (this sheet), Controller, and Processor",
        "2. Complete the Controller sheet if your organization acts as a data controller",
        "3. Complete the Processor sheet if your organization acts as a data processor",
        "4. Fill in all required fields marked with (*)",
        "5. Provide detailed and accurate information for each processing activity",
        "6. Ensure legal basis is clearly identified under GDPR Article 6",
        "7. Include appropriate safeguards for any third country transfers",
        "8. Save and upload this completed file back to the ROPA system",
        "",
        "Legal Requirements:",
        "Under GDPR Article 30, organizations must maintain records of processing activities.",
        "This applies to:",
        "• Organizations with 250+ employees",
        "• Organizations processing special categories of personal data",
        "• Organizations where processing poses risks to data subjects",
        "",
        "Sheet Descriptions:",
        "",
        "Controller Sheet:",
        "Use this sheet when your organization determines the purposes and means of processing personal data.",
        "Examples: HR records, customer databases, marketing activities",
        "",
        "Processor Sheet:",
        "Use this sheet when your organization processes personal data on behalf of another organization.",
        "Examples: Cloud service providers, payroll processors, IT support services",
        "",
        "For questions or support, contact your Data Protection Officer or Privacy Team."
    ]
    
    row = 5
    for instruction in instructions:
        intro_ws[f'A{row}'] = instruction
        if instruction.startswith(("About This Template:", "Instructions:", "Legal Requirements:", "Sheet Descriptions:")):
            intro_ws[f'A{row}'].font = Font(bold=True, size=12, color="366092")
        elif instruction.startswith(("Controller Sheet:", "Processor Sheet:")):
            intro_ws[f'A{row}'].font = Font(bold=True, size=11)
        elif instruction.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "•")):
            intro_ws[f'A{row}'].font = Font(size=10)
        else:
            intro_ws[f'A{row}'].font = Font(size=10)
        
        intro_ws[f'A{row}'].alignment = Alignment(wrap_text=True, vertical='top')
        row += 1
    
    # Set column widths for introduction
    intro_ws.column_dimensions['A'].width = 80
    
    # Create Controller Sheet
    controller_ws = wb.create_sheet("Controller", 1)
    
    # Controller headers
    controller_headers = [
        ("Processing Activity Name *", "Name of the processing activity"),
        ("Category", "Category of processing activity"),
        ("Description *", "Description of the processing activity"),
        ("Department/Function", "Department or business function responsible"),
        ("Controller Name *", "Name of the data controller"),
        ("Controller Contact *", "Contact details of the controller"),
        ("Controller Address *", "Address of the controller"),
        ("DPO Name", "Data Protection Officer name"),
        ("DPO Contact", "DPO contact details"),
        ("Purpose of Processing *", "Purpose and justification for processing"),
        ("Legal Basis *", "Legal basis under GDPR Article 6"),
        ("Legitimate Interests", "Details if legal basis is legitimate interests"),
        ("Categories of Personal Data *", "Types of personal data processed"),
        ("Special Categories", "Special categories of personal data (Article 9)"),
        ("Data Subjects *", "Categories of data subjects"),
        ("Recipients *", "Recipients or categories of recipients"),
        ("Third Country Transfers", "Details of transfers outside EU/EEA"),
        ("Safeguards", "Safeguards for international transfers"),
        ("Retention Period *", "How long data is kept"),
        ("Retention Criteria", "Criteria for determining retention period"),
        ("Security Measures *", "Technical and organizational measures"),
        ("Status", "Draft/Under Review/Approved"),
        ("Notes", "Additional notes or comments")
    ]
    
    # Add controller title
    controller_ws['A1'] = "DATA CONTROLLER - RECORD OF PROCESSING ACTIVITIES"
    controller_ws['A1'].font = title_font
    controller_ws['A1'].fill = title_fill
    controller_ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    controller_ws.merge_cells(f'A1:{get_column_letter(len(controller_headers))}1')
    controller_ws.row_dimensions[1].height = 30
    
    # Add controller headers
    for col, (header, description) in enumerate(controller_headers, 1):
        cell = controller_ws.cell(row=2, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        
        # Add description in row 3
        desc_cell = controller_ws.cell(row=3, column=col)
        desc_cell.value = description
        desc_cell.font = Font(size=9, italic=True)
        desc_cell.alignment = Alignment(wrap_text=True, vertical='top')
        desc_cell.border = border
    
    # Set row heights
    controller_ws.row_dimensions[2].height = 25
    controller_ws.row_dimensions[3].height = 35
    
    # Create Processor Sheet
    processor_ws = wb.create_sheet("Processor", 2)
    
    # Processor headers
    processor_headers = [
        ("Processing Activity Name *", "Name of the processing activity"),
        ("Category", "Category of processing activity"),
        ("Description *", "Description of the processing activity"),
        ("Department/Function", "Department or business function responsible"),
        ("Processor Name *", "Name of the data processor"),
        ("Processor Contact *", "Contact details of the processor"),
        ("Processor Address *", "Address of the processor"),
        ("Controller Name *", "Name of the data controller (client)"),
        ("Controller Contact *", "Contact details of the controller"),
        ("DPO Name", "Data Protection Officer name"),
        ("DPO Contact", "DPO contact details"),
        ("Purpose of Processing *", "Purpose of processing on behalf of controller"),
        ("Legal Basis *", "Legal basis under GDPR Article 6"),
        ("Categories of Personal Data *", "Types of personal data processed"),
        ("Special Categories", "Special categories of personal data (Article 9)"),
        ("Data Subjects *", "Categories of data subjects"),
        ("Recipients", "Recipients or categories of recipients"),
        ("Third Country Transfers", "Details of transfers outside EU/EEA"),
        ("Safeguards", "Safeguards for international transfers"),
        ("Retention Period *", "How long data is kept"),
        ("Retention Criteria", "Criteria for determining retention period"),
        ("Security Measures *", "Technical and organizational measures"),
        ("Processing Instructions", "Instructions received from controller"),
        ("Sub-processors", "Details of any sub-processors used"),
        ("Status", "Draft/Under Review/Approved"),
        ("Notes", "Additional notes or comments")
    ]
    
    # Add processor title
    processor_ws['A1'] = "DATA PROCESSOR - RECORD OF PROCESSING ACTIVITIES"
    processor_ws['A1'].font = title_font
    processor_ws['A1'].fill = title_fill
    processor_ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    processor_ws.merge_cells(f'A1:{get_column_letter(len(processor_headers))}1')
    processor_ws.row_dimensions[1].height = 30
    
    # Add processor headers
    for col, (header, description) in enumerate(processor_headers, 1):
        cell = processor_ws.cell(row=2, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        
        # Add description in row 3
        desc_cell = processor_ws.cell(row=3, column=col)
        desc_cell.value = description
        desc_cell.font = Font(size=9, italic=True)
        desc_cell.alignment = Alignment(wrap_text=True, vertical='top')
        desc_cell.border = border
    
    # Set row heights
    processor_ws.row_dimensions[2].height = 25
    processor_ws.row_dimensions[3].height = 35
    
    # Set column widths for both sheets
    controller_column_widths = [25, 15, 35, 20, 25, 25, 30, 20, 25, 35, 20, 30, 30, 25, 25, 30, 25, 30, 20, 25, 35, 15, 30]
    processor_column_widths = [25, 15, 35, 20, 25, 25, 30, 25, 25, 20, 25, 35, 20, 30, 25, 25, 30, 25, 30, 20, 25, 35, 30, 30, 15, 30]
    
    for i, width in enumerate(controller_column_widths, 1):
        controller_ws.column_dimensions[get_column_letter(i)].width = width
    
    for i, width in enumerate(processor_column_widths, 1):
        processor_ws.column_dimensions[get_column_letter(i)].width = width
    
    # Add sample rows with examples
    # Controller sample
    controller_sample = [
        "Employee Data Management", "HR", "Processing of employee personal data for HR purposes", 
        "Human Resources", "ABC Company Ltd", "hr@company.com", "123 Business St, City, Country",
        "Jane Smith", "dpo@company.com", "Employment administration, payroll, performance management",
        "Contract (Art. 6(1)(b))", "", "Name, address, phone, email, salary, performance data",
        "", "Employees, contractors", "Payroll provider, benefits administrator", "",
        "", "7 years after employment ends", "Legal retention requirements",
        "Access controls, encryption, regular backups", "Approved", ""
    ]
    
    # Processor sample
    processor_sample = [
        "Payroll Processing Service", "Financial", "Processing payroll data on behalf of client companies",
        "Operations", "XYZ Payroll Services", "contact@xyzpayroll.com", "456 Service Ave, City, Country",
        "Client Company Name", "client@company.com", "John Doe", "dpo@xyzpayroll.com",
        "Calculate and process payroll payments", "Contract (Art. 6(1)(b))",
        "Name, employee ID, salary, tax information, bank details", "",
        "Employees of client companies", "Tax authorities, banks", "", "",
        "As specified by client (typically 7 years)", "Client's retention policy",
        "ISO 27001 certified systems, encrypted data transmission", "Monthly payroll processing as per client instructions",
        "Cloud hosting provider (AWS EU)", "Approved", ""
    ]
    
    # Add sample data
    for col, value in enumerate(controller_sample, 1):
        cell = controller_ws.cell(row=4, column=col)
        cell.value = value
        cell.border = border
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        if value and col <= 2:  # Highlight first two columns
            cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
    
    for col, value in enumerate(processor_sample, 1):
        cell = processor_ws.cell(row=4, column=col)
        cell.value = value
        cell.border = border
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        if value and col <= 2:  # Highlight first two columns
            cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
    
    controller_ws.row_dimensions[4].height = 40
    processor_ws.row_dimensions[4].height = 40
    
    # Add empty rows for data entry
    for row in range(5, 15):
        for col in range(1, len(controller_headers) + 1):
            cell = controller_ws.cell(row=row, column=col)
            cell.border = border
        for col in range(1, len(processor_headers) + 1):
            cell = processor_ws.cell(row=row, column=col)
            cell.border = border
    
    # Save to temporary file
    temp_dir = tempfile.mkdtemp()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Record_of_Processing_Activities_{timestamp}.xlsx"
    file_path = os.path.join(temp_dir, filename)
    
    wb.save(file_path)
    
    return file_path
