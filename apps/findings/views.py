import csv
from datetime import timedelta
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import (
    CorrectionAssignForm,
    CorrectionReviewForm,
    CorrectionSubmitForm,
    CorrectiveActionAssignForm,
    CorrectiveActionReviewForm,
    CorrectiveActionSubmitForm,
    EvidenceUploadForm,
    FindingCreateForm,
    FindingValidationForm,
    ImprovementPlanReviewForm,
    ImprovementPlanSubmitForm,
    VerificationAssignForm,
    VerificationReviewForm,
    VerificationSubmitForm,
)
from .models import Correction, CorrectiveAction, DeadlineSetting, EffectivenessVerification, Evidence, Finding
from .permissions import assigned_or_representative, can_view_findings, is_representative, role_required
from .services import active_due_dates_for, active_due_query, due_at_from_business_days, notify_assignment, notify_new_finding, notify_representative, record_history


def action_available(finding, user, action):
    representative = is_representative(user)
    if action == "upload_evidence":
        return can_upload_evidence(finding, user)
    if action == "validate":
        return representative and finding.status in {Finding.Status.INGRESADO, Finding.Status.EN_VALIDACION}
    if action == "assign_correction":
        return (
            representative
            and finding.status == Finding.Status.CLASIFICADO
            and not is_improvement_opportunity(finding)
        )
    if action == "submit_correction":
        correction = related_or_none(finding, "correction")
        return (
            finding.status
            in {
                Finding.Status.CORRECCION_ASIGNADA,
                Finding.Status.EN_CORRECCION,
                Finding.Status.EN_ACCION_CORRECTIVA,
                Finding.Status.ACCION_CORRECTIVA_ASIGNADA,
            }
            and correction
            and (not correction.submitted_at or correction.is_conform is False)
            and assigned_or_representative(user, correction.assigned_to)
        )
    if action == "review_correction":
        correction = related_or_none(finding, "correction")
        return (
            representative
            and finding.status in {Finding.Status.CORRECCION_EN_REVISION, Finding.Status.ACCION_CORRECTIVA_EN_REVISION}
            and correction
            and correction.submitted_at
            and correction.is_conform is not True
        )
    if action == "assign_corrective_action":
        if is_improvement_opportunity(finding):
            return representative and finding.status == Finding.Status.CLASIFICADO
        return False
    if action == "submit_corrective_action":
        corrective_action = related_or_none(finding, "corrective_action")
        return (
            finding.status
            in {
                Finding.Status.CORRECCION_ASIGNADA,
                Finding.Status.EN_CORRECCION,
                Finding.Status.EN_ACCION_CORRECTIVA,
                Finding.Status.ACCION_CORRECTIVA_ASIGNADA,
            }
            and corrective_action
            and (not corrective_action.submitted_at or corrective_action.is_conform is False)
            and assigned_or_representative(user, corrective_action.assigned_to)
        )
    if action == "review_corrective_action":
        corrective_action = related_or_none(finding, "corrective_action")
        return (
            representative
            and finding.status == Finding.Status.ACCION_CORRECTIVA_EN_REVISION
            and corrective_action
            and corrective_action.submitted_at
            and corrective_action.is_conform is not True
        )
    if action == "assign_verification":
        return representative and finding.status == Finding.Status.ACCION_CORRECTIVA_APROBADA
    if action == "submit_verification":
        return (
            finding.status in {Finding.Status.SEGUIMIENTO_ASIGNADO, Finding.Status.EN_SEGUIMIENTO}
            and hasattr(finding, "effectiveness_verification")
            and assigned_or_representative(user, finding.effectiveness_verification.assigned_to)
        )
    if action == "review_verification":
        return (
            representative
            and finding.status == Finding.Status.SEGUIMIENTO_EN_REVISION
            and hasattr(finding, "effectiveness_verification")
        )
    return False


def is_improvement_opportunity(finding):
    return finding.is_improvement_classification


def finding_actions(finding, user):
    improvement = is_improvement_opportunity(finding)
    action_labels = {
        "validate": "Validar",
        "assign_correction": "Asignar responsable de Correccion y Accion Correctiva",
        "submit_correction": "Registrar correccion",
        "review_correction": "Revisar correccion",
        "assign_corrective_action": "Asignar oportunidad de mejora" if improvement else "Asignar accion correctiva",
        "submit_corrective_action": "Registrar plan de accion" if improvement else "Registrar accion correctiva",
        "review_corrective_action": "Revisar plan de accion" if improvement else "Revisar accion correctiva",
        "assign_verification": "Asignar seguimiento",
        "submit_verification": "Registrar seguimiento",
        "review_verification": "Revisar seguimiento",
        "upload_evidence": "Cargar evidencia",
    }
    return [
        {"name": name, "label": label, "url": reverse(f"findings:{name}", args=[finding.pk])}
        for name, label in action_labels.items()
        if action_available(finding, user, name)
    ]


def finding_timeline(finding):
    if is_improvement_opportunity(finding):
        steps = [
            {
                "label": "Registro",
                "statuses": {Finding.Status.INGRESADO, Finding.Status.EN_VALIDACION},
            },
            {
                "label": "Validacion",
                "statuses": {Finding.Status.CLASIFICADO, Finding.Status.CERRADO_NO_APLICA},
            },
            {
                "label": "Oportunidad de mejora",
                "statuses": {
                    Finding.Status.ACCION_CORRECTIVA_ASIGNADA,
                    Finding.Status.EN_ACCION_CORRECTIVA,
                    Finding.Status.ACCION_CORRECTIVA_EN_REVISION,
                    Finding.Status.ACCION_CORRECTIVA_APROBADA,
                },
            },
            {
                "label": "Seguimiento",
                "statuses": {
                    Finding.Status.SEGUIMIENTO_ASIGNADO,
                    Finding.Status.EN_SEGUIMIENTO,
                    Finding.Status.SEGUIMIENTO_EN_REVISION,
                },
            },
            {
                "label": "Cierre",
                "statuses": {Finding.Status.CERRADO},
            },
        ]
    else:
        steps = [
            {
                "label": "Registro",
                "statuses": {Finding.Status.INGRESADO, Finding.Status.EN_VALIDACION},
            },
            {
                "label": "Validacion",
                "statuses": {Finding.Status.CLASIFICADO, Finding.Status.CERRADO_NO_APLICA},
            },
            {
                "label": "Correccion",
                "statuses": {
                    Finding.Status.CORRECCION_ASIGNADA,
                    Finding.Status.EN_CORRECCION,
                    Finding.Status.CORRECCION_EN_REVISION,
                    Finding.Status.CORRECCION_APROBADA,
                },
            },
            {
                "label": "Accion correctiva",
                "statuses": {
                    Finding.Status.ACCION_CORRECTIVA_ASIGNADA,
                    Finding.Status.EN_ACCION_CORRECTIVA,
                    Finding.Status.ACCION_CORRECTIVA_EN_REVISION,
                    Finding.Status.ACCION_CORRECTIVA_APROBADA,
                },
            },
            {
                "label": "Verificacion",
                "statuses": {
                    Finding.Status.SEGUIMIENTO_ASIGNADO,
                    Finding.Status.EN_SEGUIMIENTO,
                    Finding.Status.SEGUIMIENTO_EN_REVISION,
                },
            },
            {
                "label": "Cierre",
                "statuses": {Finding.Status.CERRADO},
            },
        ]
    current_index = 0
    for index, step in enumerate(steps):
        if finding.status in step["statuses"]:
            current_index = index
            break

    if finding.status == Finding.Status.CERRADO_NO_APLICA:
        current_index = 1

    timeline = []
    for index, step in enumerate(steps):
        if finding.status == Finding.Status.CERRADO_NO_APLICA and index > current_index:
            state = "pending"
        elif index < current_index:
            state = "completed"
        elif index == current_index:
            state = "current"
        else:
            state = "pending"
        timeline.append({"label": step["label"], "state": state})
    return timeline


