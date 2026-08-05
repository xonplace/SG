from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.core.emailing import send_notification_email
from apps.core.models import CompanyProfile, NotificationSettings

from .models import Finding, FindingHistory, Holiday


def active_due_definitions():
    return [
        (
            "Validacion",
            "validation_due_at",
            [Finding.Status.INGRESADO, Finding.Status.EN_VALIDACION],
        ),
        (
            "Correccion",
            "correction_due_at",
            [Finding.Status.CORRECCION_ASIGNADA, Finding.Status.EN_CORRECCION],
        ),
        (
            "Revision correccion",
            "correction_review_due_at",
            [Finding.Status.CORRECCION_EN_REVISION],
        ),
        (
            "Accion correctiva",
            "corrective_action_due_at",
            [Finding.Status.ACCION_CORRECTIVA_ASIGNADA, Finding.Status.EN_ACCION_CORRECTIVA],
        ),
        (
            "Revision accion correctiva",
            "corrective_action_review_due_at",
            [Finding.Status.ACCION_CORRECTIVA_EN_REVISION],
        ),
        (
            "Verificacion",
            "verification_due_at",
            [Finding.Status.SEGUIMIENTO_ASIGNADO, Finding.Status.EN_SEGUIMIENTO],
        ),
    ]


def active_due_query(limit_at):
    query = Q(pk__in=[])
    for _label, field_name, statuses in active_due_definitions():
        query |= Q(status__in=statuses, **{f"{field_name}__isnull": False, f"{field_name}__lte": limit_at})
    return query


def active_due_dates_for(finding):
    due_dates = []
    for label, field_name, statuses in active_due_definitions():
        due_at = getattr(finding, field_name)
        if finding.status in statuses and due_at:
            if finding.classification == Finding.Classification.OPORTUNIDAD_MEJORA:
                if field_name == "corrective_action_due_at":
                    label = "Plan de accion"
                elif field_name == "corrective_action_review_due_at":
                    label = "Revision plan de accion"
            due_dates.append((label, due_at))
    return due_dates


def add_business_days(start_date, days):
    current = start_date
    added = 0
    holidays = set(Holiday.objects.values_list("date", flat=True))
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in holidays:
            added += 1
    return current


def due_at_from_business_days(start_date, days):
    due_date = add_business_days(start_date, days)
    return timezone.make_aware(datetime.combine(due_date, time(hour=18)))


def record_history(finding, action, user=None, previous_status="", new_status="", comment=""):
    return FindingHistory.objects.create(
        finding=finding,
        user=user,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        comment=comment,
    )


def user_label(user):
    if not user:
        return "-"
    full_name = user.get_full_name().strip()
    return full_name or user.username


def user_email(user):
    return user.email if user and user.email else ""


def format_due(due_at):
    if not due_at:
        return "-"
    return timezone.localtime(due_at).strftime("%d-%m-%Y %H:%M")


def finding_absolute_url(finding, request=None):
    path = reverse("findings:detail", args=[finding.pk])
    if request:
        return request.build_absolute_uri(path)
    notification_settings = NotificationSettings.current()
    if notification_settings.site_base_url:
        return f"{notification_settings.site_base_url.strip().rstrip('/')}{path}"
    base_url = settings.SITE_BASE_URL.strip().rstrip("/")
    if base_url:
        return f"{base_url}{path}"
    return path


def representative_emails():
    recipients = []
    company = CompanyProfile.current()
    if company.representative_email:
        recipients.append(company.representative_email)
    if settings.REPRESENTANTE_GERENCIA_EMAIL:
        recipients.append(settings.REPRESENTANTE_GERENCIA_EMAIL)
    return list(dict.fromkeys(email for email in recipients if email))


