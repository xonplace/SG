from django.conf import settings
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActivityCodeSequence(models.Model):
    prefix = models.CharField(max_length=4, unique=True, default="ACT")
    next_number = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Secuencia de actividad"
        verbose_name_plural = "Secuencias de actividades"

    def __str__(self):
        return f"{self.prefix}{self.next_number:03d}"


class Activity(TimeStampedModel):
    class Origin(models.TextChoices):
        MANAGEMENT_REVIEW = "revision_gerencia", "Revision por la gerencia"
        CONTEXT_ANALYSIS = "analisis_contexto", "Analisis de contexto"
        MONTHLY_COMMITTEE = "comite_mensual", "Comite mensual"
        AUDIT = "auditoria", "Auditoria"
        RISK_OPPORTUNITY = "riesgos_oportunidades", "Riesgos y oportunidades"
        OTHER = "otro", "Otro"

    class Priority(models.TextChoices):
        LOW = "baja", "Baja"
        MEDIUM = "media", "Media"
        HIGH = "alta", "Alta"
        CRITICAL = "critica", "Critica"

    class Status(models.TextChoices):
        REGISTERED = "registrada", "Registrada"
        ASSIGNED = "asignada", "Asignada"
        IN_PROGRESS = "en_ejecucion", "En ejecucion"
        RESULT_SUBMITTED = "resultado_informado", "Resultado informado"
        REVIEW_ASSIGNED = "revision_asignada", "Revision asignada"
        RETURNED = "devuelta", "Devuelta a tratamiento"
        CLOSED = "cerrada", "Cerrada"

    code = models.CharField("codigo", max_length=20, unique=True, blank=True)
    title = models.CharField("actividad", max_length=180)
    description = models.TextField("descripcion")
    origin = models.CharField("origen", max_length=40, choices=Origin.choices)
    origin_other = models.CharField("otro origen", max_length=160, blank=True)
    priority = models.CharField("prioridad", max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField("estado", max_length=40, choices=Status.choices, default=Status.REGISTERED)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="responsable principal de la actividad",
        related_name="assigned_sgc_activities",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    responsible_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="responsables de la actividad",
        related_name="responsible_sgc_activities",
        blank=True,
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="asignado por",
        related_name="created_sgc_activities",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    follow_up_due_at = models.DateTimeField("fecha de seguimiento", null=True, blank=True)
    delivery_due_at = models.DateTimeField("fecha de entrega", null=True, blank=True)
    result = models.TextField("resultado final", blank=True)
    submitted_at = models.DateTimeField("fecha resultado informado", null=True, blank=True)
    review_assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="responsable de revision y cierre",
        related_name="assigned_sgc_activity_reviews",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    review_assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="revision asignada por",
        related_name="assigned_sgc_activity_review_requests",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    review_due_at = models.DateTimeField("plazo revision y cierre", null=True, blank=True)
    review_observations = models.TextField("observaciones de revision", blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="cerrado por",
        related_name="closed_sgc_activities",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    closed_at = models.DateTimeField("fecha cierre", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Actividad SGC"
        verbose_name_plural = "Actividades SGC"

    def __str__(self):
        return f"{self.code or 'Sin codigo'} - {self.title}"

    @classmethod
    def next_code(cls):
        with transaction.atomic():
            sequence, _created = ActivityCodeSequence.objects.select_for_update().get_or_create(prefix="ACT")
            code = f"{sequence.prefix}{sequence.next_number:03d}"
            sequence.next_number += 1
            sequence.save(update_fields=["next_number"])
            return code

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.next_code()
        super().save(*args, **kwargs)

    @property
    def origin_label(self):
        return self.origin_other if self.origin == self.Origin.OTHER and self.origin_other else self.get_origin_display()

    @property
    def is_closed(self):
        return self.status == self.Status.CLOSED

    @property
    def is_overdue(self):
        now = timezone.now()
        return any(due and due < now for due in [self.follow_up_due_at, self.delivery_due_at, self.review_due_at]) and not self.is_closed

    @property
    def next_due_at(self):
        candidates = [due for due in [self.follow_up_due_at, self.delivery_due_at, self.review_due_at] if due]
        return min(candidates) if candidates else None

    @property
    def progress_percentage(self):
        values = {
            self.Status.REGISTERED: 0,
            self.Status.ASSIGNED: 0,
            self.Status.IN_PROGRESS: 45,
            self.Status.RETURNED: 55,
            self.Status.RESULT_SUBMITTED: 70,
            self.Status.REVIEW_ASSIGNED: 85,
            self.Status.CLOSED: 100,
        }
        return values.get(self.status, 0)

    def user_is_responsible(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.assigned_to_id == user.id or self.responsible_users.filter(pk=user.pk).exists()

    @property
    def responsible_names(self):
        names = []
        for user in self.responsible_users.all():
            full_name = user.get_full_name().strip()
            names.append(full_name or user.username)
        if not names and self.assigned_to:
            full_name = self.assigned_to.get_full_name().strip()
            names.append(full_name or self.assigned_to.username)
        return ", ".join(names)

    def get_absolute_url(self):
        return reverse("activities:detail", args=[self.pk])


class ActivityProgress(TimeStampedModel):
    activity = models.ForeignKey(Activity, related_name="progress_entries", on_delete=models.CASCADE)
    progress_date = models.DateField("fecha avance", default=timezone.localdate)
    progress_text = models.TextField("avance")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-progress_date", "-created_at"]
        verbose_name = "Avance de actividad"
        verbose_name_plural = "Avances de actividades"

    def __str__(self):
        return f"{self.activity.code} - {self.progress_date:%d-%m-%Y}"


class ActivityAttachment(TimeStampedModel):
    activity = models.ForeignKey(Activity, related_name="attachments", on_delete=models.CASCADE)
    progress = models.ForeignKey(ActivityProgress, related_name="attachments", on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField("archivo", upload_to="actividades/%Y/%m/")
    description = models.CharField("descripcion", max_length=180, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Evidencia de actividad"
        verbose_name_plural = "Evidencias de actividades"

    def __str__(self):
        return self.description or self.file.name


class ActivityHistory(TimeStampedModel):
    activity = models.ForeignKey(Activity, related_name="history", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=160)
    previous_status = models.CharField(max_length=40, blank=True)
    new_status = models.CharField(max_length=40, blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Historial de actividad"
        verbose_name_plural = "Historial de actividades"

    def __str__(self):
        return f"{self.activity.code} - {self.action}"
