#!/usr/bin/env python3
"""Fix SQLite database by adding test ROPA records"""

import sqlite3
from datetime import datetime

def add_test_ropa_records():
    """Add test ROPA records to SQLite database"""
    conn = sqlite3.connect('ropa_system.db')
    cursor = conn.cursor()
    
    # Check if records already exist
    cursor.execute("SELECT COUNT(*) FROM ropa_records")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"Database already has {count} records. Clearing and adding new ones...")
        cursor.execute("DELETE FROM ropa_records")
    
    # Insert test ROPA records
    test_records = [
        {
            'processing_activity_name': 'Employee Data Management',
            'category': 'HR Operations',
            'description': 'Processing of employee personal data for HR management',
            'department_function': 'Privacy',
            'controller_name': 'Trinity Pharmacy Ltd',
            'controller_contact': 'hr@trinity-pharmacy.com',
            'controller_address': '123 Pharmacy Street, Lagos, Nigeria',
            'dpo_name': 'Tendai F Mataba',
            'dpo_contact': 'dpo@trinity-pharmacy.com',
            'dpo_address': '123 Pharmacy Street, Lagos, Nigeria',
            'processing_purpose': 'Human Resources Management',
            'legal_basis': 'Contract',
            'data_categories': 'Name, Email, Phone, Address, Employment History',
            'data_subjects': 'Current and Former Employees',
            'recipients': 'HR Department, Payroll Provider',
            'retention_period': '7 years after employment ends',
            'security_measures': 'Access controls, encryption, regular backups',
            'status': 'Approved',
            'created_by': 'odada@3consult-ng.com',
            'approved_by': 'odada@3consult-ng.com'
        },
        {
            'processing_activity_name': 'Customer Order Processing',
            'category': 'Sales Operations',
            'description': 'Processing customer orders and delivery information',
            'department_function': 'Sales',
            'controller_name': 'Trinity Pharmacy Ltd',
            'controller_contact': 'sales@trinity-pharmacy.com',
            'controller_address': '123 Pharmacy Street, Lagos, Nigeria',
            'dpo_name': 'Tendai F Mataba',
            'dpo_contact': 'dpo@trinity-pharmacy.com',
            'dpo_address': '123 Pharmacy Street, Lagos, Nigeria',
            'processing_purpose': 'Order fulfillment and customer service',
            'legal_basis': 'Contract',
            'data_categories': 'Name, Address, Phone, Email, Order History',
            'data_subjects': 'Customers',
            'recipients': 'Sales Team, Delivery Partners',
            'retention_period': '5 years after last transaction',
            'security_measures': 'Secure payment processing, encrypted databases',
            'status': 'Approved',
            'created_by': 'odada@3consult-ng.com',
            'approved_by': 'odada@3consult-ng.com'
        }
    ]
    
    # Insert records
    for record in test_records:
        cursor.execute("""
            INSERT INTO ropa_records (
                processing_activity_name, category, description, department_function,
                controller_name, controller_contact, controller_address,
                dpo_name, dpo_contact, dpo_address,
                processing_purpose, legal_basis, data_categories, data_subjects,
                recipients, retention_period, security_measures,
                status, created_by, approved_by, approved_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            record['processing_activity_name'], record['category'], record['description'], record['department_function'],
            record['controller_name'], record['controller_contact'], record['controller_address'],
            record['dpo_name'], record['dpo_contact'], record['dpo_address'],
            record['processing_purpose'], record['legal_basis'], record['data_categories'], record['data_subjects'],
            record['recipients'], record['retention_period'], record['security_measures'],
            record['status'], record['created_by'], record['approved_by']
        ))
    
    conn.commit()
    
    # Verify records were inserted
    cursor.execute("SELECT id, processing_activity_name, status, department_function, created_by FROM ropa_records")
    records = cursor.fetchall()
    
    print("SQLite database now contains:")
    for record in records:
        print(f"  ID: {record[0]}, Name: {record[1]}, Status: {record[2]}, Dept: {record[3]}, Created by: {record[4]}")
    
    conn.close()
    print(f"Successfully added {len(test_records)} ROPA records to SQLite database")

if __name__ == "__main__":
    add_test_ropa_records()