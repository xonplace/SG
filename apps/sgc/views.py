from datetime import datetime, timedelta
from pathlib import Path
import csv
import mimetypes
import re
import struct
import zlib

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.findings.models import Finding
from apps.core.models import CompanyProfile, SystemHelpContent, TrainingAssignment, TrainingAttempt, TrainingCompletion, TrainingQuestion
from apps.findings.permissions import (
    can_manage_certificates,
    can_manage_documents,
    can_manage_forms,
    can_manage_important_dates,
    can_manage_processes,
    can_manage_sgc_content,
    can_manage_updates,
    can_view_documents,
    role_required,
)
from apps.findings.services import active_due_query

from .forms import (
    IsoCertificateForm,
    SgcDocumentForm,
    SgcDocumentMetadataForm,
    SgcOfficialFormForm,
    SgcImportantDatesForm,
    SgcProcessForm,
    SgcProcessVersionForm,
    SgcUpdateForm,
    TrainingAssignmentForm,
    TrainingEvaluationForm,
    TrainingQuestionForm,
)
from .models import (
    DocumentEventType,
    DocumentType,
    IsoCertificate,
    IsoClause,
    ProcessCategory,
    PublicationStatus,
    SgcDocument,
    SgcDocumentEvent,
    SgcDocumentType,
    SgcImportantDates,
    SgcOfficialForm,
    SgcProcess,
    SgcProcessVersion,
    SgcUpdate,
)


def certificate_document():
    return (
        SgcDocument.objects.filter(
            clause=IsoClause.CLAUSE_1,
            status=PublicationStatus.PUBLISHED,
            title__icontains="Certificado ISO",
        )
        .order_by("title")
        .first()
    )


def scope_document():
    return (
        SgcDocument.objects.filter(
            clause=IsoClause.CLAUSE_1,
            status=PublicationStatus.PUBLISHED,
            title__icontains="Alcance",
        )
        .order_by("title")
        .first()
    )


def sgc_dashboard_metrics():
    now = timezone.now()
    soon = now + timedelta(hours=24)
    open_statuses = [value for value, _label in Finding.Status.choices if value not in {Finding.Status.CERRADO, Finding.Status.CERRADO_NO_APLICA}]
    open_findings = Finding.objects.filter(status__in=open_statuses)
    due_findings = open_findings.filter(active_due_query(soon)).distinct()
    return {
        "documents": SgcDocument.objects.filter(status=PublicationStatus.PUBLISHED).count(),
        "obsolete_documents": SgcDocument.objects.filter(status=PublicationStatus.OBSOLETE).count(),
        "forms": SgcOfficialForm.objects.filter(is_active=True).count(),
        "processes": SgcProcess.objects.filter(is_active=True).count(),
        "open_findings": open_findings.count(),
        "due_findings": due_findings.count(),
        "closed_findings": Finding.objects.filter(status__in=[Finding.Status.CERRADO, Finding.Status.CERRADO_NO_APLICA]).count(),
    }


def active_certificate_card():
    certificate = IsoCertificate.objects.filter(is_active=True).first()
    if certificate:
        return {
            "title": certificate.title,
            "standard": certificate.standard,
            "certification_body": certificate.certification_body or "Organismo no informado",
            "scope": certificate.scope,
            "issue_date": certificate.issue_date,
            "expiry_date": certificate.expiry_date,
            "days_to_expiry": certificate.days_to_expiry,
            "preview_url": reverse("sgc:view_certificate", args=[certificate.pk]),
            "download_url": reverse("sgc:download_certificate", args=[certificate.pk]),
            "source_label": "Certificado cargado",
        }

    document = certificate_document()
    if not document:
        return None
    return {
        "title": document.title,
        "standard": "ISO 9001:2015",
        "certification_body": "TUV Rheinland",
        "scope": "Certificado vigente disponible desde la clausula 1 del Sistema de Gestion.",
        "issue_date": None,
        "expiry_date": None,
        "days_to_expiry": None,
        "preview_url": reverse("sgc:view_document", args=[document.pk]),
        "download_url": reverse("sgc:download_document", args=[document.pk]),
        "source_label": "Tomado desde clausula 1",
    }


def _content_has_active_evaluation(content):
    return content.questions.filter(is_active=True).exists()


def _approved_training_attempt(user, content):
    attempts = TrainingAttempt.objects.filter(user=user, content=content).order_by("-created_at")
    for attempt in attempts:
        if attempt.passed and attempt.percentage >= content.passing_percentage:
            return attempt
    return None


def _training_completion_state(user, content, completion=None, last_attempt=None):
    has_evaluation = _content_has_active_evaluation(content)
    approved_attempt = _approved_training_attempt(user, content) if has_evaluation else None
    is_completed = bool(approved_attempt) if has_evaluation else bool(completion)
    progress = 100 if is_completed else (last_attempt.percentage if last_attempt else 0)
    return {
        "has_evaluation": has_evaluation,
        "approved_attempt": approved_attempt,
        "is_completed": is_completed,
        "progress": progress,
    }


def highlighted_update():
    return (
        SgcUpdate.objects.filter(is_published=True, show_on_home=True).first()
        or SgcUpdate.objects.filter(is_published=True).first()
    )


def clause_cards():
    cards = []
    for value, label in IsoClause.choices:
        count = SgcDocument.objects.filter(clause=value, status=PublicationStatus.PUBLISHED).count()
        cards.append(
            {
                "value": value,
                "label": label,
                "count": count,
                "documents_url": f"{reverse('sgc:documents')}?clause={value}",
            }
        )
    return cards


def document_type_choices():
    return list(
        SgcDocumentType.objects.filter(is_active=True).values_list("value", "name")
    )


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


def controlled_documents_queryset(queryset):
    return queryset.filter(document_type__in=CONTROLLED_DOCUMENT_TYPES)


def document_metadata_return_url(request):
    if request.GET.get("next") == "control":
        return "sgc:document_control_dashboard"
    return "sgc:document_history"


@login_required
def home(request):
    updates = SgcUpdate.objects.filter(is_published=True)[:5]
    return render(
        request,
        "sgc/home.html",
        {
            "certificate": active_certificate_card(),
            "scope_document": scope_document(),
            "important_dates": SgcImportantDates.current(),
            "metrics": sgc_dashboard_metrics(),
            "updates": updates,
            "highlighted_update": highlighted_update(),
        },
    )


