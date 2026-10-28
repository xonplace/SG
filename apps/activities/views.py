from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.findings.permissions import can_create_activities, can_manage_activities, can_view_activities

from .forms import ActivityCreateForm, ActivityProgressForm, ActivityResultForm, ActivityReviewAssignForm, ActivityReviewForm
from .models import Activity, ActivityAttachment, ActivityHistory, ActivityProgress
from .services import notify_activity_assignment, notify_activity_returned, notify_activity_review_assignment


def _user_can_open(user, activity):
    return (
        can_manage_activities(user)
        or can_view_activities(user)
        or activity.user_is_responsible(user)
        or activity.review_assigned_to_id == user.id
    )


def _activity_scope(user):
    queryset = Activity.objects.select_related("assigned_to", "assigned_by", "review_assigned_to").prefetch_related("responsible_users")
    if can_manage_activities(user) or can_view_activities(user):
        return queryset
    return queryset.filter(Q(assigned_to=user) | Q(responsible_users=user) | Q(review_assigned_to=user)).distinct()


def _add_history(activity, user, action, previous_status="", comment=""):
    ActivityHistory.objects.create(
        activity=activity,
        user=user,
        action=action,
        previous_status=previous_status,
        new_status=activity.status,
        comment=comment,
    )


def _save_optional_attachment(activity, user, uploaded_file, description="", progress=None):
    if uploaded_file:
        ActivityAttachment.objects.create(
            activity=activity,
            progress=progress,
            file=uploaded_file,
            description=description,
            uploaded_by=user,
        )


def _status_counts(queryset):
    total = queryset.count()
    open_count = queryset.exclude(status=Activity.Status.CLOSED).count()
    closed_count = queryset.filter(status=Activity.Status.CLOSED).count()
    overdue_count = sum(1 for activity in queryset if activity.is_overdue)
    return {"total": total, "open": open_count, "closed": closed_count, "overdue": overdue_count}


@login_required
def activity_list(request):
    if not (can_view_activities(request.user) or can_manage_activities(request.user)):
        messages.error(request, "No tienes permiso para ver actividades SGC.")
        return redirect("core:home")

    queryset = _activity_scope(request.user)
    query = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "")
    selected_origin = request.GET.get("origin", "")

    if query:
        queryset = queryset.filter(Q(code__icontains=query) | Q(title__icontains=query) | Q(description__icontains=query))
    if selected_status:
        queryset = queryset.filter(status=selected_status)
    if selected_origin:
        queryset = queryset.filter(origin=selected_origin)

    context = {
        "activities": queryset,
        "counts": _status_counts(queryset),
        "query": query,
        "selected_status": selected_status,
        "selected_origin": selected_origin,
        "status_choices": Activity.Status.choices,
        "origin_choices": Activity.Origin.choices,
        "can_create_activity": can_create_activities(request.user) or can_manage_activities(request.user),
        "page_title": "Bandeja de actividades SGC",
        "page_intro": "Seguimiento de compromisos, planes de accion y acuerdos generados en el SGC.",
    }
    return render(request, "activities/activity_list.html", context)


@login_required
def my_activities(request):
    queryset = Activity.objects.select_related("assigned_to", "review_assigned_to").prefetch_related("responsible_users").filter(
        Q(assigned_to=request.user) | Q(responsible_users=request.user) | Q(review_assigned_to=request.user)
    ).distinct()
    context = {
        "activities": queryset,
        "counts": _status_counts(queryset),
        "query": "",
        "selected_status": "",
        "selected_origin": "",
        "status_choices": Activity.Status.choices,
        "origin_choices": Activity.Origin.choices,
        "can_create_activity": can_create_activities(request.user) or can_manage_activities(request.user),
        "page_title": "Mis actividades",
        "page_intro": "Actividades donde debes registrar avances o realizar la revision final.",
    }
    return render(request, "activities/activity_list.html", context)


@login_required
def due_activities(request):
    if not (can_view_activities(request.user) or can_manage_activities(request.user)):
        messages.error(request, "No tienes permiso para ver actividades vencidas.")
        return redirect("core:home")
    now = timezone.now()
    queryset = _activity_scope(request.user).exclude(status=Activity.Status.CLOSED).filter(
        Q(follow_up_due_at__lt=now) | Q(delivery_due_at__lt=now) | Q(review_due_at__lt=now)
    )
    context = {
        "activities": queryset,
        "counts": _status_counts(queryset),
        "query": "",
        "selected_status": "",
        "selected_origin": "",
        "status_choices": Activity.Status.choices,
        "origin_choices": Activity.Origin.choices,
        "can_create_activity": can_create_activities(request.user) or can_manage_activities(request.user),
        "page_title": "Actividades vencidas",
        "page_intro": "Actividades que requieren regularizacion por plazo vencido.",
    }
    return render(request, "activities/activity_list.html", context)


