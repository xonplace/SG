from django.urls import path

from . import views


app_name = "maintainers"

urlpatterns = [
    path("", views.home, name="home"),
    path("empresa/", views.company_profile, name="company"),
    path("logo/", views.company_logo, name="company_logo"),
    path("textos/", views.system_texts, name="system_texts"),
    path("tema/", views.theme_settings, name="theme"),
    path("modulos/", views.module_settings, name="modules"),
    path("notificaciones/", views.notification_settings, name="notifications"),
    path("autenticacion/", views.authentication_settings, name="authentication"),
    path("permisos/", views.permission_matrix, name="permission_matrix"),
    path("permisos/exportar/", views.permission_matrix_export, name="permission_matrix_export"),
    path("ayuda/", views.help_content_list, name="help_contents"),
    path("ayuda/nueva/", views.help_content_create, name="help_content_create"),
    path("ayuda/<int:pk>/editar/", views.help_content_update, name="help_content_update"),
    path("auditoria/", views.audit_log, name="audit_log"),
    path("identidad-sgc/", views.sgc_identity, name="sgc_identity"),
    path("plazos/", views.deadlines, name="deadlines"),
    path("<str:kind>/", views.item_list, name="list"),
    path("<str:kind>/nuevo/", views.item_create, name="create"),
    path("<str:kind>/<int:pk>/editar/", views.item_update, name="update"),
]
