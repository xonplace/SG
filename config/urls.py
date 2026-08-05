from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from apps.core.views import PortalLoginView, health, sso_callback


urlpatterns = [
    path("health/", health, name="health"),
    path(settings.ADMIN_URL, admin.site.urls),
    path("cuentas/login/", PortalLoginView.as_view(), name="login"),
    path("auth/callback/", sso_callback, name="sso_callback_auth"),
    path("cuentas/sso/callback/", sso_callback, name="sso_callback"),
    path("cuentas/", include("django.contrib.auth.urls")),
    path("usuarios/", include("apps.accounts.urls")),
    path("mantenedores/", include("apps.maintainers.urls")),
    path("sistema-gestion/", include("apps.sgc.urls")),
    path("hallazgos/", include("apps.findings.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
