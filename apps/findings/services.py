from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

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


def notify_new_finding(finding):
    recipients = []
    if settings.REPRESENTANTE_GERENCIA_EMAIL:
        recipients.append(settings.REPRESENTANTE_GERENCIA_EMAIL)
    recipients = [email for email in recipients if email]
    if not recipients:
        return 0
    return send_mail(
        subject=f"Nuevo hallazgo {finding.code}",
        message=(
            f"Se registro el hallazgo {finding.code}.\n\n"
            f"Descripcion: {finding.description}\n\n"
            f"Informado por: {finding.reported_by_name}\n"
            f"Fuente: {finding.get_source_display()}\n"
            f"Estado: {display_status_label(finding)}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=True,
    )


def notify_representative(subject, message):
    if not settings.REPRESENTANTE_GERENCIA_EMAIL:
        return 0
    return send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.REPRESENTANTE_GERENCIA_EMAIL],
        fail_silently=True,
    )


def notify_assignment(finding, assigned_user, phase):
    recipients = []
    if assigned_user and assigned_user.email:
        recipients.append(assigned_user.email)
    if settings.REPRESENTANTE_GERENCIA_EMAIL:
        recipients.append(settings.REPRESENTANTE_GERENCIA_EMAIL)
    if not recipients:
        return 0
    return send_mail(
        subject=f"Asignacion de {phase}: {finding.code}",
        message=(
            f"Se asigno la fase {phase} del hallazgo {finding.code}.\n\n"
            f"Descripcion: {finding.description}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=True,
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
