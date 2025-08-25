
import os
import sqlite3
from database import get_db_connection
from app import app, db
from models import User, ROPARecord, CustomTab, ApprovedCustomField, ROPACustomData, AuditLog, ExcelFileData, ExcelSheetData

def reset_database_schema():
    """Reset database to match SQLAlchemy models exactly"""
    
    # Stop the Flask app context if running
    with app.app_context():
        print("Dropping all existing tables...")
        db.drop_all()
        
        print("Creating all tables from SQLAlchemy models...")
        db.create_all()
        
        print("Database schema reset complete!")
        
        # Verify the schema matches
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(ropa_records)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"\nCurrent ropa_records columns ({len(columns)}):")
        for col in sorted(columns):
            print(f"  - {col}")
            
        # Get expected columns from model
        model_columns = [column.name for column in ROPARecord.__table__.columns]
        print(f"\nExpected model columns ({len(model_columns)}):")
        for col in sorted(model_columns):
            print(f"  - {col}")
            
        missing_in_db = set(model_columns) - set(columns)
        extra_in_db = set(columns) - set(model_columns)
        
        if missing_in_db:
            print(f"\nMissing in database: {missing_in_db}")
        if extra_in_db:
            print(f"Extra in database: {extra_in_db}")
            
        if not missing_in_db and not extra_in_db:
            print("\n✅ Database schema matches SQLAlchemy models perfectly!")
        
        conn.close()

if __name__ == "__main__":
    reset_database_schema()