@login_required
def training(request):
    contents = SystemHelpContent.objects.filter(is_active=True, show_on_training=True)
    query = request.GET.get("q", "").strip()
    selected_category = request.GET.get("category", "").strip()
    selected_status = request.GET.get("status", "").strip()
    if query:
        contents = contents.filter(
            models.Q(title__icontains=query)
            | models.Q(summary__icontains=query)
            | models.Q(content__icontains=query)
        )
    if selected_category:
        contents = contents.filter(training_category=selected_category)
    if request.method == "POST":
        content_id = request.POST.get("content_id")
        content = get_object_or_404(contents, pk=content_id)
        if _content_has_active_evaluation(content):
            messages.warning(request, "Esta capacitacion requiere aprobar la evaluacion para quedar completada.")
            return redirect("sgc:training_detail", pk=content.pk)
        TrainingCompletion.objects.get_or_create(user=request.user, content=content)
        messages.success(request, "Capacitacion marcada como completada.")
        return redirect("sgc:training")
    today = timezone.localdate()
    completions = TrainingCompletion.objects.filter(user=request.user, content__in=contents)
    completion_by_content = {completion.content_id: completion for completion in completions}
    attempts = TrainingAttempt.objects.filter(user=request.user, content__in=contents).order_by("content_id", "-created_at")
    last_attempt_by_content = {}
    for attempt in attempts:
        last_attempt_by_content.setdefault(attempt.content_id, attempt)
    completed_ids = {
        content.pk
        for content in contents
        if _training_completion_state(
            request.user,
            content,
            completion_by_content.get(content.pk),
            last_attempt_by_content.get(content.pk),
        )["is_completed"]
    }
    assignments = TrainingAssignment.objects.filter(user=request.user, content__in=contents).select_related("content")
    assignment_by_content = {assignment.content_id: assignment for assignment in assignments}
    assigned_ids = set(assignment_by_content)
    completed_count = len(completed_ids)
    content_count = contents.count()
    pending_count = len(assigned_ids - completed_ids)
    completion_percentage = round((completed_count / content_count) * 100) if content_count else 0
    assigned_completion_percentage = round((len(assigned_ids & completed_ids) / len(assigned_ids)) * 100) if assigned_ids else 0
    expired_count = contents.filter(valid_until__lt=today).count()
    overdue_count = assignments.filter(due_date__lt=today).exclude(content_id__in=completed_ids).count()
    video_count = contents.filter(models.Q(video_url__gt="") | models.Q(video_file__gt="")).count()
    material_count = contents.exclude(material_file="").count()
    total_minutes = sum(content.estimated_minutes or 0 for content in contents)
    training_items = []
    featured_content = None
    ordered_contents = sorted(
        contents,
        key=lambda content: (
            0 if content.pk in assigned_ids and content.pk not in completed_ids else 1,
            (assignment_by_content.get(content.pk).due_date or today) if content.pk in assigned_ids else today,
            content.order,
            content.title,
        ),
    )
    can_manage_training = can_manage_sgc_content(request.user)
    for content in ordered_contents:
        assignment = assignment_by_content.get(content.pk)
        state = _training_completion_state(
            request.user,
            content,
            completion_by_content.get(content.pk),
            last_attempt_by_content.get(content.pk),
        )
        is_completed = state["is_completed"]
        is_general = content.training_category == SystemHelpContent.TrainingCategory.GENERAL
        can_open = can_manage_training or is_general or bool(assignment)
        is_expired = bool(content.valid_until and content.valid_until < today)
        is_overdue = bool(assignment and assignment.due_date and assignment.due_date < today and not is_completed)
        item = {
            "content": content,
            "assignment": assignment,
            "is_general": is_general,
            "is_assigned": bool(assignment),
            "can_open": can_open,
            "is_completed": is_completed,
            "is_expired": is_expired,
            "is_overdue": is_overdue,
            "question_count": content.questions.filter(is_active=True).count(),
        }
        if selected_status == "asignadas" and not item["is_assigned"]:
            continue
        if selected_status == "pendientes" and (not item["is_assigned"] or item["is_completed"]):
            continue
        if selected_status == "completadas" and not item["is_completed"]:
            continue
        if selected_status == "vencidas" and not item["is_overdue"]:
            continue
        training_items.append(item)
        if featured_content is None and content.pk in assigned_ids and not is_completed:
            featured_content = content
    if featured_content is None:
        featured_content = next((content for content in ordered_contents if content.pk not in completed_ids), None)
    if featured_content is None:
        featured_content = contents.first()
    category_summary = []
    for value, label in SystemHelpContent.TrainingCategory.choices:
        count = contents.filter(training_category=value).count()
        if count:
            category_summary.append({"label": label, "count": count})
    return render(
        request,
        "sgc/training.html",
        {
            "contents": contents,
            "training_items": training_items,
            "featured_content": featured_content,
            "content_count": content_count,
            "completed_ids": completed_ids,
            "completed_count": completed_count,
            "assigned_count": len(assigned_ids),
            "pending_count": pending_count,
            "completion_percentage": completion_percentage,
            "assigned_completion_percentage": assigned_completion_percentage,
            "expired_count": expired_count,
            "overdue_count": overdue_count,
            "video_count": video_count,
            "material_count": material_count,
            "total_minutes": total_minutes,
            "category_summary": category_summary,
            "category_choices": SystemHelpContent.TrainingCategory.choices,
            "selected_category": selected_category,
            "selected_status": selected_status,
            "query": query,
            "can_manage_training": can_manage_training,
        },
    )


@login_required
def training_detail(request, pk):
    content = get_object_or_404(SystemHelpContent, pk=pk, is_active=True, show_on_training=True)
    is_general = content.training_category == SystemHelpContent.TrainingCategory.GENERAL
    can_manage_training = can_manage_sgc_content(request.user)
    is_assigned = TrainingAssignment.objects.filter(user=request.user, content=content).exists()
    if not (can_manage_training or is_general or is_assigned):
        messages.warning(request, "Este curso requiere asignacion previa para poder abrirlo.")
        return redirect("sgc:training")
    questions = content.questions.filter(is_active=True)
    assignment = TrainingAssignment.objects.filter(user=request.user, content=content).first()
    completion = TrainingCompletion.objects.filter(user=request.user, content=content).first()
    last_attempt = TrainingAttempt.objects.filter(user=request.user, content=content).order_by("-created_at").first()
    completion_state = _training_completion_state(request.user, content, completion, last_attempt)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "complete":
            if questions.exists():
                messages.warning(request, "Esta capacitacion requiere aprobar la evaluacion para quedar completada.")
                return redirect("sgc:training_detail", pk=content.pk)
            TrainingCompletion.objects.get_or_create(user=request.user, content=content)
            messages.success(request, "Capacitacion marcada como completada.")
            return redirect("sgc:training_detail", pk=content.pk)
        return redirect("sgc:training_detail", pk=content.pk)
    completion_state = _training_completion_state(request.user, content, completion, last_attempt)
    return render(
        request,
        "sgc/training_detail.html",
        {
            "content": content,
            "assignment": assignment,
            "completion": completion if completion_state["is_completed"] else None,
            "questions": questions,
            "last_attempt": last_attempt,
            "approved_attempt": completion_state["approved_attempt"],
            "can_manage_training": can_manage_training,
        },
    )


@login_required
def training_evaluation(request, pk):
    content = get_object_or_404(SystemHelpContent, pk=pk, is_active=True, show_on_training=True)
    is_general = content.training_category == SystemHelpContent.TrainingCategory.GENERAL
    can_manage_training = can_manage_sgc_content(request.user)
    is_assigned = TrainingAssignment.objects.filter(user=request.user, content=content).exists()
    if not (can_manage_training or is_general or is_assigned):
        messages.warning(request, "Este curso requiere asignacion previa para poder rendir la evaluacion.")
        return redirect("sgc:training")
    questions = content.questions.filter(is_active=True)
    if not questions.exists():
        messages.warning(request, "Esta capacitacion no tiene evaluacion activa.")
        return redirect("sgc:training_detail", pk=content.pk)

    session_key = f"training_evaluation_started_at_{content.pk}"
    time_limit_seconds = max(content.evaluation_time_minutes or 5, 1) * 60
    result_attempt = None
    result_attempt_id = request.GET.get("resultado")
    if result_attempt_id:
        result_attempt = TrainingAttempt.objects.filter(
            pk=result_attempt_id,
            user=request.user,
            content=content,
        ).first()

    if request.method == "POST":
        form = TrainingEvaluationForm(request.POST, questions=questions)
        if form.is_valid():
            started_at_raw = request.session.get(session_key)
            expired = False
            if started_at_raw:
                started_at = datetime.fromisoformat(started_at_raw)
                if timezone.is_naive(started_at):
                    started_at = timezone.make_aware(started_at)
                expired = (timezone.now() - started_at).total_seconds() > time_limit_seconds
            score = 0 if expired else form.score()
            percentage = round((score / questions.count()) * 100) if questions.count() else 0
            passed = percentage >= content.passing_percentage
            attempt = TrainingAttempt.objects.create(
                user=request.user,
                content=content,
                score=score,
                total_questions=questions.count(),
                passed=passed,
            )
            if passed:
                TrainingCompletion.objects.get_or_create(user=request.user, content=content)
            request.session.pop(session_key, None)
            if expired:
                messages.warning(request, "El tiempo de la evaluacion finalizo. El intento fue registrado como no aprobado.")
            return redirect(f"{reverse('sgc:training_evaluation', args=[content.pk])}?resultado={attempt.pk}")
    else:
        request.session[session_key] = timezone.now().isoformat()
        form = TrainingEvaluationForm(questions=questions)

    last_attempt = TrainingAttempt.objects.filter(user=request.user, content=content).order_by("-created_at").first()
    return render(
        request,
        "sgc/training_evaluation.html",
        {
            "content": content,
            "questions": questions,
            "evaluation_form": form,
            "last_attempt": last_attempt,
            "result_attempt": result_attempt,
            "can_manage_training": can_manage_training,
            "time_limit_seconds": time_limit_seconds,
        },
    )


@login_required
def my_training(request):
    assignments = (
        TrainingAssignment.objects.filter(user=request.user, content__show_on_training=True, content__is_active=True)
        .select_related("content", "assigned_by")
        .order_by("due_date", "-assigned_at")
    )
    content_ids = [assignment.content_id for assignment in assignments]
    completions = TrainingCompletion.objects.filter(user=request.user, content_id__in=content_ids)
    completion_by_content = {completion.content_id: completion for completion in completions}
    attempts = TrainingAttempt.objects.filter(user=request.user, content_id__in=content_ids).order_by("content_id", "-created_at")
    last_attempt_by_content = {}
    for attempt in attempts:
        last_attempt_by_content.setdefault(attempt.content_id, attempt)

    today = timezone.localdate()
    rows = []
    for assignment in assignments:
        completion = completion_by_content.get(assignment.content_id)
        last_attempt = last_attempt_by_content.get(assignment.content_id)
        state = _training_completion_state(request.user, assignment.content, completion, last_attempt)
        rows.append(
            {
                "assignment": assignment,
                "content": assignment.content,
                "completion": completion if state["is_completed"] else None,
                "last_attempt": last_attempt,
                "approved_attempt": state["approved_attempt"],
                "progress": state["progress"],
                "is_overdue": bool(assignment.due_date and assignment.due_date < today and not state["is_completed"]),
            }
        )

    assigned_count = len(rows)
    completed_count = sum(1 for row in rows if row["completion"])
    pending_count = assigned_count - completed_count
    average_progress = round(sum(row["progress"] for row in rows) / assigned_count) if assigned_count else 0
    return render(
        request,
        "sgc/my_training.html",
        {
            "rows": rows,
            "assigned_count": assigned_count,
            "completed_count": completed_count,
            "pending_count": pending_count,
            "average_progress": average_progress,
            "today": today,
        },
    )


