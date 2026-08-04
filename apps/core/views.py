from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.models import AuthenticationSettings, CompanyProfile


def health(request):
    return HttpResponse("ok", content_type="text/plain")


def authenticated_home_url():
    company = CompanyProfile.current()
    if company.show_findings_module and not company.show_sgc_menu and not company.show_training_module:
        return reverse("findings:list")
    return reverse("sgc:home")


def sso_start(request):
    messages.warning(
        request,
        "El inicio de sesion SSO aun no esta habilitado. Use el ingreso local de contingencia.",
    )
    return redirect(f"{reverse('login')}?local=1")


class PortalLoginView(LoginView):
    template_name = "registration/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        auth_settings = AuthenticationSettings.current()
        local_login_requested = self.request.GET.get("local") == "1"
        context["authentication_settings"] = auth_settings
        context["show_sso_entry"] = (
            auth_settings.sso_enabled
            and auth_settings.is_sso_configured
            and not local_login_requested
        )
        context["local_login_requested"] = local_login_requested
        return context

    def get_default_redirect_url(self):
        return authenticated_home_url()


def home(request):
    if not request.user.is_authenticated:
        return render(request, "core/home.html", {"metrics": {}})

    return redirect(authenticated_home_url())
