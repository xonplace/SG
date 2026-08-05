from django import forms

from apps.accounts.forms import ROLE_DESCRIPTIONS, ROLE_GROUPS, ensure_role_groups
from apps.core.models import AuthenticationSettings, CompanyProfile, NotificationSettings, SystemHelpContent
from apps.findings.models import DeadlineSetting, MasterArea, MasterProcess, MasterSource
from apps.sgc.models import SgcDocumentType


class StyledMaintainerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = "w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-950 outline-none ring-0 transition focus:border-neutral-950 focus:bg-white"
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "h-4 w-4 rounded border-neutral-300"})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update(
                    {
                        "class": f"{base_class} min-h-28 resize-y",
                    }
                )
            else:
                field.widget.attrs.update({"class": base_class})


class AreaForm(StyledMaintainerForm):
    class Meta:
        model = MasterArea
        fields = ["name", "order", "is_active"]
        labels = {"name": "Area", "order": "Orden", "is_active": "Activo"}


class ProcessForm(StyledMaintainerForm):
    class Meta:
        model = MasterProcess
        fields = ["name", "allows_custom_text", "order", "is_active"]
        labels = {
            "name": "Proceso",
            "allows_custom_text": "Permite texto libre",
            "order": "Orden",
            "is_active": "Activo",
        }


class SourceForm(StyledMaintainerForm):
    class Meta:
        model = MasterSource
        fields = ["value", "name", "allows_custom_text", "order", "is_active"]
        labels = {
            "value": "Valor interno",
            "name": "Fuente",
            "allows_custom_text": "Permite texto libre",
            "order": "Orden",
            "is_active": "Activo",
        }


class DocumentTypeForm(StyledMaintainerForm):
    class Meta:
        model = SgcDocumentType
        fields = ["name", "order", "is_active"]
        labels = {
            "name": "Tipo de documento",
            "order": "Orden",
            "is_active": "Activo",
        }


class DeadlineSettingForm(StyledMaintainerForm):
    class Meta:
        model = DeadlineSetting
        fields = [
            "validation_days",
            "correction_major_days",
            "correction_minor_days",
            "correction_improvement_days",
            "correction_review_days",
            "corrective_action_days",
            "corrective_action_review_days",
            "verification_days",
        ]


class CompanyProfileForm(StyledMaintainerForm):
    class Meta:
        model = CompanyProfile
        fields = [
            "company_name",
            "system_name",
            "quality_system_name",
            "iso_standard",
            "scope",
            "representative_email",
        ]
        labels = {
            "company_name": "Nombre de la empresa",
            "system_name": "Nombre del sistema",
            "quality_system_name": "Nombre del sistema de gestion",
            "iso_standard": "Norma ISO",
            "scope": "Alcance ISO",
            "representative_email": "Correo representante de gerencia",
        }
        widgets = {
            "scope": forms.Textarea(attrs={"rows": 4}),
        }


class SystemTextForm(StyledMaintainerForm):
    class Meta:
        model = CompanyProfile
        fields = [
            "welcome_text",
            "public_portal_title",
            "public_portal_text",
            "public_action_title",
            "public_entry_title",
            "public_entry_text",
            "sgc_home_title",
            "sgc_home_subtitle",
            "finding_callout_title",
            "finding_callout_text",
            "login_title",
            "login_help_text",
            "sgc_menu_label",
            "sgc_home_label",
            "documents_label",
            "forms_label",
            "certificate_label",
            "processes_label",
            "updates_label",
            "training_label",
            "findings_label",
            "findings_board_label",
            "new_finding_label",
            "my_tasks_label",
            "due_label",
            "reports_label",
            "maintainers_label",
        ]
        labels = {
            "welcome_text": "Texto de bienvenida",
            "public_portal_title": "Titulo portada publica",
            "public_portal_text": "Texto portada publica",
            "public_action_title": "Titulo bloque accion portada",
            "public_entry_title": "Titulo tarjeta ingreso portada",
            "public_entry_text": "Texto tarjeta ingreso portada",
            "sgc_home_title": "Titulo Inicio SGC",
            "sgc_home_subtitle": "Subtitulo Inicio SGC",
            "finding_callout_title": "Titulo llamado hallazgos",
            "finding_callout_text": "Texto llamado hallazgos",
            "login_title": "Titulo login",
            "login_help_text": "Texto inferior login",
            "sgc_menu_label": "Menu Sistema de Gestion",
            "sgc_home_label": "Submenu Inicio SGC",
            "documents_label": "Menu Biblioteca documental",
            "forms_label": "Menu Formularios",
            "certificate_label": "Menu Certificado",
            "processes_label": "Menu Procesos",
            "updates_label": "Menu Comunicados",
            "training_label": "Menu Capacitaciones",
            "findings_label": "Menu Hallazgos",
            "findings_board_label": "Submenu Bandeja",
            "new_finding_label": "Submenu Nuevo hallazgo",
            "my_tasks_label": "Submenu Mis tareas",
            "due_label": "Submenu Vencidos",
            "reports_label": "Submenu Reportes",
            "maintainers_label": "Menu Mantenedores",
        }
        widgets = {
            "welcome_text": forms.Textarea(attrs={"rows": 3}),
            "public_portal_text": forms.Textarea(attrs={"rows": 3}),
            "sgc_home_subtitle": forms.Textarea(attrs={"rows": 3}),
            "finding_callout_text": forms.Textarea(attrs={"rows": 3}),
        }


