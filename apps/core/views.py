from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.models import CompanyProfile


def authenticated_home_url():
    company = CompanyProfile.current()
    if company.show_findings_module and not company.show_sgc_menu and not company.show_training_module:
        return reverse("findings:list")
    return reverse("sgc:home")


class PortalLoginView(LoginView):
    template_name = "registration/login.html"

    def get_default_redirect_url(self):
        return authenticated_home_url()


def home(request):
    if not request.user.is_authenticated:
        return render(request, "core/home.html", {"metrics": {}})

    return redirect(authenticated_home_url())