def _pdf_escape(text):
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_text(text):
    return _pdf_escape(text).encode("cp1252", errors="replace").decode("cp1252")


def _png_as_pdf_image(path, max_width=900):
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None

    pos = 8
    width = height = bit_depth = color_type = None
    compressed = bytearray()
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_data = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, interlace = struct.unpack(">IIBBBBB", chunk_data)
            if bit_depth != 8 or interlace != 0 or color_type not in (2, 6):
                return None
        elif chunk_type == b"IDAT":
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            break
    if not width or not height:
        return None

    channels = 4 if color_type == 6 else 3
    stride = width * channels
    raw = zlib.decompress(bytes(compressed))
    rows = []
    offset = 0
    previous = [0] * stride
    for _row_index in range(height):
        filter_type = raw[offset]
        offset += 1
        scanline = list(raw[offset : offset + stride])
        offset += stride
        recon = [0] * stride
        for i, value in enumerate(scanline):
            left = recon[i - channels] if i >= channels else 0
            up = previous[i]
            upper_left = previous[i - channels] if i >= channels else 0
            if filter_type == 0:
                recon[i] = value
            elif filter_type == 1:
                recon[i] = (value + left) & 0xFF
            elif filter_type == 2:
                recon[i] = (value + up) & 0xFF
            elif filter_type == 3:
                recon[i] = (value + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                p = left + up - upper_left
                pa = abs(p - left)
                pb = abs(p - up)
                pc = abs(p - upper_left)
                predictor = left if pa <= pb and pa <= pc else up if pb <= pc else upper_left
                recon[i] = (value + predictor) & 0xFF
            else:
                return None
        rows.append(recon)
        previous = recon

    rgb_rows = []
    for row in rows:
        out = bytearray()
        for i in range(0, len(row), channels):
            red, green, blue = row[i], row[i + 1], row[i + 2]
            if channels == 4:
                alpha = row[i + 3]
                red = (red * alpha + 255 * (255 - alpha)) // 255
                green = (green * alpha + 255 * (255 - alpha)) // 255
                blue = (blue * alpha + 255 * (255 - alpha)) // 255
            out.extend((red, green, blue))
        rgb_rows.append(out)

    if width > max_width:
        new_width = max_width
        new_height = max(1, round(height * max_width / width))
        scaled_rows = []
        for y in range(new_height):
            source_y = min(height - 1, int(y * height / new_height))
            source = rgb_rows[source_y]
            new_row = bytearray()
            for x in range(new_width):
                source_x = min(width - 1, int(x * width / new_width))
                start = source_x * 3
                new_row.extend(source[start : start + 3])
            scaled_rows.append(new_row)
        width, height, rgb_rows = new_width, new_height, scaled_rows

    rgb = b"".join(rgb_rows)
    return {
        "width": width,
        "height": height,
        "data": zlib.compress(rgb, 9),
    }


def _training_certificate_pdf(user, content, completion, last_attempt, company):
    full_name = user.get_full_name() or user.get_username()
    completed_at = timezone.localtime(completion.completed_at).strftime("%d-%m-%Y")
    percentage = f"{last_attempt.percentage}%" if last_attempt else "Completado"
    company_name = company.company_name or "Sistema de Gestion"
    logo_field = company.header_logo or company.logo
    logo = _png_as_pdf_image(logo_field.path) if logo_field else None

    lines = [
        ("CAPACITACIÓN INTERNA", 287, 442, 28, True),
        ("CERTIFICADO DE APROBACIÓN", 282, 412, 15, False),
        ("El Portal del Sistema de Gestión certifica que", 301, 360, 12, False),
        (full_name, 0, 294, 30, True),
        ("ha completado satisfactoriamente la capacitación", 294, 272, 12, False),
        (content.title, 0, 218, 20, True),
        (f"Fecha de finalización: {completed_at}", 182, 171, 11, False),
        (f"Resultado de evaluación: {percentage}", 374, 171, 11, False),
        (f"Aprobación requerida: {content.passing_percentage}%", 572, 171, 11, False),
        ("Este certificado acredita una capacitación interna realizada en el Sistema de Gestión.", 224, 112, 9, False),
        (company_name, 0, 78, 12, True),
    ]
    page_width = 842
    page_height = 595

    def centered_x(text, size):
        return max(60, round((page_width - len(str(text)) * size * 0.52) / 2))

    commands = [
        "0.96 0.98 1 rg 0 0 842 595 re f",
        "0.08 0.20 0.38 rg 0 540 842 55 re f",
        "0.22 0.34 0.78 rg 0 0 842 14 re f",
        "1 1 1 rg 42 38 758 486 re f",
        "0.15 0.31 0.54 RG 2.2 w 42 38 758 486 re S",
        "0.75 0.84 0.96 RG 0.8 w 62 58 718 446 re S",
        "0.90 0.94 1 rg 72 338 698 112 re f",
        "0.15 0.31 0.54 rg",
    ]
    commands.extend(
        [
            "0.15 0.37 0.73 rg 105 380 16 16 re f",
            "0.24 0.75 0.45 rg 720 380 16 16 re f",
            "0.15 0.31 0.54 rg",
        ]
    )
    for text, x, y, size, bold in lines:
        if text == company_name and logo:
            continue
        if str(text).startswith("CAPACITACI"):
            x = 246
            y = 404
        elif str(text).startswith("CERTIFICADO DE APROBACI"):
            x = 275
            y = 374
        if str(text).startswith("El Portal del Sistema"):
            x = 258
            y = 348
        font = "F2" if bold else "F1"
        if x == 0:
            x = centered_x(text, size)
        commands.append(f"BT /{font} {size} Tf {x} {y} Td ({_pdf_text(text)}) Tj ET")
    if logo:
        logo_w = 120
        logo_h = round(logo_w * logo["height"] / logo["width"])
        commands.append(f"q {logo_w} 0 0 {logo_h} {round((page_width - logo_w) / 2)} 48 cm /Im1 Do Q")
    stream = "\n".join(commands).encode("cp1252", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> "
        + (b"/XObject << /Im1 7 0 R >> " if logo else b"")
        + b">> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    if logo:
        objects.append(
            b"<< /Type /XObject /Subtype /Image /Width "
            + str(logo["width"]).encode("ascii")
            + b" /Height "
            + str(logo["height"]).encode("ascii")
            + b" /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length "
            + str(len(logo["data"])).encode("ascii")
            + b" >>\nstream\n"
            + logo["data"]
            + b"\nendstream"
        )
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_at = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF".encode("ascii")
    )
    return bytes(pdf)


@login_required
def training_certificate(request, pk):
    content = get_object_or_404(SystemHelpContent, pk=pk, is_active=True, show_on_training=True)
    completion = TrainingCompletion.objects.filter(user=request.user, content=content).first()
    last_attempt = TrainingAttempt.objects.filter(user=request.user, content=content).first()
    completion_state = _training_completion_state(request.user, content, completion, last_attempt)
    if not completion_state["is_completed"]:
        messages.warning(request, "El certificado estara disponible cuando apruebes la capacitacion.")
        return redirect("sgc:training_detail", pk=content.pk)
    if not completion:
        completion, _created = TrainingCompletion.objects.get_or_create(user=request.user, content=content)
    pdf = _training_certificate_pdf(
        request.user,
        content,
        completion,
        completion_state["approved_attempt"] or last_attempt,
        CompanyProfile.current(),
    )
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "-", content.title).strip("-").lower() or "capacitacion"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="certificado-{safe_title}.pdf"'
    return response


