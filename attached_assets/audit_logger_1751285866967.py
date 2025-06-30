import psycopg2
from datetime import datetime
import pandas as pd
from database import get_db_connection
from flask import request

def log_audit_event(event_type, user_email, description, ip_address=None, additional_data=None):
    """Log an audit event to the database with enhanced error handling"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get IP address if not provided
        if ip_address is None:
            ip_address = get_client_ip()
        
        cursor.execute("""
            INSERT INTO audit_logs (event_type, user_email, ip_address, description, additional_data)
            VALUES (?, ?, ?, ?, ?)
        """, (event_type, user_email, ip_address, description, additional_data))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        # Enhanced error handling - log critical audit failures
        print(f"CRITICAL: Audit logging error: {str(e)}")
        try:
            # Attempt to log the audit failure itself
            with get_db_connection() as fallback_conn:
                fallback_cursor = fallback_conn.cursor()
                fallback_cursor.execute("""
                    INSERT INTO audit_logs (event_type, user_email, ip_address, description)
                    VALUES (?, ?, ?, ?)
                """, ("Audit Log Error", "system", get_client_ip(), f"Failed to log event: {event_type} - {str(e)}"))
                fallback_conn.commit()
        except:
            pass  # Final fallback to prevent cascading errors

def get_client_ip():
    """Get client IP address from Flask request context"""
    try:
        # Try to get real IP from headers (for proxy setups)
        if request.environ.get('HTTP_X_FORWARDED_FOR'):
            return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
        elif request.environ.get('HTTP_X_REAL_IP'):
            return request.environ['HTTP_X_REAL_IP']
        else:
            return request.environ.get('REMOTE_ADDR', '127.0.0.1')
    except:
        return "127.0.0.1"

def log_security_event(event_type, user_email, description, severity="INFO"):
    """Log security-specific events with severity levels"""
    enhanced_description = f"[{severity}] {description}"
    log_audit_event(f"Security: {event_type}", user_email, enhanced_description)

def log_error_event(error_type, user_email, error_description, traceback_info=None):
    """Log error events with enhanced details"""
    description = f"Error: {error_description}"
    if traceback_info:
        description += f" | Traceback: {traceback_info}"
    log_audit_event(f"Error: {error_type}", user_email, description)

def get_audit_logs(limit=100, event_type=None, user_email=None, start_date=None, end_date=None):
    """Retrieve audit logs with optional filters"""
    conn = get_db_connection()
    
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    
    if user_email:
        query += " AND user_email = ?"
        params.append(user_email)
    
    if start_date:
        query += " AND timestamp >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND timestamp <= ?"
        params.append(end_date)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    return df

def show_audit_log_dashboard(user_role):
    """Display audit log dashboard for Privacy Officers"""
    if user_role != "Privacy Officer":
        st.error("Access denied. Privacy Officer privileges required.")
        return
    
    st.header("📊 Audit Log Dashboard")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        event_filter = st.selectbox("Event Type", 
                                  ["All", "Login Success", "Login Failed", "ROPA Created", 
                                   "ROPA Approved", "ROPA Rejected", "File Upload", "Export"])
    
    with col2:
        user_filter = st.text_input("User Email")
    
    with col3:
        start_date = st.date_input("Start Date")
    
    with col4:
        end_date = st.date_input("End Date")
    
    # Apply filters
    event_type_filter = None if event_filter == "All" else event_filter
    user_email_filter = user_filter if user_filter else None
    
    # Get audit logs
    audit_df = get_audit_logs(
        limit=500,
        event_type=event_type_filter,
        user_email=user_email_filter,
        start_date=start_date,
        end_date=end_date
    )
    
    if audit_df.empty:
        st.info("No audit logs found matching the current filters.")
        return
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Events", len(audit_df))
    
    with col2:
        unique_users = audit_df['user_email'].nunique()
        st.metric("Unique Users", unique_users)
    
    with col3:
        login_failures = len(audit_df[audit_df['event_type'] == 'Login Failed'])
        st.metric("Login Failures", login_failures)
    
    with col4:
        successful_logins = len(audit_df[audit_df['event_type'] == 'Login Success'])
        st.metric("Successful Logins", successful_logins)
    
    # Event type distribution
    if len(audit_df) > 0:
        st.subheader("📈 Event Distribution")
        event_counts = audit_df['event_type'].value_counts()
        st.bar_chart(event_counts)
    
    # Recent activity
    st.subheader("🕒 Recent Activity")
    
    # Format the dataframe for display
    display_df = audit_df.copy()
    display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Select columns to display
    columns_to_show = ['timestamp', 'event_type', 'user_email', 'description']
    if 'ip_address' in display_df.columns:
        columns_to_show.insert(-1, 'ip_address')
    
    st.dataframe(
        display_df[columns_to_show].head(50),
        use_container_width=True,
        column_config={
            "timestamp": "Timestamp",
            "event_type": "Event Type",
            "user_email": "User",
            "ip_address": "IP Address",
            "description": "Description"
        }
    )
    
    # Export audit logs
    if st.button("📥 Export Audit Logs", use_container_width=True):
        csv = audit_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

def log_system_event(event_type, description, additional_data=None):
    """Log system events (not user-specific)"""
    log_audit_event(event_type, "SYSTEM", description, "127.0.0.1", additional_data)

# Pre-defined event types for consistency
class AuditEventTypes:
    # Authentication
    LOGIN_SUCCESS = "Login Success"
    LOGIN_FAILED = "Login Failed"
    LOGOUT = "Logout"
    
    # ROPA Management
    ROPA_CREATED = "ROPA Created"
    ROPA_UPDATED = "ROPA Updated"
    ROPA_DELETED = "ROPA Deleted"
    ROPA_SUBMITTED = "ROPA Submitted for Review"
    ROPA_APPROVED = "ROPA Approved"
    ROPA_REJECTED = "ROPA Rejected"
    
    # File Operations
    FILE_UPLOADED = "File Uploaded"
    FILE_DOWNLOAD = "File Downloaded"
    DATA_EXPORTED = "Data Exported"
    
    # User Management
    USER_CREATED = "User Created"
    USER_UPDATED = "User Updated"
    USER_DELETED = "User Deleted"
    
    # System Events
    SYSTEM_ERROR = "System Error"
    UNAUTHORIZED_ACCESS = "Unauthorized Access Attempt"
    
    # Privacy Officer Actions
    PRIVACY_OFFICER_ACCESS = "Privacy Officer Access"
    SETTINGS_CHANGED = "Settings Changed"
