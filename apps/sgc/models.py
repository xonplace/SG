from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from pathlib import Path
import re


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class IsoClause(models.TextChoices):
    CLAUSE_1 = "1", "Clausula 1 - Alcance"
    CLAUSE_2 = "2", "Clausula 2 - Referencias normativas"
    CLAUSE_3 = "3", "Clausula 3 - Terminos y definiciones"
    CLAUSE_4 = "4", "Clausula 4 - Contexto de la organizacion"
    CLAUSE_5 = "5", "Clausula 5 - Liderazgo"
    CLAUSE_6 = "6", "Clausula 6 - Planificacion"
    CLAUSE_7 = "7", "Clausula 7 - Apoyo"
    CLAUSE_8 = "8", "Clausula 8 - Operacion"
    CLAUSE_9 = "9", "Clausula 9 - Evaluacion del desempeno"
    CLAUSE_10 = "10", "Clausula 10 - Mejora"


class DocumentType(models.TextChoices):
    PROCEDURE = "procedimiento", "Procedimiento"
    FORM = "formulario", "Formulario"
    INSTRUCTION = "instructivo", "Instructivo"
    RECORD = "registro", "Registro"
    POLICY = "politica", "Politica"
    MANUAL = "manual", "Manual"
    CERTIFICATE = "certificado", "Certificado"
    EXTERNAL_STANDARD = "normativa-externa", "Normativa externa"
    OTHER = "otro", "Otro"


class PublicationStatus(models.TextChoices):
    DRAFT = "borrador", "Borrador"
    PUBLISHED = "publicado", "Publicado"
    ARCHIVED = "archivado", "Archivado"
    OBSOLETE = "obsoleto", "Obsoleto"


class ProcessCategory(models.TextChoices):
    OPERATIONAL = "operacional", "Operacional"
    SUPPORT = "apoyo", "Apoyo"


class SgcDocumentType(models.Model):
    value = models.SlugField("valor interno", max_length=30, unique=True, editable=False)
    name = models.CharField("tipo de documento", max_length=100, unique=True)
    order = models.PositiveIntegerField("orden", default=0)
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Tipo de documento"
        verbose_name_plural = "Tipos de documento"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.value:
            self.value = slugify(self.name)[:30]
        super().save(*args, **kwargs)


class SgcDocument(TimeStampedModel):
    title = models.CharField("titulo", max_length=220)
    code = models.CharField("codigo", max_length=80, blank=True)
    document_type = models.CharField("tipo", max_length=30)
    clause = models.CharField("clausula", max_length=3, choices=IsoClause.choices)
    version = models.CharField("version", max_length=40, blank=True)
    effective_date = models.DateField("fecha vigencia", null=True, blank=True)
    process = models.CharField("proceso asociado", max_length=160, blank=True)
    summary = models.TextField("resumen", blank=True)
    file = models.FileField("archivo", upload_to="sgc/documentos/%Y/%m/", max_length=500)
    status = models.CharField("estado", max_length=20, choices=PublicationStatus.choices, default=PublicationStatus.PUBLISHED)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    obsolete_at = models.DateTimeField("fecha obsolescencia", null=True, blank=True)
    obsolete_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="obsolete_sgc_documents",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    obsolete_reason = models.TextField("motivo de baja / reemplazo", blank=True)
    replaced_by = models.ForeignKey(
        "self",
        related_name="previous_versions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    identity_key = models.CharField(
        "identidad documental",
        max_length=500,
        blank=True,
        db_index=True,
        editable=False,
    )

    class Meta:
        ordering = ["clause", "document_type", "title"]
        verbose_name = "Documento SGC"
        verbose_name_plural = "Documentos SGC"

    def __str__(self):
        return self.title

    @staticmethod
    def build_identity_key(file_name, fallback=""):
        source = Path(file_name).stem if file_name else fallback
        without_version = re.sub(
            r"(?i)(?<![a-z0-9])v(?:er(?:sion)?)?[\s._-]*\d+(?:[._-]\d+)*(?![a-z0-9])",
            " ",
            source,
        )
        return slugify(without_version) or slugify(source)

    @property
    def document_key(self):
        return self.identity_key or self.build_identity_key(
            self.file.name if self.file else "",
            fallback=self.title,
        )

    def version_family_queryset(self):
        return SgcDocument.objects.filter(identity_key=self.document_key)

    def save(self, *args, **kwargs):
        if not self.identity_key:
            self.identity_key = self.build_identity_key(
                self.file.name if self.file else "",
                fallback=self.title,
            )
        super().save(*args, **kwargs)

    @property
    def file_filename(self):
        return Path(self.file.name).name if self.file else ""

    @property
    def document_type_label(self):
        document_type = SgcDocumentType.objects.filter(value=self.document_type).first()
        return document_type.name if document_type else self.document_type.replace("-", " ").title()

    @property
    def file_extension(self):
        return self.file.name.rsplit(".", 1)[-1].lower() if "." in self.file.name else ""

    @property
    def format_label(self):
        extension = self.file_extension
        if extension == "pdf":
            return "PDF"
        if extension in {"doc", "docx"}:
            return "Word"
        if extension in {"xls", "xlsx", "xlsm"}:
            return "Excel"
        if extension in {"ppt", "pptx"}:
            return "PowerPoint"
        if extension in {"jpg", "jpeg", "png"}:
            return "Imagen"
        if extension in {"msg", "eml"}:
            return "Correo"
        return extension.upper() or "Archivo"

    @property
    def format_icon(self):
        extension = self.file_extension
        if extension == "pdf":
            return "PDF"
        if extension in {"doc", "docx"}:
            return "W"
        if extension in {"xls", "xlsx", "xlsm"}:
            return "X"
        if extension in {"ppt", "pptx"}:
            return "P"
        if extension in {"jpg", "jpeg", "png"}:
            return "IMG"
        if extension in {"msg", "eml"}:
            return "@"
        return "DOC"

    @property
    def format_badge_class(self):
        extension = self.file_extension
        if extension == "pdf":
            return "sg-format-pdf"
        if extension in {"doc", "docx"}:
            return "sg-format-word"
        if extension in {"xls", "xlsx", "xlsm"}:
            return "sg-format-excel"
        if extension in {"ppt", "pptx"}:
            return "sg-format-powerpoint"
        if extension in {"jpg", "jpeg", "png"}:
            return "sg-format-image"
        if extension in {"msg", "eml"}:
            return "sg-format-mail"
        return "sg-format-file"


