import os
import requests
import logging

EMAILJS_SERVICE_ID = os.environ.get('EMAILJS_SERVICE_ID')
EMAILJS_TEMPLATE_ID = os.environ.get('EMAILJS_TEMPLATE_ID')
EMAILJS_PUBLIC_KEY = os.environ.get('EMAILJS_PUBLIC_KEY')

EMAILJS_API_URL = 'https://api.emailjs.com/api/v1.0/email/send'


def send_email(to_email, to_name, subject, message, reply_to=None):
    if not all([EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, EMAILJS_PUBLIC_KEY]):
        logging.warning("EmailJS credentials not configured. Email not sent.")
        return False
    try:
        payload = {
            "service_id": EMAILJS_SERVICE_ID,
            "template_id": EMAILJS_TEMPLATE_ID,
            "user_id": EMAILJS_PUBLIC_KEY,
            "template_params": {
                "to_email": to_email,
                "to_name": to_name,
                "subject": subject,
                "message": message,
                "reply_to": reply_to or "noreply@example.com"
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
    subject = "Welcome to the Privacy ROPA Solution – Your Account is Active"
    message = (
        f"Dear {name},\n\n"
        "Thank you for creating your account on the Privacy ROPA Solution. "
        "Your free trial has started and your account is now active.\n\n"
        "During your trial you can:\n"
        "  • Create up to 5 ROPA processing activities\n"
        "  • Upload and manage ROPA records\n"
        "  • Use the step-by-step activity wizard\n\n"
        "Log in anytime to get started. If you need help, just reply to this email.\n\n"
        "Best regards,\n"
        "The Privacy ROPA Team"
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
        "The Privacy ROPA Team"
    )
    return send_email(to_email=user_email, to_name=name, subject=subject, message=message)
