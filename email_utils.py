import os
import requests
import logging

EMAILJS_API_URL = 'https://api.emailjs.com/api/v1.0/email/send'


def _get_credentials():
    """Read EmailJS credentials from environment at call-time."""
    return (
        os.environ.get('EMAILJS_SERVICE_ID'),
        os.environ.get('EMAILJS_TEMPLATE_ID'),
        os.environ.get('EMAILJS_PUBLIC_KEY'),
    )


def send_email(to_email, to_name, subject, message, reply_to=None):
    service_id, template_id, public_key = _get_credentials()

    if not all([service_id, template_id, public_key]):
        logging.warning("EmailJS credentials not configured. Email not sent.")
        return False

    # Split name into first/last to match the EmailJS template variables
    name_parts = (to_name or '').strip().split(' ', 1)
    fname = name_parts[0] if name_parts else ''
    lname = name_parts[1] if len(name_parts) > 1 else ''

    # Combine subject + body since template has no dedicated subject field
    full_message = f"Subject: {subject}\n\n{message}"

    try:
        payload = {
            "service_id": service_id,
            "template_id": template_id,
            "user_id": public_key,
            "template_params": {
                "FName": fname,
                "LName": lname,
                "email": to_email,
                "tel": "",
                "message": full_message
            }
        }
        response = requests.post(
            EMAILJS_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code == 200:
            logging.info(f"Email sent successfully to {to_email}")
            return True
        else:
            logging.error(f"EmailJS API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error sending email to {to_email}: {str(e)}")
        return False


def send_welcome_email(user_email, organisation=None):
    name = organisation or user_email.split('@')[0]
    subject = "Welcome to ProcessLedger – Your Account is Active"
    message = (
        f"Dear {name},\n\n"
        "Thank you for creating your account on ProcessLedger by 3Consulting. "
        "Your free trial has started and your account is now active.\n\n"
        "During your trial you can:\n"
        "  • Create up to 5 ROPA processing activities\n"
        "  • Upload and manage ROPA records\n"
        "  • Use the step-by-step activity wizard\n\n"
        "Log in anytime to get started. If you need help, just reply to this email.\n\n"
        "Best regards,\n"
        "The ProcessLedger Team\n"
        "3Consulting"
    )
    return send_email(to_email=user_email, to_name=name, subject=subject, message=message)


def send_upgrade_email(user_email, organisation=None, activities_used=0, max_activities=5):
    name = organisation or user_email.split('@')[0]
    subject = "You've Reached Your Activity Limit – Time to Upgrade"
    message = (
        f"Dear {name},\n\n"
        f"You have used {activities_used} out of {max_activities} ROPA activities on your current plan.\n\n"
        "To continue adding activities and unlock more powerful features, "
        "please upgrade your subscription:\n\n"
        "  • Starter Plan  – Up to 5 activities + Excel export\n"
        "  • Growth Plan   – Up to 15 activities + multi-user + version history\n"
        "  • Enterprise    – Unlimited activities + all features\n\n"
        "Log in and visit the Pricing page to upgrade today.\n\n"
        "Best regards,\n"
        "The ProcessLedger Team\n"
        "3Consulting"
    )
    return send_email(to_email=user_email, to_name=name, subject=subject, message=message)


def send_password_reset_email(user_email, reset_link):
    name = user_email.split('@')[0]
    subject = "ProcessLedger – Password Reset Request"
    message = (
        f"Dear {name},\n\n"
        "We received a request to reset your password for your ProcessLedger account.\n\n"
        f"Click the link below to reset your password:\n{reset_link}\n\n"
        "This link will expire in 1 hour. If you did not request a password reset, "
        "please ignore this email — your account is safe.\n\n"
        "Best regards,\n"
        "The ProcessLedger Team\n"
        "3Consulting"
    )
    return send_email(to_email=user_email, to_name=name, subject=subject, message=message)


def send_activity_approved_email(user_email, activity_name, reviewer_name=None):
    name = user_email.split('@')[0]
    reviewer = reviewer_name or "your Privacy Officer"
    subject = f"ProcessLedger – Activity Approved: {activity_name}"
    message = (
        f"Dear {name},\n\n"
        f"Your ROPA processing activity '{activity_name}' has been reviewed and approved by {reviewer}.\n\n"
        "You can view the approved record by logging into ProcessLedger.\n\n"
        "Best regards,\n"
        "The ProcessLedger Team\n"
        "3Consulting"
    )
    return send_email(to_email=user_email, to_name=name, subject=subject, message=message)


def send_activity_rejected_email(user_email, activity_name, reason=None, reviewer_name=None):
    name = user_email.split('@')[0]
    reviewer = reviewer_name or "your Privacy Officer"
    reason_text = f"\n\nReason provided:\n{reason}" if reason else ""
    subject = f"ProcessLedger – Activity Requires Attention: {activity_name}"
    message = (
        f"Dear {name},\n\n"
        f"Your ROPA processing activity '{activity_name}' has been reviewed by {reviewer} "
        f"and requires further attention.{reason_text}\n\n"
        "Please log into ProcessLedger to review and update the record.\n\n"
        "Best regards,\n"
        "The ProcessLedger Team\n"
        "3Consulting"
    )
    return send_email(to_email=user_email, to_name=name, subject=subject, message=message)


def check_emailjs_configured():
    """Returns True if all EmailJS credentials are present."""
    service_id, template_id, public_key = _get_credentials()
    return all([service_id, template_id, public_key])
