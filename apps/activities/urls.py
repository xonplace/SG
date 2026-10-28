from django.urls import path

from . import views


app_name = "activities"

urlpatterns = [
    path("", views.activity_list, name="list"),
    path("nueva/", views.activity_create, name="create"),
    path("mis-actividades/", views.my_activities, name="my_tasks"),
    path("vencidas/", views.due_activities, name="due"),
    path("<int:pk>/", views.activity_detail, name="detail"),
    path("<int:pk>/avance/", views.activity_progress, name="progress"),
    path("<int:pk>/resultado/", views.activity_result, name="result"),
    path("<int:pk>/asignar-revision/", views.activity_assign_review, name="assign_review"),
    path("<int:pk>/reprogramar-plazo/", views.activity_reschedule_deadline, name="reschedule_deadline"),
    path("<int:pk>/revision/", views.activity_review, name="review"),
]
