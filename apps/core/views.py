from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.contrib.auth import login
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.models import AuthenticationSettings, CompanyProfile
from apps.core.sso import (
    SsoError,
    build_authorization_url,
    exchange_code_for_tokens,
    user_from_claims,
    verify_id_token,
)


def health(request):
    return HttpResponse("ok", content_type="text/plain")


def authenticated_home_url():
    company = CompanyProfile.current()
    if company.show_findings_module and not company.show_sgc_menu and not company.show_training_module:
        return reverse("findings:list")
    return reverse("sgc:home")


def sso_start(request):
    auth_settings = AuthenticationSettings.current()
    if not auth_settings.sso_enabled or not auth_settings.is_sso_configured:
        messages.warning(
            request,
            "El inicio de sesion SSO no esta configurado completamente. Use el ingreso local de contingencia.",
        )
        return redirect(f"{reverse('login')}?local=1")
    if auth_settings.provider != AuthenticationSettings.Provider.MICROSOFT_ENTRA:
        messages.warning(
            request,
            "Por ahora el SSO automatico esta implementado para Microsoft Entra ID.",
        )
        return redirect(f"{reverse('login')}?local=1")
    redirect_uri = auth_settings.redirect_uri or request.build_absolute_uri(reverse("core:sso_callback"))
    try:
        authorization_url, state, nonce = build_authorization_url(auth_settings, redirect_uri)
    except Exception:
        messages.error(request, "No fue posible iniciar SSO. Revise Tenant ID, Client ID y conectividad con Microsoft.")
        return redirect(f"{reverse('login')}?local=1")
    request.session["sso_state"] = state
    request.session["sso_nonce"] = nonce
    request.session["sso_redirect_uri"] = redirect_uri
    return redirect(authorization_url)


def sso_callback(request):
    auth_settings = AuthenticationSettings.current()
    if request.GET.get("error"):
        messages.error(request, request.GET.get("error_description") or "Microsoft rechazo el inicio de sesion SSO.")
        return redirect(f"{reverse('login')}?local=1")

    state = request.GET.get("state")
    code = request.GET.get("code")
    expected_state = request.session.pop("sso_state", "")
    expected_nonce = request.session.pop("sso_nonce", "")
    redirect_uri = request.session.pop("sso_redirect_uri", auth_settings.redirect_uri)

    if not code or not state or state != expected_state:
        messages.error(request, "Respuesta SSO invalida. Intente nuevamente.")
        return redirect(f"{reverse('login')}?local=1")

    try:
        tokens = exchange_code_for_tokens(auth_settings, code, redirect_uri)
        id_token = tokens.get("id_token")
        if not id_token:
            raise SsoError("Microsoft no entrego id_token.")
        claims = verify_id_token(auth_settings, id_token, expected_nonce)
        user = user_from_claims(auth_settings, claims)
    except Exception as exc:
        messages.error(request, f"No fue posible completar el inicio SSO: {exc}")
        return redirect(f"{reverse('login')}?local=1")

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect(authenticated_home_url())


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