class ThemeSettingsForm(StyledMaintainerForm):
    class Meta:
        model = CompanyProfile
        fields = ["primary_color", "secondary_color", "accent_color", "page_background_color", "button_color"]
        labels = {
            "primary_color": "Color principal",
            "secondary_color": "Color secundario",
            "accent_color": "Color acento",
            "page_background_color": "Color fondo paginas",
            "button_color": "Color botones principales",
        }
        widgets = {
            "primary_color": forms.TextInput(attrs={"type": "color"}),
            "secondary_color": forms.TextInput(attrs={"type": "color"}),
            "accent_color": forms.TextInput(attrs={"type": "color"}),
            "page_background_color": forms.TextInput(attrs={"type": "color"}),
            "button_color": forms.TextInput(attrs={"type": "color"}),
        }


class ModuleSettingsForm(StyledMaintainerForm):
    class Meta:
        model = CompanyProfile
        fields = [
            "show_findings_module",
            "show_documents_module",
            "show_certificate_module",
            "show_updates_module",
            "show_processes_module",
            "show_training_module",
        ]
        labels = {
            "show_findings_module": "Mostrar modulo de hallazgos",
            "show_documents_module": "Mostrar biblioteca documental",
            "show_certificate_module": "Mostrar certificado ISO",
            "show_updates_module": "Mostrar comunicados",
            "show_processes_module": "Mostrar procesos",
            "show_training_module": "Mostrar capacitaciones",
        }


class SystemHelpContentForm(StyledMaintainerForm):
    class Meta:
        model = SystemHelpContent
        fields = [
            "section",
            "title",
            "summary",
            "content",
            "video_url",
            "video_file",
            "image",
            "training_category",
            "estimated_minutes",
            "evaluation_time_minutes",
            "passing_percentage",
            "valid_until",
            "material_file",
            "show_on_training",
            "order",
            "is_active",
        ]
        labels = {
            "section": "Seccion",
            "title": "Titulo",
            "summary": "Resumen",
            "content": "Contenido",
            "video_url": "URL video externo",
            "video_file": "Video cargado",
            "image": "Imagen",
            "training_category": "Categoria de capacitacion",
            "estimated_minutes": "Duracion estimada (minutos)",
            "evaluation_time_minutes": "Tiempo para rendir evaluacion (minutos)",
            "passing_percentage": "Porcentaje minimo de aprobacion",
            "valid_until": "Vigente hasta",
            "material_file": "Material descargable",
            "show_on_training": "Mostrar en capacitaciones",
            "order": "Orden",
            "is_active": "Activo",
        }
        widgets = {
            "content": forms.Textarea(attrs={"rows": 8}),
            "valid_until": forms.DateInput(attrs={"type": "date"}),
            "video_file": forms.FileInput(attrs={"accept": "video/mp4,video/webm,video/ogg"}),
        }
        help_texts = {
            "video_url": "Puedes usar YouTube, Vimeo, un enlace directo a MP4/WebM/Ogg u otro recurso externo.",
            "video_file": "Si cargas un video, se reproducira directamente dentro del curso. Formatos recomendados: MP4 o WebM.",
        }


class CompanyLogoForm(StyledMaintainerForm):
    class Meta:
        model = CompanyProfile
        fields = ["logo", "header_logo"]
        labels = {
            "logo": "Logo principal",
            "header_logo": "Logo de encabezado",
        }
        help_texts = {
            "logo": "Logo general usado en portada publica y login. Recomendado PNG transparente o SVG.",
            "header_logo": "Logo horizontal usado en el encabezado interno. Si queda vacio, se usara el logo principal.",
        }


class SgcIdentityForm(StyledMaintainerForm):
    class Meta:
        model = CompanyProfile
        fields = [
            "commitment_card_title",
            "commitment_card_text",
            "commitment_dialog_title",
            "commitment_dialog_text",
            "quality_policy",
            "mission",
            "vision",
            "quality_commitment_image",
            "commitment_image_caption",
        ]
        labels = {
            "commitment_card_title": "Titulo tarjeta Inicio SGC",
            "commitment_card_text": "Texto tarjeta Inicio SGC",
            "commitment_dialog_title": "Titulo ventana emergente",
            "commitment_dialog_text": "Texto introductorio ventana emergente",
            "quality_policy": "Politica de la Calidad",
            "mission": "Mision",
            "vision": "Vision",
            "quality_commitment_image": "Imagen Nuestro compromiso",
            "commitment_image_caption": "Texto bajo imagen",
        }
        help_texts = {
            "quality_commitment_image": "Imagen opcional para acompanar la Politica de la Calidad. Si no se carga, se usara la imagen predeterminada.",
        }
        widgets = {
            "commitment_card_text": forms.Textarea(attrs={"rows": 3}),
            "commitment_dialog_text": forms.Textarea(attrs={"rows": 3}),
            "quality_policy": forms.Textarea(attrs={"rows": 7}),
            "mission": forms.Textarea(attrs={"rows": 5}),
            "vision": forms.Textarea(attrs={"rows": 5}),
        }


