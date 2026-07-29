from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from .permissions import CORRECTION_GROUP, CORRECTIVE_ACTION_GROUP, VERIFICATION_GROUP
from .models import Correction, CorrectiveAction, DeadlineSetting, EffectivenessVerification, Evidence, Finding, MasterArea, MasterProcess, MasterSource

NORMATIVE_CLAUSE_CHOICES = [
    ("", "Seleccione clausula"),
    ("4.1 Comprension de la organizacion y su contexto", "4.1 Comprension de la organizacion y su contexto"),
    ("4.2 Comprension de necesidades y expectativas de partes interesadas", "4.2 Necesidades y expectativas de partes interesadas"),
    ("4.3 Alcance del Sistema de Gestion de Calidad", "4.3 Alcance del Sistema de Gestion de Calidad"),
    ("4.4 Sistema de Gestion de Calidad y sus procesos", "4.4 Sistema de Gestion de Calidad y procesos"),
    ("5.1 Liderazgo y compromiso", "5.1 Liderazgo y compromiso"),
    ("5.2 Politica de la Calidad", "5.2 Politica de la Calidad"),
    ("5.3 Roles, responsabilidades y autoridades", "5.3 Roles, responsabilidades y autoridades"),
    ("6.1 Acciones para abordar riesgos y oportunidades", "6.1 Riesgos y oportunidades"),
    ("6.2 Objetivos de la calidad y planificacion", "6.2 Objetivos de la calidad"),
    ("6.3 Planificacion de los cambios", "6.3 Planificacion de los cambios"),
    ("7.1 Recursos", "7.1 Recursos"),
    ("7.2 Competencia", "7.2 Competencia"),
    ("7.3 Toma de conciencia", "7.3 Toma de conciencia"),
    ("7.4 Comunicacion", "7.4 Comunicacion"),
    ("7.5 Informacion documentada", "7.5 Informacion documentada"),
    ("8.1 Planificacion y control operacional", "8.1 Planificacion y control operacional"),
    ("8.2 Requisitos para productos y servicios", "8.2 Requisitos para productos y servicios"),
    ("8.3 Diseno y desarrollo", "8.3 Diseno y desarrollo"),
    ("8.4 Control de procesos, productos y servicios externos", "8.4 Control externo"),
    ("8.5 Produccion y provision del servicio", "8.5 Produccion y provision del servicio"),
    ("8.6 Liberacion de productos y servicios", "8.6 Liberacion de productos y servicios"),
    ("8.7 Control de salidas no conformes", "8.7 Control de salidas no conformes"),
    ("9.1 Seguimiento, medicion, analisis y evaluacion", "9.1 Seguimiento, medicion, analisis y evaluacion"),
    ("9.2 Auditoria interna", "9.2 Auditoria interna"),
    ("9.3 Revision por la direccion", "9.3 Revision por la direccion"),
    ("10.1 Mejora", "10.1 Mejora"),
    ("10.2 No conformidad y accion correctiva", "10.2 No conformidad y accion correctiva"),
    ("10.3 Mejora continua", "10.3 Mejora continua"),
]


def role_user_queryset(group_name):
    return (
        get_user_model()
        .objects.filter(Q(groups__name=group_name) | Q(is_superuser=True), is_active=True)
        .distinct()
        .order_by("first_name", "last_name", "username")
    )


def require_fields(form, *field_names):
    for field_name in field_names:
        if field_name in form.fields:
            form.fields[field_name].required = True


