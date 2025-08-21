
import os
import tempfile
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def get_existing_ropa_records():
    """Get all existing ROPA records for template population"""
    try:
        from models import ROPARecord, User
        from app import db
        
        records = ROPARecord.query.order_by(ROPARecord.created_at.desc()).all()
        records_data = []
        
        for record in records:
            creator = User.query.get(record.created_by)
            creator_email = creator.email if creator else 'Unknown'
            
            records_data.append({
                'processing_activity_name': record.processing_activity_name or '',
                'category': record.category or '',
                'description': record.description or '',
                'department_function': record.department_function or '',
                'controller_name': record.controller_name or '',
                'controller_contact': record.controller_contact or '',
                'controller_address': record.controller_address or '',
                'dpo_name': record.dpo_name or '',
                'dpo_contact': record.dpo_contact or '',
                'dpo_address': record.dpo_address or '',
                'processor_name': record.processor_name or '',
                'processor_contact': record.processor_contact or '',
                'processor_address': record.processor_address or '',
                'representative_name': record.representative_name or '',
                'representative_contact': record.representative_contact or '',
                'representative_address': record.representative_address or '',
                'processing_purpose': record.processing_purpose or '',
                'legal_basis': record.legal_basis or '',
                'legitimate_interests': record.legitimate_interests or '',
                'data_categories': record.data_categories or '',
                'special_categories': record.special_categories or '',
                'data_subjects': record.data_subjects or '',
                'recipients': record.recipients or '',
                'third_country_transfers': record.third_country_transfers or '',
                'safeguards': record.safeguards or '',
                'retention_period': record.retention_period or '',
                'retention_criteria': record.retention_criteria or '',
                'security_measures': record.security_measures or '',
                'breach_likelihood': record.breach_likelihood or '',
                'breach_impact': record.breach_impact or '',
                'risk_level': record.risk_level or '',
                'dpia_required': 'Yes' if record.dpia_required else 'No',
                'dpia_outcome': record.dpia_outcome or '',
                'status': record.status or '',
                'created_by': creator_email,
                'created_at': record.created_at.strftime('%Y-%m-%d %H:%M:%S') if record.created_at else ''
            })
        
        return records_data
    except Exception as e:
        print(f"Error getting existing records: {str(e)}")
        return []




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
    """Generate Excel template populated with existing ROPA data"""
    
    # Get existing ROPA records
    existing_records = get_existing_ropa_records()
    
    # Create workbook
    wb = Workbook()
    
    # Remove default sheet
    wb.remove(wb.active)
    
    # Define professional color scheme and styles
    # Main brand colors - professional blue theme
    main_blue = "1F4E79"      # Dark blue for main headers
    light_blue = "4472C4"     # Medium blue for section headers
    accent_blue = "D5E3F0"    # Light blue for alternating rows
    light_gray = "F2F2F2"     # Light gray for input areas
    white = "FFFFFF"          # White background
    dark_text = "1F1F1F"      # Dark text
    
    # Define comprehensive styles
    title_font = Font(name="Calibri", bold=True, size=18, color=white)
    title_fill = PatternFill(start_color=main_blue, end_color=main_blue, fill_type="solid")
    
    subtitle_font = Font(name="Calibri", bold=True, size=14, color=main_blue)
    subtitle_fill = PatternFill(start_color=light_gray, end_color=light_gray, fill_type="solid")
    
    header_font = Font(name="Calibri", bold=True, size=11, color=white)
    header_fill = PatternFill(start_color=light_blue, end_color=light_blue, fill_type="solid")
    
    subheader_font = Font(name="Calibri", bold=False, size=9, color=dark_text, italic=True)
    subheader_fill = PatternFill(start_color=accent_blue, end_color=accent_blue, fill_type="solid")
    
    instruction_font = Font(name="Calibri", bold=True, size=11, color=main_blue)
    normal_font = Font(name="Calibri", size=10, color=dark_text)
    small_font = Font(name="Calibri", size=9, color=dark_text)
    
    sample_fill = PatternFill(start_color=light_gray, end_color=light_gray, fill_type="solid")
    
    # Define borders
    thick_border = Border(
        left=Side(style='thick', color=main_blue), 
        right=Side(style='thick', color=main_blue), 
        top=Side(style='thick', color=main_blue),
        bottom=Side(style='thick', color=main_blue)
    )
    
    medium_border = Border(
        left=Side(style='medium', color=light_blue), 
        right=Side(style='medium', color=light_blue), 
        top=Side(style='medium', color=light_blue),
        bottom=Side(style='medium', color=light_blue)
    )
    
    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'), 
        right=Side(style='thin', color='CCCCCC'), 
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )
    
    # Create Introduction Sheet
    intro_ws = wb.create_sheet("Introduction", 0)
    
    # Main title with enhanced formatting
    intro_ws['A1'] = "RECORD OF PROCESSING ACTIVITIES"
    intro_ws['A1'].font = title_font
    intro_ws['A1'].fill = title_fill
    intro_ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    intro_ws['A1'].border = thick_border
    intro_ws.merge_cells('A1:G1')
    intro_ws.row_dimensions[1].height = 40
    
    # Subtitle
    intro_ws['A2'] = "GDPR Article 30 Compliance Template"
    intro_ws['A2'].font = subtitle_font
    intro_ws['A2'].fill = subtitle_fill
    intro_ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    intro_ws['A2'].border = medium_border
    intro_ws.merge_cells('A2:G2')
    intro_ws.row_dimensions[2].height = 30
    
    # Add logo placeholder
    intro_ws['A4'] = "🏢 Your Organization Logo Here"
    intro_ws['A4'].font = Font(name="Calibri", size=12, color=light_blue)
    intro_ws['A4'].alignment = Alignment(horizontal='center')
    intro_ws.merge_cells('A4:G4')
    intro_ws.row_dimensions[4].height = 25
    
    # Enhanced instructions with better formatting
    instructions = [
        ("📋 ABOUT THIS TEMPLATE", "header"),
        ("This template is designed to help you comply with GDPR Article 30 requirements for maintaining comprehensive records of processing activities.", "text"),
        ("", "blank"),
        ("📝 INSTRUCTIONS", "header"),
        ("1️⃣ This workbook contains three professionally formatted sheets:", "text"),
        ("   • Introduction (this sheet) - Overview and guidance", "indent"),
        ("   • Controller Processing Activity - For data controller activities", "indent"),
        ("   • Processor Processing Activity - For data processor activities", "indent"),
        ("", "blank"),
        ("2️⃣ Complete the Controller Processing Activity sheet if your organization determines purposes and means of processing", "text"),
        ("3️⃣ Complete the Processor Processing Activity sheet if your organization processes data on behalf of others", "text"),
        ("4️⃣ Fill in all required fields marked with (*) - these are mandatory under GDPR", "text"),
        ("5️⃣ Provide detailed and accurate information for each processing activity", "text"),
        ("6️⃣ Ensure legal basis is clearly identified under GDPR Article 6", "text"),
        ("7️⃣ Include appropriate safeguards for any third country transfers", "text"),
        ("8️⃣ Save and upload this completed file back to the ROPA system", "text"),
        ("", "blank"),
        ("⚖️ LEGAL REQUIREMENTS", "header"),
        ("Under GDPR Article 30, organizations must maintain detailed records of processing activities.", "text"),
        ("This requirement applies to:", "text"),
        ("   ✓ Organizations with 250+ employees", "indent"),
        ("   ✓ Organizations processing special categories of personal data", "indent"),
        ("   ✓ Organizations where processing poses risks to data subjects", "indent"),
        ("", "blank"),
        ("📊 SHEET DESCRIPTIONS", "header"),
        ("", "blank"),
        ("🎯 Controller Processing Activity Sheet:", "subheader"),
        ("Use when your organization determines the purposes and means of processing personal data.", "text"),
        ("Examples: HR records, customer databases, marketing activities, financial records", "text"),
        ("", "blank"),
        ("⚙️ Processor Processing Activity Sheet:", "subheader"),
        ("Use when your organization processes personal data on behalf of another organization.", "text"),
        ("Examples: Cloud service providers, payroll processors, IT support services", "text"),
        ("", "blank"),
        ("💡 TIPS FOR SUCCESS", "header"),
        ("• Be specific and detailed in your descriptions", "text"),
        ("• Use clear business language that stakeholders can understand", "text"),
        ("• Review and update records regularly as processing activities change", "text"),
        ("• Ensure all team members understand their data protection responsibilities", "text"),
        ("", "blank"),
        ("📞 SUPPORT", "header"),
        ("For questions or support, contact your Data Protection Officer or Privacy Team.", "text")
    ]
    
    row = 6
    for instruction, style_type in instructions:
        cell = intro_ws[f'A{row}']
        cell.value = instruction
        
        if style_type == "header":
            cell.font = Font(name="Calibri", bold=True, size=12, color=main_blue)
            cell.fill = PatternFill(start_color=accent_blue, end_color=accent_blue, fill_type="solid")
            cell.border = thin_border
            intro_ws.merge_cells(f'A{row}:G{row}')
            intro_ws.row_dimensions[row].height = 25
        elif style_type == "subheader":
            cell.font = Font(name="Calibri", bold=True, size=11, color=light_blue)
        elif style_type == "indent":
            cell.font = small_font
            cell.alignment = Alignment(indent=2)
        elif style_type == "blank":
            intro_ws.row_dimensions[row].height = 10
        else:  # text
            cell.font = normal_font
        
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        row += 1
    
    # Set column widths for introduction
    intro_ws.column_dimensions['A'].width = 90
    for col in ['B', 'C', 'D', 'E', 'F', 'G']:
        intro_ws.column_dimensions[col].width = 5
    
    # Create Controller Sheet with enhanced styling
    controller_ws = wb.create_sheet("Controller Processing Activity", 1)
    
    # Controller headers with descriptions
    controller_headers = [
        ("Processing Activity Name *", "Unique name identifying this processing activity"),
        ("Category", "Business category (HR, Marketing, Finance, etc.)"),
        ("Description *", "Detailed description of what data is processed and why"),
        ("Department/Function", "Responsible department or business function"),
        ("Controller Name *", "Legal name of the data controller organization"),
        ("Controller Contact *", "Primary contact person and details"),
        ("Controller Address *", "Legal address of the controller"),
        ("DPO Name", "Data Protection Officer name (if applicable)"),
        ("DPO Contact", "DPO contact details (email/phone)"),
        ("Purpose of Processing *", "Specific purpose and business justification"),
        ("Legal Basis *", "Legal basis under GDPR Article 6 (1)(a-f)"),
        ("Legitimate Interests", "Details if legal basis is legitimate interests"),
        ("Categories of Personal Data *", "Types of personal data processed"),
        ("Special Categories", "Special categories under GDPR Article 9"),
        ("Data Subjects *", "Categories of individuals whose data is processed"),
        ("Recipients *", "Who receives or has access to the data"),
        ("Third Country Transfers", "Details of any transfers outside EU/EEA"),
        ("Safeguards", "Protective measures for international transfers"),
        ("Retention Period *", "How long data is retained"),
        ("Retention Criteria", "Criteria used to determine retention period"),
        ("Security Measures *", "Technical and organizational security measures"),
        ("Status", "Current status (Draft/Under Review/Approved)"),
        ("Notes", "Additional comments or special considerations")
    ]
    
    # Add controller title with enhanced styling
    controller_ws['A1'] = "📊 DATA CONTROLLER - RECORD OF PROCESSING ACTIVITIES"
    controller_ws['A1'].font = title_font
    controller_ws['A1'].fill = title_fill
    controller_ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    controller_ws['A1'].border = thick_border
    controller_ws.merge_cells(f'A1:{get_column_letter(len(controller_headers))}1')
    controller_ws.row_dimensions[1].height = 35
    
    # Add controller headers with enhanced styling
    for col, (header, description) in enumerate(controller_headers, 1):
        # Main header
        cell = controller_ws.cell(row=2, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.border = medium_border
        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        
        # Description row
        desc_cell = controller_ws.cell(row=3, column=col)
        desc_cell.value = description
        desc_cell.font = subheader_font
        desc_cell.fill = subheader_fill
        desc_cell.alignment = Alignment(wrap_text=True, vertical='top')
        desc_cell.border = thin_border
    
    # Set row heights
    controller_ws.row_dimensions[2].height = 30
    controller_ws.row_dimensions[3].height = 40
    
    # Create Processor Sheet with enhanced styling
    processor_ws = wb.create_sheet("Processor Processing Activity", 2)
    
    # Processor headers with descriptions
    processor_headers = [
        ("Processing Activity Name *", "Unique name identifying this processing activity"),
        ("Category", "Business category (IT Services, Payroll, etc.)"),
        ("Description *", "Detailed description of processing on behalf of controller"),
        ("Department/Function", "Responsible department or business function"),
        ("Processor Name *", "Legal name of the data processor organization"),
        ("Processor Contact *", "Primary contact person and details"),
        ("Processor Address *", "Legal address of the processor"),
        ("Controller Name *", "Legal name of the data controller (your client)"),
        ("Controller Contact *", "Controller's contact details"),
        ("DPO Name", "Data Protection Officer name"),
        ("DPO Contact", "DPO contact details (email/phone)"),
        ("Purpose of Processing *", "Specific purpose as instructed by controller"),
        ("Legal Basis *", "Controller's legal basis under GDPR Article 6"),
        ("Categories of Personal Data *", "Types of personal data processed"),
        ("Special Categories", "Special categories under GDPR Article 9"),
        ("Data Subjects *", "Categories of individuals whose data is processed"),
        ("Recipients", "Who receives the data (usually the controller)"),
        ("Third Country Transfers", "Details of any transfers outside EU/EEA"),
        ("Safeguards", "Protective measures for international transfers"),
        ("Retention Period *", "Data retention period as per controller instructions"),
        ("Retention Criteria", "Controller's criteria for determining retention"),
        ("Security Measures *", "Technical and organizational security measures"),
        ("Processing Instructions", "Specific instructions received from controller"),
        ("Sub-processors", "Details of any sub-processors engaged"),
        ("Status", "Current status (Draft/Under Review/Approved)"),
        ("Notes", "Additional comments or special considerations")
    ]
    
    # Add processor title with enhanced styling
    processor_ws['A1'] = "⚙️ DATA PROCESSOR - RECORD OF PROCESSING ACTIVITIES"
    processor_ws['A1'].font = title_font
    processor_ws['A1'].fill = title_fill
    processor_ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    processor_ws['A1'].border = thick_border
    processor_ws.merge_cells(f'A1:{get_column_letter(len(processor_headers))}1')
    processor_ws.row_dimensions[1].height = 35
    
    # Add processor headers with enhanced styling
    for col, (header, description) in enumerate(processor_headers, 1):
        # Main header
        cell = processor_ws.cell(row=2, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.border = medium_border
        cell.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        
        # Description row
        desc_cell = processor_ws.cell(row=3, column=col)
        desc_cell.value = description
        desc_cell.font = subheader_font
        desc_cell.fill = subheader_fill
        desc_cell.alignment = Alignment(wrap_text=True, vertical='top')
        desc_cell.border = thin_border
    
    # Set row heights
    processor_ws.row_dimensions[2].height = 30
    processor_ws.row_dimensions[3].height = 40
    
    # Set optimized column widths
    controller_column_widths = [28, 18, 40, 22, 28, 28, 35, 22, 28, 40, 25, 35, 35, 28, 28, 35, 30, 35, 25, 30, 40, 18, 35]
    processor_column_widths = [28, 18, 40, 22, 28, 28, 35, 28, 28, 22, 28, 40, 25, 35, 28, 28, 35, 30, 35, 25, 30, 40, 35, 35, 18, 35]
    
    for i, width in enumerate(controller_column_widths, 1):
        controller_ws.column_dimensions[get_column_letter(i)].width = width
    
    for i, width in enumerate(processor_column_widths, 1):
        processor_ws.column_dimensions[get_column_letter(i)].width = width
    
    # Add enhanced sample rows with professional examples
    controller_sample = [
        "Employee Data Management System", "Human Resources", "Comprehensive processing of employee personal data for employment administration, payroll, benefits, and performance management", 
        "Human Resources Department", "ABC Company Limited", "hr.manager@company.com", "123 Business Street, Corporate City, CC1 2AB, United Kingdom",
        "Jane Smith", "dpo@company.com", "Employment administration, payroll processing, performance evaluation, training management, and compliance monitoring",
        "Contract (Art. 6(1)(b)) - Employment", "N/A", "Name, address, phone, email, employee ID, salary, bank details, performance data, training records",
        "", "Current employees, former employees, contractors", "Payroll provider, benefits administrator, training providers", "",
        "Adequate Decision (UK)", "7 years after employment termination", "Legal retention requirements and business needs",
        "Access controls, data encryption, regular security audits, incident response procedures", "Approved", "Regular review scheduled quarterly"
    ]
    
    processor_sample = [
        "Payroll Processing Service", "Financial Services", "Processing employee payroll data including salary calculations, tax deductions, and payment distribution on behalf of client organizations",
        "Operations Department", "XYZ Payroll Services Ltd", "operations@xyzpayroll.com", "456 Service Avenue, Business Park, BP2 3CD, United Kingdom",
        "Client Company Name", "client.contact@company.com", "John Doe", "dpo@xyzpayroll.com",
        "Calculate monthly salaries, process tax deductions, generate payslips, and facilitate payment transfers", "Contract (Art. 6(1)(b)) - Employment",
        "Name, employee ID, salary, tax code, bank details, National Insurance number", "",
        "Employees of client companies", "HMRC, client company management", "", "Standard Contractual Clauses",
        "As specified by client contract (typically 7 years)", "Client retention policy and legal requirements",
        "ISO 27001 certified systems, encrypted data transmission, segregated client environments", "Monthly payroll processing as per detailed client instructions and service agreement",
        "Cloud hosting provider (Microsoft Azure EU)", "Approved", "SLA guarantees 99.9% uptime with 24/7 monitoring"
    ]
    
    # Add sample data first
    for col, value in enumerate(controller_sample, 1):
        cell = controller_ws.cell(row=4, column=col)
        cell.value = value
        cell.border = thin_border
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        cell.font = small_font
        cell.fill = sample_fill
    
    for col, value in enumerate(processor_sample, 1):
        cell = processor_ws.cell(row=4, column=col)
        cell.value = value
        cell.border = thin_border
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        cell.font = small_font
        cell.fill = sample_fill
    
    controller_ws.row_dimensions[4].height = 50
    processor_ws.row_dimensions[4].height = 50
    
    # Add existing ROPA records starting from row 5
    if existing_records:
        for i, record in enumerate(existing_records, start=5):
            row_data = [
                record['processing_activity_name'],
                record['category'],
                record['description'],
                record['department_function'],
                record['controller_name'],
                record['controller_contact'],
                record['controller_address'],
                record['dpo_name'],
                record['dpo_contact'],
                record['processing_purpose'],
                record['legal_basis'],
                record['legitimate_interests'],
                record['data_categories'],
                record['special_categories'],
                record['data_subjects'],
                record['recipients'],
                record['third_country_transfers'],
                record['safeguards'],
                record['retention_period'],
                record['retention_criteria'],
                record['security_measures'],
                record['status'],
                f"Existing record - Created by {record['created_by']} on {record['created_at']}"
            ]
            
            fill_color = white if i % 2 == 1 else accent_blue
            fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
            
            for col, value in enumerate(row_data, 1):
                cell = controller_ws.cell(row=i, column=col)
                cell.value = value
                cell.border = thin_border
                cell.alignment = Alignment(wrap_text=True, vertical='top')
                cell.font = normal_font
                cell.fill = fill
            
            controller_ws.row_dimensions[i].height = 25
    
    # Add empty rows with alternating colors for data entry
    start_row = 5 + len(existing_records) if existing_records else 5
    end_row = max(start_row + 10, 25)  # Ensure at least 10 empty rows
    
    for row in range(start_row, end_row):
        fill_color = white if row % 2 == 1 else accent_blue
        fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
        
        for col in range(1, len(controller_headers) + 1):
            cell = controller_ws.cell(row=row, column=col)
            cell.border = thin_border
            cell.fill = fill
            cell.font = normal_font
            
        for col in range(1, len(processor_headers) + 1):
            cell = processor_ws.cell(row=row, column=col)
            cell.border = thin_border
            cell.fill = fill
            cell.font = normal_font
        
        controller_ws.row_dimensions[row].height = 25
        processor_ws.row_dimensions[row].height = 25
    
    # Add footer to each sheet
    footer_row_controller = max(26, 15 + len(existing_records) if existing_records else 26)
    footer_row_processor = max(26, 15 + len(existing_records) if existing_records else 26)
    
    controller_ws[f'A{footer_row_controller}'] = "📄 Template generated by ROPA Management System | 🔒 Ensure data confidentiality when completing"
    controller_ws[f'A{footer_row_controller}'].font = Font(name="Calibri", size=9, color=light_blue, italic=True)
    controller_ws[f'A{footer_row_controller}'].alignment = Alignment(horizontal='center')
    controller_ws.merge_cells(f'A{footer_row_controller}:{get_column_letter(len(controller_headers)-1)}{footer_row_controller}')
    
    # Add version number at bottom right for controller sheet
    version_cell_controller = controller_ws.cell(row=footer_row_controller, column=len(controller_headers))
    version_cell_controller.value = "Version 2"
    version_cell_controller.font = Font(name="Calibri", size=9, color=light_blue, italic=True, bold=True)
    version_cell_controller.alignment = Alignment(horizontal='right')
    
    processor_ws[f'A{footer_row_processor}'] = "📄 Template generated by ROPA Management System | 🔒 Ensure data confidentiality when completing"
    processor_ws[f'A{footer_row_processor}'].font = Font(name="Calibri", size=9, color=light_blue, italic=True)
    processor_ws[f'A{footer_row_processor}'].alignment = Alignment(horizontal='center')
    processor_ws.merge_cells(f'A{footer_row_processor}:{get_column_letter(len(processor_headers)-1)}{footer_row_processor}')
    
    # Add version number at bottom right for processor sheet
    version_cell_processor = processor_ws.cell(row=footer_row_processor, column=len(processor_headers))
    version_cell_processor.value = "Version 2"
    version_cell_processor.font = Font(name="Calibri", size=9, color=light_blue, italic=True, bold=True)
    version_cell_processor.alignment = Alignment(horizontal='right')
    
    # Save to temporary file
    temp_dir = tempfile.mkdtemp()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Record_of_Processing_Activities_{timestamp}.xlsx"
    file_path = os.path.join(temp_dir, filename)
    
    wb.save(file_path)
    
    return file_path
