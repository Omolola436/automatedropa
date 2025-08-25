
import sqlite3
from database import get_db_connection

def fix_database_schema():
    """Fix database schema to ensure all required columns exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(ropa_records)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    # Required columns based on models.py
    required_columns = [
        'id', 'processing_activity_name', 'category', 'description', 'department_function',
        'controller_name', 'controller_contact', 'controller_address',
        'dpo_name', 'dpo_contact', 'dpo_address',
        'processor_name', 'processor_contact', 'processor_address',
        'representative_name', 'representative_contact', 'representative_address',
        'processing_purpose', 'legal_basis', 'legitimate_interests',
        'data_categories', 'special_categories', 'data_subjects',
        'recipients', 'third_country_transfers', 'safeguards',
        'retention_period', 'deletion_procedures', 'security_measures',
        'breach_likelihood', 'breach_impact', 'risk_level',
        'dpia_required', 'dpia_outcome',
        'status', 'created_by', 'created_at', 'updated_at',
        'reviewed_by', 'reviewed_at', 'review_comments'
    ]
    
    print(f"Checking for {len(required_columns)} required columns...")
    print(f"Existing columns: {existing_columns}")
    
    missing_columns = [col for col in required_columns if col not in existing_columns]
    print(f"Missing columns: {missing_columns}")
    
    if not missing_columns:
        print("All required columns already exist!")
        conn.close()
        return
    
    # Add missing columns
    for column in required_columns:
        if column not in existing_columns:
            try:
                if column in ['dpia_required']:
                    cursor.execute(f"ALTER TABLE ropa_records ADD COLUMN {column} BOOLEAN DEFAULT 0")
                elif column in ['created_at', 'updated_at', 'reviewed_at']:
                    cursor.execute(f"ALTER TABLE ropa_records ADD COLUMN {column} DATETIME DEFAULT CURRENT_TIMESTAMP")
                elif column in ['created_by', 'reviewed_by']:
                    cursor.execute(f"ALTER TABLE ropa_records ADD COLUMN {column} INTEGER")
                else:
                    cursor.execute(f"ALTER TABLE ropa_records ADD COLUMN {column} TEXT")
                print(f"Added column: {column}")
            except sqlite3.OperationalError as e:
                print(f"Column {column} might already exist or error: {e}")
    
    conn.commit()
    conn.close()
    print("Database schema fixed!")

if __name__ == "__main__":
    fix_database_schema()
