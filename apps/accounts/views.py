from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.audit import log_audit
from apps.findings.permissions import (
    PERMISSION_DEFINITIONS,
    REPRESENTATIVE_GROUP,
    can_manage_users,
    role_required,
    user_has_permission,
)

from .forms import ROLE_DESCRIPTIONS, ROLE_GROUPS, UserCreateForm, UserUpdateForm, ensure_role_groups


def user_role_names(user):
    return list(user.groups.filter(name__in=ROLE_GROUPS).values_list("name", flat=True))


@login_required
def profile(request):
    roles = user_role_names(request.user)
    permissions = [
        {
            "code": code,
            "label": label,
            "section": section,
            "allowed": user_has_permission(request.user, code),
        }
        for code, label, section in PERMISSION_DEFINITIONS
    ]
    return render(
        request,
        "accounts/profile.html",
        {
            "roles": roles,
            "permissions": permissions,
        },
    )


@role_required(can_manage_users)
def user_list(request):
    ensure_role_groups()
    users = get_user_model().objects.prefetch_related("groups").order_by("first_name", "last_name", "username")
    representatives = users.filter(groups__name=REPRESENTATIVE_GROUP).distinct()
    for user in users:
        user.role_names = user_role_names(user)
    return render(
        request,
        "accounts/user_list.html",
        {
            "users": users,
            "representatives": representatives,
            "role_cards": [
                {"name": role_name, "description": ROLE_DESCRIPTIONS.get(role_name, "")}
                for role_name in ROLE_GROUPS
            ],
        },
    )


@role_required(can_manage_users)
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_audit(request, "Crear usuario", "Usuarios", obj=user)
            messages.success(request, "Usuario creado correctamente.")
            return redirect("accounts:user_list")
    else:
        form = UserCreateForm()
    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "title": "Crear usuario",
            "eyebrow": "Usuarios y roles",
            "submit_label": "Guardar usuario",
        },
    )


@role_required(can_manage_users)
def user_update(request, pk):
    selected_user = get_object_or_404(get_user_model(), pk=pk)
    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=selected_user)
        if form.is_valid():
            user = form.save()
            log_audit(request, "Actualizar usuario", "Usuarios", obj=user)
            messages.success(request, "Usuario actualizado correctamente.")
            return redirect("accounts:user_list")
    else:
        form = UserUpdateForm(instance=selected_user)
    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "title": "Editar usuario",
            "eyebrow": "Usuarios y roles",
            "submit_label": "Actualizar usuario",
        },
    )


@role_required(can_manage_users)
def user_toggle_active(request, pk):
    selected_user = get_object_or_404(get_user_model(), pk=pk)
    if request.method != "POST":
        return redirect("accounts:user_list")
    if selected_user == request.user:
        messages.error(request, "No puedes desactivar tu propio usuario desde esta pantalla.")
        return redirect("accounts:user_list")
    selected_user.is_active = not selected_user.is_active
    selected_user.save(update_fields=["is_active"])
    state = "activado" if selected_user.is_active else "desactivado"
    log_audit(request, f"Usuario {state}", "Usuarios", obj=selected_user)
    messages.success(request, f"Usuario {state} correctamente.")
    return redirect("accounts:user_list")
