from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


REPRESENTATIVE_GROUP = "Representante de la Gerencia"
ADMINISTRATOR_GROUP = "Administrador"
CORRECTION_GROUP = "Responsable de Correccion"
CORRECTIVE_ACTION_GROUP = "Responsable de Accion Correctiva"
VERIFICATION_GROUP = "Responsable de Seguimiento"
QUERY_GROUP = "Consulta/Auditor"


PERMISSION_PORTAL_ACCESS = "portal_access"
PERMISSION_MANAGE_USERS = "manage_users"
PERMISSION_MANAGE_SYSTEM_SETTINGS = "manage_system_settings"
PERMISSION_VIEW_DOCUMENTS = "view_documents"
PERMISSION_MANAGE_SGC_CONTENT = "manage_sgc_content"
PERMISSION_MANAGE_DOCUMENTS = "manage_documents"
PERMISSION_MANAGE_FORMS = "manage_forms"
PERMISSION_MANAGE_PROCESSES = "manage_processes"
PERMISSION_MANAGE_CERTIFICATES = "manage_certificates"
PERMISSION_MANAGE_UPDATES = "manage_updates"
PERMISSION_MANAGE_SGC_IDENTITY = "manage_sgc_identity"
PERMISSION_MANAGE_IMPORTANT_DATES = "manage_important_dates"
PERMISSION_CREATE_FINDINGS = "create_findings"
PERMISSION_VIEW_FINDINGS = "view_findings"
PERMISSION_MANAGE_FINDINGS = "manage_findings"
PERMISSION_PERFORM_CORRECTION = "perform_correction"
PERMISSION_PERFORM_CORRECTIVE_ACTION = "perform_corrective_action"
PERMISSION_PERFORM_VERIFICATION = "perform_verification"
PERMISSION_VIEW_REPORTS = "view_reports"


PERMISSION_DEFINITIONS = [
    (PERMISSION_PORTAL_ACCESS, "Acceso al portal interno", "General"),
    (PERMISSION_MANAGE_USERS, "Administrar usuarios", "Administracion"),
    (
        PERMISSION_MANAGE_SYSTEM_SETTINGS,
        "Administrar empresa, logo, tema, textos, modulos y permisos",
        "Administracion",
    ),
    (PERMISSION_VIEW_DOCUMENTS, "Ver biblioteca documental", "Sistema de Gestion"),
    (
        PERMISSION_MANAGE_SGC_CONTENT,
        "Administrar todo el contenido del SGC",
        "Sistema de Gestion",
    ),
    (PERMISSION_MANAGE_DOCUMENTS, "Administrar documentos y control documental", "Sistema de Gestion"),
    (PERMISSION_MANAGE_FORMS, "Administrar formularios oficiales", "Sistema de Gestion"),
    (PERMISSION_MANAGE_PROCESSES, "Administrar procesos y versiones", "Sistema de Gestion"),
    (PERMISSION_MANAGE_CERTIFICATES, "Administrar certificado ISO", "Sistema de Gestion"),
    (PERMISSION_MANAGE_UPDATES, "Administrar comunicados", "Sistema de Gestion"),
    (PERMISSION_MANAGE_SGC_IDENTITY, "Administrar politica, mision, vision e identidad SGC", "Sistema de Gestion"),
    (PERMISSION_MANAGE_IMPORTANT_DATES, "Administrar fechas importantes", "Sistema de Gestion"),
    (PERMISSION_CREATE_FINDINGS, "Registrar hallazgos", "Hallazgos"),
    (PERMISSION_VIEW_FINDINGS, "Ver bandeja, tareas y detalle de hallazgos", "Hallazgos"),
    (
        PERMISSION_MANAGE_FINDINGS,
        "Validar, clasificar, asignar, revisar y cerrar hallazgos",
        "Hallazgos",
    ),
    (PERMISSION_PERFORM_CORRECTION, "Registrar correccion asignada", "Hallazgos"),
    (
        PERMISSION_PERFORM_CORRECTIVE_ACTION,
        "Registrar accion correctiva / plan de accion",
        "Hallazgos",
    ),
    (PERMISSION_PERFORM_VERIFICATION, "Registrar seguimiento y verificacion", "Hallazgos"),
    (PERMISSION_VIEW_REPORTS, "Consultar reportes y registros", "Reportes"),
]


