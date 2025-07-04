
#!/usr/bin/env python3
"""
Script to fix database schema by recreating it with all required tables
"""

import os
import sqlite3
from database import init_database

def fix_database():
    """Remove existing database and recreate with proper schema"""
    db_path = 'ropa_system.db'
    
    # Backup existing data if database exists
    if os.path.exists(db_path):
        print("Backing up existing data...")
        backup_path = f'{db_path}.backup'
        
        # Create backup
        with sqlite3.connect(db_path) as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
        
        print(f"Database backed up to {backup_path}")
        
        # Remove original database
        os.remove(db_path)
        print("Removed old database")
    
    # Initialize new database with proper schema
    print("Creating new database with updated schema...")
    init_database()
    print("Database schema updated successfully!")
    
    print("\nIMPORTANT: You may need to re-register users and recreate ROPA records.")
    print("The backup file has been saved if you need to recover any data.")

if __name__ == '__main__':
    fix_database()