@role_required(can_manage_sgc_content)
def training_assign(request, pk):
    content = get_object_or_404(SystemHelpContent, pk=pk, show_on_training=True)
    if request.method == "POST":
        form = TrainingAssignmentForm(request.POST, content=content)
        if form.is_valid():
            selected_users = set(form.cleaned_data["users"])
            existing = {assignment.user: assignment for assignment in TrainingAssignment.objects.filter(content=content)}
            for user in selected_users:
                assignment = existing.get(user)
                if assignment:
                    assignment.due_date = form.cleaned_data["due_date"]
                    assignment.note = form.cleaned_data["note"]
                    assignment.assigned_by = request.user
                    assignment.save(update_fields=["due_date", "note", "assigned_by"])
                else:
                    TrainingAssignment.objects.create(
                        content=content,
                        user=user,
                        due_date=form.cleaned_data["due_date"],
                        note=form.cleaned_data["note"],
                        assigned_by=request.user,
                    )
            TrainingAssignment.objects.filter(content=content).exclude(user__in=selected_users).delete()
            messages.success(request, "Asignaciones actualizadas correctamente.")
            return redirect("sgc:training")
    else:
        form = TrainingAssignmentForm(content=content)
    assignments = TrainingAssignment.objects.filter(content=content).select_related("user").order_by(
        "user__first_name",
        "user__last_name",
        "user__username",
    )
    selected_ids = set()
    for value in form["users"].value() or []:
        try:
            selected_ids.add(int(value))
        except (TypeError, ValueError):
            continue
    assignment_by_user_id = {assignment.user_id: assignment for assignment in assignments}
    user_options = []
    for user in form.fields["users"].queryset:
        full_name = user.get_full_name() or user.username
        initials = "".join(part[:1] for part in full_name.split()[:2]).upper() or user.username[:2].upper()
        user_options.append(
            {
                "user": user,
                "full_name": full_name,
                "initials": initials,
                "checked": user.pk in selected_ids,
                "assignment": assignment_by_user_id.get(user.pk),
                "search_text": f"{full_name} {user.username} {user.email}".lower(),
            }
        )
    return render(
        request,
        "sgc/training_assign.html",
        {
            "content": content,
            "form": form,
            "assignments": assignments,
            "user_options": user_options,
        },
    )


@role_required(can_manage_sgc_content)
def training_questions(request, pk):
    content = get_object_or_404(SystemHelpContent, pk=pk, show_on_training=True)
    questions = content.questions.all()
    attempts_count = TrainingAttempt.objects.filter(content=content).count()
    return render(
        request,
        "sgc/training_questions.html",
        {
            "content": content,
            "questions": questions,
            "attempts_count": attempts_count,
        },
    )


@role_required(can_manage_sgc_content)
def training_question_create(request, pk):
    content = get_object_or_404(SystemHelpContent, pk=pk, show_on_training=True)
    if request.method == "POST":
        form = TrainingQuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.content = content
            question.save()
            messages.success(request, "Pregunta creada correctamente.")
            return redirect("sgc:training_questions", pk=content.pk)
    else:
        next_order = (content.questions.aggregate(models.Max("order")).get("order__max") or 0) + 1
        form = TrainingQuestionForm(initial={"order": next_order, "is_active": True})
    return render(
        request,
        "sgc/training_question_form.html",
        {
            "content": content,
            "form": form,
            "title": "Nueva pregunta",
            "submit_label": "Guardar pregunta",
        },
    )


@role_required(can_manage_sgc_content)
def training_question_update(request, pk):
    question = get_object_or_404(TrainingQuestion.objects.select_related("content"), pk=pk)
    if request.method == "POST":
        form = TrainingQuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, "Pregunta actualizada correctamente.")
            return redirect("sgc:training_questions", pk=question.content.pk)
    else:
        form = TrainingQuestionForm(instance=question)
    return render(
        request,
        "sgc/training_question_form.html",
        {
            "content": question.content,
            "form": form,
            "title": "Editar pregunta",
            "submit_label": "Guardar cambios",
        },
    )


@role_required(can_manage_sgc_content)
def training_question_toggle(request, pk):
    question = get_object_or_404(TrainingQuestion.objects.select_related("content"), pk=pk)
    if request.method == "POST":
        question.is_active = not question.is_active
        question.save(update_fields=["is_active"])
        status = "activada" if question.is_active else "desactivada"
        messages.success(request, f"Pregunta {status} correctamente.")
    return redirect("sgc:training_questions", pk=question.content.pk)


@role_required(can_manage_sgc_content)
def training_question_delete(request, pk):
    question = get_object_or_404(TrainingQuestion.objects.select_related("content"), pk=pk)
    content = question.content
    if request.method == "POST":
        question.delete()
        messages.success(request, "Pregunta eliminada correctamente.")
        return redirect("sgc:training_questions", pk=content.pk)
    return render(request, "sgc/training_question_confirm_delete.html", {"question": question, "content": content})


@role_required(can_manage_sgc_content)
def training_deactivate(request, pk):
    content = get_object_or_404(SystemHelpContent, pk=pk, show_on_training=True)
    if request.method == "POST":
        content.is_active = False
        content.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "Capacitacion dada de baja correctamente.")
    return redirect("sgc:training")


@role_required(can_manage_sgc_content)
def training_activate(request, pk):
    content = get_object_or_404(SystemHelpContent, pk=pk, show_on_training=True)
    if request.method == "POST":
        content.is_active = True
        content.save(update_fields=["is_active", "updated_at"])
        messages.success(request, "Capacitacion reactivada correctamente.")
    return redirect("maintainers:help_contents")


@role_required(can_manage_sgc_content)
def training_delete(request, pk):
    content = get_object_or_404(SystemHelpContent, pk=pk, show_on_training=True)
    if request.method == "POST":
        content_title = content.title
        content.delete()
        messages.success(request, f"Capacitacion eliminada: {content_title}.")
        return redirect("sgc:training")
    return render(request, "sgc/training_confirm_delete.html", {"content": content})


def _training_report_rows():
    assignments = TrainingAssignment.objects.select_related("content", "user", "assigned_by").order_by(
        "content__title",
        "user__first_name",
        "user__last_name",
        "user__username",
    )
    completion_by_key = {
        (completion.user_id, completion.content_id): completion
        for completion in TrainingCompletion.objects.select_related("user", "content")
    }
    last_attempts = {}
    for attempt in TrainingAttempt.objects.select_related("user", "content").order_by("user_id", "content_id", "-created_at"):
        last_attempts.setdefault((attempt.user_id, attempt.content_id), attempt)
    today = timezone.localdate()
    rows = []
    for assignment in assignments:
        attempt = last_attempts.get((assignment.user_id, assignment.content_id))
        completion = completion_by_key.get((assignment.user_id, assignment.content_id))
        state = _training_completion_state(assignment.user, assignment.content, completion, attempt)
        completed = state["is_completed"]
        overdue = bool(assignment.due_date and assignment.due_date < today and not completed)
        rows.append(
            {
                "assignment": assignment,
                "completed": completed,
                "overdue": overdue,
                "attempt": attempt,
                "approved_attempt": state["approved_attempt"],
                "status": "Completada" if completed else ("Vencida" if overdue else "Pendiente"),
            }
        )
    return rows


@role_required(can_manage_sgc_content)
def training_report(request):
    rows = _training_report_rows()
    total = len(rows)
    completed = sum(1 for row in rows if row["completed"])
    overdue = sum(1 for row in rows if row["overdue"])
    pending = total - completed
    completion_percentage = round((completed / total) * 100) if total else 0
    return render(
        request,
        "sgc/training_report.html",
        {
            "rows": rows,
            "total": total,
            "completed": completed,
            "pending": pending,
            "overdue": overdue,
            "completion_percentage": completion_percentage,
        },
    )


@role_required(can_manage_sgc_content)
def training_report_export(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="reporte-capacitaciones-sgc.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Capacitacion", "Usuario", "Fecha limite", "Estado", "Puntaje", "Aprobado", "Asignado por"])
    for row in _training_report_rows():
        assignment = row["assignment"]
        attempt = row["attempt"]
        writer.writerow(
            [
                assignment.content.title,
                assignment.user.get_full_name() or assignment.user.username,
                assignment.due_date.strftime("%d-%m-%Y") if assignment.due_date else "",
                row["status"],
                f"{attempt.score}/{attempt.total_questions}" if attempt else "",
                "Si" if attempt and attempt.passed else "No" if attempt else "",
                assignment.assigned_by.get_full_name() or assignment.assigned_by.username if assignment.assigned_by else "",
            ]
        )
    return response


@role_required(can_view_documents)
def documents(request):
    selected_clause = request.GET.get("clause", "")
    selected_type = request.GET.get("type", "")
    query = request.GET.get("q", "").strip()
    documents_qs = SgcDocument.objects.filter(status=PublicationStatus.PUBLISHED)
    if selected_clause:
        documents_qs = documents_qs.filter(clause=selected_clause)
    if selected_type:
        documents_qs = documents_qs.filter(document_type=selected_type)
    if query:
        documents_qs = documents_qs.filter(
            models.Q(title__icontains=query)
            | models.Q(code__icontains=query)
            | models.Q(version__icontains=query)
            | models.Q(summary__icontains=query)
            | models.Q(process__icontains=query)
        )
    types = document_type_choices()
    return render(
        request,
        "sgc/document_list.html",
        {
            "documents": documents_qs,
            "clauses": IsoClause.choices,
            "selected_clause_label": dict(IsoClause.choices).get(selected_clause, ""),
            "types": types,
            "selected_type_label": dict(types).get(selected_type, ""),
            "selected_clause": selected_clause,
            "active_document_clause": selected_clause,
            "selected_type": selected_type,
            "query": query,
            "can_manage_documents": can_manage_documents(request.user),
            "is_obsolete_view": False,
        },
    )


