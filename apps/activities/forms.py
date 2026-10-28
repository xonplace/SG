from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Activity, ActivityAttachment, ActivityProgress


CONTROL_CLASS = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"


def active_user_queryset():
    User = get_user_model()
    return User.objects.filter(is_active=True).order_by("first_name", "last_name", "username")


class StyledFormMixin:
    def apply_styles(self):
        for field in self.fields.values():
            widget = field.widget
            current = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{current} {CONTROL_CLASS}".strip()


class ActivityCreateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Activity
        fields = [
            "title",
            "origin",
            "origin_other",
            "description",
            "priority",
            "responsible_users",
            "follow_up_due_at",
            "delivery_due_at",
            "review_assigned_to",
            "review_due_at",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "responsible_users": forms.CheckboxSelectMultiple(),
            "follow_up_due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "delivery_due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "review_due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["responsible_users"].queryset = active_user_queryset()
        self.fields["responsible_users"].label = "Responsables de la actividad"
        self.fields["responsible_users"].help_text = "Puedes seleccionar mas de una persona. Cualquiera podra registrar avances e informar resultado."
        self.fields["review_assigned_to"].queryset = active_user_queryset()
        self.fields["review_assigned_to"].label = "Responsable de revision y cierre"
        self.fields["review_assigned_to"].empty_label = "Seleccionar responsable de revision"
        self.fields["review_assigned_to"].required = False
        self.fields["review_due_at"].required = False
        self.fields["origin_other"].required = False
        self.apply_styles()
        self.fields["responsible_users"].widget.attrs["class"] = "sg-user-checklist"


class ActivityProgressForm(StyledFormMixin, forms.ModelForm):
    file = forms.FileField(label="Archivo de respaldo", required=False)
    file_description = forms.CharField(label="Descripcion del archivo", required=False, max_length=180)

    class Meta:
        model = ActivityProgress
        fields = ["progress_date", "progress_text"]
        widgets = {
            "progress_date": forms.DateInput(attrs={"type": "date"}),
            "progress_text": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()


class ActivityResultForm(StyledFormMixin, forms.ModelForm):
    file = forms.FileField(label="Evidencia del resultado", required=False)
    file_description = forms.CharField(label="Descripcion del archivo", required=False, max_length=180)

    class Meta:
        model = Activity
        fields = ["result"]
        widgets = {
            "result": forms.Textarea(attrs={"rows": 7}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()


class ActivityReviewAssignForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["review_assigned_to", "review_due_at"]
        widgets = {
            "review_due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["review_assigned_to"].queryset = active_user_queryset()
        self.fields["review_assigned_to"].empty_label = "Seleccionar responsable de revision"
        self.apply_styles()


class ActivityDeadlineRescheduleForm(StyledFormMixin, forms.Form):
    new_due_at = forms.DateTimeField(
        label="Nueva fecha de compromiso",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    reason = forms.CharField(
        label="Motivo y constancia del atraso",
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Indica el incumplimiento observado y el motivo por el que se acuerda un nuevo plazo.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()

    def clean_new_due_at(self):
        due_at = self.cleaned_data["new_due_at"]
        if due_at <= timezone.now():
            raise forms.ValidationError("La nueva fecha de compromiso debe ser futura.")
        return due_at


class ActivityReviewForm(StyledFormMixin, forms.Form):
    is_conform = forms.ChoiceField(
        label="Resultado de la revision",
        choices=(("yes", "Conforme, cerrar actividad"), ("no", "No conforme, devolver a tratamiento")),
        widget=forms.RadioSelect,
    )
    review_observations = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    new_delivery_due_at = forms.DateTimeField(
        label="Nuevo plazo de entrega si se devuelve",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
        self.fields["is_conform"].widget.attrs.pop("class", None)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_conform") == "no" and not cleaned.get("review_observations"):
            self.add_error("review_observations", "Indica el motivo de la devolucion.")
        return cleaned


class ActivityAttachmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ActivityAttachment
        fields = ["file", "description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
