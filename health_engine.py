from datetime import datetime, timedelta


SAFE_COUNTRIES = [
    'United Kingdom', 'European Union', 'Germany', 'France', 'Netherlands',
    'Sweden', 'Denmark', 'Norway', 'Finland', 'Ireland', 'Belgium', 'Austria',
    'Switzerland', 'Canada', 'New Zealand', 'Japan', 'South Korea', 'Israel',
    'Australia', 'Argentina', 'Uruguay',
]

SCORED_FIELDS = [
    'processing_activity_name',
    'category',
    'description',
    'department_function',
    'controller_name',
    'controller_contact',
    'dpo_name',
    'dpo_contact',
    'processing_purpose',
    'legal_basis',
    'data_categories',
    'data_subjects',
    'recipients',
    'retention_period',
    'security_measures',
    'breach_likelihood',
    'breach_impact',
    'risk_level',
]


def calculate_compliance_score(record):
    total = len(SCORED_FIELDS)
    completed = 0
    missing = []

    for field in SCORED_FIELDS:
        value = getattr(record, field, None)
        if value and str(value).strip():
            completed += 1
        else:
            missing.append(field)

    score = int((completed / total) * 100)

    if score >= 90:
        label = 'Excellent'
        color = 'success'
    elif score >= 70:
        label = 'Good'
        color = 'primary'
    elif score >= 50:
        label = 'Needs Attention'
        color = 'warning'
    else:
        label = 'Critical'
        color = 'danger'

    return {
        'score': score,
        'label': label,
        'color': color,
        'completed': completed,
        'total': total,
        'missing_fields': missing,
    }


def calculate_org_compliance_score(records):
    if not records:
        return {'score': 0, 'label': 'No Data', 'color': 'secondary', 'record_count': 0}

    scores = [calculate_compliance_score(r)['score'] for r in records]
    avg = int(sum(scores) / len(scores))

    if avg >= 90:
        label, color = 'Excellent', 'success'
    elif avg >= 70:
        label, color = 'Good', 'primary'
    elif avg >= 50:
        label, color = 'Needs Attention', 'warning'
    else:
        label, color = 'Critical', 'danger'

    return {
        'score': avg,
        'label': label,
        'color': color,
        'record_count': len(records),
    }


def run_health_checks(records, user, db, Notification):
    alerts_created = 0
    now = datetime.utcnow()

    for record in records:
        existing_ids = {
            n.related_record_id
            for n in Notification.query.filter_by(
                user_id=user.id, is_read=False
            ).all()
            if n.related_record_id
        }

        if record.risk_level and record.risk_level.lower() == 'high':
            if not _alert_exists(Notification, user.id, record.id, 'High-Risk Activity'):
                n = Notification(
                    user_id=user.id,
                    title='🔴 High-Risk Activity Detected',
                    message=f'"{record.processing_activity_name}" has been flagged as HIGH RISK. '
                            f'Please review and consider a DPIA.',
                    alert_type='danger',
                    related_record_id=record.id,
                )
                db.session.add(n)
                alerts_created += 1

        if not record.legal_basis or not str(record.legal_basis).strip():
            if not _alert_exists(Notification, user.id, record.id, 'Missing Legal Basis'):
                n = Notification(
                    user_id=user.id,
                    title='🟡 Missing Legal Basis',
                    message=f'"{record.processing_activity_name}" has no legal basis defined. '
                            f'This is a GDPR/NDPA compliance requirement.',
                    alert_type='warning',
                    related_record_id=record.id,
                )
                db.session.add(n)
                alerts_created += 1

        if record.updated_at:
            days_since_update = (now - record.updated_at).days
            if days_since_update > 365:
                if not _alert_exists(Notification, user.id, record.id, 'Review Due'):
                    n = Notification(
                        user_id=user.id,
                        title='🔵 Review Due',
                        message=f'"{record.processing_activity_name}" has not been reviewed in '
                                f'over {days_since_update} days. Annual review is recommended.',
                        alert_type='info',
                        related_record_id=record.id,
                    )
                    db.session.add(n)
                    alerts_created += 1

        if record.third_country_transfers and str(record.third_country_transfers).strip():
            transfers = str(record.third_country_transfers)
            risky = any(
                country.lower() not in [s.lower() for s in SAFE_COUNTRIES]
                for country in transfers.split(',')
                if country.strip()
            )
            if risky:
                if not _alert_exists(Notification, user.id, record.id, 'Third-Party Risk'):
                    n = Notification(
                        user_id=user.id,
                        title='⚠️ Third-Party Transfer Risk',
                        message=f'"{record.processing_activity_name}" involves transfers to '
                                f'potentially non-adequate countries. Review safeguards.',
                        alert_type='warning',
                        related_record_id=record.id,
                    )
                    db.session.add(n)
                    alerts_created += 1

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return alerts_created


def notify_new_activity(record, submitter_user, privacy_officers, db, Notification):
    for officer in privacy_officers:
        if officer.id == submitter_user.id:
            continue
        n = Notification(
            user_id=officer.id,
            title='🟣 New Activity Submitted',
            message=f'{submitter_user.email} submitted "{record.processing_activity_name}" '
                    f'for review.',
            alert_type='primary',
            related_record_id=record.id,
        )
        db.session.add(n)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def check_vendor_alerts(vendors, user, db, Notification):
    now = datetime.utcnow()
    alerts_created = 0

    for vendor in vendors:
        if vendor.contract_expiry:
            days_until_expiry = (vendor.contract_expiry - now).days
            if 0 <= days_until_expiry <= 30:
                key = f'contract_expiry_{vendor.id}'
                if not _vendor_alert_exists(Notification, user.id, key):
                    n = Notification(
                        user_id=user.id,
                        title='⚠️ Vendor Contract Expiring',
                        message=f'Vendor "{vendor.name}" contract expires in {days_until_expiry} days '
                                f'({vendor.contract_expiry.strftime("%Y-%m-%d")}). Please renew.',
                        alert_type='warning',
                    )
                    db.session.add(n)
                    alerts_created += 1

        if vendor.country and vendor.country not in SAFE_COUNTRIES:
            key = f'vendor_country_risk_{vendor.id}'
            if not _vendor_alert_exists(Notification, user.id, key):
                n = Notification(
                    user_id=user.id,
                    title='⚠️ Third-Party Vendor Risk',
                    message=f'Vendor "{vendor.name}" is based in {vendor.country}, '
                            f'which may not have adequate data protection. Review safeguards.',
                    alert_type='warning',
                )
                db.session.add(n)
                alerts_created += 1

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return alerts_created


def _alert_exists(Notification, user_id, record_id, title_keyword):
    return Notification.query.filter(
        Notification.user_id == user_id,
        Notification.related_record_id == record_id,
        Notification.title.contains(title_keyword),
    ).first() is not None


def _vendor_alert_exists(Notification, user_id, key):
    return Notification.query.filter(
        Notification.user_id == user_id,
        Notification.message.contains(key),
    ).first() is not None
