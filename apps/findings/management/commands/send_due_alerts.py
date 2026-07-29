from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from apps.findings.models import Finding
from apps.findings.services import findings_due_for_24h_alert


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
        sent = 0
        for finding, due_field, sent_field in findings_due_for_24h_alert():
            recipients = []
            if settings.REPRESENTANTE_GERENCIA_EMAIL:
                recipients.append(settings.REPRESENTANTE_GERENCIA_EMAIL)
            due_at = getattr(finding, due_field)
            label = FIELD_LABELS[due_field]
            if finding.classification == Finding.Classification.OPORTUNIDAD_MEJORA:
                if due_field == "corrective_action_due_at":
                    label = "plan de accion"
                elif due_field == "corrective_action_review_due_at":
                    label = "revision de plan de accion"
            if recipients:
                send_mail(
                    subject=f"Alerta 24h: {label} de {finding.code}",
                    message=f"El plazo de {label} del hallazgo {finding.code} vence el {due_at:%d-%m-%Y %H:%M}.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipients,
                    fail_silently=True,
                )
            setattr(finding, sent_field, True)
            finding.save(update_fields=[sent_field, "updated_at"])
            sent += 1
        self.stdout.write(self.style.SUCCESS(f"Alertas procesadas: {sent}"))
