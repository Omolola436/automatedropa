from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean


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


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(Integer, primary_key=True)
    event_type = db.Column(String(100), nullable=False)
    user_email = db.Column(String(120))
    ip_address = db.Column(String(45))
    description = db.Column(Text)
    additional_data = db.Column(Text)
    timestamp = db.Column(DateTime, default=datetime.utcnow)