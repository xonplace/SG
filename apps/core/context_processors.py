from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.utils import timezone

from .models import CompanyProfile, TrainingAssignment, TrainingAttempt, TrainingCompletion
from apps.findings.models import Finding
from apps.findings.permissions import (
    can_create_findings,
    can_manage_certificates,
    can_manage_documents,
    can_manage_forms,
    can_manage_important_dates,
    can_manage_processes,
    can_manage_sgc_content,
    can_manage_sgc_identity,
    can_manage_updates,
    can_manage_users,
    can_create_activities,
    can_manage_activities,
    can_view_documents,
    can_view_findings,
    can_view_activities,
    can_view_reports,
    is_administrator,
    is_representative,
)
from apps.findings.services import active_due_dates_for
from apps.findings.views import tasks_for_user_queryset
from apps.sgc.models import DocumentType, PublicationStatus, SgcDocument, SgcImportantDates, SgcUpdate


CONTROLLED_DOCUMENT_TYPES = {
    DocumentType.PROCEDURE,
    DocumentType.FORM,
    DocumentType.INSTRUCTION,
    DocumentType.RECORD,
    DocumentType.POLICY,
    DocumentType.MANUAL,
    "diagrama-flujo",
    "diagrama-de-flujo",
    "documento-interno",
}


def _notification_action_label(finding, representative_task=False):
    improvement = finding.classification == Finding.Classification.OPORTUNIDAD_MEJORA
    if representative_task:
        labels = {
            Finding.Status.INGRESADO: "Validar hallazgo",
            Finding.Status.EN_VALIDACION: "Validar hallazgo",
            Finding.Status.CLASIFICADO: "Asignar oportunidad de mejora" if improvement else "Asignar correccion",
            Finding.Status.CORRECCION_EN_REVISION: "Revisar correccion",
            Finding.Status.CORRECCION_APROBADA: "Asignar accion correctiva",
            Finding.Status.ACCION_CORRECTIVA_EN_REVISION: "Revisar plan de accion" if improvement else "Revisar accion correctiva",
            Finding.Status.ACCION_CORRECTIVA_APROBADA: "Asignar seguimiento",
            Finding.Status.SEGUIMIENTO_EN_REVISION: "Revisar seguimiento",
        }
        return labels.get(finding.status, "Pendiente RG")

    labels = {
        Finding.Status.CORRECCION_ASIGNADA: "Registrar correccion",
        Finding.Status.EN_CORRECCION: "Registrar correccion",
        Finding.Status.ACCION_CORRECTIVA_ASIGNADA: "Registrar plan de accion" if improvement else "Registrar accion correctiva",
        Finding.Status.EN_ACCION_CORRECTIVA: "Registrar plan de accion" if improvement else "Registrar accion correctiva",
        Finding.Status.SEGUIMIENTO_ASIGNADO: "Registrar seguimiento",
        Finding.Status.EN_SEGUIMIENTO: "Registrar seguimiento",
    }
    return labels.get(finding.status, "Tarea asignada")


def _notification_due_label(finding):
    due_dates = active_due_dates_for(finding)
    if not due_dates:
        return ""
    _label, due_at = min(due_dates, key=lambda item: item[1])
    local_due = timezone.localtime(due_at)
    prefix = "Vencido" if due_at < timezone.now() else "Plazo"
    return f"{prefix}: {local_due:%d-%m %H:%M}"