class DocumentEventType(models.TextChoices):
    PUBLISHED = "publicado", "Documento publicado"
    UPDATED = "actualizado", "Metadatos actualizados"
    REPLACED = "reemplazado", "Version reemplazada"
    OBSOLETED = "baja", "Documento dado de baja"
    RESTORED = "restaurado", "Documento restaurado"
    DELETED = "eliminado", "Documento eliminado"


class SgcDocumentEvent(models.Model):
    document = models.ForeignKey(
        SgcDocument,
        related_name="events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    family_key = models.CharField("familia documental", max_length=300, db_index=True)
    document_label = models.CharField("documento", max_length=300)
    version = models.CharField("version", max_length=40, blank=True)
    event_type = models.CharField("evento", max_length=20, choices=DocumentEventType.choices)
    detail = models.TextField("detalle", blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="sgc_document_events",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "Evento documental"
        verbose_name_plural = "Eventos documentales"

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.document_label}"


class SgcOfficialForm(TimeStampedModel):
    name = models.CharField("nombre del formulario", max_length=220)
    code = models.CharField("codigo", max_length=80, blank=True)
    version = models.CharField("version", max_length=40)
    file = models.FileField("archivo", upload_to="sgc/formularios/%Y/%m/", max_length=500)
    processes = models.ManyToManyField("SgcProcess", related_name="official_forms", blank=True)
    is_active = models.BooleanField("vigente", default=True)
    show_on_home = models.BooleanField("mostrar en Inicio SGC", default=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["name", "version"]
        verbose_name = "Formulario SGC"
        verbose_name_plural = "Formularios SGC"

    def __str__(self):
        return f"{self.name} {self.version}"

    @property
    def file_extension(self):
        return self.file.name.rsplit(".", 1)[-1].lower() if "." in self.file.name else ""

    @property
    def file_filename(self):
        return Path(self.file.name).name if self.file else ""

    @property
    def format_label(self):
        extension = self.file_extension
        if extension == "pdf":
            return "PDF"
        if extension in {"doc", "docx"}:
            return "Word"
        if extension in {"xls", "xlsx", "xlsm"}:
            return "Excel"
        if extension in {"ppt", "pptx"}:
            return "PowerPoint"
        if extension in {"jpg", "jpeg", "png"}:
            return "Imagen"
        return extension.upper() or "Archivo"

    @property
    def format_icon(self):
        extension = self.file_extension
        if extension == "pdf":
            return "PDF"
        if extension in {"doc", "docx"}:
            return "W"
        if extension in {"xls", "xlsx", "xlsm"}:
            return "X"
        if extension in {"ppt", "pptx"}:
            return "P"
        if extension in {"jpg", "jpeg", "png"}:
            return "IMG"
        return "DOC"

    @property
    def format_badge_class(self):
        extension = self.file_extension
        if extension == "pdf":
            return "sg-format-pdf"
        if extension in {"doc", "docx"}:
            return "sg-format-word"
        if extension in {"xls", "xlsx", "xlsm"}:
            return "sg-format-excel"
        if extension in {"ppt", "pptx"}:
            return "sg-format-powerpoint"
        if extension in {"jpg", "jpeg", "png"}:
            return "sg-format-image"
        return "sg-format-file"


class IsoCertificate(TimeStampedModel):
    title = models.CharField("titulo", max_length=220, default="Certificado ISO vigente")
    standard = models.CharField("norma", max_length=120, default="ISO 9001")
    certification_body = models.CharField("organismo certificador", max_length=180, blank=True)
    scope = models.TextField("alcance", blank=True)
    issue_date = models.DateField("fecha emision", null=True, blank=True)
    expiry_date = models.DateField("fecha vencimiento", null=True, blank=True)
    file = models.FileField("certificado", upload_to="sgc/certificados/%Y/%m/", max_length=500)
    is_active = models.BooleanField("vigente", default=True)

    class Meta:
        ordering = ["-is_active", "-expiry_date"]
        verbose_name = "Certificado ISO"
        verbose_name_plural = "Certificados ISO"

    def __str__(self):
        return self.title

    @property
    def days_to_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.localdate()).days


class SgcUpdate(TimeStampedModel):
    title = models.CharField("titulo", max_length=220)
    body = models.TextField("contenido")
    published_at = models.DateTimeField("fecha publicacion", default=timezone.now)
    is_published = models.BooleanField("publicado", default=True)
    show_on_home = models.BooleanField("mostrar en Inicio SGC", default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "Actualizacion SGC"
        verbose_name_plural = "Actualizaciones SGC"

    def __str__(self):
        return self.title


class SgcImportantDates(TimeStampedModel):
    external_audit_date = models.DateField("fecha proxima auditoria externa", null=True, blank=True)
    internal_audit_date = models.DateField("fecha proxima auditoria interna", null=True, blank=True)
    management_review_date = models.DateField("fecha proxima revision por la gerencia", null=True, blank=True)

    class Meta:
        verbose_name = "Fecha importante SGC"
        verbose_name_plural = "Fechas importantes SGC"

    def __str__(self):
        return "Fechas importantes SGC"

    @classmethod
    def current(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class SgcProcess(TimeStampedModel):
    code = models.CharField("codigo", max_length=80, unique=True)
    name = models.CharField("nombre del proceso", max_length=220)
    category = models.CharField("tipo de proceso", max_length=30, choices=ProcessCategory.choices)
    owner = models.CharField("responsable", max_length=160, blank=True)
    description = models.TextField("descripcion general", blank=True)
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        ordering = ["category", "name"]
        verbose_name = "Proceso SGC"
        verbose_name_plural = "Procesos SGC"

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def current_version(self):
        return self.versions.filter(is_current=True).first()


class SgcProcessVersion(TimeStampedModel):
    process = models.ForeignKey(SgcProcess, related_name="versions", on_delete=models.CASCADE)
    version = models.CharField("version", max_length=40)
    published_at = models.DateField("fecha publicacion", default=timezone.localdate)
    change_summary = models.TextField("control de cambio")
    prose = models.TextField("descripcion del proceso", blank=True)
    process_image = models.FileField("imagen del proceso", upload_to="sgc/procesos/imagenes/%Y/%m/", max_length=500, blank=True)
    flow_file = models.FileField("archivo flujo descargable", upload_to="sgc/procesos/flujos/%Y/%m/", max_length=500, blank=True)
    procedure_file = models.FileField("procedimiento asociado", upload_to="sgc/procesos/procedimientos/%Y/%m/", max_length=500, blank=True)
    is_current = models.BooleanField("version vigente", default=True)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        unique_together = [("process", "version")]
        verbose_name = "Version de proceso"
        verbose_name_plural = "Versiones de procesos"

    def __str__(self):
        return f"{self.process.code} {self.version}"

    @property
    def process_image_filename(self):
        return Path(self.process_image.name).name if self.process_image else ""

    @property
    def flow_filename(self):
        return Path(self.flow_file.name).name if self.flow_file else ""

    @property
    def procedure_filename(self):
        return Path(self.procedure_file.name).name if self.procedure_file else ""

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_current:
            self.process.versions.exclude(pk=self.pk).filter(is_current=True).update(is_current=False)