@login_required
def activity_create(request):
    if not (can_create_activities(request.user) or can_manage_activities(request.user)):
        messages.error(request, "Solo el Representante de la Gerencia puede crear actividades.")
        return redirect("activities:list")
    form = ActivityCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        activity = form.save(commit=False)
        activity.assigned_by = request.user
        activity.save()
        form.save_m2m()
        first_responsible = activity.responsible_users.first()
        if first_responsible and not activity.assigned_to:
            activity.assigned_to = first_responsible
        if activity.review_assigned_to:
            activity.review_assigned_by = request.user
        activity.status = Activity.Status.ASSIGNED if activity.responsible_users.exists() or activity.assigned_to else Activity.Status.REGISTERED
        activity.save(update_fields=["assigned_to", "review_assigned_by", "status", "updated_at"])
        _add_history(activity, request.user, "Actividad creada", comment="Actividad registrada en el plan de seguimiento.")
        if activity.review_assigned_to:
            _add_history(activity, request.user, "Responsable de revision definido", comment=f"Revision asignada a {activity.review_assigned_to}.")
        notify_activity_assignment(activity)
        messages.success(request, f"Actividad {activity.code} creada correctamente.")
        return redirect("activities:detail", activity.pk)
    return render(request, "activities/activity_form.html", {"form": form, "title": "Nueva actividad SGC"})


@login_required
def activity_detail(request, pk):
    activity = get_object_or_404(_activity_scope(request.user), pk=pk)
    if not _user_can_open(request.user, activity):
        messages.error(request, "No tienes permiso para abrir esta actividad.")
        return redirect("activities:list")
    actions = []
    can_record_progress = activity.user_is_responsible(request.user) or can_manage_activities(request.user)
    if can_record_progress and activity.status in [Activity.Status.ASSIGNED, Activity.Status.IN_PROGRESS, Activity.Status.RETURNED]:
        actions.append({"label": "Registrar avance", "url": reverse("activities:progress", args=[activity.pk])})
    if activity.user_is_responsible(request.user) and activity.status in [Activity.Status.ASSIGNED, Activity.Status.IN_PROGRESS, Activity.Status.RETURNED]:
        actions.append({"label": "Informar resultado", "url": reverse("activities:result", args=[activity.pk])})
    if can_manage_activities(request.user) and activity.status == Activity.Status.RESULT_SUBMITTED and not activity.review_assigned_to:
        actions.append({"label": "Asignar revision final", "url": reverse("activities:assign_review", args=[activity.pk])})
    if (activity.review_assigned_to_id == request.user.id or can_manage_activities(request.user)) and activity.status == Activity.Status.REVIEW_ASSIGNED:
        actions.append({"label": "Revisar y cerrar", "url": reverse("activities:review", args=[activity.pk])})

    return render(
        request,
        "activities/activity_detail.html",
        {
            "activity": activity,
            "actions": actions,
            "progress_entries": activity.progress_entries.select_related("created_by"),
            "attachments": activity.attachments.select_related("uploaded_by"),
            "history": activity.history.select_related("user"),
        },
    )


@login_required
def activity_progress(request, pk):
    activity = get_object_or_404(_activity_scope(request.user), pk=pk)
    if not (activity.user_is_responsible(request.user) or can_manage_activities(request.user)):
        messages.error(request, "No puedes registrar avances en esta actividad.")
        return redirect("activities:detail", activity.pk)
    form = ActivityProgressForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        previous_status = activity.status
        progress = form.save(commit=False)
        progress.activity = activity
        progress.created_by = request.user
        progress.save()
        _save_optional_attachment(activity, request.user, form.cleaned_data.get("file"), form.cleaned_data.get("file_description", ""), progress=progress)
        if activity.status in [Activity.Status.ASSIGNED, Activity.Status.RETURNED]:
            activity.status = Activity.Status.IN_PROGRESS
            activity.save(update_fields=["status", "updated_at"])
        _add_history(activity, request.user, "Avance registrado", previous_status=previous_status, comment=progress.progress_text)
        messages.success(request, "Avance registrado correctamente.")
        return redirect("activities:detail", activity.pk)
    return render(request, "activities/activity_form.html", {"form": form, "title": f"Registrar avance {activity.code}", "activity": activity})