class FindingCreateForm(forms.ModelForm):
    area = forms.ChoiceField(label="Area", required=False)
    process = forms.ChoiceField(label="Proceso", required=False)
    process_other = forms.CharField(label="Otro proceso", required=False, max_length=160)
    source = forms.ChoiceField(label="Fuente")
    source_other = forms.CharField(label="Otra fuente", required=False, max_length=160)
    evidence_file = forms.FileField(label="Adjuntar documento de respaldo", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["area"].choices = [("", "Seleccione area")] + [
            (area.name, area.name) for area in MasterArea.objects.filter(is_active=True)
        ]
        self.fields["process"].choices = [("", "Seleccione proceso")] + [
            (process.name, process.name) for process in MasterProcess.objects.filter(is_active=True)
        ]
        self.fields["source"].choices = [("", "Seleccione fuente")] + [
            (source.value, source.name) for source in MasterSource.objects.filter(is_active=True)
        ]
        base_class = "w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-950 outline-none ring-0 transition focus:border-neutral-950 focus:bg-white"
        textarea_class = f"{base_class} min-h-28 resize-y"
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "h-4 w-4 rounded border-neutral-300"})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": textarea_class})
            else:
                field.widget.attrs.update({"class": base_class})

    class Meta:
        model = Finding
        fields = [
            "description",
            "detection_date",
            "reported_by_name",
            "reported_by_email",
            "reported_by_position",
            "area",
            "process",
            "process_other",
            "source",
            "source_other",
            "objective_evidence",
            "evidence_file",
        ]
        labels = {
            "description": "Descripcion del hallazgo",
        }
        widgets = {
            "detection_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "objective_evidence": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        process = cleaned_data.get("process")
        process_other = cleaned_data.get("process_other")
        source = cleaned_data.get("source")
        source_other = cleaned_data.get("source_other")

        if process == "Otro" and not process_other:
            self.add_error("process_other", "Debe indicar el proceso cuando selecciona Otro.")
        if source == Finding.Source.OTRO and not source_other:
            self.add_error("source_other", "Debe indicar la fuente cuando selecciona Otro.")
        return cleaned_data

    def save(self, commit=True):
        finding = super().save(commit=False)
        if finding.process == "Otro" and self.cleaned_data.get("process_other"):
            finding.process_other = self.cleaned_data["process_other"]
        if finding.source == Finding.Source.OTRO and self.cleaned_data.get("source_other"):
            finding.source_other = self.cleaned_data["source_other"]
        if not finding.title:
            description = " ".join(finding.description.split())
            finding.title = description[:177] + "..." if len(description) > 180 else description
        if commit:
            finding.save()
            self.save_m2m()
        return finding


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = "w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-950 outline-none ring-0 transition focus:border-neutral-950 focus:bg-white"
        textarea_class = f"{base_class} min-h-28 resize-y"
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "h-4 w-4 rounded border-neutral-300"})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": textarea_class})
            else:
                field.widget.attrs.update({"class": base_class})