class NotificationSettingsForm(StyledMaintainerForm):
    smtp_password = forms.CharField(
        label="Contrasena SMTP",
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Se guarda cifrada. Dejar vacio para conservar la contrasena actual.",
    )

    class Meta:
        model = NotificationSettings
        fields = [
            "email_alerts_enabled",
            "notify_finding_created",
            "notify_assignments",
            "notify_due_24h",
            "notify_overdue",
            "sender_name",
            "sender_email",
            "smtp_host",
            "smtp_port",
            "smtp_use_tls",
            "smtp_username",
            "smtp_password",
            "internal_copy_emails",
            "due_alert_check_frequency",
        ]
        labels = {
            "email_alerts_enabled": "Activar alertas por correo",
            "notify_finding_created": "Notificar cuando se crea un hallazgo",
            "notify_assignments": "Notificar asignaciones de responsables",
            "notify_due_24h": "Alertar 24 horas antes de vencer",
            "notify_overdue": "Alertar actividades vencidas",
            "sender_name": "Nombre remitente visible",
            "sender_email": "Correo remitente visible",
            "smtp_host": "Servidor SMTP",
            "smtp_port": "Puerto SMTP",
            "smtp_use_tls": "Usar TLS",
            "smtp_username": "Usuario SMTP",
            "internal_copy_emails": "Correos copia internos",
            "due_alert_check_frequency": "Frecuencia sugerida revision vencimientos",
        }
        help_texts = {
            "email_alerts_enabled": "Si esta desactivado, el sistema no enviara correos aunque SMTP este configurado.",
            "sender_email": "Correo visible para los usuarios. Puede coincidir con el usuario SMTP.",
            "smtp_host": "Ejemplo Office 365: smtp.office365.com",
            "internal_copy_emails": "Ingrese un correo por linea. No guardar contrasenas.",
        }
        widgets = {
            "internal_copy_emails": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.has_smtp_password:
            self.fields["smtp_password"].help_text = "Contrasena SMTP configurada. Dejar vacio para conservarla."

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.set_smtp_password(self.cleaned_data.get("smtp_password"))
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class AuthenticationSettingsForm(StyledMaintainerForm):
    default_role = forms.ChoiceField(label="Rol por defecto para usuarios nuevos", required=False)
    client_secret = forms.CharField(
        label="Client Secret",
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Se guarda cifrado. Dejar vacio para conservar el secret actual.",
    )

    class Meta:
        model = AuthenticationSettings
        fields = [
            "local_login_enabled",
            "sso_enabled",
            "provider",
            "allowed_domain",
            "client_id",
            "tenant_id",
            "redirect_uri",
            "client_secret",
            "auto_create_users",
            "default_role",
            "force_sso_for_internal_users",
        ]
        labels = {
            "local_login_enabled": "Login local habilitado",
            "sso_enabled": "SSO habilitado",
            "provider": "Proveedor SSO",
            "allowed_domain": "Dominio permitido",
            "client_id": "Client ID",
            "tenant_id": "Tenant ID",
            "redirect_uri": "Redirect URI",
            "auto_create_users": "Crear usuarios automaticamente",
            "default_role": "Rol por defecto para usuarios nuevos",
            "force_sso_for_internal_users": "Forzar SSO para usuarios internos",
        }
        help_texts = {
            "sso_enabled": "Activa la autenticacion SSO solo cuando la configuracion este completa.",
            "local_login_enabled": "Mantener activo durante la puesta en marcha para no bloquear administradores.",
            "default_role": "Debe coincidir con el nombre de un grupo/rol existente si se usa auto creacion.",
            "redirect_uri": "Ejemplo: https://sg.tecnodatasa.cl/cuentas/sso/callback/",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ensure_role_groups()
        self.fields["default_role"].choices = [("", "Sin rol por defecto")] + [
            (role, f"{role} - {ROLE_DESCRIPTIONS.get(role, '')}") for role in ROLE_GROUPS
        ]
        if self.instance and self.instance.has_client_secret:
            self.fields["client_secret"].help_text = "Client Secret configurado. Dejar vacio para conservarlo."

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.set_client_secret(self.cleaned_data.get("client_secret"))
        if commit:
            instance.save()
            self.save_m2m()
        return instance