def _topbar_notifications(user):
    if not user.is_authenticated:
        return {"items": [], "count": 0, "has_more": False}

    queryset = tasks_for_user_queryset(user)
    finding_total = queryset.count()
    representative_statuses = {
        Finding.Status.INGRESADO,
        Finding.Status.EN_VALIDACION,
        Finding.Status.CLASIFICADO,
        Finding.Status.CORRECCION_EN_REVISION,
        Finding.Status.CORRECCION_APROBADA,
        Finding.Status.ACCION_CORRECTIVA_EN_REVISION,
        Finding.Status.ACCION_CORRECTIVA_APROBADA,
        Finding.Status.SEGUIMIENTO_EN_REVISION,
    }
    items = []
    findings = list(queryset.order_by("-created_at")[:6])
    for finding in findings:
        representative_task = is_representative(user) and finding.status in representative_statuses
        items.append(
            {
                "code": finding.code,
                "description": finding.description,
                "action": _notification_action_label(finding, representative_task=representative_task),
                "due": _notification_due_label(finding),
                "url": reverse("findings:detail", args=[finding.pk]),
                "kind": "RG" if representative_task else "Tarea",
            }
        )

    activity_items = _activity_notifications(user)
    training_items = _training_assignment_notifications(user)
    document_items = _document_control_notifications(user)
    date_items = _important_date_notifications()
    update_items = _update_notifications()
    secondary_items = [*activity_items, *training_items, *document_items, *date_items, *update_items]
    available_slots = max(8 - len(items), 0)
    items.extend(secondary_items[:available_slots])
    total = finding_total + len(secondary_items)
    return {"items": items, "count": total, "has_more": total > len(items)}


def _activity_notifications(user):
    try:
        from apps.activities.services import activity_notifications_for_user
    except Exception:
        return []
    return activity_notifications_for_user(user)


def _training_is_completed(user, content):
    questions = content.questions.filter(is_active=True)
    if questions.exists():
        attempts = TrainingAttempt.objects.filter(user=user, content=content, passed=True)
        return any(attempt.percentage >= content.passing_percentage for attempt in attempts)
    return TrainingCompletion.objects.filter(user=user, content=content).exists()


def _training_assignment_notifications(user):
    today = timezone.localdate()
    assignments = (
        TrainingAssignment.objects.filter(
            user=user,
            content__is_active=True,
            content__show_on_training=True,
        )
        .select_related("content")
        .order_by("due_date", "-assigned_at")
    )
    items = []
    for assignment in assignments:
        if _training_is_completed(user, assignment.content):
            continue
        due = ""
        if assignment.due_date:
            due = "Vencida" if assignment.due_date < today else f"Limite: {assignment.due_date:%d-%m-%Y}"
        items.append(
            {
                "code": "CAP",
                "description": assignment.content.title,
                "action": "Capacitacion asignada",
                "due": due,
                "url": reverse("sgc:training_detail", args=[assignment.content.pk]),
                "kind": "Capacitacion",
            }
        )
        if len(items) >= 4:
            break
    return items


def _important_date_notifications():
    dates = SgcImportantDates.current()
    today = timezone.localdate()
    limit = today + timedelta(days=30)
    candidates = [
        ("FECHA", "Auditoria interna", dates.internal_audit_date),
        ("FECHA", "Auditoria externa", dates.external_audit_date),
        ("FECHA", "Revision por la gerencia", dates.management_review_date),
    ]
    items = []
    for code, action, date_value in candidates:
        if date_value and today <= date_value <= limit:
            days = (date_value - today).days
            items.append(
                {
                    "code": code,
                    "description": f"{action} programada para el {date_value:%d-%m-%Y}.",
                    "action": action,
                    "due": "Hoy" if days == 0 else f"En {days} dias",
                    "url": reverse("sgc:home"),
                    "kind": "Calendario",
                }
            )
    return items


def _update_notifications():
    recent_threshold = timezone.now() - timedelta(days=7)
    updates = SgcUpdate.objects.filter(is_published=True, published_at__gte=recent_threshold)[:3]
    return [
        {
            "code": "COM",
            "description": update.title,
            "action": "Comunicado reciente",
            "due": timezone.localtime(update.published_at).strftime("%d-%m %H:%M"),
            "url": reverse("sgc:updates"),
            "kind": "Comunicado",
        }
        for update in updates
    ]