@login_required
def activity_result(request, pk):
    activity = get_object_or_404(_activity_scope(request.user), pk=pk)
    if not (activity.user_is_responsible(request.user) or can_manage_activities(request.user)):
        messages.error(request, "No puedes informar el resultado de esta actividad.")
        return redirect("activities:detail", activity.pk)
    form = ActivityResultForm(request.POST or None, request.FILES or None, instance=activity)
    if request.method == "POST" and form.is_valid():
        previous_status = activity.status
        activity = form.save(commit=False)
        activity.status = Activity.Status.REVIEW_ASSIGNED if activity.review_assigned_to else Activity.Status.RESULT_SUBMITTED
        activity.submitted_at = timezone.now()
        activity.save(update_fields=["result", "status", "submitted_at", "updated_at"])
        _save_optional_attachment(activity, request.user, form.cleaned_data.get("file"), form.cleaned_data.get("file_description", ""))
        _add_history(activity, request.user, "Resultado informado", previous_status=previous_status, comment=activity.result)
        if activity.review_assigned_to:
            notify_activity_review_assignment(activity)
            messages.success(request, "Resultado enviado. La actividad paso directamente a revision final.")
        else:
            messages.success(request, "Resultado enviado. Ahora debe asignarse un responsable de revision y cierre.")
        return redirect("activities:detail", activity.pk)
    return render(request, "activities/activity_form.html", {"form": form, "title": f"Informar resultado {activity.code}", "activity": activity})


@login_required
def activity_assign_review(request, pk):
    if not can_manage_activities(request.user):
        messages.error(request, "Solo el Representante de la Gerencia puede asignar la revision final.")
        return redirect("activities:list")
    activity = get_object_or_404(Activity, pk=pk)
    form = ActivityReviewAssignForm(request.POST or None, instance=activity)
    if request.method == "POST" and form.is_valid():
        previous_status = activity.status
        activity = form.save(commit=False)
        activity.review_assigned_by = request.user
        activity.status = Activity.Status.REVIEW_ASSIGNED
        activity.save(update_fields=["review_assigned_to", "review_assigned_by", "review_due_at", "status", "updated_at"])
        _add_history(activity, request.user, "Revision final asignada", previous_status=previous_status)
        notify_activity_review_assignment(activity)
        messages.success(request, "Responsable de revision asignado correctamente.")
        return redirect("activities:detail", activity.pk)
    return render(request, "activities/activity_form.html", {"form": form, "title": f"Asignar revision final {activity.code}", "activity": activity})


@login_required
def activity_review(request, pk):
    activity = get_object_or_404(_activity_scope(request.user), pk=pk)
    if not (activity.review_assigned_to_id == request.user.id or can_manage_activities(request.user)):
        messages.error(request, "No puedes revisar esta actividad.")
        return redirect("activities:detail", activity.pk)
    form = ActivityReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        previous_status = activity.status
        activity.review_observations = form.cleaned_data.get("review_observations", "")
        if form.cleaned_data["is_conform"] == "yes":
            activity.status = Activity.Status.CLOSED
            activity.closed_by = request.user
            activity.closed_at = timezone.now()
            activity.save(update_fields=["review_observations", "status", "closed_by", "closed_at", "updated_at"])
            _add_history(activity, request.user, "Actividad cerrada", previous_status=previous_status, comment=activity.review_observations)
            messages.success(request, "Actividad cerrada correctamente.")
        else:
            activity.status = Activity.Status.RETURNED
            new_due = form.cleaned_data.get("new_delivery_due_at")
            if new_due:
                activity.delivery_due_at = new_due
            activity.save(update_fields=["review_observations", "delivery_due_at", "status", "updated_at"])
            _add_history(activity, request.user, "Actividad devuelta a tratamiento", previous_status=previous_status, comment=activity.review_observations)
            notify_activity_returned(activity)
            messages.warning(request, "Actividad devuelta al responsable de tratamiento.")
        return redirect("activities:detail", activity.pk)
    return render(request, "activities/activity_form.html", {"form": form, "title": f"Revision final {activity.code}", "activity": activity})