def finding_context_lines(finding, *, action_expected="", due_at=None, assigned_user=None, request=None):
    lines = [
        f"Codigo: {finding.code}",
        f"Estado actual: {display_status_label(finding)}",
        f"Clasificacion: {finding.get_classification_display() if finding.classification else 'Pendiente'}",
        f"Fuente: {finding.get_source_display()}",
        f"Proceso: {finding.process_label or '-'}",
        f"Informado por: {finding.reported_by_name}",
    ]
    if assigned_user:
        lines.append(f"Responsable: {user_label(assigned_user)}")
    if due_at:
        lines.append(f"Plazo: {format_due(due_at)}")
    if action_expected:
        lines.append(f"Accion esperada: {action_expected}")
    lines.extend(
        [
            "",
            "Descripcion:",
            finding.description,
            "",
            f"Ver hallazgo: {finding_absolute_url(finding, request=request)}",
            "",
            "Este correo fue generado automaticamente por el Portal SGC.",
        ]
    )
    return "\n".join(lines)


def due_recipient_user(finding, due_field):
    if due_field in {"correction_due_at", "corrective_action_due_at"}:
        correction = related_or_none(finding, "correction")
        action = related_or_none(finding, "corrective_action")
        return (correction and correction.assigned_to) or (action and action.assigned_to)
    if due_field == "verification_due_at":
        verification = related_or_none(finding, "effectiveness_verification")
        return verification and verification.assigned_to
    return None


def review_action_label(finding, due_field):
    if due_field == "validation_due_at":
        return "Validar si el hallazgo aplica y clasificarlo si corresponde."
    if due_field == "correction_due_at":
        return "Registrar la correccion aplicada y cargar evidencia si corresponde."
    if due_field == "correction_review_due_at":
        return "Revisar si la correccion aplicada es conforme."
    if due_field == "corrective_action_due_at":
        return "Registrar el plan de accion y el analisis de causa raiz."
    if due_field == "corrective_action_review_due_at":
        return "Revisar si el plan de accion es conforme."
    if due_field == "verification_due_at":
        return "Registrar el seguimiento y la verificacion de eficacia."
    return "Revisar la actividad pendiente en el Portal SGC."


def related_or_none(instance, relation_name):
    try:
        return getattr(instance, relation_name)
    except (AttributeError, ObjectDoesNotExist):
        return None


def display_status_label(finding):
    correction = related_or_none(finding, "correction")
    if finding.status == Finding.Status.EN_CORRECCION and correction and correction.is_conform is False:
        return "Correccion observada"
    action = related_or_none(finding, "corrective_action")
    verification = related_or_none(finding, "effectiveness_verification")
    if finding.status == Finding.Status.EN_ACCION_CORRECTIVA and verification and verification.is_effective is False:
        if finding.classification == Finding.Classification.OPORTUNIDAD_MEJORA:
            return "Seguimiento no eficaz - revisar plan de accion"
        return "Seguimiento no eficaz - revisar accion correctiva"
    if finding.status == Finding.Status.EN_ACCION_CORRECTIVA and action and action.is_conform is False:
        if finding.classification == Finding.Classification.OPORTUNIDAD_MEJORA:
            return "Plan de accion observado"
        return "Accion correctiva observada"
    if finding.classification != Finding.Classification.OPORTUNIDAD_MEJORA:
        return finding.get_status_display()
    labels = {
        Finding.Status.ACCION_CORRECTIVA_ASIGNADA: "Oportunidad de mejora asignada",
        Finding.Status.EN_ACCION_CORRECTIVA: "Plan de accion en desarrollo",
        Finding.Status.ACCION_CORRECTIVA_EN_REVISION: "Plan de accion en revision",
        Finding.Status.ACCION_CORRECTIVA_APROBADA: "Plan de accion aprobado",
        Finding.Status.SEGUIMIENTO_ASIGNADO: "Seguimiento asignado",
        Finding.Status.EN_SEGUIMIENTO: "Seguimiento en desarrollo",
        Finding.Status.SEGUIMIENTO_EN_REVISION: "Seguimiento en revision",
    }
    return labels.get(finding.status, finding.get_status_display())


