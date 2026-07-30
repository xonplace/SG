import csv

from django.contrib import messages
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.forms import ROLE_DESCRIPTIONS, ROLE_GROUPS
from apps.core.audit import log_audit
from apps.core.models import (
    AuditLog,
    AuthenticationSettings,
    CompanyProfile,
    NotificationSettings,
    RolePermission,
    SystemHelpContent,
)
from apps.findings.models import DeadlineSetting, MasterArea, MasterProcess, MasterSource
from apps.findings.permissions import (
    ADMINISTRATOR_GROUP,
    PERMISSION_DEFINITIONS,
    can_manage_sgc_content,
    can_manage_sgc_identity,
    default_permission_for_role,
    is_administrator,
    role_required,
)
from apps.sgc.models import SgcDocumentType

from .forms import (
    AreaForm,
    AuthenticationSettingsForm,
    CompanyLogoForm,
    CompanyProfileForm,
    DeadlineSettingForm,
    DocumentTypeForm,
    ModuleSettingsForm,
    NotificationSettingsForm,
    ProcessForm,
    SgcIdentityForm,
    SourceForm,
    SystemHelpContentForm,
    SystemTextForm,
    ThemeSettingsForm,
)


MAINTAINERS = {
    "areas": {
        "title": "Areas",
        "model": MasterArea,
        "form": AreaForm,
    },
    "procesos": {
        "title": "Procesos",
        "model": MasterProcess,
        "form": ProcessForm,
    },
    "fuentes": {
        "title": "Fuentes",
        "model": MasterSource,
        "form": SourceForm,
    },
    "tipos-documento": {
        "title": "Tipos de documento",
        "model": SgcDocumentType,
        "form": DocumentTypeForm,
    },
}


def maintainer_config(kind):
    return MAINTAINERS[kind]


@role_required(is_administrator)
def home(request):
    return render(
        request,
        "maintainers/home.html",
        {
            "area_count": MasterArea.objects.count(),
            "process_count": MasterProcess.objects.count(),
            "source_count": MasterSource.objects.count(),
            "deadlines": DeadlineSetting.current(),
            "company_profile": CompanyProfile.current(),
        },
    )


@role_required(is_administrator)
def item_list(request, kind):
    config = maintainer_config(kind)
    items = config["model"].objects.all()
    return render(request, "maintainers/item_list.html", {"kind": kind, "title": config["title"], "items": items})


@role_required(is_administrator)
def item_create(request, kind):
    config = maintainer_config(kind)
    form_class = config["form"]
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            log_audit(request, "Crear registro", f"Mantenedor {config['title']}", obj=form.instance)
            messages.success(request, "Registro creado correctamente.")
            return redirect("maintainers:list", kind=kind)
    else:
        form = form_class()
    return render(
        request,
        "maintainers/item_form.html",
        {"kind": kind, "title": f"Nuevo registro - {config['title']}", "form": form},
    )


@role_required(is_administrator)
def item_update(request, kind, pk):
    config = maintainer_config(kind)
    item = get_object_or_404(config["model"], pk=pk)
    form_class = config["form"]
    if request.method == "POST":
        form = form_class(request.POST, instance=item)
        if form.is_valid():
            form.save()
            log_audit(request, "Actualizar registro", f"Mantenedor {config['title']}", obj=item)
            messages.success(request, "Registro actualizado correctamente.")
            return redirect("maintainers:list", kind=kind)
    else:
        form = form_class(instance=item)
    return render(
        request,
        "maintainers/item_form.html",
        {"kind": kind, "title": f"Editar registro - {config['title']}", "form": form},
    )


@role_required(is_administrator)
def deadlines(request):
    setting = DeadlineSetting.current()
    if request.method == "POST":
        form = DeadlineSettingForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            log_audit(request, "Actualizar plazos", "Mantenedores", obj="Plazos")
            messages.success(request, "Plazos actualizados correctamente.")
            return redirect("maintainers:deadlines")
    else:
        form = DeadlineSettingForm(instance=setting)
    return render(request, "maintainers/deadline_form.html", {"form": form})


