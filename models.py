from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean

# Create a shared db instance
db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(Integer, primary_key=True)
    email = db.Column(String(120), unique=True, nullable=False)
    password_hash = db.Column(String(256), nullable=False)
    role = db.Column(String(50), nullable=False, default='Privacy Champion')
    department = db.Column(String(100))
    created_at = db.Column(DateTime, default=datetime.utcnow)
    last_login = db.Column(DateTime)
    
    # Relationship
    ropa_records = db.relationship('ROPARecord', foreign_keys='ROPARecord.created_by', backref='creator', lazy=True)


class ROPARecord(db.Model):
    __tablename__ = 'ropa_records'
    
    # Allow dynamic columns to be accessed
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(Integer, primary_key=True)
    processing_activity_name = db.Column(String(200), nullable=False)
    category = db.Column(String(100))
    description = db.Column(Text)
    department_function = db.Column(String(100))
    
    # Controller information
    controller_name = db.Column(String(200))
    controller_contact = db.Column(String(200))
    controller_address = db.Column(Text)
    
    # DPO information  
    dpo_name = db.Column(String(200))
    dpo_contact = db.Column(String(200))
    dpo_address = db.Column(Text)
    
    # Processor information
    processor_name = db.Column(String(200))
    processor_contact = db.Column(String(200))
    processor_address = db.Column(Text)
    
    # Representative information
    representative_name = db.Column(String(200))
    representative_contact = db.Column(String(200))
    representative_address = db.Column(Text)
    
    # Processing details
    processing_purpose = db.Column(Text)
    legal_basis = db.Column(String(200))
    legitimate_interests = db.Column(Text)
    data_categories = db.Column(Text)
    special_categories = db.Column(Text)
    data_subjects = db.Column(Text)
    recipients = db.Column(Text)
    third_country_transfers = db.Column(Text)
    safeguards = db.Column(Text)
    retention_period = db.Column(String(100))
    deletion_procedures = db.Column(Text)
    security_measures = db.Column(Text)
    
    # Risk assessment
    breach_likelihood = db.Column(String(50))
    breach_impact = db.Column(String(50))
    risk_level = db.Column(String(50))
    dpia_required = db.Column(Boolean, default=False)
    dpia_outcome = db.Column(Text)
    
    # Metadata
    status = db.Column(String(50), default='Draft')
    created_by = db.Column(Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_by = db.Column(Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(DateTime)
    review_comments = db.Column(Text)

class ExcelFileData(db.Model):
    __tablename__ = 'excel_files'

    id = db.Column(Integer, primary_key=True)
    filename = db.Column(String(255), nullable=False)
    uploaded_by = db.Column(Integer, db.ForeignKey('users.id'), nullable=False)
    total_sheets = db.Column(Integer, default=0)
    sheet_names = db.Column(Text)  # JSON array of sheet names
    upload_timestamp = db.Column(DateTime, default=datetime.utcnow)
    file_metadata = db.Column(Text)  # JSON metadata about the file

    uploader = db.relationship('User', backref='uploaded_excel_files')
    sheets = db.relationship('ExcelSheetData', backref='excel_file', cascade='all, delete-orphan')

class ExcelSheetData(db.Model):
    __tablename__ = 'excel_sheets'

    id = db.Column(Integer, primary_key=True)
    excel_file_id = db.Column(Integer, db.ForeignKey('excel_files.id'), nullable=False)
    sheet_name = db.Column(String(255), nullable=False)
    columns = db.Column(Text)  # JSON array of column names
    row_count = db.Column(Integer, default=0)
    column_count = db.Column(Integer, default=0)
    sheet_data = db.Column(Text)  # JSON data of the sheet content
    created_at = db.Column(DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(Integer, primary_key=True)
    event_type = db.Column(String(100), nullable=False)
    user_email = db.Column(String(120))
    ip_address = db.Column(String(45))
    description = db.Column(Text)
    additional_data = db.Column(Text)
    timestamp = db.Column(DateTime, default=datetime.utcnow)


class CustomTab(db.Model):
    __tablename__ = 'custom_tabs'
    
    id = db.Column(Integer, primary_key=True)
    tab_category = db.Column(String(50), nullable=False)  # Basic Info, Controller, etc.
    field_name = db.Column(String(100), nullable=False)
    field_description = db.Column(Text)
    field_type = db.Column(String(50), default='text')  # text, textarea, select, checkbox
    field_options = db.Column(Text)  # JSON for select options
    is_required = db.Column(Boolean, default=False)
    status = db.Column(String(50), default='Draft')  # Draft, Pending Review, Approved, Rejected
    created_by = db.Column(Integer, db.ForeignKey('users.id'), nullable=False)
    reviewed_by = db.Column(Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(DateTime)
    review_comments = db.Column(Text)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='custom_tabs_created')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='custom_tabs_reviewed')


class ApprovedCustomField(db.Model):
    __tablename__ = 'approved_custom_fields'
    
    id = db.Column(Integer, primary_key=True)
    custom_tab_id = db.Column(Integer, db.ForeignKey('custom_tabs.id'), nullable=False)
    field_name = db.Column(String(100), nullable=False)
    tab_category = db.Column(String(50), nullable=False)
    field_type = db.Column(String(50), nullable=False)
    field_options = db.Column(Text)
    is_required = db.Column(Boolean, default=False)
    approved_at = db.Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    custom_tab = db.relationship('CustomTab', backref='approved_field')


class ROPACustomData(db.Model):
    __tablename__ = 'ropa_custom_data'
    
    id = db.Column(Integer, primary_key=True)
    ropa_record_id = db.Column(Integer, db.ForeignKey('ropa_records.id'), nullable=False)
    custom_field_id = db.Column(Integer, db.ForeignKey('approved_custom_fields.id'), nullable=False)
    field_value = db.Column(Text)
    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ropa_record = db.relationship('ROPARecord', backref='custom_data')
    custom_field = db.relationship('ApprovedCustomField', backref='ropa_data')