DEFAULT_ROLE_PERMISSIONS = {
    ADMINISTRATOR_GROUP: {code for code, _label, _section in PERMISSION_DEFINITIONS},
    REPRESENTATIVE_GROUP: {
        PERMISSION_PORTAL_ACCESS,
        PERMISSION_VIEW_DOCUMENTS,
        PERMISSION_MANAGE_SGC_CONTENT,
        PERMISSION_MANAGE_DOCUMENTS,
        PERMISSION_MANAGE_FORMS,
        PERMISSION_MANAGE_PROCESSES,
        PERMISSION_MANAGE_CERTIFICATES,
        PERMISSION_MANAGE_UPDATES,
        PERMISSION_MANAGE_SGC_IDENTITY,
        PERMISSION_MANAGE_IMPORTANT_DATES,
        PERMISSION_CREATE_FINDINGS,
        PERMISSION_VIEW_FINDINGS,
        PERMISSION_MANAGE_FINDINGS,
        PERMISSION_PERFORM_CORRECTION,
        PERMISSION_PERFORM_CORRECTIVE_ACTION,
        PERMISSION_PERFORM_VERIFICATION,
        PERMISSION_VIEW_REPORTS,
    },
    CORRECTION_GROUP: {
        PERMISSION_PORTAL_ACCESS,
        PERMISSION_VIEW_DOCUMENTS,
        PERMISSION_CREATE_FINDINGS,
        PERMISSION_VIEW_FINDINGS,
        PERMISSION_PERFORM_CORRECTION,
        PERMISSION_VIEW_REPORTS,
    },
    CORRECTIVE_ACTION_GROUP: {
        PERMISSION_PORTAL_ACCESS,
        PERMISSION_VIEW_DOCUMENTS,
        PERMISSION_CREATE_FINDINGS,
        PERMISSION_VIEW_FINDINGS,
        PERMISSION_PERFORM_CORRECTIVE_ACTION,
        PERMISSION_VIEW_REPORTS,
    },
    VERIFICATION_GROUP: {
        PERMISSION_PORTAL_ACCESS,
        PERMISSION_VIEW_DOCUMENTS,
        PERMISSION_CREATE_FINDINGS,
        PERMISSION_VIEW_FINDINGS,
        PERMISSION_PERFORM_VERIFICATION,
        PERMISSION_VIEW_REPORTS,
    },
    QUERY_GROUP: {
        PERMISSION_PORTAL_ACCESS,
        PERMISSION_VIEW_DOCUMENTS,
        PERMISSION_VIEW_FINDINGS,
        PERMISSION_VIEW_REPORTS,
    },
}


def user_role_names(user):
    if not user.is_authenticated:
        return []
    return list(user.groups.values_list("name", flat=True))


def default_permission_for_role(role_name, permission_code):
    return permission_code in DEFAULT_ROLE_PERMISSIONS.get(role_name, set())


def role_has_permission(role_name, permission_code):
    if role_name == ADMINISTRATOR_GROUP:
        return True
    from apps.core.models import RolePermission

    permission = RolePermission.objects.filter(role_name=role_name, permission_code=permission_code).first()
    if permission is None:
        return default_permission_for_role(role_name, permission_code)
    return permission.is_allowed


def user_has_permission(user, permission_code):
    if not user.is_authenticated:
        return False
    if user.is_superuser or in_group(user, ADMINISTRATOR_GROUP):
        return True
    return any(role_has_permission(role_name, permission_code) for role_name in user_role_names(user))


def in_group(user, group_name):
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


def is_representative(user):
    return user_has_permission(user, PERMISSION_MANAGE_FINDINGS)


def is_management_representative(user):
    return user_has_permission(user, PERMISSION_MANAGE_SGC_CONTENT) or user_has_permission(
        user, PERMISSION_MANAGE_FINDINGS
    )


def can_manage_sgc_content(user):
    return user_has_permission(user, PERMISSION_MANAGE_SGC_CONTENT)


def _can_manage_specific_sgc(user, permission_code):
    return can_manage_sgc_content(user) or user_has_permission(user, permission_code)


def can_manage_documents(user):
    return _can_manage_specific_sgc(user, PERMISSION_MANAGE_DOCUMENTS)


def can_manage_forms(user):
    return _can_manage_specific_sgc(user, PERMISSION_MANAGE_FORMS)


def can_manage_processes(user):
    return _can_manage_specific_sgc(user, PERMISSION_MANAGE_PROCESSES)


def can_manage_certificates(user):
    return _can_manage_specific_sgc(user, PERMISSION_MANAGE_CERTIFICATES)


def can_manage_updates(user):
    return _can_manage_specific_sgc(user, PERMISSION_MANAGE_UPDATES)


def can_manage_sgc_identity(user):
    return _can_manage_specific_sgc(user, PERMISSION_MANAGE_SGC_IDENTITY)


def can_manage_important_dates(user):
    return _can_manage_specific_sgc(user, PERMISSION_MANAGE_IMPORTANT_DATES)


def can_manage_users(user):
    return user_has_permission(user, PERMISSION_MANAGE_USERS)


def can_view_documents(user):
    return user_has_permission(user, PERMISSION_VIEW_DOCUMENTS)


def can_create_findings(user):
    return user_has_permission(user, PERMISSION_CREATE_FINDINGS)


def can_view_reports(user):
    return user_has_permission(user, PERMISSION_VIEW_REPORTS)


def is_administrator(user):
    return user_has_permission(user, PERMISSION_MANAGE_SYSTEM_SETTINGS)


def can_view_findings(user):
    return user_has_permission(user, PERMISSION_VIEW_FINDINGS)


def assigned_or_representative(user, assigned_user):
    return user.is_superuser or is_representative(user) or (assigned_user and assigned_user == user)


def role_required(check, message="No tienes permiso para realizar esta accion."):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if check(request.user):
                return view_func(request, *args, **kwargs)
            messages.error(request, message)
            return redirect("core:home")

        return wrapper

    return decorator