@role_required(is_administrator)
def company_profile(request):
    profile = CompanyProfile.current()
    if request.method == "POST":
        form = CompanyProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            log_audit(request, "Actualizar empresa", "Mantenedores", obj=profile)
            messages.success(request, "Configuracion de empresa actualizada correctamente.")
            return redirect("maintainers:company")
    else:
        form = CompanyProfileForm(instance=profile)
    return render(request, "maintainers/company_form.html", {"form": form, "profile": profile})


@role_required(is_administrator)
def company_logo(request):
    profile = CompanyProfile.current()
    if request.method == "POST":
        form = CompanyLogoForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            log_audit(request, "Actualizar logo", "Mantenedores", obj=profile)
            messages.success(request, "Logo actualizado correctamente.")
            return redirect("maintainers:company_logo")
    else:
        form = CompanyLogoForm(instance=profile)
    return render(request, "maintainers/company_logo_form.html", {"form": form, "profile": profile})


@role_required(is_administrator)
def system_texts(request):
    profile = CompanyProfile.current()
    if request.method == "POST":
        form = SystemTextForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            log_audit(request, "Actualizar textos", "Mantenedores", obj=profile)
            messages.success(request, "Textos del sistema actualizados correctamente.")
            return redirect("maintainers:system_texts")
    else:
        form = SystemTextForm(instance=profile)
    return render(
        request,
        "maintainers/settings_form.html",
        {
            "form": form,
            "title": "Textos del sistema",
            "description": "Personaliza titulos, textos visibles y nombres de menus para adaptar el sistema a cada empresa.",
            "submit_label": "Guardar textos",
        },
    )


@role_required(is_administrator)
def theme_settings(request):
    profile = CompanyProfile.current()
    if request.method == "POST":
        form = ThemeSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            log_audit(request, "Actualizar tema visual", "Mantenedores", obj=profile)
            messages.success(request, "Tema visual actualizado correctamente.")
            return redirect("maintainers:theme")
    else:
        form = ThemeSettingsForm(instance=profile)
    return render(
        request,
        "maintainers/settings_form.html",
        {
            "form": form,
            "title": "Tema visual",
            "description": "Configura la paleta base del sitio para alinearla a la identidad visual de cada empresa.",
            "submit_label": "Guardar tema",
        },
    )


@role_required(is_administrator)
def module_settings(request):
    profile = CompanyProfile.current()
    if request.method == "POST":
        form = ModuleSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            log_audit(request, "Actualizar modulos", "Mantenedores", obj=profile)
            messages.success(request, "Modulos del sistema actualizados correctamente.")
            return redirect("maintainers:modules")
    else:
        form = ModuleSettingsForm(instance=profile)
    return render(
        request,
        "maintainers/settings_form.html",
        {
            "form": form,
            "title": "Modulos del sistema",
            "description": "Activa o desactiva los modulos disponibles para la empresa que utiliza el sistema.",
            "submit_label": "Guardar modulos",
        },
    )


@role_required(is_administrator)
def notification_settings(request):
    settings_obj = NotificationSettings.current()
    if request.method == "POST":
        form = NotificationSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            log_audit(request, "Actualizar notificaciones", "Mantenedores", obj=settings_obj)
            messages.success(request, "Configuracion de notificaciones actualizada correctamente.")
            return redirect("maintainers:notifications")
    else:
        form = NotificationSettingsForm(instance=settings_obj)
    return render(
        request,
        "maintainers/settings_form.html",
        {
            "form": form,
            "title": "Notificaciones por correo",
            "description": "Activa alertas funcionales del sistema. Las credenciales SMTP se mantienen en variables de entorno.",
            "submit_label": "Guardar notificaciones",
        },
    )


