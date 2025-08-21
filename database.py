import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
import os
from sqlalchemy import create_engine

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('ropa_system.db')

def init_database():
    """Initialize database with all required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Privacy Champion',
            department TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME
        )
    """)

    # ROPA records table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ropa_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processing_activity_name TEXT NOT NULL,
            category TEXT,
            description TEXT,
            department_function TEXT,
            controller_name TEXT,
            controller_contact TEXT,
            controller_address TEXT,
            dpo_name TEXT,
            dpo_contact TEXT,
            dpo_address TEXT,
            processor_name TEXT,
            processor_contact TEXT,
            processor_address TEXT,
            representative_name TEXT,
            representative_contact TEXT,
            representative_address TEXT,
            processing_purpose TEXT,
            legal_basis TEXT,
            legitimate_interests TEXT,
            data_categories TEXT,
            special_categories TEXT,
            data_subjects TEXT,
            recipients TEXT,
            third_country_transfers TEXT,
            safeguards TEXT,
            retention_period TEXT,
            retention_criteria TEXT,
            retention_justification TEXT,
            security_measures TEXT,
            breach_likelihood TEXT,
            breach_impact TEXT,
            dpia_required TEXT,
            additional_info TEXT,
            international_transfers TEXT,
            status TEXT DEFAULT 'Draft',
            created_by TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT,
            reviewed_by TEXT,
            reviewed_at DATETIME,
            approved_by TEXT,
            approved_at DATETIME
        )
    """)

    # Audit logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT NOT NULL,
            user_email TEXT NOT NULL,
            ip_address TEXT,
            description TEXT NOT NULL,
            additional_data TEXT
        )
    """)

    # Custom tabs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_tabs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tab_category TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_description TEXT,
            field_type TEXT DEFAULT 'text',
            field_options TEXT,
            is_required BOOLEAN DEFAULT 0,
            status TEXT DEFAULT 'Draft',
            created_by INTEGER NOT NULL,
            reviewed_by INTEGER,
            reviewed_at DATETIME,
            review_comments TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id),
            FOREIGNKEY (reviewed_by) REFERENCES users (id)
        )
    """)

    # Approved custom fields table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS approved_custom_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            custom_tab_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            tab_category TEXT NOT NULL,
            field_type TEXT NOT NULL,
            field_options TEXT,
            is_required BOOLEAN DEFAULT 0,
            approved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (custom_tab_id) REFERENCES custom_tabs (id)
        )
    """)

    # ROPA custom data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ropa_custom_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ropa_record_id INTEGER NOT NULL,
            custom_field_id INTEGER NOT NULL,
            field_value TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ropa_record_id) REFERENCES ropa_records (id),
            FOREIGN KEY (custom_field_id) REFERENCES approved_custom_fields (id)
        )
    """)

    conn.commit()

    # Database initialization complete - users must register to access the system

    conn.close()

def authenticate_user(email, password):
    """Authenticate user login"""
    conn = get_db_connection()
    cursor = conn.cursor()

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute("SELECT * FROM users WHERE email = ? AND password_hash = ?", (email, password_hash))
    user = cursor.fetchone()

    if user:
        # Update last login
        cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE email = ?", (email,))
        conn.commit()

    conn.close()
    return user is not None

def get_user_role(email):
    """Get user role by email"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT role FROM users WHERE email = ?", (email,))
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None

