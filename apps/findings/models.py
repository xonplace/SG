from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FindingCodeSequence(models.Model):
    prefix = models.CharField(max_length=4, unique=True)
    next_number = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Secuencia de codigo"
        verbose_name_plural = "Secuencias de codigos"

    def __str__(self):
        return f"{self.prefix}{self.next_number:03d}"


class MasterArea(TimeStampedModel):
    name = models.CharField("area", max_length=160, unique=True)
    is_active = models.BooleanField("activo", default=True)
    order = models.PositiveIntegerField("orden", default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Area"
        verbose_name_plural = "Areas"

    def __str__(self):
        return self.name


class MasterProcess(TimeStampedModel):
    name = models.CharField("proceso", max_length=160, unique=True)
    is_active = models.BooleanField("activo", default=True)
    allows_custom_text = models.BooleanField("permite texto libre", default=False)
    order = models.PositiveIntegerField("orden", default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Proceso"
        verbose_name_plural = "Procesos"

    def __str__(self):
        return self.name


class MasterSource(TimeStampedModel):
    value = models.CharField("valor", max_length=40, unique=True)
    name = models.CharField("fuente", max_length=160)
    is_active = models.BooleanField("activo", default=True)
    allows_custom_text = models.BooleanField("permite texto libre", default=False)
    order = models.PositiveIntegerField("orden", default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Fuente"
        verbose_name_plural = "Fuentes"

    def __str__(self):
        return self.name


class DeadlineSetting(TimeStampedModel):
    validation_days = models.PositiveIntegerField("dias validacion del hallazgo", default=2)
    correction_major_days = models.PositiveIntegerField("dias correccion NC Mayor", default=5)
    correction_minor_days = models.PositiveIntegerField("dias correccion NC Menor", default=5)
    correction_improvement_days = models.PositiveIntegerField("dias correccion oportunidad de mejora", default=10)
    correction_review_days = models.PositiveIntegerField("dias revision correccion", default=2)
    corrective_action_days = models.PositiveIntegerField("dias accion correctiva", default=10)
    corrective_action_review_days = models.PositiveIntegerField("dias revision accion correctiva", default=2)
    verification_days = models.PositiveIntegerField("dias verificacion de eficacia", default=15)

    class Meta:
        verbose_name = "Plazo"
        verbose_name_plural = "Plazos"

    def __str__(self):
        return "Configuracion de plazos"

    @classmethod
    def current(cls):
        setting, _created = cls.objects.get_or_create(pk=1)
        return setting


class Finding(TimeStampedModel):
    class Status(models.TextChoices):
        INGRESADO = "ingresado", "Ingresado"
        EN_VALIDACION = "en_validacion", "En validacion"
        CERRADO_NO_APLICA = "cerrado_no_aplica", "Cerrado no aplica"
        CLASIFICADO = "clasificado", "Clasificado"
        CORRECCION_ASIGNADA = "correccion_asignada", "Correccion asignada"
        EN_CORRECCION = "en_correccion", "En correccion"
        CORRECCION_EN_REVISION = "correccion_en_revision", "Correccion en revision"
        CORRECCION_APROBADA = "correccion_aprobada", "Correccion aprobada"
        ACCION_CORRECTIVA_ASIGNADA = "accion_correctiva_asignada", "Accion correctiva asignada"
        EN_ACCION_CORRECTIVA = "en_accion_correctiva", "En accion correctiva"
        ACCION_CORRECTIVA_EN_REVISION = "accion_correctiva_en_revision", "Accion correctiva en revision"
        ACCION_CORRECTIVA_APROBADA = "accion_correctiva_aprobada", "Accion correctiva aprobada"
        SEGUIMIENTO_ASIGNADO = "seguimiento_asignado", "Seguimiento asignado"
        EN_SEGUIMIENTO = "en_seguimiento", "En seguimiento"
        SEGUIMIENTO_EN_REVISION = "seguimiento_en_revision", "Seguimiento en revision"
        CERRADO = "cerrado", "Cerrado"

    class Source(models.TextChoices):
        AUDITORIA_INTERNA = "auditoria_interna", "Auditoria interna"
        AUDITORIA_EXTERNA = "auditoria_externa", "Auditoria externa"
        RECLAMO = "reclamo", "Reclamo"
        SALIDA_NO_CONFORME = "salida_no_conforme", "Salida no conforme"
        REVISION_GERENCIA = "revision_gerencia", "Revision por la gerencia"
        FISCALIZACION = "fiscalizacion", "Fiscalizacion"
        DETECCION_INTERNA = "deteccion_interna", "Deteccion interna"
        REQUERIMIENTO = "requerimiento", "Requerimiento"
        OTRO = "otro", "Otro"

    class Classification(models.TextChoices):
        NO_CONFORMIDAD_MAYOR = "no_conformidad_mayor", "No Conformidad Mayor"
        NO_CONFORMIDAD_MENOR = "no_conformidad_menor", "No Conformidad Menor"
        OPORTUNIDAD_MEJORA = "oportunidad_mejora", "Oportunidad de Mejora"
        OPORTUNIDAD = "oportunidad", "Oportunidad"

    code = models.CharField("codigo", max_length=20, unique=True, blank=True)
    title = models.CharField("titulo", max_length=180)
    description = models.TextField("descripcion")
    detection_date = models.DateField("fecha de deteccion")
    report_date = models.DateField("fecha de registro", default=timezone.localdate)
    reported_by_name = models.CharField("informado por", max_length=160)
    reported_by_email = models.EmailField("correo del informante")
    reported_by_position = models.CharField("cargo", max_length=160, blank=True)
    area = models.CharField("area", max_length=160, blank=True)
    process = models.CharField("proceso", max_length=160, blank=True)
    process_other = models.CharField("otro proceso", max_length=160, blank=True)
    source = models.CharField("fuente", max_length=40, choices=Source.choices)
    source_other = models.CharField("otra fuente", max_length=160, blank=True)
    normative_clause = models.CharField("clausula normativa / documento", max_length=200, blank=True)
    objective_evidence = models.TextField("evidencia objetiva", blank=True)
    status = models.CharField("estado", max_length=40, choices=Status.choices, default=Status.INGRESADO)
    applies_treatment = models.BooleanField("aplica tratamiento", null=True, blank=True)
    no_apply_reason = models.TextField("motivo no aplica", blank=True)
    classification = models.CharField("clasificacion", max_length=40, choices=Classification.choices, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="aprobado por",
        related_name="approved_findings",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    similar_previous_finding = models.BooleanField("hallazgo similar previo", null=True, blank=True)
    similar_previous_finding_record = models.ForeignKey(
        "self",
        verbose_name="hallazgo previo similar",
        related_name="related_similar_findings",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    corrective_action_reference = models.CharField("identificacion de AC", max_length=120, blank=True)
    has_real_or_potential_risk = models.BooleanField("riesgo real o potencial", null=True, blank=True)
    risk_identification = models.CharField("identificacion de riesgo", max_length=200, blank=True)
    risk_treated = models.BooleanField("riesgo tratado", null=True, blank=True)
    representative = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Representante de la Gerencia",
        related_name="represented_findings",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    validation_due_at = models.DateTimeField("plazo validacion", null=True, blank=True)
    correction_due_at = models.DateTimeField("plazo correccion", null=True, blank=True)
    correction_review_due_at = models.DateTimeField("plazo revision correccion", null=True, blank=True)
    corrective_action_due_at = models.DateTimeField("plazo accion correctiva", null=True, blank=True)
    corrective_action_review_due_at = models.DateTimeField("plazo revision accion correctiva", null=True, blank=True)
    verification_due_at = models.DateTimeField("plazo verificacion eficacia", null=True, blank=True)
    validation_alert_24h_sent = models.BooleanField(default=False)
    correction_alert_24h_sent = models.BooleanField(default=False)
    correction_review_alert_24h_sent = models.BooleanField(default=False)
    corrective_action_alert_24h_sent = models.BooleanField(default=False)
    corrective_action_review_alert_24h_sent = models.BooleanField(default=False)
    verification_alert_24h_sent = models.BooleanField(default=False)
    validation_overdue_alert_sent = models.BooleanField(default=False)
    correction_overdue_alert_sent = models.BooleanField(default=False)
    correction_review_overdue_alert_sent = models.BooleanField(default=False)
    corrective_action_overdue_alert_sent = models.BooleanField(default=False)
    corrective_action_review_overdue_alert_sent = models.BooleanField(default=False)
    verification_overdue_alert_sent = models.BooleanField(default=False)
    closed_at = models.DateTimeField("fecha cierre", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Hallazgo"
        verbose_name_plural = "Hallazgos"

    def __str__(self):
        return f"{self.code or 'Sin codigo'} - {self.title}"

    @staticmethod
    def _code_prefix_for_classification(classification):
        if classification in {
            Finding.Classification.NO_CONFORMIDAD_MAYOR,
            Finding.Classification.NO_CONFORMIDAD_MENOR,
        }:
            return "NC"
        if classification in {Finding.Classification.OPORTUNIDAD_MEJORA, Finding.Classification.OPORTUNIDAD}:
            return "OM"
        return ""

    @classmethod
    def _next_code(cls, prefix):
        with transaction.atomic():
            sequence = FindingCodeSequence.objects.select_for_update().filter(prefix=prefix).first()
            if sequence is None:
                sequence = FindingCodeSequence.objects.create(prefix=prefix, next_number=cls._existing_next_number(prefix))
            code = f"{prefix}{sequence.next_number:03d}"
            sequence.next_number += 1
            sequence.save(update_fields=["next_number"])
        return code

    @classmethod
    def _existing_next_number(cls, prefix):
        next_number = 1
        existing_codes = cls.objects.filter(code__startswith=prefix).values_list("code", flat=True)
        for code in existing_codes:
            suffix = code.removeprefix(prefix)
            if suffix.isdigit():
                next_number = max(next_number, int(suffix) + 1)
        return next_number

    def assign_classified_code(self):
        prefix = self._code_prefix_for_classification(self.classification)
        if not prefix:
            raise ValidationError("Debe clasificar el hallazgo antes de asignar codigo definitivo.")
        if not self.code.startswith(prefix):
            self.code = self._next_code(prefix)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._next_code("H")
        super().save(*args, **kwargs)

    @property
    def is_closed(self):
        return self.status in {self.Status.CERRADO, self.Status.CERRADO_NO_APLICA}

    @property
    def source_label(self):
        if self.source == self.Source.OTRO and self.source_other:
            return self.source_other
        return self.get_source_display()

    @property
    def process_label(self):
        if self.process == "Otro" and self.process_other:
            return self.process_other
        return self.process

    @property
    def is_improvement_classification(self):
        return self.classification in {self.Classification.OPORTUNIDAD_MEJORA, self.Classification.OPORTUNIDAD}


class Correction(TimeStampedModel):
    finding = models.OneToOneField(Finding, related_name="correction", on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="assigned_corrections",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    action = models.TextField(blank=True)
    result = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reviewed_corrections",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_conform = models.BooleanField(null=True, blank=True)
    review_observations = models.TextField(blank=True)

    class Meta:
        verbose_name = "Correccion"
        verbose_name_plural = "Correcciones"

    def __str__(self):
        return f"Correccion {self.finding.code}"


class CorrectiveAction(TimeStampedModel):
    class AnalysisTechnique(models.TextChoices):
        FIVE_WHYS = "5_por_que", "5 Por que"
        ISHIKAWA = "ishikawa", "Ishikawa"
        OTHER = "otro", "Otro"

    finding = models.OneToOneField(Finding, related_name="corrective_action", on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="assigned_corrective_actions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    analysis_technique = models.CharField(max_length=30, choices=AnalysisTechnique.choices, blank=True)
    analysis_technique_other = models.TextField(blank=True)
    question_1 = models.CharField(max_length=250, blank=True)
    answer_1 = models.TextField(blank=True)
    question_2 = models.CharField(max_length=250, blank=True)
    answer_2 = models.TextField(blank=True)
    question_3 = models.CharField(max_length=250, blank=True)
    answer_3 = models.TextField(blank=True)
    question_4 = models.CharField(max_length=250, blank=True)
    answer_4 = models.TextField(blank=True)
    question_5 = models.CharField(max_length=250, blank=True)
    answer_5 = models.TextField(blank=True)
    conclusion = models.TextField(blank=True)
    action_description = models.TextField("accion correctiva", blank=True)
    recurrence_prevention = models.TextField("accion para evitar recurrencia", blank=True)
    verification_method = models.CharField("medio de verificacion", max_length=200, blank=True)
    risk_matrix_review = models.TextField("revision matriz de riesgos", blank=True)
    resources_hours = models.DecimalField("recursos HH", max_digits=8, decimal_places=2, null=True, blank=True)
    resources_money = models.DecimalField("recursos M$", max_digits=12, decimal_places=2, null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reviewed_corrective_actions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_conform = models.BooleanField(null=True, blank=True)
    review_observations = models.TextField(blank=True)

    class Meta:
        verbose_name = "Accion correctiva"
        verbose_name_plural = "Acciones correctivas"

    def __str__(self):
        return f"Accion correctiva {self.finding.code}"


class EffectivenessVerification(TimeStampedModel):
    finding = models.OneToOneField(Finding, related_name="effectiveness_verification", on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="assigned_verifications",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    technique = models.CharField("tecnica de seguimiento", max_length=200, blank=True)
    effectiveness_criteria = models.TextField("criterio medicion eficacia", blank=True)
    result = models.TextField("resultado", blank=True)
    effectiveness_percentage = models.DecimalField("% efectividad", max_digits=5, decimal_places=2, null=True, blank=True)
    requires_additional_follow_up = models.BooleanField("requiere seguimiento adicional", default=False)
    additional_follow_up_assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="additional_assigned_verifications",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    additional_follow_up_due_at = models.DateTimeField("plazo segundo seguimiento", null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reviewed_verifications",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_effective = models.BooleanField("eficaz", null=True, blank=True)
    observations = models.TextField("observaciones", blank=True)

    class Meta:
        verbose_name = "Verificacion de eficacia"
        verbose_name_plural = "Verificaciones de eficacia"

    def __str__(self):
        return f"Verificacion {self.finding.code}"


class Evidence(TimeStampedModel):
    finding = models.ForeignKey(Finding, related_name="evidences", on_delete=models.CASCADE)
    correction = models.ForeignKey(Correction, related_name="evidences", on_delete=models.CASCADE, null=True, blank=True)
    corrective_action = models.ForeignKey(
        CorrectiveAction,
        related_name="evidences",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    verification = models.ForeignKey(
        EffectivenessVerification,
        related_name="evidences",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    file = models.FileField(upload_to="evidencias/%Y/%m/")
    description = models.CharField(max_length=250, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Evidencia"
        verbose_name_plural = "Evidencias"

    def __str__(self):
        return self.description or self.file.name


class FindingHistory(TimeStampedModel):
    finding = models.ForeignKey(Finding, related_name="history", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=160)
    previous_status = models.CharField(max_length=40, blank=True)
    new_status = models.CharField(max_length=40, blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Historial de hallazgo"
        verbose_name_plural = "Historial de hallazgos"

    def __str__(self):
        return f"{self.finding.code} - {self.action}"


class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=160)

    class Meta:
        ordering = ["date"]
        verbose_name = "Feriado"
        verbose_name_plural = "Feriados"

    def __str__(self):
        return f"{self.date} - {self.name}"
