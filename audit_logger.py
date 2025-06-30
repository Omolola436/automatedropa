import sqlite3
from datetime import datetime
from database import get_db_connection

def log_audit_event(event_type, user_email, ip_address, description, additional_data=None):
    """Log an audit event"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_logs (event_type, user_email, ip_address, description, additional_data)
            VALUES (?, ?, ?, ?, ?)
        """, (event_type, user_email, ip_address, description, additional_data))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error logging audit event: {str(e)}")
        return False

def get_audit_logs(limit=100, page=1, per_page=50):
    """Get audit logs with pagination"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    offset = (page - 1) * per_page
    
    cursor.execute("""
        SELECT timestamp, event_type, user_email, ip_address, description, additional_data
        FROM audit_logs 
        ORDER BY timestamp DESC 
        LIMIT ? OFFSET ?
    """, (per_page, offset))
    
    logs = cursor.fetchall()
    
    # Get total count for pagination
    cursor.execute("SELECT COUNT(*) FROM audit_logs")
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    # Convert to list of dictionaries
    log_list = []
    for log in logs:
        log_list.append({
            'timestamp': log[0],
            'event_type': log[1],
            'user_email': log[2],
            'ip_address': log[3],
            'description': log[4],
            'additional_data': log[5]
        })
    
    return {
        'logs': log_list,
        'total_count': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page
    }

def get_recent_audit_logs(limit=10):
    """Get recent audit logs for dashboard"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT timestamp, event_type, user_email, ip_address, description
        FROM audit_logs 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (limit,))
    
    logs = cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    log_list = []
    for log in logs:
        log_list.append({
            'timestamp': log[0],
            'event_type': log[1],
            'user_email': log[2],
            'ip_address': log[3],
            'description': log[4]
        })
    
    return log_list
