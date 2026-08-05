from django.core.management.base import BaseCommand

from apps.core.emailing import send_notification_email
from apps.core.models import NotificationSettings
from apps.findings.models import Finding
from apps.findings.services import (
    due_recipient_user,
    finding_context_lines,
    findings_due_for_24h_alert,
    findings_overdue_for_alert,
    format_due,
    representative_emails,
    review_action_label,
    user_email,
)


FIELD_LABELS = {
    "validation_due_at": "validacion",
    "correction_due_at": "correccion",
    "correction_review_due_at": "revision de correccion",
    "corrective_action_due_at": "accion correctiva",
    "corrective_action_review_due_at": "revision de accion correctiva",
    "verification_due_at": "verificacion de eficacia",
}


class Command(BaseCommand):
    help = "Envia alertas 24 horas antes de vencimientos de hallazgos."

    def handle(self, *args, **options):
        notification_settings = NotificationSettings.current()
        if not notification_settings.email_alerts_enabled:
            self.stdout.write(self.style.WARNING("Alertas por correo desactivadas desde mantenedor."))
            return

        sent = 0
        if notification_settings.notify_due_24h:
            sent += self._send_24h_alerts(notification_settings)
        if notification_settings.notify_overdue:
            sent += self._send_overdue_alerts(notification_settings)
        self.stdout.write(self.style.SUCCESS(f"Alertas procesadas: {sent}"))

    def _label_for(self, finding, due_field):
        label = FIELD_LABELS[due_field]
        if finding.classification == Finding.Classification.OPORTUNIDAD_MEJORA:
            if due_field == "corrective_action_due_at":
                label = "plan de accion"
            elif due_field == "corrective_action_review_due_at":
                label = "revision de plan de accion"
        return label

    def _recipients_for(self, notification_settings, finding, due_field):
        recipients = notification_settings.copy_recipients()
        recipients.extend(representative_emails())
        assigned_user = due_recipient_user(finding, due_field)
        email = user_email(assigned_user)
        if email:
            recipients.append(email)
        return list(dict.fromkeys(email for email in recipients if email))

    def _send_24h_alerts(self, notification_settings):
        sent = 0
        for finding, due_field, sent_field in findings_due_for_24h_alert():
            recipients = notification_settings.copy_recipients()
            recipients = self._recipients_for(notification_settings, finding, due_field)
            due_at = getattr(finding, due_field)
            label = self._label_for(finding, due_field)
            if recipients:
                send_notification_email(
                    subject=f"Plazo proximo a vencer: {finding.code}",
                    message=finding_context_lines(
                        finding,
                        action_expected=f"{review_action_label(finding, due_field)} El plazo vence el {format_due(due_at)}.",
                        due_at=due_at,
                        assigned_user=due_recipient_user(finding, due_field),
                    ),
                    recipients=recipients,
                    notification_settings=notification_settings,
                )
            setattr(finding, sent_field, True)
            finding.save(update_fields=[sent_field, "updated_at"])
            sent += 1
        return sent

    def _send_overdue_alerts(self, notification_settings):
        sent = 0
        for finding, due_field, sent_field in findings_overdue_for_alert():
            recipients = self._recipients_for(notification_settings, finding, due_field)
            due_at = getattr(finding, due_field)
            label = self._label_for(finding, due_field)
            if recipients:
                send_notification_email(
                    subject=f"Actividad vencida: {finding.code}",
                    message=finding_context_lines(
                        finding,
                        action_expected=f"La actividad '{label}' se encuentra vencida. {review_action_label(finding, due_field)}",
                        due_at=due_at,
                        assigned_user=due_recipient_user(finding, due_field),
                    ),
                    recipients=recipients,
                    notification_settings=notification_settings,
                )
            setattr(finding, sent_field, True)
            finding.save(update_fields=[sent_field, "updated_at"])
            sent += 1
        return sent