@role_required(is_administrator)
def authentication_settings(request):
    settings_obj = AuthenticationSettings.current()
    if request.method == "POST":
        form = AuthenticationSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            log_audit(request, "Actualizar autenticacion", "Mantenedores", obj=settings_obj)
            messages.success(request, "Configuracion de autenticacion actualizada correctamente.")
            return redirect("maintainers:authentication")
    else:
        form = AuthenticationSettingsForm(instance=settings_obj)
    return render(
        request,
        "maintainers/settings_form.html",
        {
            "form": form,
            "title": "Autenticacion y SSO",
            "description": "Configura la estrategia de acceso. Los secretos SSO se mantienen en variables de entorno.",
            "submit_label": "Guardar autenticacion",
        },
    )


@role_required(can_manage_sgc_identity)
def sgc_identity(request):
    profile = CompanyProfile.current()
    if request.method == "POST":
        form = SgcIdentityForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            log_audit(request, "Actualizar identidad SGC", "Mantenedores", obj=profile)
            messages.success(request, "Identidad del SGC actualizada correctamente.")
            return redirect("maintainers:sgc_identity")
    else:
        form = SgcIdentityForm(instance=profile)
    return render(request, "maintainers/sgc_identity_form.html", {"form": form})


@role_required(is_administrator)
def permission_matrix(request):
    roles = [{"name": role, "description": ROLE_DESCRIPTIONS.get(role, "")} for role in ROLE_GROUPS]

    for role in ROLE_GROUPS:
        for code, _label, _section in PERMISSION_DEFINITIONS:
            RolePermission.objects.get_or_create(
                role_name=role,
                permission_code=code,
                defaults={"is_allowed": True if role == ADMINISTRATOR_GROUP else default_permission_for_role(role, code)},
            )

    if request.method == "POST":
        selected_permissions = set(request.POST.getlist("permissions"))
        for role in ROLE_GROUPS:
            for code, _label, _section in PERMISSION_DEFINITIONS:
                allowed = role == ADMINISTRATOR_GROUP or f"{role}|{code}" in selected_permissions
                RolePermission.objects.update_or_create(
                    role_name=role,
                    permission_code=code,
                    defaults={"is_allowed": allowed},
                )
        log_audit(request, "Actualizar matriz de permisos", "Mantenedores", obj="Matriz de permisos")
        messages.success(request, "Matriz de permisos actualizada correctamente.")
        return redirect("maintainers:permission_matrix")

    saved_permissions = {
        (permission.role_name, permission.permission_code): permission.is_allowed
        for permission in RolePermission.objects.filter(role_name__in=ROLE_GROUPS)
    }
    permissions = []
    for code, label, section in PERMISSION_DEFINITIONS:
        permissions.append(
            {
                "code": code,
                "label": label,
                "section": section,
                "roles": [
                    {
                        "role": role["name"],
                        "allowed": True
                        if role["name"] == ADMINISTRATOR_GROUP
                        else saved_permissions.get(
                            (role["name"], code),
                            default_permission_for_role(role["name"], code),
                        ),
                        "locked": role["name"] == ADMINISTRATOR_GROUP,
                    }
                    for role in roles
                ],
            }
        )
    return render(
        request,
        "maintainers/permission_matrix.html",
        {"roles": roles, "permissions": permissions},
    )


@role_required(is_administrator)
def permission_matrix_export(request):
    for role in ROLE_GROUPS:
        for code, _label, _section in PERMISSION_DEFINITIONS:
            RolePermission.objects.get_or_create(
                role_name=role,
                permission_code=code,
                defaults={"is_allowed": True if role == ADMINISTRATOR_GROUP else default_permission_for_role(role, code)},
            )

    saved_permissions = {
        (permission.role_name, permission.permission_code): permission.is_allowed
        for permission in RolePermission.objects.filter(role_name__in=ROLE_GROUPS)
    }
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="matriz-permisos-sgc.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Seccion", "Permiso", *ROLE_GROUPS])
    for code, label, section in PERMISSION_DEFINITIONS:
        row = [section, label]
        for role in ROLE_GROUPS:
            allowed = True if role == ADMINISTRATOR_GROUP else saved_permissions.get(
                (role, code),
                default_permission_for_role(role, code),
            )
            row.append("Si" if allowed else "No")
        writer.writerow(row)
    log_audit(request, "Exportar matriz de permisos", "Mantenedores", obj="Matriz de permisos")
    return response