def evidence_stage_groups(finding):
    correction = related_or_none(finding, "correction")
    corrective_action = related_or_none(finding, "corrective_action")
    verification = related_or_none(finding, "effectiveness_verification")
    evidences = list(finding.evidences.select_related("uploaded_by", "correction", "corrective_action", "verification"))
    action_stage_title = "Plan de accion" if is_improvement_opportunity(finding) else "Accion correctiva"
    action_stage_description = (
        "Evidencias de la propuesta e implementacion del plan de accion."
        if is_improvement_opportunity(finding)
        else "Evidencias del analisis de causa raiz y accion correctiva."
    )
    groups = [
        {
            "title": "Hallazgo general",
            "description": "Archivos asociados al registro inicial o antecedentes generales.",
            "items": [evidence for evidence in evidences if not evidence.correction_id and not evidence.corrective_action_id and not evidence.verification_id],
        },
        {
            "title": action_stage_title,
            "description": action_stage_description,
            "items": [evidence for evidence in evidences if corrective_action and evidence.corrective_action_id == corrective_action.id],
        },
        {
            "title": "Verificacion de eficacia",
            "description": "Evidencias del seguimiento y medicion de eficacia.",
            "items": [evidence for evidence in evidences if verification and evidence.verification_id == verification.id],
        },
    ]
    if not is_improvement_opportunity(finding):
        groups.insert(
            1,
            {
                "title": "Correccion",
                "description": "Evidencias del tratamiento de la correccion inmediata.",
                "items": [evidence for evidence in evidences if correction and evidence.correction_id == correction.id],
            },
        )
    return groups


def can_upload_evidence(finding, user, phase=None):
    if not user.is_authenticated:
        return False
    if is_representative(user):
        return True

    phase = phase or detected_evidence_phase(finding)
    if phase == EvidenceUploadForm.PHASE_GENERAL:
        return False
    if phase == EvidenceUploadForm.PHASE_CORRECTION:
        correction = related_or_none(finding, "correction")
        return bool(
            correction
            and finding.status in {Finding.Status.CORRECCION_ASIGNADA, Finding.Status.EN_CORRECCION}
            and assigned_or_representative(user, correction.assigned_to)
        )
    if phase == EvidenceUploadForm.PHASE_CORRECTIVE_ACTION:
        corrective_action = related_or_none(finding, "corrective_action")
        return bool(
            corrective_action
            and finding.status in {Finding.Status.ACCION_CORRECTIVA_ASIGNADA, Finding.Status.EN_ACCION_CORRECTIVA}
            and assigned_or_representative(user, corrective_action.assigned_to)
        )
    if phase == EvidenceUploadForm.PHASE_VERIFICATION:
        verification = related_or_none(finding, "effectiveness_verification")
        return bool(
            verification
            and finding.status in {Finding.Status.SEGUIMIENTO_ASIGNADO, Finding.Status.EN_SEGUIMIENTO}
            and assigned_or_representative(user, verification.assigned_to)
        )
    return False


def detected_evidence_phase(finding):
    if finding.status in {
        Finding.Status.CORRECCION_ASIGNADA,
        Finding.Status.EN_CORRECCION,
        Finding.Status.CORRECCION_EN_REVISION,
        Finding.Status.CORRECCION_APROBADA,
    }:
        return EvidenceUploadForm.PHASE_CORRECTION
    if finding.status in {
        Finding.Status.ACCION_CORRECTIVA_ASIGNADA,
        Finding.Status.EN_ACCION_CORRECTIVA,
        Finding.Status.ACCION_CORRECTIVA_EN_REVISION,
        Finding.Status.ACCION_CORRECTIVA_APROBADA,
    }:
        return EvidenceUploadForm.PHASE_CORRECTIVE_ACTION
    if finding.status in {
        Finding.Status.SEGUIMIENTO_ASIGNADO,
        Finding.Status.EN_SEGUIMIENTO,
        Finding.Status.SEGUIMIENTO_EN_REVISION,
        Finding.Status.CERRADO,
    }:
        return EvidenceUploadForm.PHASE_VERIFICATION
    return EvidenceUploadForm.PHASE_GENERAL


def ensure_action_available(request, finding, action):
    if action_available(finding, request.user, action):
        return True
    messages.error(request, "Esta accion no esta disponible para el estado actual del hallazgo.")
    return False


def representative_pending_query():
    return (
        Q(status__in=[Finding.Status.INGRESADO, Finding.Status.EN_VALIDACION])
        | Q(status=Finding.Status.CLASIFICADO)
        | Q(status=Finding.Status.CORRECCION_EN_REVISION)
        | Q(status=Finding.Status.CORRECCION_APROBADA)
        | Q(status=Finding.Status.ACCION_CORRECTIVA_EN_REVISION)
        | Q(status=Finding.Status.ACCION_CORRECTIVA_APROBADA)
        | Q(status=Finding.Status.SEGUIMIENTO_EN_REVISION)
    )


def representative_pending_queryset():
    return Finding.objects.filter(representative_pending_query())


def assigned_to_user_query(user):
    return (
        Q(
            correction__assigned_to=user,
            status__in=[Finding.Status.CORRECCION_ASIGNADA, Finding.Status.EN_CORRECCION],
        )
        | Q(
            corrective_action__assigned_to=user,
            status__in=[Finding.Status.ACCION_CORRECTIVA_ASIGNADA, Finding.Status.EN_ACCION_CORRECTIVA],
        )
        | Q(
            effectiveness_verification__assigned_to=user,
            status__in=[Finding.Status.SEGUIMIENTO_ASIGNADO, Finding.Status.EN_SEGUIMIENTO],
        )
    )


def assigned_to_user_queryset(user):
    return Finding.objects.filter(assigned_to_user_query(user)).distinct()


def tasks_for_user_queryset(user):
    query = assigned_to_user_query(user)
    if is_representative(user):
        query |= representative_pending_query()
    return Finding.objects.filter(query).distinct()


def due_queryset():
    now = timezone.now()
    soon = now + timedelta(hours=24)
    return Finding.objects.filter(active_due_query(soon))


def next_due_for(finding):
    due_dates = active_due_dates_for(finding)
    if due_dates:
        label, due_at = min(due_dates, key=lambda item: item[1])
        local_due = timezone.localtime(due_at)
        return f"{short_due_label(label)}: {local_due:%d-%m %H:%M}"
    return pending_milestone_label(finding)


def next_due_state_for(finding):
    due_dates = [due_at for _label, due_at in active_due_dates_for(finding)]
    if not due_dates:
        return ""
    next_due = min(due_dates)
    now = timezone.now()
    if next_due < now:
        return "overdue"
    if next_due <= now + timedelta(hours=24):
        return "soon"
    return ""


def pending_milestone_label(finding):
    if finding.is_closed:
        return ""
    improvement = is_improvement_opportunity(finding)
    labels = {
        Finding.Status.CLASIFICADO: "Asignar OM" if improvement else "Asignar responsable de Correccion y Accion Correctiva",
        Finding.Status.CORRECCION_APROBADA: "Asignar accion correctiva",
        Finding.Status.ACCION_CORRECTIVA_APROBADA: "Asignar seguimiento",
        Finding.Status.SEGUIMIENTO_EN_REVISION: "Revisar seguimiento",
    }
    return labels.get(finding.status, "")