def filtered_document_matrix_queryset(request):
    selected_clause = request.GET.get("clause", "")
    selected_type = request.GET.get("type", "")
    selected_status = request.GET.get("status", PublicationStatus.PUBLISHED)
    query = request.GET.get("q", "").strip()

    documents_qs = SgcDocument.objects.all().select_related("uploaded_by", "obsolete_by", "replaced_by")
    if selected_status:
        documents_qs = documents_qs.filter(status=selected_status)
    if selected_clause:
        documents_qs = documents_qs.filter(clause=selected_clause)
    if selected_type:
        documents_qs = documents_qs.filter(document_type=selected_type)
    if query:
        documents_qs = documents_qs.filter(
            models.Q(title__icontains=query)
            | models.Q(code__icontains=query)
            | models.Q(version__icontains=query)
            | models.Q(summary__icontains=query)
            | models.Q(process__icontains=query)
            | models.Q(file__icontains=query)
        )
    return documents_qs.order_by("clause", "document_type", "title"), {
        "selected_clause": selected_clause,
        "selected_type": selected_type,
        "selected_status": selected_status,
        "query": query,
    }


@role_required(can_manage_documents)
def document_matrix(request):
    documents_qs, filters = filtered_document_matrix_queryset(request)
    types = document_type_choices()
    total_documents = documents_qs.count()
    controlled_count = controlled_documents_queryset(documents_qs).count()
    external_count = total_documents - controlled_count
    obsolete_count = documents_qs.filter(status=PublicationStatus.OBSOLETE).count()

    return render(
        request,
        "sgc/document_matrix.html",
        {
            "documents": documents_qs,
            "clauses": IsoClause.choices,
            "types": types,
            "statuses": PublicationStatus.choices,
            "selected_clause_label": dict(IsoClause.choices).get(filters["selected_clause"], ""),
            "selected_type_label": dict(types).get(filters["selected_type"], ""),
            "selected_status_label": dict(PublicationStatus.choices).get(filters["selected_status"], ""),
            "total_documents": total_documents,
            "controlled_count": controlled_count,
            "external_count": external_count,
            "obsolete_count": obsolete_count,
            **filters,
        },
    )


@role_required(can_manage_documents)
def document_matrix_export(request):
    documents_qs, _filters = filtered_document_matrix_queryset(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="matriz-documental-sgc.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        [
            "Estado",
            "Clausula",
            "Tipo",
            "Codigo",
            "Documento",
            "Version",
            "Vigencia",
            "Archivo",
            "Controlado",
            "Observaciones",
            "Responsable carga",
            "Fecha carga",
            "Obsoleto desde",
            "Motivo baja",
            "Reemplazado por",
        ]
    )
    for document in documents_qs:
        is_controlled = document.document_type in CONTROLLED_DOCUMENT_TYPES
        observations = []
        if is_controlled and not document.code:
            observations.append("Sin codigo")
        if is_controlled and not document.version:
            observations.append("Sin version")
        if not document.effective_date:
            observations.append("Sin vigencia")
        if document.document_type == DocumentType.OTHER:
            observations.append("Tipo Otro / pendiente de clasificar")
        writer.writerow(
            [
                document.get_status_display(),
                document.get_clause_display(),
                document.document_type_label,
                document.code,
                document.title,
                document.version,
                document.effective_date.strftime("%d-%m-%Y") if document.effective_date else "",
                document.file_filename,
                "Si" if is_controlled else "No",
                " | ".join(observations) or "OK",
                document.uploaded_by.get_username() if document.uploaded_by else "",
                timezone.localtime(document.created_at).strftime("%d-%m-%Y %H:%M") if document.created_at else "",
                timezone.localtime(document.obsolete_at).strftime("%d-%m-%Y %H:%M") if document.obsolete_at else "",
                document.obsolete_reason,
                document.replaced_by.code or document.replaced_by.title if document.replaced_by else "",
            ]
        )
    return response


@role_required(can_manage_documents)
def document_control_dashboard(request):
    published = SgcDocument.objects.filter(status=PublicationStatus.PUBLISHED)
    controlled_published = controlled_documents_queryset(published)
    incomplete_query = (
        models.Q(code="")
        | models.Q(version="")
        | models.Q(effective_date__isnull=True)
    )
    incomplete_documents = controlled_published.filter(incomplete_query).order_by("clause", "title")
    missing_code_documents = controlled_published.filter(code="").order_by("clause", "title")
    missing_version_documents = controlled_published.filter(version="").order_by("clause", "title")
    missing_effective_date_documents = published.filter(effective_date__isnull=True).order_by("clause", "title")
    unclassified_documents = published.filter(document_type=DocumentType.OTHER).order_by("clause", "title")
    duplicate_groups_qs = (
        published.exclude(identity_key="")
        .values("identity_key")
        .annotate(total=models.Count("pk"))
        .filter(total__gt=1)
        .order_by("-total", "identity_key")
    )
    duplicate_groups = []
    for group in duplicate_groups_qs:
        group_documents = list(
            published.filter(identity_key=group["identity_key"]).order_by("-created_at")
        )
        duplicate_groups.append(
            {
                "name": Path(group_documents[0].file.name).stem,
                "total": group["total"],
                "documents": group_documents,
            }
        )

    total_published = published.count()
    incomplete_count = incomplete_documents.count()
    unclassified_count = unclassified_documents.count()
    complete_count = max(total_published - incomplete_count, 0)
    quality_percentage = round((complete_count / total_published) * 100) if total_published else 100

    return render(
        request,
        "sgc/document_control_dashboard.html",
        {
            "total_published": total_published,
            "total_obsolete": SgcDocument.objects.filter(status=PublicationStatus.OBSOLETE).count(),
            "incomplete_count": incomplete_count,
            "unclassified_count": unclassified_count,
            "duplicate_group_count": duplicate_groups_qs.count(),
            "quality_percentage": quality_percentage,
            "incomplete_documents": incomplete_documents,
            "missing_code_documents": missing_code_documents,
            "missing_version_documents": missing_version_documents,
            "missing_effective_date_documents": missing_effective_date_documents,
            "unclassified_documents": unclassified_documents,
            "duplicate_groups": duplicate_groups,
        },
    )


@role_required(can_manage_documents)
def document_control_export(request):
    published = SgcDocument.objects.filter(status=PublicationStatus.PUBLISHED).order_by("clause", "title")
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="control-documental-sgc.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        [
            "Documento",
            "Codigo",
            "Tipo",
            "Clausula",
            "Version",
            "Vigencia",
            "Archivo",
            "Observaciones",
        ]
    )
    for document in published:
        observations = []
        is_controlled = document.document_type in CONTROLLED_DOCUMENT_TYPES
        if is_controlled and not document.code:
            observations.append("Sin codigo")
        if is_controlled and not document.version:
            observations.append("Sin version")
        if not document.effective_date:
            observations.append("Sin vigencia")
        if document.document_type == DocumentType.OTHER:
            observations.append("Tipo Otro / pendiente de clasificar")
        writer.writerow(
            [
                document.title,
                document.code,
                document.document_type_label,
                document.get_clause_display(),
                document.version,
                document.effective_date.strftime("%d-%m-%Y") if document.effective_date else "",
                document.file_filename,
                " | ".join(observations) or "OK",
            ]
        )
    return response


@role_required(can_view_documents)
def official_forms(request):
    selected_process = request.GET.get("process", "")
    query = request.GET.get("q", "").strip()
    forms_qs = SgcOfficialForm.objects.filter(is_active=True).prefetch_related("processes")
    if selected_process and selected_process.isdigit():
        forms_qs = forms_qs.filter(processes__pk=selected_process)
    if query:
        forms_qs = forms_qs.filter(
            models.Q(name__icontains=query)
            | models.Q(code__icontains=query)
            | models.Q(version__icontains=query)
            | models.Q(processes__name__icontains=query)
        ).distinct()
    processes_qs = SgcProcess.objects.filter(is_active=True).order_by("category", "name")
    featured_forms_qs = (
        SgcOfficialForm.objects.filter(is_active=True, show_on_home=True)
        .prefetch_related("processes")
        .order_by("name", "version")[:8]
    )
    return render(
        request,
        "sgc/form_list.html",
        {
            "forms": forms_qs,
            "featured_forms": featured_forms_qs,
            "processes": processes_qs,
            "selected_process": selected_process,
            "selected_process_label": processes_qs.filter(pk=selected_process).first() if selected_process and selected_process.isdigit() else "",
            "query": query,
            "can_manage_forms": can_manage_forms(request.user),
        },
    )


