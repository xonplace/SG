import random

from django import forms
from django.contrib.auth import get_user_model

from apps.core.models import TrainingAssignment, TrainingQuestion
from apps.findings.models import MasterProcess

from .models import (
    IsoCertificate,
    SgcDocument,
    SgcDocumentType,
    SgcImportantDates,
    SgcOfficialForm,
    SgcProcess,
    SgcProcessVersion,
    SgcUpdate,
)


class StyledSgcForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = "w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-950 outline-none ring-0 transition focus:border-neutral-950 focus:bg-white"
        textarea_class = f"{base_class} min-h-28 resize-y"
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.update({"class": "grid gap-2 text-sm text-neutral-800 md:grid-cols-2"})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "h-4 w-4 rounded border-neutral-300"})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": textarea_class})
            else:
                field.widget.attrs.update({"class": base_class})


class StyledSgcPlainForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = "w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-950 outline-none ring-0 transition focus:border-neutral-950 focus:bg-white"
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.update({"class": "grid gap-2 text-sm text-neutral-800 md:grid-cols-2"})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": f"{base_class} min-h-24 resize-y"})
            else:
                field.widget.attrs.update({"class": base_class})


class TrainingAssignmentForm(StyledSgcPlainForm):
    users = forms.ModelMultipleChoiceField(
        label="Usuarios asignados",
        queryset=get_user_model().objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    due_date = forms.DateField(label="Fecha limite", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    note = forms.CharField(label="Observacion", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, content=None, **kwargs):
        self.content = content
        super().__init__(*args, **kwargs)
        self.fields["users"].queryset = get_user_model().objects.filter(is_active=True).order_by(
            "first_name",
            "last_name",
            "username",
        )
        if content and not self.is_bound:
            self.fields["users"].initial = TrainingAssignment.objects.filter(content=content).values_list(
                "user_id",
                flat=True,
            )


class TrainingEvaluationForm(StyledSgcPlainForm):
    def __init__(self, *args, questions=None, **kwargs):
        self.questions = list(questions or [])
        super().__init__(*args, **kwargs)
        for question in self.questions:
            choices = [
                ("a", question.option_a),
                ("b", question.option_b),
            ]
            if question.option_c:
                choices.append(("c", question.option_c))
            if question.option_d:
                choices.append(("d", question.option_d))
            random.shuffle(choices)
            self.fields[f"question_{question.pk}"] = forms.ChoiceField(
                label=question.question,
                choices=choices,
                widget=forms.RadioSelect,
            )

    def score(self):
        score = 0
        for question in self.questions:
            if self.cleaned_data.get(f"question_{question.pk}") == question.correct_option:
                score += 1
        return score


class TrainingQuestionForm(StyledSgcForm):
    class Meta:
        model = TrainingQuestion
        fields = [
            "question",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_option",
            "order",
            "is_active",
        ]
        labels = {
            "question": "Pregunta",
            "option_a": "Alternativa A",
            "option_b": "Alternativa B",
            "option_c": "Alternativa C",
            "option_d": "Alternativa D",
            "correct_option": "Respuesta correcta",
            "order": "Orden",
            "is_active": "Pregunta activa",
        }
        widgets = {
            "question": forms.Textarea(attrs={"rows": 3}),
        }


class SgcDocumentForm(StyledSgcForm):
    process = forms.ChoiceField(label="Proceso asociado", required=False)
    document_type = forms.ChoiceField(label="Tipo")
    replace_previous = forms.BooleanField(
        label="Reemplazar version vigente anterior",
        required=False,
        initial=True,
        help_text="Si existe una version vigente con el mismo codigo, quedara automaticamente como obsoleta.",
    )

    def __init__(self, *args, **kwargs):
        self.is_new_version = kwargs.pop("is_new_version", False)
        self.previous_document = kwargs.pop("previous_document", None)
        super().__init__(*args, **kwargs)
        self.fields["process"].choices = [("", "Sin proceso asociado")] + [
            (process.name, process.name) for process in MasterProcess.objects.filter(is_active=True)
        ]
        type_choices = list(
            SgcDocumentType.objects.filter(is_active=True).values_list("value", "name")
        )
        current_type = self.instance.document_type if self.instance and self.instance.pk else ""
        if current_type and current_type not in dict(type_choices):
            current_label = SgcDocumentType.objects.filter(value=current_type).values_list("name", flat=True).first()
            type_choices.append((current_type, current_label or current_type.title()))
        self.fields["document_type"].choices = type_choices
        if not self.is_new_version:
            self.fields.pop("replace_previous", None)

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        uploaded_file = cleaned_data.get("file")

        if uploaded_file and status == "publicado" and not self.is_new_version:
            identity_key = SgcDocument.build_identity_key(
                uploaded_file.name,
                fallback=cleaned_data.get("title") or "",
            )
            published = SgcDocument.objects.filter(
                identity_key=identity_key,
                status="publicado",
            )
            if self.instance.pk:
                published = published.exclude(pk=self.instance.pk)
            if published.exists():
                self.add_error(
                    "file",
                    "Ya existe un documento vigente con este nombre. Utiliza la opcion Nueva version.",
                )

        if self.is_new_version and self.previous_document:
            version = (cleaned_data.get("version") or "").strip()
            if version and version.casefold() == (self.previous_document.version or "").strip().casefold():
                self.add_error("version", "La nueva version debe ser distinta de la version vigente.")

        return cleaned_data

    class Meta:
        model = SgcDocument
        fields = [
            "title",
            "code",
            "document_type",
            "clause",
            "version",
            "effective_date",
            "process",
            "summary",
            "file",
            "status",
            "replace_previous",
        ]
        labels = {
            "title": "Titulo",
            "code": "Codigo",
            "document_type": "Tipo",
            "clause": "Clausula",
            "version": "Version",
            "effective_date": "Fecha vigencia",
            "summary": "Resumen",
            "file": "Archivo",
            "status": "Estado",
        }
        widgets = {
            "effective_date": forms.DateInput(attrs={"type": "date"}),
            "summary": forms.Textarea(attrs={"rows": 4}),
        }


class SgcDocumentMetadataForm(StyledSgcForm):
    process = forms.ChoiceField(label="Proceso asociado", required=False)
    document_type = forms.ChoiceField(label="Tipo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["process"].choices = [("", "Sin proceso asociado")] + [
            (process.name, process.name) for process in MasterProcess.objects.filter(is_active=True)
        ]
        type_choices = list(
            SgcDocumentType.objects.filter(is_active=True).values_list("value", "name")
        )
        current_type = self.instance.document_type if self.instance and self.instance.pk else ""
        if current_type and current_type not in dict(type_choices):
            current_label = SgcDocumentType.objects.filter(value=current_type).values_list("name", flat=True).first()
            type_choices.append((current_type, current_label or current_type.title()))
        self.fields["document_type"].choices = type_choices

    class Meta:
        model = SgcDocument
        fields = [
            "code",
            "version",
            "document_type",
            "clause",
            "effective_date",
            "process",
            "summary",
        ]
        labels = {
            "code": "Codigo",
            "version": "Version",
            "document_type": "Tipo",
            "clause": "Clausula",
            "effective_date": "Fecha vigencia",
            "summary": "Resumen",
        }
        widgets = {
            "effective_date": forms.DateInput(attrs={"type": "date"}),
            "summary": forms.Textarea(attrs={"rows": 4}),
        }


class SgcOfficialFormForm(StyledSgcForm):
    processes = forms.ModelMultipleChoiceField(
        label="Procesos asociados",
        queryset=SgcProcess.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["processes"].queryset = SgcProcess.objects.filter(is_active=True).order_by("category", "name")

    class Meta:
        model = SgcOfficialForm
        fields = ["name", "code", "version", "file", "processes", "is_active", "show_on_home"]
        labels = {
            "name": "Nombre del formulario",
            "code": "Codigo",
            "version": "Version",
            "file": "Archivo del formulario",
            "is_active": "Formulario vigente",
            "show_on_home": "Marcar como formulario principal",
        }
        help_texts = {
            "file": "Si cargas un nuevo archivo al editar, reemplazara el archivo anterior.",
        }


class IsoCertificateForm(StyledSgcForm):
    class Meta:
        model = IsoCertificate
        fields = [
            "title",
            "standard",
            "certification_body",
            "scope",
            "issue_date",
            "expiry_date",
            "file",
            "is_active",
        ]
        labels = {
            "title": "Titulo",
            "standard": "Norma",
            "certification_body": "Organismo certificador",
            "scope": "Alcance",
            "issue_date": "Fecha emision",
            "expiry_date": "Fecha vencimiento",
            "file": "Certificado",
            "is_active": "Vigente",
        }
        widgets = {
            "scope": forms.Textarea(attrs={"rows": 4}),
            "issue_date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
        }


class SgcUpdateForm(StyledSgcForm):
    def __init__(self, *args, can_highlight_home=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not can_highlight_home:
            self.fields.pop("show_on_home", None)

    class Meta:
        model = SgcUpdate
        fields = ["title", "body", "published_at", "is_published", "show_on_home"]
        labels = {
            "title": "Titulo",
            "body": "Contenido",
            "published_at": "Fecha publicacion",
            "is_published": "Publicado",
            "show_on_home": "Mostrar en Inicio SGC",
        }
        widgets = {
            "body": forms.Textarea(attrs={"rows": 6}),
            "published_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class SgcImportantDatesForm(StyledSgcForm):
    def clean(self):
        cleaned_data = super().clean()
        date_fields = ["internal_audit_date", "external_audit_date", "management_review_date"]
        for field_name in date_fields:
            field_key = self.add_prefix(field_name)
            existing_value = getattr(self.instance, field_name, None)
            if self.is_bound and not self.data.get(field_key) and existing_value:
                cleaned_data[field_name] = existing_value
        return cleaned_data

    class Meta:
        model = SgcImportantDates
        fields = ["internal_audit_date", "external_audit_date", "management_review_date"]
        labels = {
            "internal_audit_date": "Fecha proxima auditoria interna",
            "external_audit_date": "Fecha proxima auditoria externa",
            "management_review_date": "Fecha proxima revision por la gerencia",
        }
        widgets = {
            "internal_audit_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "external_audit_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "management_review_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }


class SgcProcessForm(StyledSgcForm):
    class Meta:
        model = SgcProcess
        fields = ["code", "name", "category", "owner", "is_active"]
        labels = {
            "code": "Codigo",
            "name": "Nombre del proceso",
            "category": "Tipo de proceso",
            "owner": "Responsable",
            "is_active": "Activo",
        }


class SgcProcessVersionForm(StyledSgcForm):
    def clean(self):
        cleaned_data = super().clean()
        is_current = cleaned_data.get("is_current")
        if (
            self.instance
            and self.instance.pk
            and self.instance.process_id
            and not is_current
            and not self.instance.process.versions.exclude(pk=self.instance.pk).filter(is_current=True).exists()
        ):
            self.add_error(
                "is_current",
                "Debe existir al menos una version vigente del proceso.",
            )
        return cleaned_data

    class Meta:
        model = SgcProcessVersion
        fields = [
            "version",
            "published_at",
            "change_summary",
            "prose",
            "process_image",
            "flow_file",
            "procedure_file",
            "is_current",
        ]
        labels = {
            "version": "Version",
            "published_at": "Fecha publicacion",
            "change_summary": "Control de cambio",
            "prose": "Prosa / descripcion del proceso",
            "process_image": "Imagen del proceso",
            "flow_file": "Flujo descargable",
            "procedure_file": "Procedimiento asociado",
            "is_current": "Marcar como version vigente",
        }
        help_texts = {
            "is_current": "Si marcas esta opcion, las versiones anteriores quedaran historicas y no vigentes.",
        }
        widgets = {
            "published_at": forms.DateInput(attrs={"type": "date"}),
            "change_summary": forms.Textarea(attrs={"rows": 4}),
            "prose": forms.Textarea(attrs={"rows": 8}),
        }
