
#!/usr/bin/env python3
"""
Database migration script to ensure schema compatibility
"""

import sqlite3
from app import app, db
from models import CustomTab, ApprovedCustomField, ROPACustomData

def migrate_database():
    """Migrate database to ensure schema compatibility"""
    with app.app_context():
        # Check if custom_tabs table exists with correct schema
        try:
            # Try to query the table to see if it has the expected columns
            CustomTab.query.first()
            print("Custom tabs table schema is correct")
        except Exception as e:
            print(f"Schema issue detected: {e}")
            
            # Drop and recreate all tables
            print("Recreating database tables...")
            db.drop_all()
            db.create_all()
            print("Database tables recreated successfully")

if __name__ == '__main__':
    migrate_database()