def notify_new_finding(finding, request=None):
    notification_settings = NotificationSettings.current()
    if not notification_settings.email_alerts_enabled or not notification_settings.notify_finding_created:
        return 0

    recipients = notification_settings.copy_recipients()
    if finding.reported_by_email:
        recipients.append(finding.reported_by_email)
    recipients.extend(representative_emails())
    recipients = list(dict.fromkeys(email for email in recipients if email))
    if not recipients:
        return 0
    return send_notification_email(
        subject=f"Nuevo hallazgo registrado: {finding.code}",
        message=finding_context_lines(
            finding,
            action_expected="El Representante de la Gerencia debe validar si corresponde tratamiento.",
            due_at=finding.validation_due_at,
            request=request,
        ),
        recipients=recipients,
        notification_settings=notification_settings,
    )


def notify_representative(subject, finding, action_expected, *, due_at=None, submitted_by=None, request=None):
    recipients = representative_emails()
    if not recipients:
        return 0
    message = finding_context_lines(
        finding,
        action_expected=action_expected,
        due_at=due_at,
        assigned_user=submitted_by,
        request=request,
    )
    return send_notification_email(
        subject=subject,
        message=message,
        recipients=recipients,
    )


def notify_assignment(finding, assigned_user, phase, *, due_at=None, request=None):
    notification_settings = NotificationSettings.current()
    if not notification_settings.email_alerts_enabled or not notification_settings.notify_assignments:
        return 0

    recipients = notification_settings.copy_recipients()
    if assigned_user and assigned_user.email:
        recipients.append(assigned_user.email)
    recipients.extend(representative_emails())
    recipients = list(dict.fromkeys(email for email in recipients if email))
    if not recipients:
        return 0
    return send_notification_email(
        subject=f"Tarea asignada en hallazgo {finding.code}",
        message=finding_context_lines(
            finding,
            action_expected=f"Completar la etapa asignada: {phase}.",
            due_at=due_at,
            assigned_user=assigned_user,
            request=request,
        ),
        recipients=recipients,
        notification_settings=notification_settings,
    )


def findings_due_for_24h_alert(now=None):
    now = now or timezone.now()
    window_start = now
    window_end = now + timedelta(hours=24)
    sent_fields = {
        "validation_due_at": "validation_alert_24h_sent",
        "correction_due_at": "correction_alert_24h_sent",
        "correction_review_due_at": "correction_review_alert_24h_sent",
        "corrective_action_due_at": "corrective_action_alert_24h_sent",
        "corrective_action_review_due_at": "corrective_action_review_alert_24h_sent",
        "verification_due_at": "verification_alert_24h_sent",
    }
    results = []
    for _label, due_field, statuses in active_due_definitions():
        sent_field = sent_fields[due_field]
        query = {
            "status__in": statuses,
            f"{due_field}__gt": window_start,
            f"{due_field}__lte": window_end,
            sent_field: False,
        }
        for finding in Finding.objects.filter(**query):
            results.append((finding, due_field, sent_field))
    return results


def findings_overdue_for_alert(now=None):
    now = now or timezone.now()
    sent_fields = {
        "validation_due_at": "validation_overdue_alert_sent",
        "correction_due_at": "correction_overdue_alert_sent",
        "correction_review_due_at": "correction_review_overdue_alert_sent",
        "corrective_action_due_at": "corrective_action_overdue_alert_sent",
        "corrective_action_review_due_at": "corrective_action_review_overdue_alert_sent",
        "verification_due_at": "verification_overdue_alert_sent",
    }
    results = []
    for _label, due_field, statuses in active_due_definitions():
        sent_field = sent_fields[due_field]
        query = {
            "status__in": statuses,
            f"{due_field}__lt": now,
            sent_field: False,
        }
        for finding in Finding.objects.filter(**query):
            results.append((finding, due_field, sent_field))
    return results
