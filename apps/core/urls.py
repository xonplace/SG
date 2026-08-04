from django.urls import path

from . import views


app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("sso/iniciar/", views.sso_start, name="sso_start"),
    path("sso/callback/", views.sso_callback, name="sso_callback"),
]
