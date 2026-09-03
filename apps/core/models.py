from urllib.parse import parse_qs, urlparse

from django.db import models
from django.conf import settings

from .crypto import decrypt_value, encrypt_value


class CompanyProfile(models.Model):
    company_name = models.CharField("nombre de la empresa", max_length=180, default="Tecnodata S.A.")
    system_name = models.CharField("nombre del sistema", max_length=180, default="Sistema de gestion")
    quality_system_name = models.CharField(
        "nombre del sistema de gestion",
        max_length=220,
        default="Sistema de Gestion de Calidad",
    )
    iso_standard = models.CharField("norma ISO", max_length=80, default="ISO 9001:2015")
    scope = models.TextField(
        "alcance ISO",
        default="Arriendo, implementacion y provision de servicios de impresion, equipos computacionales y otros dispositivos TI.",
    )
    primary_color = models.CharField("color principal", max_length=20, default="#2271b1")
    secondary_color = models.CharField("color secundario", max_length=20, default="#193456")
    accent_color = models.CharField("color acento", max_length=20, default="#4f6df5")
    page_background_color = models.CharField("color fondo paginas", max_length=20, default="#f5f7fa")
    button_color = models.CharField("color botones principales", max_length=20, default="#2271b1")
    representative_email = models.EmailField("correo representante de gerencia", blank=True)
    welcome_text = models.TextField(
        "texto de bienvenida",
        blank=True,
        default="Administracion documental, certificado vigente, actualizaciones internas y seguimiento de hallazgos del SGC.",
    )
    public_portal_title = models.CharField(
        "titulo portada publica",
        max_length=220,
        default="Bienvenido al Sistema de gestion",
    )
    public_portal_text = models.TextField(
        "texto portada publica",
        blank=True,
        default="Este portal centraliza la gestion del sistema, la documentacion y el registro de hallazgos para su tratamiento y seguimiento.",
    )
    public_action_title = models.CharField(
        "titulo bloque accion portada",
        max_length=220,
        default="Registro y gestion de hallazgos",
    )
    public_entry_title = models.CharField(
        "titulo tarjeta ingreso portada",
        max_length=120,
        default="Ingresar al sitio",
    )
    public_entry_text = models.CharField(
        "texto tarjeta ingreso portada",
        max_length=180,
        default="Acceso usuarios autorizados",
    )
    finding_callout_title = models.CharField(
        "titulo llamado hallazgos",
        max_length=180,
        default="Deseas registrar un hallazgo?",
    )
    finding_callout_text = models.TextField(
        "texto llamado hallazgos",
        blank=True,
        default="Presiona el boton Hallazgo para informar una situacion detectada. El representante de gerencia recibira la solicitud para validar si corresponde su tratamiento.",
    )
    quality_policy = models.TextField("politica de la calidad", blank=True)
    mission = models.TextField("mision", blank=True)
    vision = models.TextField("vision", blank=True)
    sgc_home_title = models.CharField(
        "titulo Inicio SGC",
        max_length=220,
        default="Portal del Sistema de Gestion de Calidad",
    )
    sgc_home_subtitle = models.TextField(
        "subtitulo Inicio SGC",
        blank=True,
        default="Administracion documental, certificado vigente, comunicados internos y seguimiento de hallazgos del SGC.",
    )
    commitment_card_title = models.CharField(
        "titulo tarjeta compromiso",
        max_length=160,
        default="Nuestro compromiso",
    )
    commitment_card_text = models.TextField(
        "texto tarjeta compromiso",
        blank=True,
        default="Consulta la Politica de la Calidad, Mision y Vision disponibles para el sistema.",
    )
    commitment_dialog_title = models.CharField(
        "titulo ventana compromiso",
        max_length=160,
        default="Nuestro compromiso",
    )
    commitment_dialog_text = models.TextField(
        "texto ventana compromiso",
        blank=True,
        default="Principios declarados que orientan el Sistema de Gestion de Calidad y su comunicacion interna.",
    )
    commitment_image_caption = models.CharField(
        "texto bajo imagen compromiso",
        max_length=160,
        default="Presiona la imagen para ampliarla",
    )
    quality_commitment_image = models.FileField(
        "imagen nuestro compromiso",
        upload_to="empresa/identidad/",
        blank=True,
    )
    login_title = models.CharField(
        "titulo login",
        max_length=180,
        default="Bienvenido al Sistema de gestion",
    )
    login_help_text = models.CharField(
        "texto inferior login",
        max_length=220,
        default="Acceso restringido a usuarios autorizados del SGC.",
    )
    sgc_menu_label = models.CharField("menu sistema de gestion", max_length=80, default="Sistema de Gestion")
    sgc_home_label = models.CharField("submenu inicio SGC", max_length=80, default="Inicio SGC")
    documents_label = models.CharField("menu biblioteca documental", max_length=80, default="Biblioteca documental")
    forms_label = models.CharField("menu formularios", max_length=80, default="Formularios")
    certificate_label = models.CharField("menu certificado", max_length=80, default="Certificado ISO")
    processes_label = models.CharField("menu procesos", max_length=80, default="Procesos")
    updates_label = models.CharField("menu comunicados", max_length=80, default="Comunicados")
    training_label = models.CharField("menu capacitaciones", max_length=80, default="Capacitaciones")
    activities_label = models.CharField("menu actividades SGC", max_length=80, default="Actividades SGC")
    findings_label = models.CharField("menu hallazgos", max_length=80, default="Hallazgos")
    findings_board_label = models.CharField("submenu bandeja hallazgos", max_length=80, default="Bandeja de Hallazgos")
    new_finding_label = models.CharField("submenu nuevo hallazgo", max_length=80, default="Nuevo Hallazgo")
    my_tasks_label = models.CharField("submenu mis tareas", max_length=80, default="Mis Tareas")
    due_label = models.CharField("submenu vencidos", max_length=80, default="Vencidos")
    reports_label = models.CharField("submenu reportes", max_length=80, default="Reportes")
    maintainers_label = models.CharField("menu mantenedores", max_length=80, default="Mantenedores")
    show_findings_module = models.BooleanField("mostrar modulo de hallazgos", default=True)
    show_documents_module = models.BooleanField("mostrar biblioteca documental", default=True)
    show_certificate_module = models.BooleanField("mostrar certificado ISO", default=True)
    show_updates_module = models.BooleanField("mostrar actualizaciones", default=True)
    show_processes_module = models.BooleanField("mostrar procesos", default=True)
    show_training_module = models.BooleanField("mostrar capacitaciones", default=False)
    show_activities_module = models.BooleanField("mostrar actividades SGC", default=True)
    logo = models.FileField("logo principal", upload_to="empresa/logos/", blank=True)
    header_logo = models.FileField("logo encabezado", upload_to="empresa/logos/", blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuracion de empresa"
        verbose_name_plural = "Configuracion de empresa"

    def __str__(self):
        return self.company_name

    @classmethod
    def current(cls):
        profile, _created = cls.objects.get_or_create(pk=1)
        return profile

    @property
    def show_sgc_menu(self):
        return (
            self.show_documents_module
            or self.show_certificate_module
            or self.show_updates_module
            or self.show_processes_module
        )


class SystemHelpContent(models.Model):
    class Section(models.TextChoices):
        GENERAL = "general", "General"
        FINDINGS = "hallazgos", "Hallazgos"
        DOCUMENTS = "documentos", "Documentos"
        PROCESSES = "procesos", "Procesos"
        TRAINING = "capacitaciones", "Capacitaciones"

    class TrainingCategory(models.TextChoices):
        GENERAL = "general", "General SGC"
        INDUCTION = "induccion", "Induccion"
        FINDINGS = "hallazgos", "Hallazgos"
        DOCUMENTS = "documentos", "Documentos"
        PROCESSES = "procesos", "Procesos"
        AUDITS = "auditorias", "Auditorias"
        OTHER = "otro", "Otro"

    section = models.CharField("seccion", max_length=40, choices=Section.choices, default=Section.GENERAL)
    title = models.CharField("titulo", max_length=180)
    summary = models.CharField("resumen", max_length=240, blank=True)
    content = models.TextField("contenido")
    video_url = models.URLField("url video", blank=True)
    video_file = models.FileField("archivo de video", upload_to="empresa/capacitaciones/videos/", blank=True)
    image = models.FileField("imagen", upload_to="empresa/ayuda/", blank=True)
    training_category = models.CharField(
        "categoria capacitacion",
        max_length=40,
        choices=TrainingCategory.choices,
        default=TrainingCategory.GENERAL,
    )
    estimated_minutes = models.PositiveIntegerField("duracion estimada min.", default=0, blank=True)
    evaluation_time_minutes = models.PositiveIntegerField("tiempo evaluacion min.", default=5)
    passing_percentage = models.PositiveIntegerField("porcentaje aprobacion", default=60)
    valid_until = models.DateField("vigente hasta", null=True, blank=True)
    material_file = models.FileField("material descargable", upload_to="empresa/capacitaciones/", blank=True)
    is_active = models.BooleanField("activo", default=True)
    show_on_training = models.BooleanField("mostrar en capacitaciones", default=False)
    order = models.PositiveIntegerField("orden", default=0)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def has_training_resources(self):
        return bool(self.video_url or self.video_file or self.material_file)

    @property
    def has_video(self):
        return bool(self.video_file or self.video_url)

    @property
    def video_url_is_direct_file(self):
        parsed = urlparse(self.video_url or "")
        return parsed.path.lower().endswith((".mp4", ".webm", ".ogg"))

    @property
    def video_embed_url(self):
        parsed = urlparse(self.video_url or "")
        host = parsed.netloc.lower().replace("www.", "")
        if host in {"youtube.com", "m.youtube.com"}:
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            return f"https://www.youtube.com/embed/{video_id}" if video_id else ""
        if host == "youtu.be":
            video_id = parsed.path.strip("/")
            return f"https://www.youtube.com/embed/{video_id}" if video_id else ""
        if host == "vimeo.com":
            video_id = parsed.path.strip("/").split("/")[0]
            return f"https://player.vimeo.com/video/{video_id}" if video_id else ""
        return ""

    class Meta:
        ordering = ["section", "order", "title"]
        verbose_name = "Contenido de ayuda"
        verbose_name_plural = "Contenidos de ayuda"

    def __str__(self):
        return self.title


class AuditLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField("accion", max_length=120)
    module = models.CharField("modulo", max_length=80)
    object_repr = models.CharField("objeto", max_length=220, blank=True)
    details = models.TextField("detalle", blank=True)
    ip_address = models.GenericIPAddressField("ip", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Registro de auditoria"
        verbose_name_plural = "Registros de auditoria"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} - {self.action}"


class RolePermission(models.Model):
    role_name = models.CharField("rol", max_length=120)
    permission_code = models.CharField("permiso", max_length=80)
    is_allowed = models.BooleanField("permitido", default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("role_name", "permission_code")
        ordering = ["role_name", "permission_code"]
        verbose_name = "Permiso por rol"
        verbose_name_plural = "Permisos por rol"

    def __str__(self):
        status = "permitido" if self.is_allowed else "bloqueado"
        return f"{self.role_name} - {self.permission_code}: {status}"


class NotificationSettings(models.Model):
    email_alerts_enabled = models.BooleanField("activar alertas por correo", default=False)
    notify_finding_created = models.BooleanField("notificar creacion de hallazgo", default=True)
    notify_assignments = models.BooleanField("notificar asignaciones", default=True)
    notify_due_24h = models.BooleanField("alertar 24 horas antes del vencimiento", default=True)
    notify_overdue = models.BooleanField("alertar vencimientos incumplidos", default=True)
    sender_name = models.CharField("nombre remitente", max_length=120, default="Sistema de Gestion")
    sender_email = models.EmailField("correo remitente visible", blank=True)
    smtp_host = models.CharField("servidor SMTP", max_length=180, blank=True)
    smtp_port = models.PositiveIntegerField("puerto SMTP", default=587)
    smtp_use_tls = models.BooleanField("usar TLS", default=True)
    smtp_username = models.CharField("usuario SMTP", max_length=180, blank=True)
    smtp_password_encrypted = models.TextField("contrasena SMTP cifrada", blank=True)
    internal_copy_emails = models.TextField(
        "correos copia internos",
        blank=True,
        help_text="Un correo por linea. No guardar contrasenas ni credenciales en este campo.",
    )
    site_base_url = models.URLField(
        "URL publica del sitio",
        blank=True,
        help_text="URL usada para construir enlaces en correos, por ejemplo https://sg.tecnodatasa.cl.",
    )
    due_alert_check_frequency = models.CharField(
        "frecuencia sugerida revision vencimientos",
        max_length=80,
        default="Cada 1 hora",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuracion de notificaciones"
        verbose_name_plural = "Configuracion de notificaciones"

    def __str__(self):
        return "Notificaciones por correo"

    @classmethod
    def current(cls):
        settings_obj, _created = cls.objects.get_or_create(pk=1)
        return settings_obj

    def copy_recipients(self):
        return [email.strip() for email in self.internal_copy_emails.splitlines() if email.strip()]

    def set_smtp_password(self, value):
        if value:
            self.smtp_password_encrypted = encrypt_value(value)

    def get_smtp_password(self):
        return decrypt_value(self.smtp_password_encrypted)

    @property
    def has_smtp_password(self):
        return bool(self.smtp_password_encrypted)

    @property
    def is_smtp_configured(self):
        return bool(self.smtp_host and self.smtp_username and self.smtp_password_encrypted)


class AuthenticationSettings(models.Model):
    class Provider(models.TextChoices):
        MICROSOFT_ENTRA = "microsoft_entra", "Microsoft Entra ID"
        GOOGLE = "google", "Google"
        OTHER = "other", "Otro"

    local_login_enabled = models.BooleanField("login local habilitado", default=True)
    sso_enabled = models.BooleanField("SSO habilitado", default=False)
    provider = models.CharField(
        "proveedor SSO",
        max_length=40,
        choices=Provider.choices,
        default=Provider.MICROSOFT_ENTRA,
    )
    allowed_domain = models.CharField("dominio permitido", max_length=120, blank=True, default="tecnodatasa.cl")
    client_id = models.CharField("Client ID", max_length=220, blank=True)
    tenant_id = models.CharField("Tenant ID", max_length=220, blank=True)
    redirect_uri = models.URLField("Redirect URI", blank=True)
    client_secret_encrypted = models.TextField("Client Secret cifrado", blank=True)
    auto_create_users = models.BooleanField("crear usuarios automaticamente", default=False)
    default_role = models.CharField("rol por defecto nuevos usuarios", max_length=120, blank=True)
    force_sso_for_internal_users = models.BooleanField("forzar SSO para usuarios internos", default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuracion de autenticacion"
        verbose_name_plural = "Configuracion de autenticacion"

    def __str__(self):
        return "Autenticacion y SSO"

    @classmethod
    def current(cls):
        settings_obj, _created = cls.objects.get_or_create(pk=1)
        return settings_obj

    def set_client_secret(self, value):
        if value:
            self.client_secret_encrypted = encrypt_value(value)

    def get_client_secret(self):
        return decrypt_value(self.client_secret_encrypted)

    @property
    def has_client_secret(self):
        return bool(self.client_secret_encrypted)

    @property
    def is_sso_configured(self):
        return bool(self.client_id and self.tenant_id and self.redirect_uri and self.client_secret_encrypted)


class TrainingCompletion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="training_completions")
    content = models.ForeignKey(SystemHelpContent, on_delete=models.CASCADE, related_name="completions")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "content")
        ordering = ["-completed_at"]
        verbose_name = "Capacitacion completada"
        verbose_name_plural = "Capacitaciones completadas"

    def __str__(self):
        return f"{self.user} - {self.content}"


class TrainingAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="training_assignments")
    content = models.ForeignKey(SystemHelpContent, on_delete=models.CASCADE, related_name="assignments")
    due_date = models.DateField("fecha limite", null=True, blank=True)
    note = models.CharField("observacion", max_length=240, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="training_assignments_created",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "content")
        ordering = ["due_date", "-assigned_at"]
        verbose_name = "Capacitacion asignada"
        verbose_name_plural = "Capacitaciones asignadas"

    def __str__(self):
        return f"{self.content} -> {self.user}"


class TrainingQuestion(models.Model):
    class CorrectOption(models.TextChoices):
        A = "a", "A"
        B = "b", "B"
        C = "c", "C"
        D = "d", "D"

    content = models.ForeignKey(SystemHelpContent, on_delete=models.CASCADE, related_name="questions")
    question = models.CharField("pregunta", max_length=260)
    option_a = models.CharField("alternativa A", max_length=220)
    option_b = models.CharField("alternativa B", max_length=220)
    option_c = models.CharField("alternativa C", max_length=220, blank=True)
    option_d = models.CharField("alternativa D", max_length=220, blank=True)
    correct_option = models.CharField("respuesta correcta", max_length=1, choices=CorrectOption.choices)
    order = models.PositiveIntegerField("orden", default=0)
    is_active = models.BooleanField("activa", default=True)

    class Meta:
        ordering = ["content", "order", "id"]
        verbose_name = "Pregunta de capacitacion"
        verbose_name_plural = "Preguntas de capacitacion"

    def __str__(self):
        return f"{self.content} - {self.question}"


class TrainingAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="training_attempts")
    content = models.ForeignKey(SystemHelpContent, on_delete=models.CASCADE, related_name="attempts")
    score = models.PositiveIntegerField("puntaje", default=0)
    total_questions = models.PositiveIntegerField("total preguntas", default=0)
    passed = models.BooleanField("aprobado", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Intento de evaluacion"
        verbose_name_plural = "Intentos de evaluacion"

    @property
    def percentage(self):
        return round((self.score / self.total_questions) * 100) if self.total_questions else 0

    def __str__(self):
        return f"{self.user} - {self.content} ({self.percentage}%)"