@role_required(can_manage_forms)
def official_form_create(request):
    if request.method == "POST":
        form = SgcOfficialFormForm(request.POST, request.FILES)
        if form.is_valid():
            official_form = form.save(commit=False)
            official_form.uploaded_by = request.user
            official_form.save()
            form.save_m2m()
            messages.success(request, "Formulario cargado correctamente.")
            return redirect("sgc:official_forms")
        messages.error(request, "No se pudo cargar el formulario. Revisa los campos marcados.")
    else:
        form = SgcOfficialFormForm()
    return render(request, "sgc/form.html", {"title": "Cargar formulario", "form": form, "cancel_url": "sgc:official_forms"})


@role_required(can_manage_forms)
def official_form_update(request, pk):
    official_form = get_object_or_404(SgcOfficialForm, pk=pk)
    if request.method == "POST":
        old_file = official_form.file
        form = SgcOfficialFormForm(request.POST, request.FILES, instance=official_form)
        if form.is_valid():
            updated_form = form.save()
            if request.FILES.get("file") and old_file and old_file.name != updated_form.file.name:
                old_file.delete(save=False)
            messages.success(request, "Formulario actualizado correctamente.")
            return redirect("sgc:official_forms")
        messages.error(request, "No se pudo actualizar el formulario. Revisa los campos marcados.")
    else:
        form = SgcOfficialFormForm(instance=official_form)
    return render(request, "sgc/form.html", {"title": "Editar formulario", "form": form, "cancel_url": "sgc:official_forms"})


@role_required(can_manage_forms)
def official_form_delete(request, pk):
    official_form = get_object_or_404(SgcOfficialForm, pk=pk)
    if request.method == "POST":
        name = official_form.name
        if official_form.file:
            official_form.file.delete(save=False)
        official_form.delete()
        messages.success(request, f"Formulario {name} eliminado correctamente.")
        return redirect("sgc:official_forms")
    return render(request, "sgc/form_confirm_delete.html", {"form_item": official_form})


@role_required(can_manage_forms)
def official_form_toggle_home(request, pk):
    official_form = get_object_or_404(SgcOfficialForm, pk=pk, is_active=True)
    if request.method == "POST":
        official_form.show_on_home = not official_form.show_on_home
        official_form.save(update_fields=["show_on_home", "updated_at"])
        if official_form.show_on_home:
            messages.success(request, f"Formulario {official_form.name} marcado como principal en Formularios.")
        else:
            messages.success(request, f"Formulario {official_form.name} retirado de los principales.")
    return redirect("sgc:official_forms")


@role_required(can_view_documents)
def download_official_form(request, pk):
    official_form = get_object_or_404(SgcOfficialForm, pk=pk, is_active=True)
    try:
        file_handle = official_form.file.open("rb")
    except FileNotFoundError as exc:
        raise Http404("El formulario no existe.") from exc
    return FileResponse(file_handle, as_attachment=True, filename=Path(official_form.file.name).name)


@role_required(can_manage_documents)
def obsolete_documents(request):
    selected_clause = request.GET.get("clause", "")
    selected_type = request.GET.get("type", "")
    selected_retirement = request.GET.get("retirement", "")
    query = request.GET.get("q", "").strip()
    documents_qs = SgcDocument.objects.filter(status=PublicationStatus.OBSOLETE).select_related(
        "obsolete_by",
        "replaced_by",
        "uploaded_by",
    )
    if selected_clause:
        documents_qs = documents_qs.filter(clause=selected_clause)
    if selected_type:
        documents_qs = documents_qs.filter(document_type=selected_type)
    if selected_retirement == "replaced":
        documents_qs = documents_qs.filter(replaced_by__isnull=False)
    elif selected_retirement == "manual":
        documents_qs = documents_qs.filter(replaced_by__isnull=True)
    if query:
        documents_qs = documents_qs.filter(
            models.Q(title__icontains=query)
            | models.Q(code__icontains=query)
            | models.Q(version__icontains=query)
            | models.Q(summary__icontains=query)
            | models.Q(process__icontains=query)
            | models.Q(obsolete_reason__icontains=query)
            | models.Q(file__icontains=query)
        )
    documents_qs = documents_qs.order_by("-obsolete_at", "clause", "title")
    types = document_type_choices()
    total_obsolete = documents_qs.count()
    replaced_count = documents_qs.filter(replaced_by__isnull=False).count()
    manual_count = documents_qs.filter(replaced_by__isnull=True).count()
    return render(
        request,
        "sgc/obsolete_documents.html",
        {
            "documents": documents_qs,
            "clauses": IsoClause.choices,
            "selected_clause_label": dict(IsoClause.choices).get(selected_clause, ""),
            "types": types,
            "selected_type_label": dict(types).get(selected_type, ""),
            "selected_clause": selected_clause,
            "selected_type": selected_type,
            "selected_retirement": selected_retirement,
            "selected_retirement_label": {
                "replaced": "Reemplazados",
                "manual": "Baja manual",
            }.get(selected_retirement, ""),
            "query": query,
            "total_obsolete": total_obsolete,
            "replaced_count": replaced_count,
            "manual_count": manual_count,
        },
    )


@role_required(can_view_documents)
def processes(request):
    selected_category = request.GET.get("category", "")
    query = request.GET.get("q", "").strip()
    process_qs = SgcProcess.objects.filter(is_active=True).prefetch_related("versions")
    if not can_manage_processes(request.user):
        process_qs = process_qs.filter(versions__is_current=True).distinct()
    if selected_category:
        process_qs = process_qs.filter(category=selected_category)
    if query:
        process_qs = process_qs.filter(
            models.Q(code__icontains=query)
            | models.Q(name__icontains=query)
            | models.Q(owner__icontains=query)
            | models.Q(description__icontains=query)
        )
    process_list = list(process_qs)
    operational_processes = [
        process for process in process_list if process.category == ProcessCategory.OPERATIONAL
    ]
    support_processes = [
        process for process in process_list if process.category == ProcessCategory.SUPPORT
    ]
    return render(
        request,
        "sgc/process_list.html",
        {
            "operational_processes": operational_processes,
            "support_processes": support_processes,
            "total_processes": len(process_list),
            "categories": ProcessCategory.choices,
            "selected_category": selected_category,
            "selected_category_label": dict(ProcessCategory.choices).get(selected_category, ""),
            "query": query,
            "can_manage_processes": can_manage_processes(request.user),
            "is_obsolete_view": False,
        },
    )


@role_required(can_manage_processes)
def obsolete_processes(request):
    selected_category = request.GET.get("category", "")
    query = request.GET.get("q", "").strip()
    process_qs = SgcProcess.objects.filter(is_active=False).prefetch_related("versions")
    if selected_category:
        process_qs = process_qs.filter(category=selected_category)
    if query:
        process_qs = process_qs.filter(
            models.Q(code__icontains=query)
            | models.Q(name__icontains=query)
            | models.Q(owner__icontains=query)
        )
    process_list = list(process_qs)
    operational_processes = [
        process for process in process_list if process.category == ProcessCategory.OPERATIONAL
    ]
    support_processes = [
        process for process in process_list if process.category == ProcessCategory.SUPPORT
    ]
    return render(
        request,
        "sgc/process_list.html",
        {
            "operational_processes": operational_processes,
            "support_processes": support_processes,
            "total_processes": len(process_list),
            "categories": ProcessCategory.choices,
            "selected_category": selected_category,
            "selected_category_label": dict(ProcessCategory.choices).get(selected_category, ""),
            "query": query,
            "can_manage_processes": True,
            "is_obsolete_view": True,
        },
    )


@role_required(can_view_documents)
def process_detail(request, pk):
    process = get_object_or_404(SgcProcess.objects.prefetch_related("versions", "official_forms"), pk=pk)
    if not process.is_active and not can_manage_processes(request.user):
        raise Http404("El proceso no existe.")
    current_version = process.current_version
    if not current_version and not can_manage_processes(request.user):
        raise Http404("El proceso no existe.")
    can_view_version_history = can_manage_processes(request.user)
    versions = process.versions.all()
    return render(
        request,
        "sgc/process_detail.html",
        {
            "process": process,
            "current_version": current_version,
            "versions": versions,
            "version_count": versions.count(),
            "process_forms": process.official_forms.filter(is_active=True),
            "can_view_version_history": can_view_version_history,
            "can_manage_processes": can_manage_processes(request.user),
        },
    )


@role_required(can_manage_processes)
def process_create(request):
    if request.method == "POST":
        form = SgcProcessForm(request.POST)
        version_form = SgcProcessVersionForm(request.POST, request.FILES)
        if form.is_valid() and version_form.is_valid():
            with transaction.atomic():
                process = form.save()
                version = version_form.save(commit=False)
                version.process = process
                version.published_by = request.user
                version.is_current = True
                version.save()
            messages.success(request, "Proceso publicado correctamente con su version vigente.")
            return redirect("sgc:process_detail", pk=process.pk)
        messages.error(request, "No se pudo publicar el proceso. Revisa los campos marcados e intenta nuevamente.")
    else:
        form = SgcProcessForm()
        version_form = SgcProcessVersionForm()
    return render(
        request,
        "sgc/process_form.html",
        {
            "title": "Publicar proceso",
            "form": form,
            "version_form": version_form,
            "cancel_url": "sgc:processes",
        },
    )