def create_user(email, password, role, department):
    """Create new user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("""
            INSERT INTO users (email, password_hash, role, department)
            VALUES (?, ?, ?, ?)
        """, (email, password_hash, role, department))

        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def get_all_users():
    """Get all users for admin management"""
    conn = get_db_connection()
    df = pd.read_sql_query("""
        SELECT email, role, department, created_at, last_login 
        FROM users ORDER BY created_at DESC
    """, conn)
    conn.close()
    return df

def save_ropa_record(data, created_by):
    """Save ROPA record to database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    print(f"DEBUG: Saving ROPA record for user: {created_by}")
    print(f"DEBUG: Record name: {data.get('processing_activity_name')}")
    print(f"DEBUG: Record status: {data.get('status', 'Draft')}")

    cursor.execute("""
        INSERT INTO ropa_records (
            processing_activity_name, category, description, department_function,
            controller_name, controller_contact, controller_address,
            dpo_name, dpo_contact, dpo_address,
            processor_name, processor_contact, processor_address,
            representative_name, representative_contact, representative_address,
            processing_purpose, legal_basis, legitimate_interests,
            data_categories, special_categories, data_subjects, recipients,
            third_country_transfers, safeguards, retention_period, retention_criteria,
            retention_justification, security_measures, breach_likelihood, breach_impact,
            dpia_required, additional_info, international_transfers,
            status, created_by, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        data.get('processing_activity_name', ''),
        data.get('category', ''),
        data.get('description', ''),
        data.get('department_function', ''),
        data.get('controller_name', ''),
        data.get('controller_contact', ''),
        data.get('controller_address', ''),
        data.get('dpo_name', ''),
        data.get('dpo_contact', ''),
        data.get('dpo_address', ''),
        data.get('processor_name', ''),
        data.get('processor_contact', ''),
        data.get('processor_address', ''),
        data.get('representative_name', ''),
        data.get('representative_contact', ''),
        data.get('representative_address', ''),
        data.get('processing_purpose', ''),
        data.get('legal_basis', ''),
        data.get('legitimate_interests', ''),
        data.get('data_categories', ''),
        data.get('special_categories', ''),
        data.get('data_subjects', ''),
        data.get('recipients', ''),
        data.get('third_country_transfers', ''),
        data.get('safeguards', ''),
        data.get('retention_period', ''),
        data.get('retention_criteria', ''),
        data.get('retention_justification', ''),
        data.get('security_measures', ''),
        data.get('breach_likelihood', ''),
        data.get('breach_impact', ''),
        data.get('dpia_required', ''),
        data.get('additional_info', ''),
        data.get('international_transfers', ''),
        data.get('status', 'Draft'),
        created_by
    ))

    record_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print(f"DEBUG: Successfully saved record with ID: {record_id}")
    return record_id

def get_ropa_records(user_email=None, role=None, status=None):
    """Get ROPA records based on user role and filters"""
    engine = create_engine('sqlite:///ropa_system.db')

    query = "SELECT * FROM ropa_records WHERE 1=1"
    params = {}

    # Role-based filtering
    if role == "Privacy Champion":
        # Get user's department to filter records
        user_dept = get_user_department(user_email)
        if user_dept:
            query += " AND (created_by = :user_email OR department_function = :department)"
            params['user_email'] = user_email
            params['department'] = user_dept
        else:
            query += " AND created_by = :user_email"
            params['user_email'] = user_email
    elif status:
        query += " AND status = :status"
        params['status'] = status

    query += " ORDER BY created_at DESC"

    df = pd.read_sql_query(query, engine, params=params)
    return df

def get_user_department(user_email):
    """Get user's department"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT department FROM users WHERE email = ?", (user_email,))
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None

def get_ropa_record_by_id(record_id, user_email=None, role=None):
    """Get specific ROPA record by ID with access control"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check access permissions
    if role == "Privacy Champion":
        user_dept = get_user_department(user_email)
        cursor.execute("""
            SELECT * FROM ropa_records 
            WHERE id = ? AND (created_by = ? OR department_function = ?)
        """, (record_id, user_email, user_dept))
    else:
        cursor.execute("SELECT * FROM ropa_records WHERE id = ?", (record_id,))

    record = cursor.fetchone()

    if record:
        columns = [
            'id', 'processing_activity_name', 'category', 'description', 'department_function',
            'controller_name', 'controller_contact', 'controller_address', 'dpo_name', 'dpo_contact',
            'dpo_address', 'processor_name', 'processor_contact', 'processor_address',
            'representative_name', 'representative_contact', 'representative_address',
            'processing_purpose', 'legal_basis', 'legitimate_interests', 'data_categories', 'special_categories',
            'data_subjects', 'recipients', 'third_country_transfers', 'safeguards',
            'retention_period', 'retention_criteria', 'retention_justification', 'security_measures',
            'breach_likelihood', 'breach_impact', 'dpia_required', 'additional_info',
            'international_transfers', 'status', 'created_by', 'created_at', 'updated_at', 'updated_by',
            'reviewed_by', 'reviewed_at', 'approved_by', 'approved_at'
        ]
        conn.close()
        return dict(zip(columns, record))

    conn.close()
    return None

def update_ropa_record(record_id, data, updated_by):
    """Update existing ROPA record"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE ropa_records SET
                processing_activity_name = ?,
                category = ?,
                description = ?,
                department_function = ?,
                controller_name = ?,
                controller_contact = ?,
                controller_address = ?,
                dpo_name = ?,
                dpo_contact = ?,
                dpo_address = ?,
                processor_name = ?,
                processor_contact = ?,
                processor_address = ?,
                representative_name = ?,
                representative_contact = ?,
                representative_address = ?,
                processing_purpose = ?,
                legal_basis = ?,
                data_categories = ?,
                special_categories = ?,
                data_subjects = ?,
                recipients = ?,
                third_country_transfers = ?,
                international_transfers = ?,
                retention_period = ?,
                retention_criteria = ?,
                retention_justification = ?,
                security_measures = ?,
                breach_likelihood = ?,
                breach_impact = ?,
                dpia_required = ?,
                additional_info = ?,
                status = ?,
                updated_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            data.get('processing_activity_name'),
            data.get('category'),
            data.get('description'),
            data.get('department_function'),
            data.get('controller_name'),
            data.get('controller_contact'),
            data.get('controller_address'),
            data.get('dpo_name'),
            data.get('dpo_contact'),
            data.get('dpo_address'),
            data.get('processor_name'),
            data.get('processor_contact'),
            data.get('processor_address'),
            data.get('representative_name'),
            data.get('representative_contact'),
            data.get('representative_address'),
            data.get('processing_purpose'),
            data.get('legal_basis'),
            data.get('data_categories'),
            data.get('special_categories'),
            data.get('data_subjects'),
            data.get('recipients'),
            data.get('third_country_transfers'),
            data.get('international_transfers'),
            data.get('retention_period'),
            data.get('retention_criteria'),
            data.get('retention_justification'),
            data.get('security_measures'),
            data.get('breach_likelihood'),
            data.get('breach_impact'),
            data.get('dpia_required'),
            data.get('additional_info'),
            data.get('status'),
            updated_by,
            record_id
        ))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        conn.close()
        raise e

def update_ropa_status(record_id, status, updated_by):
    """Update ROPA record status"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if status == 'Approved':
            cursor.execute("""
                UPDATE ropa_records SET
                    status = ?,
                    approved_by = ?,
                    approved_at = CURRENT_TIMESTAMP,
                    updated_by = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, updated_by, updated_by, record_id))
        else:
            cursor.execute("""
                UPDATE ropa_records SET
                    status = ?,
                    updated_by = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, updated_by, record_id))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        conn.close()
        raise e

def delete_ropa_record(record_id):
    """Delete ROPA record"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM ropa_records WHERE id = ?", (record_id,))
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result

    except Exception as e:
        conn.close()
        raise e