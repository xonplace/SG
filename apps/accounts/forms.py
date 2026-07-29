from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

from apps.findings.permissions import (
    ADMINISTRATOR_GROUP,
    CORRECTION_GROUP,
    CORRECTIVE_ACTION_GROUP,
    QUERY_GROUP,
    REPRESENTATIVE_GROUP,
    VERIFICATION_GROUP,
)


ROLE_GROUPS = [
    ADMINISTRATOR_GROUP,
    REPRESENTATIVE_GROUP,
    CORRECTION_GROUP,
    CORRECTIVE_ACTION_GROUP,
    VERIFICATION_GROUP,
    QUERY_GROUP,
]

ROLE_DESCRIPTIONS = {
    ADMINISTRATOR_GROUP: "Administra usuarios, mantenedores, configuracion de empresa y todos los modulos del sistema.",
    REPRESENTATIVE_GROUP: "Valida hallazgos, clasifica, asigna responsables, revisa etapas y cierra el flujo.",
    CORRECTION_GROUP: "Registra la correccion inmediata asignada y carga evidencia de ejecucion.",
    CORRECTIVE_ACTION_GROUP: "Realiza analisis de causa raiz, define acciones correctivas y adjunta evidencia.",
    VERIFICATION_GROUP: "Ejecuta seguimiento, verifica eficacia y registra resultados de la medicion.",
    QUERY_GROUP: "Consulta informacion del SGC y hallazgos sin administrar configuraciones.",
}


def ensure_role_groups():
    for group_name in ROLE_GROUPS:
        Group.objects.get_or_create(name=group_name)


def role_group_queryset():
    ensure_role_groups()
    return Group.objects.filter(name__in=ROLE_GROUPS).order_by("name")


class StyledUserFormMixin:
    def apply_styles(self):
        base_class = "w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-950 outline-none ring-0 transition focus:border-neutral-950 focus:bg-white"
        checkbox_class = "h-4 w-4 rounded border-neutral-300"
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": checkbox_class})
            elif isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.update({"class": "space-y-2"})
            else:
                field.widget.attrs.update({"class": base_class})
            if field_name == "groups":
                field.label = "Roles"


class UserCreateForm(StyledUserFormMixin, UserCreationForm):
    groups = forms.ModelMultipleChoiceField(
        label="Roles",
        queryset=Group.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = get_user_model()
        fields = ["username", "first_name", "last_name", "email", "groups", "is_active"]
        labels = {
            "username": "Usuario",
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo",
            "is_active": "Usuario activo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = role_group_queryset()
        self.fields["is_active"].initial = True
        self.apply_styles()

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            user.groups.set(self.cleaned_data["groups"])
        return user


class UserUpdateForm(StyledUserFormMixin, forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        label="Roles",
        queryset=Group.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    new_password = forms.CharField(
        label="Nueva contrasena",
        required=False,
        widget=forms.PasswordInput,
        help_text="Dejar en blanco para mantener la contrasena actual.",
    )

    class Meta:
        model = get_user_model()
        fields = ["username", "first_name", "last_name", "email", "groups", "is_active", "new_password"]
        labels = {
            "username": "Usuario",
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo",
            "is_active": "Usuario activo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = role_group_queryset()
        self.fields["groups"].initial = self.instance.groups.filter(name__in=ROLE_GROUPS)
        self.apply_styles()

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("new_password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
            user.groups.set(self.cleaned_data["groups"])
        return user