@role_required(can_manage_processes)
def process_update(request, pk):
    process = get_object_or_404(SgcProcess, pk=pk)
    current_version = process.current_version
    if request.method == "POST":
        form = SgcProcessForm(request.POST, instance=process)
        version_form = SgcProcessVersionForm(request.POST, request.FILES, instance=current_version)
        if form.is_valid() and version_form.is_valid():
            with transaction.atomic():
                process = form.save()
                version = version_form.save(commit=False)
                version.process = process
                if not version.published_by_id:
                    version.published_by = request.user
                version.save()
            uploaded = ", ".join(file.name for file in request.FILES.values())
            if uploaded:
                messages.success(request, f"Proceso actualizado correctamente. Archivos recibidos: {uploaded}.")
            else:
                messages.success(request, "Proceso actualizado correctamente.")
            return redirect("sgc:process_detail", pk=process.pk)
        messages.error(request, "No se pudo actualizar el proceso. Revisa los campos marcados e intenta nuevamente.")
    else:
        form = SgcProcessForm(instance=process)
        version_form = SgcProcessVersionForm(instance=current_version)
    return render(
        request,
        "sgc/process_form.html",
        {
            "title": "Editar proceso",
            "form": form,
            "version_form": version_form,
            "current_version": current_version,
            "cancel_url": "sgc:process_detail",
            "cancel_pk": process.pk,
        },
    )


def delete_process_files(process):
    for version in process.versions.all():
        for field_name in ["process_image", "flow_file", "procedure_file"]:
            file_field = getattr(version, field_name)
            if file_field:
                file_field.delete(save=False)


@role_required(can_manage_processes)
def process_mark_obsolete(request, pk):
    process = get_object_or_404(SgcProcess, pk=pk, is_active=True)
    if request.method != "POST":
        return redirect("sgc:process_detail", pk=process.pk)
    process.is_active = False
    process.save(update_fields=["is_active", "updated_at"])
    messages.success(request, f"Proceso {process.name} enviado a procesos obsoletos.")
    return redirect("sgc:processes")


@role_required(can_manage_processes)
def process_delete(request, pk):
    process = get_object_or_404(SgcProcess.objects.prefetch_related("versions"), pk=pk, is_active=False)
    if request.method == "POST":
        process_name = process.name
        with transaction.atomic():
            delete_process_files(process)
            process.delete()
        messages.success(request, f"Proceso {process_name} eliminado correctamente.")
        return redirect("sgc:obsolete_processes")
    return render(
        request,
        "sgc/process_confirm_delete.html",
        {"process": process, "versions": process.versions.all()},
    )


@role_required(can_manage_processes)
def process_version_create(request, pk):
    process = get_object_or_404(SgcProcess, pk=pk)
    if request.method == "POST":
        form = SgcProcessVersionForm(request.POST, request.FILES)
        if form.is_valid():
            version = form.save(commit=False)
            version.process = process
            version.published_by = request.user
            if not process.current_version:
                version.is_current = True
            version.save()
            messages.success(request, "Version publicada correctamente.")
            return redirect("sgc:process_detail", pk=process.pk)
        messages.error(request, "No se pudo publicar la version. Revisa los campos marcados e intenta nuevamente.")
    else:
        form = SgcProcessVersionForm()
    return render(
        request,
        "sgc/process_form.html",
        {
            "title": f"Nueva version - {process.name}",
            "form": form,
            "cancel_url": "sgc:process_detail",
            "cancel_pk": process.pk,
        },
    )


@login_required
def download_process_file(request, pk, file_kind):
    version = get_object_or_404(SgcProcessVersion.objects.select_related("process"), pk=pk)
    if not version.process.is_active and not can_manage_processes(request.user):
        raise Http404("El archivo no existe.")
    files = {
        "flujo": version.flow_file,
        "procedimiento": version.procedure_file,
        "imagen": version.process_image,
    }
    file_field = files.get(file_kind)
    if not file_field:
        raise Http404("El archivo no existe.")
    try:
        file_handle = file_field.open("rb")
    except (FileNotFoundError, ValueError) as exc:
        raise Http404("El archivo no existe.") from exc
    return FileResponse(file_handle, as_attachment=True, filename=Path(file_field.name).name)


@login_required
def recent_documents(request):
    documents_qs = SgcDocument.objects.filter(status=PublicationStatus.PUBLISHED).order_by("-created_at", "-updated_at")[:20]
    return render(
        request,
        "sgc/recent_documents.html",
        {
            "documents": documents_qs,
        },
    )


@role_required(can_manage_documents)
def document_create(request):
    if request.method == "POST":
        form = SgcDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploaded_by = request.user
            document.save()
            record_document_event(
                document,
                DocumentEventType.PUBLISHED,
                request.user,
                "Carga inicial del documento.",
            )
            messages.success(request, "Documento cargado correctamente.")
            return redirect("sgc:documents")
    else:
        form = SgcDocumentForm()
    return render(request, "sgc/form.html", {"title": "Cargar documento", "form": form, "cancel_url": "sgc:documents"})


def record_document_event(document, event_type, user, detail=""):
    return SgcDocumentEvent.objects.create(
        document=document,
        family_key=document.document_key,
        document_label=document.code or document.title,
        version=document.version,
        event_type=event_type,
        detail=detail,
        performed_by=user,
    )


def obsolete_document(document, user, reason="", replaced_by=None):
    document.status = PublicationStatus.OBSOLETE
    document.obsolete_at = timezone.now()
    document.obsolete_by = user
    document.obsolete_reason = reason
    document.replaced_by = replaced_by
    document.save(update_fields=["status", "obsolete_at", "obsolete_by", "obsolete_reason", "replaced_by", "updated_at"])
    record_document_event(
        document,
        DocumentEventType.REPLACED if replaced_by else DocumentEventType.OBSOLETED,
        user,
        reason,
    )


@role_required(can_manage_documents)
def document_new_version(request, pk):
    previous_document = get_object_or_404(SgcDocument, pk=pk, status=PublicationStatus.PUBLISHED)
    initial = {
        "title": previous_document.title,
        "code": previous_document.code,
        "document_type": previous_document.document_type,
        "clause": previous_document.clause,
        "process": previous_document.process,
        "summary": previous_document.summary,
        "status": PublicationStatus.PUBLISHED,
        "replace_previous": True,
    }
    if request.method == "POST":
        form = SgcDocumentForm(
            request.POST,
            request.FILES,
            is_new_version=True,
            previous_document=previous_document,
        )
        if form.is_valid():
            with transaction.atomic():
                document = form.save(commit=False)
                document.uploaded_by = request.user
                document.status = PublicationStatus.PUBLISHED
                document.identity_key = previous_document.document_key
                document.save()
                record_document_event(
                    document,
                    DocumentEventType.PUBLISHED,
                    request.user,
                    f"Nueva version publicada desde {previous_document.version or 'version anterior'}.",
                )
                if form.cleaned_data.get("replace_previous"):
                    published_versions = (
                        previous_document.version_family_queryset()
                        .select_for_update()
                        .filter(status=PublicationStatus.PUBLISHED)
                        .exclude(pk=document.pk)
                    )
                    reason = f"Reemplazado por version {document.version or 'nueva'} ({document.code or document.title})."
                    for published_document in published_versions:
                        obsolete_document(
                            published_document,
                            request.user,
                            reason=reason,
                            replaced_by=document,
                        )
            messages.success(request, "Nueva version publicada correctamente. La version anterior quedo como obsoleta.")
            return redirect("sgc:document_history", pk=document.pk)
        messages.error(request, "No se pudo publicar la nueva version. Revisa los campos marcados.")
    else:
        form = SgcDocumentForm(
            initial=initial,
            is_new_version=True,
            previous_document=previous_document,
        )
    return render(
        request,
        "sgc/form.html",
        {
            "title": f"Nueva version - {previous_document.title}",
            "form": form,
            "cancel_url": "sgc:documents",
        },
    )


