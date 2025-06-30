import streamlit as st
from database import authenticate_user
from audit_logger import log_audit_event
import os

def login_page():
    """Display login page"""
    st.title("🔒 GDPR ROPA System Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="form-section">
            <h3>Please sign in to continue</h3>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            email = st.text_input("Email Address", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            col_a, col_b = st.columns(2)
            with col_a:
                login_button = st.form_submit_button("Login", use_container_width=True)
            with col_b:
                demo_button = st.form_submit_button("Demo Login", use_container_width=True)
            
            if login_button:
                if email and password:
                    user = authenticate_user(email, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_email = user[0]
                        st.session_state.user_role = user[1]
                        
                        # Log successful login
                        log_audit_event("Login Success", email, "User successfully logged in")
                        
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        # Log failed login
                        log_audit_event("Login Failed", email, "Login failed: Invalid credentials")
                        st.error("Invalid email or password")
                else:
                    st.error("Please enter both email and password")
            
            if demo_button:
                # Demo login with admin account
                st.session_state.authenticated = True
                st.session_state.user_email = "admin@ropa.system"
                st.session_state.user_role = "Admin"
                
                log_audit_event("Login Success", "admin@ropa.system", "Demo login successful")
                st.success("Demo login successful!")
                st.rerun()
        
        st.info("💡 **Demo Access**: Use 'Demo Login' button or login with admin@ropa.system / admin123")

def logout():
    """Handle user logout"""
    user_email = st.session_state.get('user_email', 'Unknown')
    
    # Log logout
    log_audit_event("Logout", user_email, "User logged out")
    
    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]

def check_authentication():
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)

def get_client_ip():
    """Get client IP address"""
    try:
        # Try to get IP from headers
        if 'X-Forwarded-For' in st.context.headers:
            return st.context.headers['X-Forwarded-For'].split(',')[0].strip()
        elif 'X-Real-IP' in st.context.headers:
            return st.context.headers['X-Real-IP']
        else:
            return "127.0.0.1"
    except:
        return "127.0.0.1"
