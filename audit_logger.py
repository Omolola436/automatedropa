from datetime import datetime
from flask import request
import json
import hashlib
import os

def log_audit_event(event_type, user_email, description, additional_data=None):
    """Enhanced security audit logging with comprehensive details"""
    try:
        from flask import current_app
        from models import db, AuditLog
        
        # Get comprehensive request information
        ip_address = get_client_ip()
        user_agent = request.headers.get('User-Agent', 'Unknown') if request else 'System'
        referer = request.headers.get('Referer', '') if request else ''
        request_method = request.method if request else 'N/A'
        request_url = request.url if request else 'N/A'
        session_id = get_session_hash()
        
        # Create comprehensive audit data
        audit_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_email': user_email,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'session_id': session_id,
            'request_method': request_method,
            'request_url': request_url,
            'referer': referer,
            'description': description,
            'server_name': request.host if request else 'localhost',
            'additional_data': additional_data
        }
        
        # Create audit log entry using SQLAlchemy
        audit_log = AuditLog(
            event_type=event_type,
            user_email=user_email,
            ip_address=ip_address,
            description=description,
            additional_data=json.dumps(audit_data)
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
        # Log high-priority security events to console for immediate visibility
        if is_security_event(event_type):
            print(f"[SECURITY AUDIT] {datetime.utcnow()} | {event_type} | {user_email} | {ip_address} | {description}")
        
        return True
        
    except Exception as e:
        print(f"Error logging audit event: {str(e)}")
        # Fallback logging to ensure we don't lose critical security events
        try:
            print(f"[AUDIT FALLBACK] {datetime.utcnow()} | {event_type} | {user_email} | {description}")
        except:
            pass
        return False

def get_client_ip():
    """Get client IP address with proxy support"""
    if not request:
        return 'System'
    
    # Check for forwarded headers (common in proxy setups)
    forwarded_ips = request.headers.get('X-Forwarded-For')
    if forwarded_ips:
        return forwarded_ips.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    return request.remote_addr or 'Unknown'

def get_session_hash():
    """Generate a hash of the session for tracking without exposing session data"""
    if not request or not hasattr(request, 'cookies'):
        return 'System'
    
    session_data = request.cookies.get('session', '')
    if session_data:
        return hashlib.sha256(session_data.encode()).hexdigest()[:16]
    return 'No-Session'

def is_security_event(event_type):
    """Determine if an event is security-critical"""
    security_events = [
        'Login Failed', 'Unauthorized Access', 'Permission Denied',
        'Account Locked', 'Password Reset', 'Role Changed',
        'Data Export', 'File Upload', 'System Error',
        'ROPA Deleted', 'User Deleted'
    ]
    return event_type in security_events

def get_audit_logs(limit=100, page=1, per_page=50):
    """Get audit logs with pagination using SQLAlchemy"""
    try:
        from models import AuditLog
        
        # Query audit logs with pagination
        logs_query = AuditLog.query.order_by(AuditLog.timestamp.desc())
        paginated_logs = logs_query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Process logs and parse additional data
        log_list = []
        for log in paginated_logs.items:
            # Parse additional data JSON
            additional_data = {}
            if log.additional_data:
                try:
                    additional_data = json.loads(log.additional_data)
                except (json.JSONDecodeError, TypeError):
                    additional_data = {}
            
            log_entry = {
                'id': log.id,
                'timestamp': log.timestamp,
                'event_type': log.event_type,
                'user_email': log.user_email,
                'ip_address': log.ip_address,
                'description': log.description,
                'user_agent': additional_data.get('user_agent', 'Unknown'),
                'session_id': additional_data.get('session_id', 'N/A'),
                'request_method': additional_data.get('request_method', 'N/A'),
                'request_url': additional_data.get('request_url', 'N/A'),
                'referer': additional_data.get('referer', ''),
                'server_name': additional_data.get('server_name', 'localhost'),
                'is_security_event': is_security_event(log.event_type),
                'additional_data': additional_data
            }
            log_list.append(log_entry)
        
        return {
            'logs': log_list,
            'total_count': paginated_logs.total,
            'page': page,
            'per_page': per_page,
            'total_pages': paginated_logs.pages,
            'has_prev': paginated_logs.has_prev,
            'has_next': paginated_logs.has_next
        }
        
    except Exception as e:
        print(f"Error retrieving audit logs: {str(e)}")
        return {
            'logs': [],
            'total_count': 0,
            'page': 1,
            'per_page': per_page,
            'total_pages': 0,
            'has_prev': False,
            'has_next': False
        }

def get_recent_audit_logs(limit=10):
    """Get recent audit logs for dashboard"""
    try:
        from models import AuditLog
        
        logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
        
        log_list = []
        for log in logs:
            # Parse additional data for enhanced display
            additional_data = {}
            if log.additional_data:
                try:
                    additional_data = json.loads(log.additional_data)
                except (json.JSONDecodeError, TypeError):
                    additional_data = {}
            
            log_entry = {
                'timestamp': log.timestamp,
                'event_type': log.event_type,
                'user_email': log.user_email,
                'ip_address': log.ip_address,
                'description': log.description,
                'user_agent': additional_data.get('user_agent', 'Unknown'),
                'is_security_event': is_security_event(log.event_type)
            }
            log_list.append(log_entry)
        
        return log_list
        
    except Exception as e:
        print(f"Error retrieving recent audit logs: {str(e)}")
        return []

def log_security_event(event_type, user_email, description, severity="HIGH"):
    """Log a high-priority security event"""
    security_description = f"[{severity}] {description}"
    return log_audit_event(event_type, user_email, security_description, 
                          additional_data={'severity': severity, 'security_event': True})

def log_system_event(event_type, description, additional_data=None):
    """Log system events (not user-specific)"""
    return log_audit_event(event_type, 'system', description, additional_data)

def get_audit_statistics():
    """Get audit statistics for dashboard"""
    try:
        from models import db, AuditLog
        
        total_events = AuditLog.query.count()
        
        # Get events by type
        event_counts = db.session.query(
            AuditLog.event_type,
            db.func.count(AuditLog.id).label('count')
        ).group_by(AuditLog.event_type).all()
        
        # Get recent security events
        security_events = AuditLog.query.filter(
            AuditLog.event_type.in_([
                'Login Failed', 'Unauthorized Access', 'Permission Denied',
                'Account Locked', 'Password Reset', 'Role Changed',
                'Data Export', 'File Upload', 'System Error',
                'ROPA Deleted', 'User Deleted'
            ])
        ).order_by(AuditLog.timestamp.desc()).limit(5).all()
        
        return {
            'total_events': total_events,
            'event_counts': {event_type: count for event_type, count in event_counts},
            'recent_security_events': len(security_events),
            'security_events': security_events
        }
        
    except Exception as e:
        print(f"Error getting audit statistics: {str(e)}")
        return {
            'total_events': 0,
            'event_counts': {},
            'recent_security_events': 0,
            'security_events': []
        }
