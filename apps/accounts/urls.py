from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    path("perfil/", views.profile, name="profile"),
    path("", views.user_list, name="user_list"),
    path("nuevo/", views.user_create, name="user_create"),
    path("<int:pk>/editar/", views.user_update, name="user_update"),
    path("<int:pk>/activar-desactivar/", views.user_toggle_active, name="user_toggle_active"),
]