def _document_control_notifications(user):
    if not can_manage_documents(user):
        return []

    published = SgcDocument.objects.filter(status=PublicationStatus.PUBLISHED)
    controlled = published.filter(document_type__in=CONTROLLED_DOCUMENT_TYPES)
    control_url = reverse("sgc:document_control_dashboard")
    obsolete_url = reverse("sgc:obsolete_documents")
    recent_threshold = timezone.now() - timedelta(days=7)

    missing_code = controlled.filter(code="").count()
    missing_version = controlled.filter(version="").count()
    missing_effective_date = published.filter(effective_date__isnull=True).count()
    unclassified = published.filter(document_type=DocumentType.OTHER).count()
    duplicate_groups = (
        published.exclude(identity_key="")
        .values("identity_key")
        .annotate(total=models.Count("pk"))
        .filter(total__gt=1)
        .count()
    )
    recent_obsolete = SgcDocument.objects.filter(
        status=PublicationStatus.OBSOLETE,
        obsolete_at__gte=recent_threshold,
    ).count()

    alerts = []
    if missing_code:
        alerts.append(
            {
                "code": "DOC",
                "description": f"{missing_code} documento(s) controlado(s) no tienen codigo registrado.",
                "action": "Completar codigos",
                "due": "",
                "url": control_url,
                "kind": "Control",
            }
        )
    if missing_version:
        alerts.append(
            {
                "code": "DOC",
                "description": f"{missing_version} documento(s) controlado(s) no tienen version registrada.",
                "action": "Completar versiones",
                "due": "",
                "url": control_url,
                "kind": "Control",
            }
        )
    if missing_effective_date:
        alerts.append(
            {
                "code": "DOC",
                "description": f"{missing_effective_date} documento(s) no tienen fecha de vigencia.",
                "action": "Revisar vigencias",
                "due": "",
                "url": control_url,
                "kind": "Control",
            }
        )
    if unclassified:
        alerts.append(
            {
                "code": "DOC",
                "description": f"{unclassified} documento(s) siguen clasificados como Otro.",
                "action": "Clasificar documentos",
                "due": "",
                "url": control_url,
                "kind": "Control",
            }
        )
    if duplicate_groups:
        alerts.append(
            {
                "code": "DOC",
                "description": f"{duplicate_groups} familia(s) documental(es) tienen mas de un documento vigente.",
                "action": "Revisar duplicados",
                "due": "",
                "url": control_url,
                "kind": "Control",
            }
        )
    if recent_obsolete:
        alerts.append(
            {
                "code": "DOC",
                "description": f"{recent_obsolete} documento(s) fueron enviados a obsoletos en los ultimos 7 dias.",
                "action": "Obsoletos recientes",
                "due": "",
                "url": obsolete_url,
                "kind": "Obsoleto",
            }
        )
    return alerts


def company_profile(request):
    company = CompanyProfile.current()
    notifications = _topbar_notifications(request.user)
    return {
        "company": company,
        "default_authenticated_url": "findings:list"
        if company.show_findings_module and not company.show_sgc_menu and not company.show_training_module
        else "sgc:home",
        "can_manage_system": is_administrator(request.user),
        "can_manage_users": can_manage_users(request.user),
        "can_manage_sgc_content": can_manage_sgc_content(request.user),
        "can_manage_sgc_dates": can_manage_important_dates(request.user),
        "can_manage_sgc_documents": can_manage_documents(request.user),
        "can_manage_sgc_certificates": can_manage_certificates(request.user),
        "can_manage_sgc_updates": can_manage_updates(request.user),
        "can_manage_sgc_identity": can_manage_sgc_identity(request.user),
        "can_manage_sgc_forms": can_manage_forms(request.user),
        "can_manage_sgc_processes": can_manage_processes(request.user),
        "can_highlight_sgc_update": can_manage_updates(request.user),
        "can_view_sgc_documents": can_view_documents(request.user),
        "can_create_findings": can_create_findings(request.user),
        "can_view_findings": can_view_findings(request.user),
        "can_view_activities": can_view_activities(request.user),
        "can_create_activities": can_create_activities(request.user),
        "can_manage_activities": can_manage_activities(request.user),
        "can_view_reports": can_view_reports(request.user),
        "topbar_notifications": notifications,
    }
