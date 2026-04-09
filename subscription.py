from datetime import datetime, timedelta

TIER_CONFIG = {
    'trial': {
        'name': 'Free Trial',
        'max_activities': 3,
        'duration_days': 7,
        'has_dashboard': False,
        'has_automation': False,
        'has_version_history': False,
        'has_audit_logs': False,
        'has_multi_user': False,
        'has_compliance_mapping': False,
        'has_export': False,
        'has_compliance_score': False,
        'has_alerts': False,
        'has_health_engine': False,
        'has_vendor_tracking': False,
        'has_risk_engine': False,
        'has_dpia_triggers': False,
        'has_ai_suggestions': False,
        'color': 'secondary',
        'price_monthly': 0,
        'price_annual': 0,
    },
    'starter': {
        'name': 'Starter',
        'max_activities': 3,
        'duration_days': None,
        'has_dashboard': False,
        'has_automation': False,
        'has_version_history': False,
        'has_audit_logs': False,
        'has_multi_user': False,
        'has_compliance_mapping': False,
        'has_export': True,
        'has_compliance_score': False,
        'has_alerts': False,
        'has_health_engine': False,
        'has_vendor_tracking': False,
        'has_risk_engine': False,
        'has_dpia_triggers': False,
        'has_ai_suggestions': False,
        'color': 'success',
        'price_monthly': 29,
        'price_annual': 278,
    },
    'growth': {
        'name': 'Growth',
        'max_activities': 15,
        'duration_days': None,
        'has_dashboard': True,
        'has_automation': False,
        'has_version_history': True,
        'has_audit_logs': False,
        'has_multi_user': True,
        'has_compliance_mapping': True,
        'has_export': True,
        'has_compliance_score': False,
        'has_alerts': True,
        'has_health_engine': False,
        'has_vendor_tracking': False,
        'has_risk_engine': True,
        'has_dpia_triggers': False,
        'has_ai_suggestions': False,
        'color': 'primary',
        'price_monthly': 99,
        'price_annual': 950,
    },
    'enterprise': {
        'name': 'Enterprise',
        'max_activities': None,
        'duration_days': None,
        'has_dashboard': True,
        'has_automation': True,
        'has_version_history': True,
        'has_audit_logs': True,
        'has_multi_user': True,
        'has_compliance_mapping': True,
        'has_export': True,
        'has_compliance_score': True,
        'has_alerts': True,
        'has_health_engine': True,
        'has_vendor_tracking': True,
        'has_risk_engine': True,
        'has_dpia_triggers': True,
        'has_ai_suggestions': True,
        'color': 'purple',
        'price_monthly': 299,
        'price_annual': 2870,
    },
}


def get_user_effective_tier(user):
    tier = user.subscription_tier or 'trial'
    if tier == 'trial':
        trial_start = user.trial_start_date or user.created_at or datetime.utcnow()
        if datetime.utcnow() > trial_start + timedelta(days=7):
            return 'expired'
    return tier


def get_tier_config(tier):
    if tier == 'expired':
        return {
            'name': 'Trial Expired',
            'max_activities': 0,
            'has_dashboard': False,
            'has_automation': False,
            'has_version_history': False,
            'has_audit_logs': False,
            'has_multi_user': False,
            'has_compliance_mapping': False,
            'has_export': False,
            'has_compliance_score': False,
            'has_alerts': False,
            'has_health_engine': False,
            'has_vendor_tracking': False,
            'has_risk_engine': False,
            'has_dpia_triggers': False,
            'has_ai_suggestions': False,
            'color': 'danger',
        }
    return TIER_CONFIG.get(tier, TIER_CONFIG['trial'])


def get_trial_days_remaining(user):
    if user.subscription_tier != 'trial':
        return None
    trial_start = user.trial_start_date or user.created_at or datetime.utcnow()
    expiry = trial_start + timedelta(days=7)
    remaining = (expiry - datetime.utcnow()).days
    return max(0, remaining)


def can_add_activity(user, current_count):
    tier = get_user_effective_tier(user)
    config = get_tier_config(tier)
    max_activities = config.get('max_activities')
    if max_activities is None:
        return True
    return current_count < max_activities


def has_feature(user, feature_key):
    tier = get_user_effective_tier(user)
    config = get_tier_config(tier)
    return config.get(feature_key, False)