def correction_was_observed(finding):
    correction = related_or_none(finding, "correction")
    return finding.status == Finding.Status.EN_CORRECCION and correction and correction.is_conform is False


def corrective_action_was_observed(finding):
    action = related_or_none(finding, "corrective_action")
    return finding.status == Finding.Status.EN_ACCION_CORRECTIVA and action and action.is_conform is False


def verification_was_not_effective(finding):
    verification = related_or_none(finding, "effectiveness_verification")
    return finding.status == Finding.Status.EN_ACCION_CORRECTIVA and verification and verification.is_effective is False


def stage_was_returned(finding):
    return correction_was_observed(finding) or corrective_action_was_observed(finding) or verification_was_not_effective(finding)


def short_due_label(label):
    labels = {
        "Validacion": "Validacion",
        "Correccion": "Correccion",
        "Revision correccion": "Rev. correccion",
        "Accion correctiva": "Accion correctiva",
        "Revision accion correctiva": "Rev. accion",
        "Plan de accion": "Plan accion",
        "Revision plan de accion": "Rev. plan",
        "Verificacion": "Verificacion",
    }
    return labels.get(label, label)


def remaining_time_label(due_at):
    if not due_at:
        return ""
    delta = due_at - timezone.now()
    total_minutes = int(delta.total_seconds() // 60)
    overdue = total_minutes < 0
    total_minutes = abs(total_minutes)
    days = total_minutes // (60 * 24)
    hours = (total_minutes % (60 * 24)) // 60
    minutes = total_minutes % 60
    if days:
        text = f"{days} dias y {hours} horas"
    elif hours:
        text = f"{hours} horas y {minutes} minutos"
    else:
        text = f"{minutes} minutos"
    return f"Vencido hace {text}" if overdue else f"Quedan {text}"


def status_badge_class(finding):
    if finding.status in {Finding.Status.CERRADO, Finding.Status.CERRADO_NO_APLICA}:
        return "sg-badge-neutral"
    if stage_was_returned(finding):
        return "sg-badge-attention"
    if finding.status in {
        Finding.Status.CORRECCION_EN_REVISION,
        Finding.Status.ACCION_CORRECTIVA_EN_REVISION,
        Finding.Status.SEGUIMIENTO_EN_REVISION,
    }:
        return "sg-badge-attention"
    if finding.status in {
        Finding.Status.CORRECCION_ASIGNADA,
        Finding.Status.EN_CORRECCION,
        Finding.Status.ACCION_CORRECTIVA_ASIGNADA,
        Finding.Status.EN_ACCION_CORRECTIVA,
        Finding.Status.SEGUIMIENTO_ASIGNADO,
        Finding.Status.EN_SEGUIMIENTO,
    }:
        return "sg-badge-progress"
    return "sg-badge-pending"


def display_status_label(finding):
    if correction_was_observed(finding):
        return "Correccion observada"
    if verification_was_not_effective(finding):
        return "Seguimiento no eficaz - revisar plan de accion" if is_improvement_opportunity(finding) else "Seguimiento no eficaz - revisar accion correctiva"
    if corrective_action_was_observed(finding):
        return "Plan de accion observado" if is_improvement_opportunity(finding) else "Accion correctiva observada"
    if not is_improvement_opportunity(finding):
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


def status_button_style(finding):
    base = (
        "display:inline-flex;align-items:center;justify-content:center;"
        "width:172px;height:38px;border-radius:8px;padding:0.35rem 0.75rem;"
        "font-size:12px;font-weight:600;line-height:1.1;text-align:center;"
        "color:#ffffff;box-shadow:0 1px 2px rgba(15,23,42,.12);"
    )
    if finding.status in {Finding.Status.CERRADO, Finding.Status.CERRADO_NO_APLICA}:
        return base + "background:linear-gradient(135deg,#34d399 0%,#059669 100%);"
    if stage_was_returned(finding):
        return base + "background:linear-gradient(135deg,#fb923c 0%,#dc2626 100%);"
    if finding.status in {Finding.Status.INGRESADO, Finding.Status.EN_VALIDACION}:
        return base + "background:linear-gradient(135deg,#f87171 0%,#dc2626 100%);"
    if finding.status in {Finding.Status.CLASIFICADO, Finding.Status.CORRECCION_ASIGNADA, Finding.Status.EN_CORRECCION}:
        return base + "background:linear-gradient(135deg,#fb923c 0%,#f97316 100%);"
    if finding.status in {
        Finding.Status.CORRECCION_EN_REVISION,
        Finding.Status.ACCION_CORRECTIVA_EN_REVISION,
    }:
        return base + "background:linear-gradient(135deg,#fde047 0%,#f59e0b 100%);color:#111827;"
    if finding.status in {
        Finding.Status.CORRECCION_APROBADA,
        Finding.Status.ACCION_CORRECTIVA_APROBADA,
        Finding.Status.SEGUIMIENTO_ASIGNADO,
        Finding.Status.EN_SEGUIMIENTO,
        Finding.Status.SEGUIMIENTO_EN_REVISION,
    }:
        return base + "background:linear-gradient(135deg,#86efac 0%,#22c55e 100%);"
    if finding.status in {
        Finding.Status.ACCION_CORRECTIVA_ASIGNADA,
        Finding.Status.EN_ACCION_CORRECTIVA,
    }:
        return base + "background:linear-gradient(135deg,#facc15 0%,#eab308 100%);color:#111827;"
    return base + "background:linear-gradient(135deg,#374151 0%,#111827 100%);"


def classification_short_label(finding):
    if finding.classification in {
        Finding.Classification.NO_CONFORMIDAD_MAYOR,
        Finding.Classification.NO_CONFORMIDAD_MENOR,
    }:
        return "NC"
    if finding.classification == Finding.Classification.OPORTUNIDAD_MEJORA:
        return "OM"
    if finding.classification == Finding.Classification.OPORTUNIDAD:
        return "OP"
    return "Pendiente"


def representative_label(finding):
    if finding.representative:
        return user_label(finding.representative)
    return "Representante de la Gerencia"


def assigned_to_label(finding):
    if finding.status in {Finding.Status.CERRADO, Finding.Status.CERRADO_NO_APLICA}:
        return "-"
    if finding.status in {
        Finding.Status.INGRESADO,
        Finding.Status.EN_VALIDACION,
        Finding.Status.CLASIFICADO,
        Finding.Status.CORRECCION_EN_REVISION,
        Finding.Status.CORRECCION_APROBADA,
        Finding.Status.ACCION_CORRECTIVA_EN_REVISION,
        Finding.Status.ACCION_CORRECTIVA_APROBADA,
        Finding.Status.SEGUIMIENTO_EN_REVISION,
    }:
        return representative_label(finding)
    correction = related_or_none(finding, "correction")
    corrective_action = related_or_none(finding, "corrective_action")
    verification = related_or_none(finding, "effectiveness_verification")
    if finding.status in {Finding.Status.CORRECCION_ASIGNADA, Finding.Status.EN_CORRECCION}:
        return user_label(correction.assigned_to) if correction and correction.assigned_to else "-"
    if finding.status in {Finding.Status.ACCION_CORRECTIVA_ASIGNADA, Finding.Status.EN_ACCION_CORRECTIVA}:
        return user_label(corrective_action.assigned_to) if corrective_action and corrective_action.assigned_to else "-"
    if finding.status in {Finding.Status.SEGUIMIENTO_ASIGNADO, Finding.Status.EN_SEGUIMIENTO}:
        return user_label(verification.assigned_to) if verification and verification.assigned_to else "-"
    return representative_label(finding)


def attach_next_due(findings):
    findings = list(findings)
    for finding in findings:
        finding.next_due_label = next_due_for(finding)
        finding.next_due_state = next_due_state_for(finding)
        finding.status_badge_class = status_badge_class(finding)
        finding.status_button_style = status_button_style(finding)
        finding.display_status_label = display_status_label(finding)
        finding.classification_short_label = classification_short_label(finding)
        finding.assigned_to_label = assigned_to_label(finding)
    return findings


def open_status_values():
    return [
        status_value
        for status_value, _label in Finding.Status.choices
        if status_value not in {Finding.Status.CERRADO, Finding.Status.CERRADO_NO_APLICA}
    ]


def filtered_findings(params):
    findings = Finding.objects.all()
    query = params.get("q", "").strip()
    status = params.get("status")
    classification = params.get("classification")
    if query:
        findings = findings.filter(
            Q(code__icontains=query)
            | Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(reported_by_name__icontains=query)
            | Q(area__icontains=query)
            | Q(process__icontains=query)
        )
    if status in {"abiertos", "open"}:
        findings = findings.filter(status__in=open_status_values())
    elif status in {"cerrados", "closed"}:
        findings = findings.filter(status__in=[Finding.Status.CERRADO, Finding.Status.CERRADO_NO_APLICA])
    elif status:
        findings = findings.filter(status=status)
    if classification:
        findings = findings.filter(classification=classification)
    return findings.annotate(
        closed_order=Case(
            When(status__in=[Finding.Status.CERRADO, Finding.Status.CERRADO_NO_APLICA], then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by("closed_order", "-created_at")


def related_or_none(instance, relation_name):
    try:
        return getattr(instance, relation_name)
    except ObjectDoesNotExist:
        return None


def format_datetime(value):
    if not value:
        return ""
    return timezone.localtime(value).strftime("%d-%m-%Y %H:%M")


def format_date(value):
    if not value:
        return ""
    return value.strftime("%d-%m-%Y")


def format_bool(value):
    if value is True:
        return "Si"
    if value is False:
        return "No"
    return "Pendiente"


def user_label(user):
    if not user:
        return ""
    full_name = user.get_full_name()
    return full_name or user.get_username()


def correction_days_for_finding(finding):
    deadlines = DeadlineSetting.current()
    if finding.classification == Finding.Classification.NO_CONFORMIDAD_MAYOR:
        return deadlines.correction_major_days
    if finding.classification == Finding.Classification.NO_CONFORMIDAD_MENOR:
        return deadlines.correction_minor_days
    return deadlines.correction_improvement_days


def ensure_review_deadline(finding):
    deadlines = DeadlineSetting.current()
    update_fields = []
    if (
        finding.status == Finding.Status.CORRECCION_EN_REVISION
        and not finding.correction_review_due_at
        and hasattr(finding, "correction")
        and finding.correction.submitted_at
    ):
        finding.correction_review_due_at = due_at_from_business_days(
            timezone.localtime(finding.correction.submitted_at).date(),
            deadlines.correction_review_days,
        )
        update_fields.append("correction_review_due_at")
    if (
        finding.status == Finding.Status.ACCION_CORRECTIVA_EN_REVISION
        and not finding.corrective_action_review_due_at
        and hasattr(finding, "corrective_action")
        and finding.corrective_action.submitted_at
    ):
        finding.corrective_action_review_due_at = due_at_from_business_days(
            timezone.localtime(finding.corrective_action.submitted_at).date(),
            deadlines.corrective_action_review_days,
        )
        update_fields.append("corrective_action_review_due_at")
    if update_fields:
        finding.save(update_fields=[*update_fields, "updated_at"])


def grouped_counts(field_name, choices=None, empty_label="Sin dato"):
    labels = dict(choices or [])
    rows = Finding.objects.values(field_name).annotate(total=Count("id")).order_by("-total", field_name)
    return [
        {
            "label": labels.get(row[field_name], row[field_name] or empty_label),
            "total": row["total"],
        }
        for row in rows
    ]


def field_counts(field_name, empty_label="Sin dato", limit=10):
    rows = (
        Finding.objects.values(field_name)
        .annotate(total=Count("id"))
        .order_by("-total", field_name)[:limit]
    )
    return [{"label": row[field_name] or empty_label, "total": row["total"]} for row in rows]


def percent(value, total):
    if not total:
        return 0
    return round((value / total) * 100)


def report_rows_with_percent(rows, total, colors=None):
    colors = colors or ["#2271b1", "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6"]
    enriched = []
    for index, row in enumerate(rows):
        enriched.append(
            {
                **row,
                "percent": percent(row["total"], total),
                "color": colors[index % len(colors)],
            }
        )
    return enriched


def stage_distribution(total):
    stage_map = [
        (
            "Registro",
            [Finding.Status.INGRESADO, Finding.Status.EN_VALIDACION],
            "#60a5fa",
        ),
        (
            "Validacion RG",
            [Finding.Status.CLASIFICADO, Finding.Status.CERRADO_NO_APLICA],
            "#818cf8",
        ),
        (
            "Correccion",
            [
                Finding.Status.CORRECCION_ASIGNADA,
                Finding.Status.EN_CORRECCION,
                Finding.Status.CORRECCION_EN_REVISION,
                Finding.Status.CORRECCION_APROBADA,
            ],
            "#f59e0b",
        ),
        (
            "Accion correctiva",
            [
                Finding.Status.ACCION_CORRECTIVA_ASIGNADA,
                Finding.Status.EN_ACCION_CORRECTIVA,
                Finding.Status.ACCION_CORRECTIVA_EN_REVISION,
                Finding.Status.ACCION_CORRECTIVA_APROBADA,
            ],
            "#14b8a6",
        ),
        (
            "Verificacion",
            [
                Finding.Status.SEGUIMIENTO_ASIGNADO,
                Finding.Status.EN_SEGUIMIENTO,
                Finding.Status.SEGUIMIENTO_EN_REVISION,
            ],
            "#22c55e",
        ),
        (
            "Cierre",
            [Finding.Status.CERRADO],
            "#64748b",
        ),
    ]
    return [
        {
            "label": label,
            "total": Finding.objects.filter(status__in=statuses).count(),
            "percent": percent(Finding.objects.filter(status__in=statuses).count(), total),
            "color": color,
        }
        for label, statuses, color in stage_map
    ]


def due_breakdown():
    now = timezone.now()
    soon = now + timedelta(hours=24)
    return {
        "overdue": Finding.objects.filter(active_due_query(now)).distinct().count(),
        "next_24h": Finding.objects.filter(active_due_query(soon)).exclude(active_due_query(now)).distinct().count(),
    }


@role_required(can_view_findings)
def finding_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status")
    classification = request.GET.get("classification")
    if status == "open":
        status = "abiertos"
    elif status == "closed":
        status = "cerrados"
    findings = filtered_findings(request.GET)
    return render(
        request,
        "findings/finding_list.html",
        {
            "findings": attach_next_due(findings),
            "status_choices": Finding.Status.choices,
            "classification_choices": Finding.Classification.choices,
            "query": query,
            "selected_status": status or "",
            "selected_classification": classification or "",
        },
    )


@role_required(can_view_findings)
def export_findings_csv(request):
    findings = filtered_findings(request.GET).select_related(
        "correction__assigned_to",
        "corrective_action__assigned_to",
        "effectiveness_verification__assigned_to",
    )
    filename = f"hallazgos_{timezone.localdate():%Y%m%d}.csv"
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")

    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        [
            "Codigo",
            "Descripcion",
            "Estado",
            "Clasificacion",
            "Fuente",
            "Area",
            "Proceso",
            "Informado por",
            "Correo informante",
            "Fecha deteccion",
            "Fecha registro",
            "Plazo validacion",
            "Responsable correccion",
            "Plazo correccion",
            "Accion correccion",
            "Resultado correccion",
            "Responsable accion correctiva",
            "Plazo accion correctiva",
            "Tecnica analisis",
            "Causa raiz / conclusion",
            "Accion correctiva",
            "Responsable verificacion",
            "Plazo verificacion",
            "Resultado verificacion",
            "Eficaz",
            "Fecha cierre",
        ]
    )

    for finding in findings:
        correction = related_or_none(finding, "correction")
        corrective_action = related_or_none(finding, "corrective_action")
        verification = related_or_none(finding, "effectiveness_verification")
        writer.writerow(
            [
                finding.code,
                finding.description,
                display_status_label(finding),
                finding.get_classification_display() if finding.classification else "",
                finding.source_label,
                finding.area,
                finding.process_label,
                finding.reported_by_name,
                finding.reported_by_email,
                format_date(finding.detection_date),
                format_date(finding.report_date),
                format_datetime(finding.validation_due_at),
                user_label(correction.assigned_to) if correction else "",
                format_datetime(correction.due_at) if correction else "",
                correction.action if correction else "",
                correction.result if correction else "",
                user_label(corrective_action.assigned_to) if corrective_action else "",
                format_datetime(corrective_action.due_at) if corrective_action else "",
                corrective_action.get_analysis_technique_display() if corrective_action and corrective_action.analysis_technique else "",
                corrective_action.conclusion if corrective_action else "",
                corrective_action.action_description if corrective_action else "",
                user_label(verification.assigned_to) if verification else "",
                format_datetime(verification.due_at) if verification else "",
                verification.result if verification else "",
                format_bool(verification.is_effective) if verification else "",
                format_datetime(finding.closed_at),
            ]
        )
    return response


@role_required(is_representative)
def representative_pending(request):
    findings = attach_next_due(representative_pending_queryset())
    return render(
        request,
        "findings/finding_board.html",
        {
            "title": "Pendientes por Representante de la Gerencia",
            "eyebrow": "Bandeja de gestion",
            "description": "Hallazgos que requieren validacion, asignacion, revision o cierre por parte del Representante de la Gerencia.",
            "findings": findings,
            "empty_message": "No hay pendientes para el Representante de la Gerencia.",
        },
    )


@role_required(can_view_findings)
def my_tasks(request):
    findings = attach_next_due(tasks_for_user_queryset(request.user).order_by("-created_at"))
    if is_representative(request.user):
        description = "Tareas asignadas a tu usuario y pendientes que requieren gestion del Representante de la Gerencia."
    else:
        description = "Correcciones, acciones correctivas y verificaciones asignadas a tu usuario."
    return render(
        request,
        "findings/finding_board.html",
        {
            "title": "Mis tareas",
            "eyebrow": "Bandeja personal",
            "description": description,
            "findings": findings,
            "empty_message": "No tienes tareas pendientes.",
        },
    )


@role_required(can_view_findings)
def due_findings(request):
    findings = attach_next_due(due_queryset())
    return render(
        request,
        "findings/finding_board.html",
        {
            "title": "Vencidos / por vencer",
            "eyebrow": "Control de plazos",
            "description": "Hallazgos abiertos con plazos vencidos o próximos a vencer dentro de las próximas 24 horas.",
            "findings": findings,
            "empty_message": "No hay hallazgos vencidos o por vencer dentro de las proximas 24 horas.",
        },
    )


@role_required(can_view_findings)
def reports(request):
    total = Finding.objects.count()
    closed = Finding.objects.filter(status__in=[Finding.Status.CERRADO, Finding.Status.CERRADO_NO_APLICA]).count()
    open_count = Finding.objects.filter(status__in=open_status_values()).count()
    due = due_queryset().count()
    representative_pending = representative_pending_queryset().count()
    by_status = report_rows_with_percent(grouped_counts("status", Finding.Status.choices), total)
    by_classification = report_rows_with_percent(
        grouped_counts("classification", Finding.Classification.choices, empty_label="Pendiente"),
        total,
        colors=["#2563eb", "#f97316", "#10b981", "#94a3b8"],
    )
    by_source = report_rows_with_percent(grouped_counts("source", Finding.Source.choices), total)
    by_area = report_rows_with_percent(field_counts("area", empty_label="Sin area"), total)
    by_process = report_rows_with_percent(field_counts("process", empty_label="Sin proceso"), total)
    due_data = due_breakdown()
    metrics = {
        "total": total,
        "open": open_count,
        "closed": closed,
        "representative_pending": representative_pending,
        "due": due,
        "closed_percent": percent(closed, total),
        "open_percent": percent(open_count, total),
        "due_percent": percent(due, total),
        "representative_pending_percent": percent(representative_pending, total),
    }
    return render(
        request,
        "findings/reports.html",
        {
            "metrics": metrics,
            "by_status": by_status,
            "by_classification": by_classification,
            "by_source": by_source,
            "by_area": by_area,
            "by_process": by_process,
            "stages": stage_distribution(total),
            "due_data": due_data,
        },
    )


def finding_create(request):
    if request.method == "POST":
        form = FindingCreateForm(request.POST, request.FILES)
        if form.is_valid():
            finding = form.save()
            finding.validation_due_at = due_at_from_business_days(
                timezone.localdate(),
                DeadlineSetting.current().validation_days,
            )
            finding.save(update_fields=["validation_due_at", "updated_at"])
            record_history(finding, "Hallazgo ingresado", new_status=finding.status)
            evidence_file = form.cleaned_data.get("evidence_file")
            if evidence_file:
                evidence = Evidence.objects.create(
                    finding=finding,
                    file=evidence_file,
                    description="Evidencia inicial del hallazgo",
                )
                record_history(
                    finding,
                    "Evidencia inicial cargada",
                    previous_status=finding.status,
                    new_status=finding.status,
                    comment=evidence.file.name,
                )
            notify_new_finding(finding, request=request)
            request.session["last_created_finding"] = {
                "code": finding.code,
                "description": finding.description,
                "reported_by_email": finding.reported_by_email,
            }
            return redirect("findings:create_success")
    else:
        form = FindingCreateForm()
    return render(request, "findings/finding_form.html", {"form": form})


def finding_create_success(request):
    finding_data = request.session.pop("last_created_finding", None)
    if not finding_data:
        return redirect("findings:create")
    return render(request, "findings/finding_success.html", {"finding_data": finding_data})


@role_required(can_view_findings)
def finding_detail(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    finding.display_status_label = display_status_label(finding)
    detected_phase = detected_evidence_phase(finding)
    return render(
        request,
        "findings/finding_detail.html",
        {
            "finding": finding,
            "actions": finding_actions(finding, request.user),
            "timeline": finding_timeline(finding),
            "evidence_groups": evidence_stage_groups(finding),
            "can_upload_evidence": can_upload_evidence(finding, request.user, detected_phase),
            "can_delete_finding": request.user.is_superuser,
        },
    )


@login_required
def finding_delete(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied("Solo un superusuario puede eliminar hallazgos definitivamente.")

    finding = get_object_or_404(Finding, pk=pk)
    finding.display_status_label = display_status_label(finding)
    if request.method == "POST":
        code = finding.code
        file_delete_errors = []
        evidence_files = list(finding.evidences.all())
        for evidence in evidence_files:
            if evidence.file:
                try:
                    evidence.file.delete(save=False)
                except OSError:
                    file_delete_errors.append(evidence.file.name)
        finding.delete()
        messages.success(request, f"Hallazgo {code} eliminado definitivamente.")
        if file_delete_errors:
            messages.warning(
                request,
                "El hallazgo fue eliminado, pero algunos archivos fisicos no pudieron borrarse por permisos del servidor.",
            )
        return redirect("findings:list")

    return render(request, "findings/finding_confirm_delete.html", {"finding": finding})


@role_required(can_view_findings)
def upload_evidence(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    phase = request.GET.get("phase") or detected_evidence_phase(finding)
    if not can_upload_evidence(finding, request.user, phase):
        messages.error(request, "Solo el responsable asignado de la etapa o el Representante de la Gerencia puede cargar evidencia.")
        return redirect("findings:detail", pk=finding.pk)
    if request.method == "POST":
        form = EvidenceUploadForm(request.POST, request.FILES, finding=finding, phase=phase)
        if form.is_valid():
            evidence = form.save(commit=False)
            evidence.uploaded_by = request.user if request.user.is_authenticated else None
            evidence.save()
            record_history(
                finding,
                "Evidencia cargada",
                user=request.user if request.user.is_authenticated else None,
                previous_status=finding.status,
                new_status=finding.status,
                comment=evidence.description or evidence.file.name,
            )
            messages.success(request, "Evidencia cargada correctamente.")
            return redirect("findings:detail", pk=finding.pk)
    else:
        form = EvidenceUploadForm(finding=finding, phase=phase)
    return render(
        request,
        "findings/evidence_form.html",
        {
            "finding": finding,
            "form": form,
            "phase_label": form.phase_label,
        },
    )


@role_required(can_view_findings)
def download_evidence(request, pk):
    evidence = get_object_or_404(Evidence, pk=pk)
    try:
        file_handle = evidence.file.open("rb")
    except FileNotFoundError as exc:
        raise Http404("El archivo de evidencia no existe.") from exc
    filename = Path(evidence.file.name).name
    return FileResponse(file_handle, as_attachment=True, filename=filename)


def transition_view(request, pk, title, form_class, instance, on_valid):
    finding = get_object_or_404(Finding, pk=pk)
    ensure_review_deadline(finding)
    if callable(instance):
        instance = instance(finding)
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            on_valid(finding, form)
            messages.success(request, "Etapa actualizada correctamente.")
            return redirect("findings:detail", pk=finding.pk)
    else:
        form = form_class(instance=instance)
    due_dates = [due_at for _label, due_at in active_due_dates_for(finding)]
    return render(
        request,
        "findings/transition_form.html",
        {
            "finding": finding,
            "title": title,
            "form": form,
            "deadline_label": next_due_for(finding),
            "remaining_label": remaining_time_label(min(due_dates, default=None)),
            "evidence_phase": detected_evidence_phase(finding),
        },
    )


@role_required(is_representative)
def validate_finding(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    if not ensure_action_available(request, finding, "validate"):
        return redirect("findings:detail", pk=finding.pk)

    def on_valid(finding, form):
        previous = finding.status
        previous_code = finding.code
        finding = form.save(commit=False)
        if finding.applies_treatment is False:
            finding.status = Finding.Status.CERRADO_NO_APLICA
            finding.closed_at = timezone.now()
        else:
            finding.status = Finding.Status.CLASIFICADO
            finding.assign_classified_code()
        finding.save()
        comment = ""
        if previous_code != finding.code:
            comment = f"Codigo actualizado de {previous_code} a {finding.code}."
        record_history(
            finding,
            "Hallazgo validado",
            user=request.user if request.user.is_authenticated else None,
            previous_status=previous,
            new_status=finding.status,
            comment=comment,
        )

    return transition_view(request, pk, "Validar hallazgo", FindingValidationForm, finding, on_valid)


@role_required(is_representative)
def assign_correction(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    if not ensure_action_available(request, finding, "assign_correction"):
        return redirect("findings:detail", pk=finding.pk)

    def get_instance(finding):
        return getattr(finding, "correction", None) or Correction(finding=finding)

    def on_valid(finding, form):
        previous = finding.status
        correction = form.save(commit=False)
        correction.finding = finding
        correction.assigned_at = timezone.now()
        correction.due_at = due_at_from_business_days(
            timezone.localtime(correction.assigned_at).date(),
            correction_days_for_finding(finding),
        )
        correction.save()
        action, _created = CorrectiveAction.objects.get_or_create(finding=finding)
        action.assigned_to = correction.assigned_to
        action.assigned_at = correction.assigned_at
        action.due_at = due_at_from_business_days(
            timezone.localtime(correction.assigned_at).date(),
            DeadlineSetting.current().corrective_action_days,
        )
        action.save(update_fields=["assigned_to", "assigned_at", "due_at", "updated_at"])
        finding.status = Finding.Status.CORRECCION_ASIGNADA
        finding.correction_due_at = correction.due_at
        finding.corrective_action_due_at = action.due_at
        finding.correction_alert_24h_sent = False
        finding.corrective_action_alert_24h_sent = False
        finding.correction_overdue_alert_sent = False
        finding.corrective_action_overdue_alert_sent = False
        finding.save(
            update_fields=[
                "status",
                "correction_due_at",
                "corrective_action_due_at",
                "correction_alert_24h_sent",
                "corrective_action_alert_24h_sent",
                "correction_overdue_alert_sent",
                "corrective_action_overdue_alert_sent",
                "updated_at",
            ]
        )
        notify_assignment(
            finding,
            correction.assigned_to,
            "tratamiento del hallazgo: correccion y accion correctiva",
            due_at=min(correction.due_at, action.due_at),
            request=request,
        )
        record_history(finding, "Tratamiento asignado", user=request.user if request.user.is_authenticated else None, previous_status=previous, new_status=finding.status)

    return transition_view(request, pk, "Asignar responsable de Correccion y Accion Correctiva", CorrectionAssignForm, get_instance, on_valid)


@login_required
def submit_correction(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    if not ensure_action_available(request, finding, "submit_correction"):
        return redirect("findings:detail", pk=finding.pk)

    def get_instance(finding):
        correction = get_object_or_404(Correction, finding=finding)
        if not assigned_or_representative(request.user, correction.assigned_to):
            raise PermissionDenied
        return correction

    def on_valid(finding, form):
        previous = finding.status
        correction = form.save(commit=False)
        correction.submitted_at = timezone.now()
        correction.save()
        evidence_file = form.cleaned_data.get("evidence_file")
        if evidence_file:
            evidence = Evidence.objects.create(
                finding=finding,
                correction=correction,
                file=evidence_file,
                uploaded_by=request.user if request.user.is_authenticated else None,
                description="Evidencia de la correccion",
            )
        action = related_or_none(finding, "corrective_action")
        finding.status = Finding.Status.ACCION_CORRECTIVA_EN_REVISION if action and action.submitted_at else Finding.Status.EN_ACCION_CORRECTIVA
        finding.correction_review_due_at = due_at_from_business_days(
            timezone.localtime(correction.submitted_at).date(),
            DeadlineSetting.current().correction_review_days,
        )
        finding.correction_review_alert_24h_sent = False
        finding.correction_review_overdue_alert_sent = False
        finding.save(
            update_fields=[
                "status",
                "correction_review_due_at",
                "correction_review_alert_24h_sent",
                "correction_review_overdue_alert_sent",
                "updated_at",
            ]
        )
        notify_representative(
            f"Revision pendiente: correccion {finding.code}",
            finding,
            "Revisar si la correccion aplicada es conforme. Si la accion correctiva ya fue registrada, revisar tambien el plan de accion.",
            due_at=finding.correction_review_due_at,
            submitted_by=request.user if request.user.is_authenticated else None,
            request=request,
        )
        comment = f"Evidencia cargada: {evidence.file.name}" if evidence_file else ""
        record_history(finding, "Correccion enviada a revision", user=request.user if request.user.is_authenticated else None, previous_status=previous, new_status=finding.status, comment=comment)

    return transition_view(request, pk, "Registrar correccion aplicada", CorrectionSubmitForm, get_instance, on_valid)


@role_required(is_representative)
def review_correction(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    if not ensure_action_available(request, finding, "review_correction"):
        return redirect("findings:detail", pk=finding.pk)

    def get_instance(finding):
        return get_object_or_404(Correction, finding=finding)

    def on_valid(finding, form):
        previous = finding.status
        correction = form.save(commit=False)
        correction.reviewed_by = request.user if request.user.is_authenticated else None
        correction.reviewed_at = timezone.now()
        correction.save()
        action = related_or_none(finding, "corrective_action")
        if correction.is_conform:
            finding.status = (
                Finding.Status.ACCION_CORRECTIVA_APROBADA
                if action and action.is_conform is True
                else Finding.Status.ACCION_CORRECTIVA_EN_REVISION
                if action and action.submitted_at
                else Finding.Status.EN_ACCION_CORRECTIVA
            )
            finding.correction_due_at = None
            finding.correction_review_due_at = None
            history_label = "Correccion aprobada"
        else:
            finding.status = Finding.Status.EN_CORRECCION
            finding.correction_due_at = due_at_from_business_days(
                timezone.localdate(),
                correction_days_for_finding(finding),
            )
            finding.correction_review_due_at = None
            finding.correction_alert_24h_sent = False
            finding.correction_review_alert_24h_sent = False
            finding.correction_overdue_alert_sent = False
            finding.correction_review_overdue_alert_sent = False
            history_label = "Correccion observada y devuelta"
        finding.save(
            update_fields=[
                "status",
                "correction_due_at",
                "correction_review_due_at",
                "corrective_action_due_at",
                "corrective_action_review_due_at",
                "correction_alert_24h_sent",
                "correction_review_alert_24h_sent",
                "correction_overdue_alert_sent",
                "correction_review_overdue_alert_sent",
                "updated_at",
            ]
        )
        record_history(finding, history_label, user=request.user if request.user.is_authenticated else None, previous_status=previous, new_status=finding.status, comment=correction.review_observations)

    return transition_view(request, pk, "Revisar correccion", CorrectionReviewForm, get_instance, on_valid)


@role_required(is_representative)
def assign_corrective_action(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    if not ensure_action_available(request, finding, "assign_corrective_action"):
        return redirect("findings:detail", pk=finding.pk)

    def get_instance(finding):
        return getattr(finding, "corrective_action", None) or CorrectiveAction(finding=finding)

    def on_valid(finding, form):
        previous = finding.status
        action = form.save(commit=False)
        action.finding = finding
        action.assigned_at = timezone.now()
        action.due_at = due_at_from_business_days(timezone.localdate(), DeadlineSetting.current().corrective_action_days)
        action.save()
        finding.status = Finding.Status.ACCION_CORRECTIVA_ASIGNADA
        finding.corrective_action_due_at = action.due_at
        finding.corrective_action_alert_24h_sent = False
        finding.corrective_action_overdue_alert_sent = False
        finding.save(
            update_fields=[
                "status",
                "corrective_action_due_at",
                "corrective_action_alert_24h_sent",
                "corrective_action_overdue_alert_sent",
                "updated_at",
            ]
        )
        assignment_label = "oportunidad de mejora" if is_improvement_opportunity(finding) else "accion correctiva"
        history_label = "Oportunidad de mejora asignada" if is_improvement_opportunity(finding) else "Accion correctiva asignada"
        notify_assignment(finding, action.assigned_to, assignment_label, due_at=action.due_at, request=request)
        record_history(finding, history_label, user=request.user if request.user.is_authenticated else None, previous_status=previous, new_status=finding.status)

    title = "Asignar oportunidad de mejora" if is_improvement_opportunity(finding) else "Asignar accion correctiva"
    return transition_view(request, pk, title, CorrectiveActionAssignForm, get_instance, on_valid)


@login_required
def submit_corrective_action(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    if not ensure_action_available(request, finding, "submit_corrective_action"):
        return redirect("findings:detail", pk=finding.pk)

    def get_instance(finding):
        action = get_object_or_404(CorrectiveAction, finding=finding)
        if not assigned_or_representative(request.user, action.assigned_to):
            raise PermissionDenied
        return action

    def on_valid(finding, form):
        previous = finding.status
        action = form.save(commit=False)
        action.submitted_at = timezone.now()
        action.save()
        correction = related_or_none(finding, "correction")
        finding.status = Finding.Status.ACCION_CORRECTIVA_EN_REVISION if correction and correction.submitted_at else Finding.Status.EN_CORRECCION
        finding.corrective_action_review_due_at = due_at_from_business_days(
            timezone.localtime(action.submitted_at).date(),
            DeadlineSetting.current().corrective_action_review_days,
        )
        finding.corrective_action_review_alert_24h_sent = False
        finding.corrective_action_review_overdue_alert_sent = False
        finding.save(
            update_fields=[
                "status",
                "corrective_action_review_due_at",
                "corrective_action_review_alert_24h_sent",
                "corrective_action_review_overdue_alert_sent",
                "updated_at",
            ]
        )
        evidence_file = form.cleaned_data.get("evidence_file")
        if evidence_file:
            Evidence.objects.create(
                finding=finding,
                corrective_action=action,
                file=evidence_file,
                uploaded_by=request.user if request.user.is_authenticated else None,
                description="Evidencia de la accion correctiva",
            )
        if is_improvement_opportunity(finding):
            notify_representative(
                f"Revision pendiente: plan de accion {finding.code}",
                finding,
                "Revisar si el plan de accion de la oportunidad de mejora es conforme.",
                due_at=finding.corrective_action_review_due_at,
                submitted_by=request.user if request.user.is_authenticated else None,
                request=request,
            )
            history_label = "Plan de accion enviado a revision"
        else:
            notify_representative(
                f"Revision pendiente: accion correctiva {finding.code}",
                finding,
                "Revisar si el plan de accion y la causa raiz son conformes.",
                due_at=finding.corrective_action_review_due_at,
                submitted_by=request.user if request.user.is_authenticated else None,
                request=request,
            )
            history_label = "Accion correctiva enviada a revision"
        record_history(finding, history_label, user=request.user if request.user.is_authenticated else None, previous_status=previous, new_status=finding.status)

    form_class = ImprovementPlanSubmitForm if is_improvement_opportunity(finding) else CorrectiveActionSubmitForm
    title = "Registrar plan de accion" if is_improvement_opportunity(finding) else "Registrar accion correctiva"
    return transition_view(request, pk, title, form_class, get_instance, on_valid)


@role_required(is_representative)
def review_corrective_action(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    if not ensure_action_available(request, finding, "review_corrective_action"):
        return redirect("findings:detail", pk=finding.pk)

    def get_instance(finding):
        return get_object_or_404(CorrectiveAction, finding=finding)

    def on_valid(finding, form):
        previous = finding.status
        action = form.save(commit=False)
        action.reviewed_by = request.user if request.user.is_authenticated else None
        action.reviewed_at = timezone.now()
        action.save()
        correction = related_or_none(finding, "correction")
        if action.is_conform:
            if is_improvement_opportunity(finding) or (correction and correction.is_conform is True):
                finding.status = Finding.Status.ACCION_CORRECTIVA_APROBADA
                finding.corrective_action_due_at = None
                finding.corrective_action_review_due_at = None
            else:
                finding.status = Finding.Status.CORRECCION_EN_REVISION if correction and correction.submitted_at else Finding.Status.EN_CORRECCION
                finding.corrective_action_due_at = None
                finding.corrective_action_review_due_at = None
            history_label = "Plan de accion aprobado" if is_improvement_opportunity(finding) else "Plan de accion aprobado"
        else:
            finding.status = Finding.Status.EN_ACCION_CORRECTIVA
            finding.corrective_action_due_at = due_at_from_business_days(
                timezone.localdate(),
                DeadlineSetting.current().corrective_action_days,
            )
            finding.corrective_action_review_due_at = None
            finding.corrective_action_alert_24h_sent = False
            finding.corrective_action_review_alert_24h_sent = False
            finding.corrective_action_overdue_alert_sent = False
            finding.corrective_action_review_overdue_alert_sent = False
            history_label = "Plan de accion observado y devuelto" if is_improvement_opportunity(finding) else "Accion correctiva observada y devuelta"
        finding.save(
            update_fields=[
                "status",
                "corrective_action_due_at",
                "corrective_action_review_due_at",
                "corrective_action_alert_24h_sent",
                "corrective_action_review_alert_24h_sent",
                "corrective_action_overdue_alert_sent",
                "corrective_action_review_overdue_alert_sent",
                "updated_at",
            ]
        )
        record_history(finding, history_label, user=request.user if request.user.is_authenticated else None, previous_status=previous, new_status=finding.status, comment=action.review_observations)

    form_class = ImprovementPlanReviewForm if is_improvement_opportunity(finding) else CorrectiveActionReviewForm
    title = "Revisar plan de accion" if is_improvement_opportunity(finding) else "Revisar accion correctiva"
    return transition_view(request, pk, title, form_class, get_instance, on_valid)


@role_required(is_representative)
def assign_verification(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    if not ensure_action_available(request, finding, "assign_verification"):
        return redirect("findings:detail", pk=finding.pk)

    def get_instance(finding):
        return getattr(finding, "effectiveness_verification", None) or EffectivenessVerification(finding=finding)

    def on_valid(finding, form):
        previous = finding.status
        verification = form.save(commit=False)
        verification.finding = finding
        verification.assigned_at = timezone.now()
        verification.due_at = due_at_from_business_days(timezone.localdate(), DeadlineSetting.current().verification_days)
        verification.save()
        finding.status = Finding.Status.SEGUIMIENTO_ASIGNADO
        finding.verification_due_at = verification.due_at
        finding.verification_alert_24h_sent = False
        finding.verification_overdue_alert_sent = False
        finding.save(
            update_fields=[
                "status",
                "verification_due_at",
                "verification_alert_24h_sent",
                "verification_overdue_alert_sent",
                "updated_at",
            ]
        )
        notify_assignment(
            finding,
            verification.assigned_to,
            "seguimiento y verificacion de eficacia",
            due_at=verification.due_at,
            request=request,
        )
        record_history(finding, "Seguimiento asignado", user=request.user if request.user.is_authenticated else None, previous_status=previous, new_status=finding.status)

    return transition_view(request, pk, "Asignar seguimiento", VerificationAssignForm, get_instance, on_valid)


@login_required
def submit_verification(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    if not ensure_action_available(request, finding, "submit_verification"):
        return redirect("findings:detail", pk=finding.pk)

    def get_instance(finding):
        verification = get_object_or_404(EffectivenessVerification, finding=finding)
        if not assigned_or_representative(request.user, verification.assigned_to):
            raise PermissionDenied
        return verification

    def on_valid(finding, form):
        previous = finding.status
        verification = form.save(commit=False)
        if verification.requires_additional_follow_up:
            verification.additional_follow_up_due_at = due_at_from_business_days(
                timezone.localdate(),
                form.cleaned_data["additional_follow_up_days"],
            )
        verification.submitted_at = timezone.now()
        verification.save()
        finding.status = Finding.Status.SEGUIMIENTO_EN_REVISION
        finding.save(update_fields=["status", "updated_at"])
        notify_representative(
            f"Revision pendiente: seguimiento {finding.code}",
            finding,
            "Revisar el resultado del seguimiento y decidir si corresponde cierre o nuevo tratamiento.",
            due_at=None,
            submitted_by=request.user if request.user.is_authenticated else None,
            request=request,
        )
        record_history(finding, "Seguimiento enviado a revision", user=request.user if request.user.is_authenticated else None, previous_status=previous, new_status=finding.status)

    return transition_view(request, pk, "Registrar seguimiento", VerificationSubmitForm, get_instance, on_valid)


@role_required(is_representative)
def review_verification(request, pk):
    finding = get_object_or_404(Finding, pk=pk)
    if not ensure_action_available(request, finding, "review_verification"):
        return redirect("findings:detail", pk=finding.pk)

    def get_instance(finding):
        return get_object_or_404(EffectivenessVerification, finding=finding)

    def on_valid(finding, form):
        previous = finding.status
        verification = form.save(commit=False)
        verification.reviewed_by = request.user if request.user.is_authenticated else None
        verification.reviewed_at = timezone.now()
        verification.save()
        if form.cleaned_data.get("close_finding"):
            finding.status = Finding.Status.CERRADO
            finding.closed_at = timezone.now()
            finding.verification_due_at = None
            finding.verification_alert_24h_sent = False
            finding.verification_overdue_alert_sent = False
            finding.corrective_action_due_at = None
            finding.corrective_action_alert_24h_sent = False
            finding.corrective_action_overdue_alert_sent = False
            history_label = "Verificacion eficaz y hallazgo cerrado"
        else:
            if verification.is_effective:
                finding.status = Finding.Status.SEGUIMIENTO_EN_REVISION
                history_label = "Verificacion eficaz pendiente de cierre"
            else:
                finding.status = Finding.Status.EN_ACCION_CORRECTIVA
                finding.corrective_action_due_at = due_at_from_business_days(
                    timezone.localdate(),
                    DeadlineSetting.current().corrective_action_days,
                )
                finding.corrective_action_alert_24h_sent = False
                finding.corrective_action_overdue_alert_sent = False
                history_label = "Seguimiento no eficaz, accion devuelta"
            finding.verification_due_at = None
            finding.verification_alert_24h_sent = False
            finding.verification_overdue_alert_sent = False
        finding.save(
            update_fields=[
                "status",
                "closed_at",
                "verification_due_at",
                "verification_alert_24h_sent",
                "verification_overdue_alert_sent",
                "corrective_action_due_at",
                "corrective_action_alert_24h_sent",
                "corrective_action_overdue_alert_sent",
                "updated_at",
            ]
        )
        record_history(finding, history_label, user=request.user if request.user.is_authenticated else None, previous_status=previous, new_status=finding.status, comment=verification.observations)

    return transition_view(request, pk, "Revisar verificacion", VerificationReviewForm, get_instance, on_valid)
