import os
import ssl
import smtplib
import logging
from email.message import EmailMessage


def _get_smtp_config():
    """Load SMTP configuration from environment variables."""
    host = os.environ.get('SMTP_HOST')
    port = 587
    username = "support@3consult-ng.com"
    password = "@consulting."
    use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    use_ssl = os.environ.get('SMTP_USE_SSL', 'false').lower() == 'true'

    from_email = os.environ.get('FROM_EMAIL', 'support@3consult-ng.com')
    from_name = os.environ.get('FROM_NAME', 'DataProcess Flow')
    bcc_email = os.environ.get('BCC_EMAIL', 'odada@3consult-ng.com')

    return {
        'host': host,
        'port': port,
        'username': username,
        'password': password,
        'use_tls': use_tls,
        'use_ssl': use_ssl,
        'from_email': from_email,
        'from_name': from_name,
        'bcc_email': bcc_email,
    }


def send_email(to_email, to_name, subject, message, reply_to=None):
    """Send an email via SMTP from support@3consult-ng.com, BCC odada@3consult-ng.com."""
    cfg = _get_smtp_config()

    if not cfg['host'] or not cfg['password']:
        logging.warning(
            "SMTP credentials not configured (SMTP_HOST / SMTP_PASSWORD missing). "
            "Email to %s not sent.", to_email
        )
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"{cfg['from_name']} <{cfg['from_email']}>"
    msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
    if reply_to:
        msg['Reply-To'] = reply_to
    msg.set_content(message)

    # Build full recipient list including BCC
    recipients = [to_email]
    if cfg['bcc_email']:
        recipients.append(cfg['bcc_email'])

    try:
        if cfg['use_ssl']:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg['host'], cfg['port'], context=context, timeout=15) as server:
                server.login(cfg['username'], cfg['password'])
                server.send_message(msg, from_addr=cfg['from_email'], to_addrs=recipients)
        else:
            with smtplib.SMTP(cfg['host'], cfg['port'], timeout=15) as server:
                server.ehlo()
                if cfg['use_tls']:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                server.login(cfg['username'], cfg['password'])
                server.send_message(msg, from_addr=cfg['from_email'], to_addrs=recipients)

        logging.info("Email '%s' sent to %s (BCC: %s)", subject, to_email, cfg['bcc_email'])
        return True
    except Exception as e:
        logging.error("Error sending email to %s: %s", to_email, str(e))
        return False


def _greeting_name(full_name=None, organisation=None, user_email=None):
    """Pick the best name to greet the user with."""
    if full_name and full_name.strip():
        return full_name.strip()
    if organisation and organisation.strip():
        return organisation.strip()
    if user_email:
        return user_email.split('@')[0]
    return "there"


def send_welcome_email(user_email, full_name=None, organisation=None):
    """Email #1 — sent right after a user creates an account."""
    greeting = _greeting_name(full_name, organisation, user_email)
    org_line = f" on behalf of {organisation}" if organisation else ""
    subject = "Welcome to DataProcess Flow – Your Account is Active"
    message = (
        f"Dear {greeting},\n\n"
        f"Thank you for creating your account on DataProcess Flow by 3Consulting{org_line}. "
        "Your free trial has started and your account is now active.\n\n"
        "During your trial you can:\n"
        "  • Create up to 5 ROPA processing activities\n"
        "  • Upload and manage ROPA records\n"
        "  • Use the step-by-step activity wizard\n\n"
        "Log in anytime to get started. If you need help, just reply to this email.\n\n"
        "Best regards,\n"
        "The DataProcess Flow Team\n"
        "3Consulting"
    )
    return send_email(to_email=user_email, to_name=greeting, subject=subject, message=message)


def send_upgrade_email(user_email, full_name=None, organisation=None, activities_used=0, max_activities=5):
    """Email #2 — sent when the free trial / activity limit is reached."""
    greeting = _greeting_name(full_name, organisation, user_email)
    subject = "Your Free Trial Has Ended – Time to Upgrade"
    message = (
        f"Dear {greeting},\n\n"
        f"Your DataProcess Flow free trial has ended. You have used "
        f"{activities_used} out of {max_activities} ROPA activities on your current plan.\n\n"
        "To continue adding activities and unlock more powerful features, "
        "please upgrade your subscription:\n\n"
        "  • Starter Plan  – Up to 5 activities + Excel export\n"
        "  • Growth Plan   – Up to 15 activities + multi-user + version history\n"
        "  • Enterprise    – Unlimited activities + all features\n\n"
        "Log in and visit the Pricing page to upgrade today.\n\n"
        "Best regards,\n"
        "The DataProcess Flow Team\n"
        "3Consulting"
    )
    return send_email(to_email=user_email, to_name=greeting, subject=subject, message=message)


def send_password_reset_email(user_email, reset_link):
    name = user_email.split('@')[0]
    subject = "DataProcess Flow – Password Reset Request"
    message = (
        f"Dear {name},\n\n"
        "We received a request to reset your password for your DataProcess Flow account.\n\n"
        f"Click the link below to reset your password:\n{reset_link}\n\n"
        "This link will expire in 1 hour. If you did not request a password reset, "
        "please ignore this email — your account is safe.\n\n"
        "Best regards,\n"
        "The DataProcess Flow Team\n"
        "3Consulting"
    )
    return send_email(to_email=user_email, to_name=name, subject=subject, message=message)


def send_activity_approved_email(user_email, activity_name, reviewer_name=None):
    name = user_email.split('@')[0]
    reviewer = reviewer_name or "your Privacy Officer"
    subject = f"DataProcess Flow – Activity Approved: {activity_name}"
    message = (
        f"Dear {name},\n\n"
        f"Your ROPA processing activity '{activity_name}' has been reviewed and approved by {reviewer}.\n\n"
        "You can view the approved record by logging into DataProcess Flow.\n\n"
        "Best regards,\n"
        "The DataProcess Flow Team\n"
        "3Consulting"
    )
    return send_email(to_email=user_email, to_name=name, subject=subject, message=message)


def send_activity_rejected_email(user_email, activity_name, reason=None, reviewer_name=None):
    name = user_email.split('@')[0]
    reviewer = reviewer_name or "your Privacy Officer"
    reason_text = f"\n\nReason provided:\n{reason}" if reason else ""
    subject = f"DataProcess Flow – Activity Requires Attention: {activity_name}"
    message = (
        f"Dear {name},\n\n"
        f"Your ROPA processing activity '{activity_name}' has been reviewed by {reviewer} "
        f"and requires further attention.{reason_text}\n\n"
        "Please log into DataProcess Flow to review and update the record.\n\n"
        "Best regards,\n"
        "The DataProcess Flow Team\n"
        "3Consulting"
    )
    return send_email(to_email=user_email, to_name=name, subject=subject, message=message)


def check_emailjs_configured():
    """Backwards-compatible name. Returns True if SMTP credentials are configured."""
    cfg = _get_smtp_config()
    return bool(cfg['host'] and cfg['password'])


def check_smtp_configured():
    """Returns True if SMTP credentials are present."""
    return check_emailjs_configured()
