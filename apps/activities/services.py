from datetime import timedelta

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.core.models import NotificationSettings
from apps.findings.services import send_notification_email

from .models import Activity


def _absolute_activity_url(activity):
    settings = NotificationSettings.current()
    path = reverse("activities:detail", args=[activity.pk])
    if settings.site_base_url:
        return f"{settings.site_base_url.rstrip('/')}{path}"
    return path


def _user_email(user):
    return getattr(user, "email", "") if user else ""


def activity_email_body(activity, title, action, due_at=None):
    due_at = due_at or activity.next_due_at
    due = timezone.localtime(due_at).strftime("%d-%m-%Y %H:%M") if due_at else "Sin plazo definido"
    return (
        f"{title}\n\n"
        f"Codigo: {activity.code}\n"
        f"Actividad: {activity.title}\n"
        f"Origen: {activity.origin_label}\n"
        f"Estado actual: {activity.get_status_display()}\n"
        f"Responsables: {activity.responsible_names or '-'}\n"
        f"Plazo proximo: {due}\n\n"
        f"Accion requerida: {action}\n\n"
        f"Descripcion:\n{activity.description}\n\n"
        f"Ver actividad: {_absolute_activity_url(activity)}\n\n"
        "Este correo fue generado automaticamente por el Portal SGC."
    )


def notify_activity_assignment(activity):
    recipients = {email for email in (_user_email(user) for user in activity.responsible_users.all()) if email}
    if not recipients and activity.assigned_to:
        recipients.add(_user_email(activity.assigned_to))
    recipients.discard("")
    if not recipients:
        return
    send_notification_email(
        subject=f"Actividad SGC asignada: {activity.code}",
        message=activity_email_body(activity, "Actividad SGC asignada", "Registrar avances y resultado en la plataforma."),
        recipients=sorted(recipients),
    )


def notify_activity_review_assignment(activity):
    recipient = _user_email(activity.review_assigned_to)
    if not recipient:
        return
    send_notification_email(
        subject=f"Revision de actividad SGC asignada: {activity.code}",
        message=activity_email_body(activity, "Revision final asignada", "Revisar el resultado informado y aprobar el cierre o devolver a tratamiento."),
        recipients=[recipient],
    )


def notify_activity_returned(activity):
    recipients = {email for email in (_user_email(user) for user in activity.responsible_users.all()) if email}
    if not recipients and activity.assigned_to:
        recipients.add(_user_email(activity.assigned_to))
    recipients.discard("")
    if not recipients:
        return
    send_notification_email(
        subject=f"Actividad SGC devuelta a tratamiento: {activity.code}",
        message=activity_email_body(activity, "Actividad devuelta a tratamiento", "Revisar las observaciones y actualizar el resultado."),
        recipients=sorted(recipients),
    )


def activities_due_for_review_alert(now=None):
    now = now or timezone.now()
    return Activity.objects.filter(
        status=Activity.Status.REVIEW_ASSIGNED,
        review_assigned_to__isnull=False,
        review_due_at__gt=now,
        review_due_at__lte=now + timedelta(hours=24),
        review_alert_24h_sent=False,
    ).select_related("review_assigned_to")


def activities_overdue_for_review_alert(now=None):
    now = now or timezone.now()
    return Activity.objects.filter(
        status=Activity.Status.REVIEW_ASSIGNED,
        review_assigned_to__isnull=False,
        review_due_at__lt=now,
        review_overdue_alert_sent=False,
    ).select_related("review_assigned_to")


def activities_due_for_delivery_alert(now=None):
    now = now or timezone.now()
    return Activity.objects.filter(
        status__in=[Activity.Status.ASSIGNED, Activity.Status.IN_PROGRESS, Activity.Status.RETURNED],
        delivery_due_at__gt=now,
        delivery_due_at__lte=now + timedelta(hours=24),
        delivery_alert_24h_sent=False,
    ).prefetch_related("responsible_users").select_related("assigned_to")


def activities_overdue_for_delivery_alert(now=None):
    now = now or timezone.now()
    return Activity.objects.filter(
        status__in=[Activity.Status.ASSIGNED, Activity.Status.IN_PROGRESS, Activity.Status.RETURNED],
        delivery_due_at__lt=now,
        delivery_overdue_alert_sent=False,
    ).prefetch_related("responsible_users").select_related("assigned_to")


def activity_responsible_emails(activity):
    recipients = {_user_email(user) for user in activity.responsible_users.all()}
    if not recipients and activity.assigned_to:
        recipients.add(_user_email(activity.assigned_to))
    recipients.discard("")
    return sorted(recipients)


def activity_notifications_for_user(user, limit=4):
    if not user.is_authenticated:
        return []
    assigned = Activity.objects.filter(
        Q(assigned_to=user) | Q(responsible_users=user),
        status__in=[Activity.Status.ASSIGNED, Activity.Status.IN_PROGRESS, Activity.Status.RETURNED],
    ).distinct()
    reviews = Activity.objects.filter(
        review_assigned_to=user,
        status=Activity.Status.REVIEW_ASSIGNED,
    )
    items = []
    for activity in assigned.order_by("delivery_due_at", "-created_at")[:limit]:
        items.append(_notification_item(activity, "Completar actividad", "Actividad"))
    remaining = max(limit - len(items), 0)
    for activity in reviews.order_by("review_due_at", "-created_at")[:remaining]:
        items.append(_notification_item(activity, "Revisar y cerrar", "Revision"))
    return items


def _notification_item(activity, action, kind):
    due = ""
    if activity.next_due_at:
        due = f"Plazo: {activity.next_due_at:%d-%m %H:%M}"
    return {
        "code": activity.code,
        "description": activity.title,
        "action": action,
        "due": due,
        "url": reverse("activities:detail", args=[activity.pk]),
        "kind": kind,
    }
