import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from database import get_dashboard_stats, get_ropa_records
from audit_logger import get_audit_logs

def show_dashboard(user_role):
    """Display main dashboard with metrics and charts"""
    
    st.header("📊 ROPA Dashboard")
    
    # Get dashboard statistics
    stats = get_dashboard_stats()
    
    # Key Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>Total Records</h3>
            <h2 style="color: #8B5CF6;">""" + str(stats['total_records']) + """</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        approved_count = stats['by_status'].get('Approved', 0)
        st.markdown("""
        <div class="metric-card">
            <h3>Approved</h3>
            <h2 style="color: #10B981;">""" + str(approved_count) + """</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        under_review_count = stats['by_status'].get('Under Review', 0)
        st.markdown("""
        <div class="metric-card">
            <h3>Under Review</h3>
            <h2 style="color: #F59E0B;">""" + str(under_review_count) + """</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        draft_count = stats['by_status'].get('Draft', 0)
        st.markdown("""
        <div class="metric-card">
            <h3>Drafts</h3>
            <h2 style="color: #6B7280;">""" + str(draft_count) + """</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        # Status Distribution Pie Chart
        if stats['by_status']:
            st.subheader("📈 Status Distribution")
            
            status_df = pd.DataFrame(list(stats['by_status'].items()))
            status_df.columns = ['Status', 'Count']
            
            # Define colors for each status
            colors = {
                'Draft': '#6B7280',
                'Pending Review': '#F59E0B', 
                'Approved': '#10B981',
                'Rejected': '#EF4444'
            }
            
            fig = px.pie(status_df, values='Count', names='Status',
                        color='Status',
                        color_discrete_map=colors,
                        hole=0.4)
            
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='white',
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Recent Activity Timeline
        st.subheader("🕒 Recent Activity")
        
        if stats['recent_activity']:
            activity_data = []
            for activity in stats['recent_activity']:
                activity_data.append({
                    'Activity': activity[0],
                    'Status': activity[1],
                    'Date': activity[2]
                })
            
            activity_df = pd.DataFrame(activity_data)
            
            # Simple timeline view
            for _, row in activity_df.iterrows():
                status_color = get_status_color(row['Status'])
                st.markdown(f"""
                <div style="border-left: 4px solid {status_color}; padding-left: 10px; margin-bottom: 10px;">
                    <strong>{row['Activity']}</strong><br>
                    <small>Status: {row['Status']} | {row['Date']}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No recent activity to display")
    
    # Compliance Overview
    st.subheader("🛡️ Compliance Overview")
    
    compliance_col1, compliance_col2, compliance_col3 = st.columns(3)
    
    with compliance_col1:
        # Calculate completion rate
        total = stats['total_records']
        completed = approved_count
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        st.metric(
            "Completion Rate",
            f"{completion_rate:.1f}%",
            delta=f"{completion_rate - 75:.1f}%" if completion_rate > 75 else None
        )
    
    with compliance_col2:
        # Review pending rate
        review_rate = (under_review_count / total * 100) if total > 0 else 0
        st.metric(
            "Pending Review",
            f"{review_rate:.1f}%",
            delta=f"-{review_rate:.1f}%" if review_rate < 20 else None,
            delta_color="inverse"
        )
    
    with compliance_col3:
        # Draft completion needed
        draft_rate = (draft_count / total * 100) if total > 0 else 0
        st.metric(
            "Draft Records",
            f"{draft_rate:.1f}%",
            delta=f"-{draft_rate:.1f}%" if draft_rate < 10 else None,
            delta_color="inverse"
        )
    
    # Role-specific sections
    if user_role == "Privacy Officer":
        show_privacy_officer_admin_section()
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("📝 Create New ROPA", use_container_width=True):
            st.session_state.current_page = "new_ropa"
            st.rerun()
    
    with action_col2:
        if st.button("📤 Upload ROPA File", use_container_width=True):
            st.session_state.current_page = "upload_ropa"
            st.rerun()
    
    with action_col3:
        if st.button("📊 Export Data", use_container_width=True):
            st.session_state.current_page = "export"
            st.rerun()



def show_privacy_officer_admin_section():
    """Privacy Officer specific dashboard section"""
    st.subheader("🔧 Privacy Officer Overview")
    
    admin_col1, admin_col2 = st.columns(2)
    
    with admin_col1:
        # System metrics
        st.write("**System Health**")
        
        # Get recent audit logs
        recent_logs = get_audit_logs(limit=10)
        failed_logins = len(recent_logs[recent_logs['event_type'] == 'Login Failed'])
        
        if failed_logins > 5:
            st.warning(f"⚠️ {failed_logins} failed login attempts recently")
        else:
            st.success("✅ System security status normal")
    
    with admin_col2:
        # Quick admin actions
        st.write("**Quick Actions**")
        
        if st.button("👥 Manage Users", key="privacy_officer_users"):
            st.session_state.current_page = "user_management"
            st.rerun()
        
        if st.button("📋 View Audit Logs", key="privacy_officer_audit"):
            from audit_logger import show_audit_log_dashboard
            show_audit_log_dashboard("Privacy Officer")

def get_status_color(status):
    """Get color for status"""
    colors = {
        'Draft': '#6B7280',
        'Pending Review': '#F59E0B',
        'Approved': '#10B981',
        'Rejected': '#EF4444'
    }
    return colors.get(status, '#6B7280')

def create_trend_chart(data, title):
    """Create a trend chart for dashboard metrics"""
    if not data:
        return None
    
    fig = go.Figure()
    
    dates = [item['date'] for item in data]
    values = [item['value'] for item in data]
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode='lines+markers',
        line=dict(color='#8B5CF6', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title=title,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        height=300,
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
    )
    
    return fig

def get_compliance_score():
    """Calculate overall compliance score"""
    stats = get_dashboard_stats()
    
    total = stats['total_records']
    if total == 0:
        return 0
    
    approved = stats['by_status'].get('Approved', 0)
    pending = stats['by_status'].get('Pending Review', 0)
    
    # Score based on approved records and pending reviews
    score = (approved / total) * 100
    
    # Penalty for too many pending reviews
    if pending > total * 0.3:  # More than 30% pending
        score *= 0.8
    
    return min(100, max(0, score))
