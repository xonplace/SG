from django.urls import path

from . import views


app_name = "findings"

urlpatterns = [
    path("", views.finding_list, name="list"),
    path("pendientes-representante/", views.representative_pending, name="representative_pending"),
    path("mis-tareas/", views.my_tasks, name="my_tasks"),
    path("vencidos/", views.due_findings, name="due"),
    path("reportes/", views.reports, name="reports"),
    path("exportar-csv/", views.export_findings_csv, name="export_csv"),
    path("nuevo/", views.finding_create, name="create"),
    path("nuevo/registrado/", views.finding_create_success, name="create_success"),
    path("evidencias/<int:pk>/descargar/", views.download_evidence, name="download_evidence"),
    path("<int:pk>/", views.finding_detail, name="detail"),
    path("<int:pk>/evidencias/nueva/", views.upload_evidence, name="upload_evidence"),
    path("<int:pk>/validar/", views.validate_finding, name="validate"),
    path("<int:pk>/asignar-correccion/", views.assign_correction, name="assign_correction"),
    path("<int:pk>/registrar-correccion/", views.submit_correction, name="submit_correction"),
    path("<int:pk>/revisar-correccion/", views.review_correction, name="review_correction"),
    path("<int:pk>/asignar-accion-correctiva/", views.assign_corrective_action, name="assign_corrective_action"),
    path("<int:pk>/registrar-accion-correctiva/", views.submit_corrective_action, name="submit_corrective_action"),
    path("<int:pk>/revisar-accion-correctiva/", views.review_corrective_action, name="review_corrective_action"),
    path("<int:pk>/asignar-seguimiento/", views.assign_verification, name="assign_verification"),
    path("<int:pk>/registrar-seguimiento/", views.submit_verification, name="submit_verification"),
    path("<int:pk>/revisar-seguimiento/", views.review_verification, name="review_verification"),
]
