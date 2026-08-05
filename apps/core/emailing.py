from django.core.mail import EmailMultiAlternatives, get_connection

from .models import NotificationSettings


def notification_from_email(notification_settings=None):
    notification_settings = notification_settings or NotificationSettings.current()
    if notification_settings.sender_email:
        return f"{notification_settings.sender_name} <{notification_settings.sender_email}>"
    return ""


def notification_connection(notification_settings=None):
    notification_settings = notification_settings or NotificationSettings.current()
    if not notification_settings.is_smtp_configured:
        return None
    return get_connection(
        host=notification_settings.smtp_host,
        port=notification_settings.smtp_port,
        username=notification_settings.smtp_username,
        password=notification_settings.get_smtp_password(),
        use_tls=notification_settings.smtp_use_tls,
    )


def send_notification_email(subject, message, recipients, notification_settings=None, respect_enabled=True, html_message=""):
    notification_settings = notification_settings or NotificationSettings.current()
    recipients = list(dict.fromkeys(email for email in recipients if email))
    if respect_enabled and not notification_settings.email_alerts_enabled:
        return 0
    if not recipients or not notification_settings.is_smtp_configured:
        return 0
    email = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=notification_from_email(notification_settings) or notification_settings.smtp_username,
        to=recipients,
        connection=notification_connection(notification_settings),
    )
    if html_message:
        email.attach_alternative(html_message, "text/html")
    return email.send(fail_silently=True)