@role_required(can_manage_documents)
def document_edit_metadata(request, pk):
    document = get_object_or_404(SgcDocument, pk=pk)
    return_url = document_metadata_return_url(request)
    original_values = {
        field: getattr(document, field)
        for field in ("code", "version", "document_type", "clause", "effective_date", "process", "summary")
    }
    if request.method == "POST":
        form = SgcDocumentMetadataForm(request.POST, instance=document)
        if form.is_valid():
            changed_fields = [
                field
                for field, original_value in original_values.items()
                if form.cleaned_data.get(field) != original_value
            ]
            document = form.save()
            if changed_fields:
                labels = {
                    "code": "codigo",
                    "version": "version",
                    "document_type": "tipo",
                    "clause": "clausula",
                    "effective_date": "fecha de vigencia",
                    "process": "proceso asociado",
                    "summary": "resumen",
                }
                detail = "Campos modificados: " + ", ".join(labels[field] for field in changed_fields) + "."
                record_document_event(
                    document,
                    DocumentEventType.UPDATED,
                    request.user,
                    detail,
                )
                messages.success(request, "Metadatos del documento actualizados correctamente.")
            else:
                messages.info(request, "No se detectaron cambios en los metadatos.")
            if return_url == "sgc:document_control_dashboard":
                return redirect(return_url)
            return redirect(return_url, pk=document.pk)
    else:
        form = SgcDocumentMetadataForm(instance=document)

    return render(
        request,
        "sgc/form.html",
        {
            "title": f"Editar metadatos - {document.code or document.title}",
            "form": form,
            "cancel_url": return_url,
            "cancel_pk": document.pk if return_url == "sgc:document_history" else None,
        },
    )


@role_required(can_manage_documents)
def document_mark_obsolete(request, pk):
    document = get_object_or_404(SgcDocument, pk=pk, status=PublicationStatus.PUBLISHED)
    if request.method != "POST":
        return redirect("sgc:documents")
    reason = request.POST.get("obsolete_reason", "").strip() or "Baja manual desde biblioteca documental."
    obsolete_document(document, request.user, reason=reason)
    messages.success(request, f"Documento {document.title} enviado a obsoletos.")
    return redirect("sgc:documents")


@role_required(can_manage_documents)
def document_restore(request, pk):
    if request.method != "POST":
        return redirect("sgc:obsolete_documents")

    with transaction.atomic():
        document = get_object_or_404(
            SgcDocument.objects.select_for_update(),
            pk=pk,
            status=PublicationStatus.OBSOLETE,
        )
        published_version = (
            document.version_family_queryset()
            .select_for_update()
            .filter(status=PublicationStatus.PUBLISHED)
            .exclude(pk=document.pk)
            .first()
        )
        if published_version:
            messages.error(
                request,
                f"No se puede restaurar {document.title}: ya existe una version vigente "
                f"({published_version.version or published_version.title}).",
            )
            return redirect("sgc:obsolete_documents")

        document.status = PublicationStatus.PUBLISHED
        document.obsolete_at = None
        document.obsolete_by = None
        document.obsolete_reason = ""
        document.replaced_by = None
        document.save(
            update_fields=[
                "status",
                "obsolete_at",
                "obsolete_by",
                "obsolete_reason",
                "replaced_by",
                "updated_at",
            ]
        )
        record_document_event(
            document,
            DocumentEventType.RESTORED,
            request.user,
            "Documento restaurado desde documentos obsoletos.",
        )

    messages.success(request, f"Documento {document.title} restaurado como version vigente.")
    return redirect("sgc:documents")


@role_required(can_manage_documents)
def document_delete(request, pk):
    document = get_object_or_404(SgcDocument, pk=pk, status=PublicationStatus.OBSOLETE)
    if request.method == "POST":
        title = document.title
        record_document_event(
            document,
            DocumentEventType.DELETED,
            request.user,
            "Eliminacion definitiva de un documento obsoleto.",
        )
        if document.file:
            document.file.delete(save=False)
        document.delete()
        messages.success(request, f"Documento obsoleto {title} eliminado definitivamente.")
        return redirect("sgc:obsolete_documents")
    return render(request, "sgc/document_confirm_delete.html", {"document": document})


@login_required
def document_history(request, pk):
    document = accessible_document_or_404(request.user, pk)
    can_view_history = can_manage_documents(request.user)
    if not can_view_history and document.status != PublicationStatus.PUBLISHED:
        raise Http404("El documento no existe.")
    versions = document.version_family_queryset().select_related("uploaded_by", "obsolete_by", "replaced_by").order_by("-created_at")
    events = SgcDocumentEvent.objects.filter(family_key=document.document_key).select_related("performed_by")
    return render(
        request,
        "sgc/document_history.html",
        {
            "document": document,
            "versions": versions,
            "events": events,
            "can_manage_documents": can_manage_documents(request.user),
        },
    )


def accessible_document_or_404(user, pk):
    document = get_object_or_404(SgcDocument, pk=pk)
    if document.status == PublicationStatus.PUBLISHED:
        return document
    if document.status == PublicationStatus.OBSOLETE and can_manage_documents(user):
        return document
    raise Http404("El documento no existe.")


@login_required
@xframe_options_sameorigin
def view_document(request, pk):
    document = accessible_document_or_404(request.user, pk)
    try:
        file_handle = document.file.open("rb")
    except FileNotFoundError as exc:
        raise Http404("El archivo no existe.") from exc
    content_type, _ = mimetypes.guess_type(document.file.name)
    response = FileResponse(file_handle, content_type=content_type or "application/octet-stream")
    response["Content-Disposition"] = f'inline; filename="{Path(document.file.name).name}"'
    return response


@login_required
def download_document(request, pk):
    document = accessible_document_or_404(request.user, pk)
    try:
        file_handle = document.file.open("rb")
    except FileNotFoundError as exc:
        raise Http404("El archivo no existe.") from exc
    return FileResponse(file_handle, as_attachment=True, filename=Path(document.file.name).name)


@login_required
def certificate(request):
    certificates = IsoCertificate.objects.all()
    return render(
        request,
        "sgc/certificate.html",
        {"certificates": certificates, "active_certificate": active_certificate_card()},
    )


@role_required(can_manage_certificates)
def certificate_create(request):
    if request.method == "POST":
        form = IsoCertificateForm(request.POST, request.FILES)
        if form.is_valid():
            certificate = form.save()
            if certificate.is_active:
                IsoCertificate.objects.exclude(pk=certificate.pk).update(is_active=False)
            messages.success(request, "Certificado cargado correctamente.")
            return redirect("sgc:certificate")
    else:
        form = IsoCertificateForm()
    return render(request, "sgc/form.html", {"title": "Cargar certificado ISO", "form": form, "cancel_url": "sgc:certificate"})


@login_required
@xframe_options_sameorigin
def view_certificate(request, pk):
    certificate = get_object_or_404(IsoCertificate, pk=pk)
    try:
        file_handle = certificate.file.open("rb")
    except FileNotFoundError as exc:
        raise Http404("El certificado no existe.") from exc
    content_type, _ = mimetypes.guess_type(certificate.file.name)
    response = FileResponse(file_handle, content_type=content_type or "application/octet-stream")
    response["Content-Disposition"] = f'inline; filename="{Path(certificate.file.name).name}"'
    return response


@login_required
def download_certificate(request, pk):
    certificate = get_object_or_404(IsoCertificate, pk=pk)
    try:
        file_handle = certificate.file.open("rb")
    except FileNotFoundError as exc:
        raise Http404("El certificado no existe.") from exc
    return FileResponse(file_handle, as_attachment=True, filename=Path(certificate.file.name).name)


@login_required
def updates(request):
    return render(request, "sgc/updates.html", {"updates": SgcUpdate.objects.filter(is_published=True)})


@role_required(can_manage_updates)
def update_create(request):
    can_highlight_home = can_manage_updates(request.user)
    if request.method == "POST":
        form = SgcUpdateForm(request.POST, can_highlight_home=can_highlight_home)
        if form.is_valid():
            update = form.save(commit=False)
            update.created_by = request.user
            if not can_highlight_home:
                update.show_on_home = False
            update.save()
            if update.show_on_home:
                SgcUpdate.objects.exclude(pk=update.pk).update(show_on_home=False)
            messages.success(request, "Comunicado publicado correctamente.")
            return redirect("sgc:updates")
    else:
        form = SgcUpdateForm(can_highlight_home=can_highlight_home)
    return render(request, "sgc/form.html", {"title": "Publicar comunicado", "form": form, "cancel_url": "sgc:updates"})


@role_required(can_manage_updates)
def update_highlight(request, pk):
    update = get_object_or_404(SgcUpdate, pk=pk, is_published=True)
    if request.method == "POST":
        SgcUpdate.objects.exclude(pk=update.pk).update(show_on_home=False)
        update.show_on_home = True
        update.save(update_fields=["show_on_home", "updated_at"])
        messages.success(request, "Comunicado destacado en Inicio SGC.")
    return redirect("sgc:updates")


@role_required(can_manage_important_dates)
def important_dates(request):
    dates = SgcImportantDates.current()
    if request.method == "POST":
        form = SgcImportantDatesForm(request.POST, instance=dates)
        if form.is_valid():
            form.save()
            messages.success(request, "Fechas importantes actualizadas correctamente.")
            return redirect("sgc:important_dates")
    else:
        form = SgcImportantDatesForm(instance=dates)
    return render(
        request,
        "sgc/form.html",
        {
            "title": "Fechas importantes SGC",
            "form": form,
            "cancel_url": "sgc:home",
        },
    )