@role_required(can_manage_sgc_content)
def help_content_list(request):
    contents = SystemHelpContent.objects.all()
    return render(request, "maintainers/help_content_list.html", {"contents": contents})


@role_required(can_manage_sgc_content)
def help_content_create(request):
    if request.method == "POST":
        form = SystemHelpContentForm(request.POST, request.FILES)
        if form.is_valid():
            content = form.save()
            log_audit(request, "Crear ayuda/capacitacion", "Mantenedores", obj=content)
            messages.success(request, "Contenido creado correctamente.")
            return redirect("maintainers:help_contents")
    else:
        initial = {}
        if request.GET.get("training") == "1":
            initial = {"section": SystemHelpContent.Section.TRAINING, "show_on_training": True}
        form = SystemHelpContentForm(initial=initial)
    return render(request, "maintainers/settings_form.html", {"form": form, "title": "Nuevo contenido de ayuda", "description": "Publica contenidos de ayuda, capacitacion o apoyo para los usuarios.", "submit_label": "Guardar contenido", "multipart": True})


@role_required(can_manage_sgc_content)
def help_content_update(request, pk):
    content = get_object_or_404(SystemHelpContent, pk=pk)
    if request.method == "POST":
        form = SystemHelpContentForm(request.POST, request.FILES, instance=content)
        if form.is_valid():
            content = form.save()
            log_audit(request, "Actualizar ayuda/capacitacion", "Mantenedores", obj=content)
            messages.success(request, "Contenido actualizado correctamente.")
            return redirect("maintainers:help_contents")
    else:
        form = SystemHelpContentForm(instance=content)
    return render(request, "maintainers/settings_form.html", {"form": form, "title": "Editar contenido de ayuda", "description": "Actualiza contenidos de ayuda, capacitacion o apoyo para los usuarios.", "submit_label": "Guardar contenido", "multipart": True})


@role_required(is_administrator)
def audit_log(request):
    query = request.GET.get("q", "").strip()
    selected_module = request.GET.get("module", "").strip()
    selected_action = request.GET.get("action", "").strip()
    selected_user = request.GET.get("user", "").strip()
    logs = AuditLog.objects.select_related("user")
    if query:
        logs = logs.filter(
            models.Q(action__icontains=query)
            | models.Q(module__icontains=query)
            | models.Q(object_repr__icontains=query)
            | models.Q(details__icontains=query)
            | models.Q(user__username__icontains=query)
        )
    if selected_module:
        logs = logs.filter(module=selected_module)
    if selected_action:
        logs = logs.filter(action=selected_action)
    if selected_user:
        logs = logs.filter(user__username=selected_user)
    modules = AuditLog.objects.exclude(module="").order_by("module").values_list("module", flat=True).distinct()
    actions = AuditLog.objects.exclude(action="").order_by("action").values_list("action", flat=True).distinct()
    users = (
        AuditLog.objects.exclude(user__isnull=True)
        .order_by("user__username")
        .values_list("user__username", flat=True)
        .distinct()
    )
    return render(
        request,
        "maintainers/audit_log.html",
        {
            "logs": logs[:300],
            "query": query,
            "modules": modules,
            "actions": actions,
            "users": users,
            "selected_module": selected_module,
            "selected_action": selected_action,
            "selected_user": selected_user,
            "total_logs": logs.count(),
        },
    )