class FindingValidationForm(StyledModelForm):
    similar_previous_finding = forms.BooleanField(label="Existe hallazgo similar previo", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["classification"].choices = [("", "Seleccione clasificacion")] + list(Finding.Classification.choices)
        self.fields["normative_clause"] = forms.ChoiceField(
            label="Clausula normativa",
            choices=NORMATIVE_CLAUSE_CHOICES,
            required=False,
        )
        self.fields["similar_previous_finding_record"].queryset = Finding.objects.exclude(
            pk=self.instance.pk if self.instance and self.instance.pk else None
        ).order_by("-created_at")
        self.fields["similar_previous_finding_record"].label_from_instance = lambda finding: f"{finding.code} - {finding.description[:80]}"
        field_class = "w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-950 outline-none ring-0 transition focus:border-neutral-950 focus:bg-white"
        self.fields["normative_clause"].widget.attrs.update({"class": field_class})
        self.fields["similar_previous_finding_record"].widget.attrs.update({"class": field_class})

    def clean(self):
        cleaned_data = super().clean()
        applies_treatment = cleaned_data.get("applies_treatment")
        classification = cleaned_data.get("classification")
        no_apply_reason = cleaned_data.get("no_apply_reason")
        normative_clause = cleaned_data.get("normative_clause")
        similar_previous = cleaned_data.get("similar_previous_finding")
        similar_record = cleaned_data.get("similar_previous_finding_record")

        if applies_treatment is True and not classification:
            self.add_error("classification", "Debe clasificar el hallazgo como No Conformidad u Oportunidad de Mejora.")
        if applies_treatment is True and not normative_clause:
            self.add_error("normative_clause", "Debe seleccionar la clausula normativa asociada.")
        if applies_treatment is True and similar_previous and not similar_record:
            self.add_error("similar_previous_finding_record", "Debe seleccionar el hallazgo previo similar.")
        if applies_treatment is False and not no_apply_reason:
            self.add_error("no_apply_reason", "Debe indicar el motivo cuando el hallazgo no aplica.")
        if applies_treatment is False:
            cleaned_data["classification"] = ""
            cleaned_data["normative_clause"] = ""
            cleaned_data["similar_previous_finding"] = False
            cleaned_data["similar_previous_finding_record"] = None
        return cleaned_data

    class Meta:
        model = Finding
        fields = [
            "applies_treatment",
            "no_apply_reason",
            "classification",
            "normative_clause",
            "similar_previous_finding",
            "similar_previous_finding_record",
        ]
        labels = {
            "similar_previous_finding_record": "Hallazgo previo similar",
        }
        widgets = {
            "no_apply_reason": forms.Textarea(attrs={"rows": 3}),
        }


class CorrectionAssignForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = role_user_queryset(CORRECTION_GROUP)
        require_fields(self, "assigned_to", "action")

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("assigned_to"):
            self.add_error("assigned_to", "Debe asignar un responsable del tratamiento.")
        if not cleaned_data.get("action"):
            self.add_error("action", "Debe indicar las instrucciones del tratamiento.")
        return cleaned_data

    class Meta:
        model = Correction
        fields = ["assigned_to", "action"]
        labels = {
            "assigned_to": "Responsable del tratamiento",
            "action": "Indicaciones para el tratamiento",
        }
        widgets = {
            "action": forms.Textarea(attrs={"rows": 4}),
        }


class CorrectionSubmitForm(StyledModelForm):
    evidence_file = forms.FileField(label="Adjuntar evidencia de la correccion", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        require_fields(self, "result")

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("result"):
            self.add_error("result", "Debe registrar el detalle de la correccion aplicada.")
        return cleaned_data

    class Meta:
        model = Correction
        fields = ["result", "evidence_file"]
        labels = {
            "result": "Detalle de correccion aplicada",
        }
        widgets = {
            "result": forms.Textarea(attrs={"rows": 5}),
        }


class CorrectionReviewForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        require_fields(self, "is_conform")

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("is_conform") is None:
            self.add_error("is_conform", "Debe indicar si la correccion esta conforme.")
        if cleaned_data.get("is_conform") is False and not cleaned_data.get("review_observations"):
            self.add_error("review_observations", "Debe indicar observaciones cuando la correccion no esta conforme.")
        return cleaned_data

    class Meta:
        model = Correction
        fields = ["is_conform", "review_observations"]
        labels = {
            "is_conform": "Conforme con la correccion aplicada",
            "review_observations": "Motivo de desconformidad / observaciones",
        }
        widgets = {
            "review_observations": forms.Textarea(attrs={"rows": 4}),
        }


class CorrectiveActionAssignForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = role_user_queryset(CORRECTIVE_ACTION_GROUP)
        require_fields(self, "assigned_to")

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("assigned_to"):
            self.add_error("assigned_to", "Debe asignar un responsable.")
        return cleaned_data

    class Meta:
        model = CorrectiveAction
        fields = ["assigned_to"]
        labels = {
            "assigned_to": "Responsable",
        }


class CorrectiveActionSubmitForm(StyledModelForm):
    evidence_file = forms.FileField(label="Adjuntar evidencia de la accion correctiva", required=False)
    risk_matrix_review = forms.ChoiceField(
        label="Es necesario actualizar los riesgos",
        choices=[("", "Seleccione opcion"), ("si", "Si"), ("no", "No")],
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        require_fields(self, "conclusion", "action_description", "risk_matrix_review")

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("conclusion"):
            self.add_error("conclusion", "Debe registrar la conclusion o causa raiz.")
        if not cleaned_data.get("action_description"):
            self.add_error("action_description", "Debe registrar la accion correctiva.")
        if not cleaned_data.get("risk_matrix_review"):
            self.add_error("risk_matrix_review", "Debe indicar si es necesario actualizar los riesgos.")
        return cleaned_data

    class Meta:
        model = CorrectiveAction
        fields = [
            "conclusion",
            "action_description",
            "risk_matrix_review",
            "evidence_file",
        ]
        labels = {
            "conclusion": "Conclusion / causa raiz",
            "action_description": "Plan de accion para mitigar el hallazgo",
        }
        widgets = {
            "conclusion": forms.Textarea(attrs={"rows": 3}),
            "action_description": forms.Textarea(attrs={"rows": 4}),
        }


class CorrectiveActionReviewForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        require_fields(self, "is_conform")

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("is_conform") is None:
            self.add_error("is_conform", "Debe indicar si la accion esta conforme.")
        if cleaned_data.get("is_conform") is False and not cleaned_data.get("review_observations"):
            self.add_error("review_observations", "Debe indicar observaciones cuando la accion no esta conforme.")
        return cleaned_data

    class Meta:
        model = CorrectiveAction
        fields = ["is_conform", "review_observations"]
        labels = {
            "is_conform": "Conforme con el plan de accion",
            "review_observations": "Motivo de desconformidad / observaciones",
        }
        widgets = {
            "review_observations": forms.Textarea(attrs={"rows": 4}),
        }


class ImprovementPlanSubmitForm(StyledModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        require_fields(self, "action_description", "verification_method")

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("action_description"):
            self.add_error("action_description", "Debe registrar el plan de accion propuesto.")
        if not cleaned_data.get("verification_method"):
            self.add_error("verification_method", "Debe indicar el medio de verificacion de la implementacion.")
        return cleaned_data

    class Meta:
        model = CorrectiveAction
        fields = [
            "action_description",
            "verification_method",
            "risk_matrix_review",
        ]
        labels = {
            "action_description": "Plan de accion propuesto",
            "verification_method": "Medio de verificacion de la implementacion",
            "risk_matrix_review": "Observaciones / analisis complementario",
        }
        widgets = {
            "action_description": forms.Textarea(attrs={"rows": 5}),
            "risk_matrix_review": forms.Textarea(attrs={"rows": 4}),
        }


class ImprovementPlanReviewForm(CorrectiveActionReviewForm):
    def clean(self):
        cleaned_data = forms.ModelForm.clean(self)
        if cleaned_data.get("is_conform") is None:
            self.add_error("is_conform", "Debe indicar si el plan de accion esta conforme.")
        if cleaned_data.get("is_conform") is False and not cleaned_data.get("review_observations"):
            self.add_error("review_observations", "Debe indicar observaciones cuando el plan no esta conforme.")
        return cleaned_data

    class Meta(CorrectiveActionReviewForm.Meta):
        labels = {
            "is_conform": "Plan de accion conforme",
            "review_observations": "Observaciones de revision",
        }


class VerificationAssignForm(StyledModelForm):
    verification_days = forms.IntegerField(label="Plazo de seguimiento en dias habiles", min_value=1, initial=15)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = role_user_queryset(VERIFICATION_GROUP)
        require_fields(self, "assigned_to", "verification_days")

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("assigned_to"):
            self.add_error("assigned_to", "Debe asignar un responsable del seguimiento.")
        if not cleaned_data.get("verification_days"):
            self.add_error("verification_days", "Debe indicar el plazo de seguimiento.")
        return cleaned_data

    class Meta:
        model = EffectivenessVerification
        fields = ["assigned_to", "verification_days"]
        labels = {
            "assigned_to": "Responsable del seguimiento",
        }


class VerificationSubmitForm(StyledModelForm):
    additional_follow_up_days = forms.IntegerField(label="Dias para segundo seguimiento", min_value=1, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["additional_follow_up_assigned_to"].queryset = role_user_queryset(VERIFICATION_GROUP)
        require_fields(self, "technique", "effectiveness_criteria", "result", "effectiveness_percentage")

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("technique"):
            self.add_error("technique", "Debe registrar la tecnica de seguimiento.")
        if not cleaned_data.get("effectiveness_criteria"):
            self.add_error("effectiveness_criteria", "Debe registrar el criterio de medicion de eficacia.")
        if not cleaned_data.get("result"):
            self.add_error("result", "Debe registrar el resultado del seguimiento.")
        if cleaned_data.get("effectiveness_percentage") is None:
            self.add_error("effectiveness_percentage", "Debe registrar el porcentaje de efectividad.")
        if cleaned_data.get("requires_additional_follow_up"):
            if not cleaned_data.get("additional_follow_up_assigned_to"):
                self.add_error("additional_follow_up_assigned_to", "Debe asignar responsable del segundo seguimiento.")
            if not cleaned_data.get("additional_follow_up_days"):
                self.add_error("additional_follow_up_days", "Debe indicar plazo para el segundo seguimiento.")
        return cleaned_data

    class Meta:
        model = EffectivenessVerification
        fields = [
            "technique",
            "effectiveness_criteria",
            "result",
            "effectiveness_percentage",
            "requires_additional_follow_up",
            "additional_follow_up_assigned_to",
            "additional_follow_up_days",
        ]
        labels = {
            "technique": "Tecnica de seguimiento",
            "effectiveness_criteria": "Criterio de medicion de eficacia",
            "result": "Resultado",
            "effectiveness_percentage": "% efectividad",
            "requires_additional_follow_up": "Corresponde seguimiento adicional",
            "additional_follow_up_assigned_to": "Responsable segundo seguimiento",
        }
        widgets = {
            "effectiveness_criteria": forms.Textarea(attrs={"rows": 4}),
            "result": forms.Textarea(attrs={"rows": 5}),
        }


class VerificationReviewForm(StyledModelForm):
    close_finding = forms.BooleanField(label="Cerrar hallazgo", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        require_fields(self, "is_effective")

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("is_effective") is None:
            self.add_error("is_effective", "Debe indicar si el seguimiento fue eficaz.")
        if cleaned_data.get("is_effective") is False and not cleaned_data.get("observations"):
            self.add_error("observations", "Debe indicar observaciones cuando el seguimiento no fue eficaz.")
        if cleaned_data.get("close_finding") and cleaned_data.get("is_effective") is not True:
            self.add_error("close_finding", "Solo se puede cerrar el hallazgo si el seguimiento fue eficaz.")
        return cleaned_data

    class Meta:
        model = EffectivenessVerification
        fields = ["is_effective", "observations", "close_finding"]
        labels = {
            "is_effective": "Eficaz",
            "observations": "Observaciones de eficacia o devolucion",
        }
        widgets = {
            "observations": forms.Textarea(attrs={"rows": 4}),
        }


class EvidenceUploadForm(StyledModelForm):
    PHASE_GENERAL = "general"
    PHASE_CORRECTION = "correction"
    PHASE_CORRECTIVE_ACTION = "corrective_action"
    PHASE_VERIFICATION = "verification"

    phase = forms.ChoiceField(label="Etapa")

    def __init__(self, *args, finding=None, phase=None, **kwargs):
        self.finding = finding
        super().__init__(*args, **kwargs)
        choices = [(self.PHASE_GENERAL, "Hallazgo general")]
        if finding and hasattr(finding, "correction"):
            choices.append((self.PHASE_CORRECTION, "Correccion"))
        if finding and hasattr(finding, "corrective_action"):
            action_label = (
                "Plan de accion"
                if finding.is_improvement_classification
                else "Accion correctiva"
            )
            choices.append((self.PHASE_CORRECTIVE_ACTION, action_label))
        if finding and hasattr(finding, "effectiveness_verification"):
            choices.append((self.PHASE_VERIFICATION, "Seguimiento / verificacion"))
        self.fields["phase"].choices = choices
        valid_values = [value for value, _label in choices]
        if phase not in valid_values:
            phase = self.PHASE_GENERAL
        self.forced_phase = phase
        self.fields["phase"].initial = phase
        self.phase_label = dict(choices).get(phase, "Hallazgo general")
        self.fields["phase"].widget = forms.HiddenInput()

    def clean_phase(self):
        return self.forced_phase or self.cleaned_data["phase"]

    class Meta:
        model = Evidence
        fields = ["phase", "file", "description"]

    def save(self, commit=True):
        evidence = super().save(commit=False)
        evidence.finding = self.finding
        phase = self.cleaned_data["phase"]

        if phase == self.PHASE_CORRECTION:
            evidence.correction = self.finding.correction
        elif phase == self.PHASE_CORRECTIVE_ACTION:
            evidence.corrective_action = self.finding.corrective_action
        elif phase == self.PHASE_VERIFICATION:
            evidence.verification = self.finding.effectiveness_verification

        if commit:
            evidence.save()
        return evidence
