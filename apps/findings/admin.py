from django.contrib import admin

from .models import (
    Correction,
    CorrectiveAction,
    EffectivenessVerification,
    Evidence,
    Finding,
    FindingCodeSequence,
    FindingHistory,
    Holiday,
    DeadlineSetting,
    MasterArea,
    MasterProcess,
    MasterSource,
)


class CorrectionInline(admin.StackedInline):
    model = Correction
    extra = 0


class CorrectiveActionInline(admin.StackedInline):
    model = CorrectiveAction
    extra = 0


class EffectivenessVerificationInline(admin.StackedInline):
    model = EffectivenessVerification
    extra = 0


class EvidenceInline(admin.TabularInline):
    model = Evidence
    extra = 0
    fields = ("file", "description", "uploaded_by", "created_at")
    readonly_fields = ("created_at",)


class FindingHistoryInline(admin.TabularInline):
    model = FindingHistory
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("created_at", "user", "action", "previous_status", "new_status", "comment")


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "status", "classification", "source", "reported_by_name", "created_at")
    list_filter = ("status", "classification", "source")
    search_fields = ("code", "title", "description", "reported_by_name", "reported_by_email")
    readonly_fields = ("code", "created_at", "updated_at")
    inlines = [CorrectionInline, CorrectiveActionInline, EffectivenessVerificationInline, EvidenceInline, FindingHistoryInline]


@admin.register(FindingCodeSequence)
class FindingCodeSequenceAdmin(admin.ModelAdmin):
    list_display = ("prefix", "next_number")
    search_fields = ("prefix",)


@admin.register(Correction)
class CorrectionAdmin(admin.ModelAdmin):
    list_display = ("finding", "assigned_to", "due_at", "is_conform")
    list_filter = ("is_conform",)


@admin.register(CorrectiveAction)
class CorrectiveActionAdmin(admin.ModelAdmin):
    list_display = ("finding", "assigned_to", "analysis_technique", "due_at", "is_conform")
    list_filter = ("analysis_technique", "is_conform")


@admin.register(EffectivenessVerification)
class EffectivenessVerificationAdmin(admin.ModelAdmin):
    list_display = ("finding", "assigned_to", "due_at", "effectiveness_percentage", "is_effective")
    list_filter = ("is_effective", "requires_additional_follow_up")


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("finding", "description", "uploaded_by", "created_at")
    search_fields = ("finding__code", "description")


@admin.register(FindingHistory)
class FindingHistoryAdmin(admin.ModelAdmin):
    list_display = ("finding", "action", "previous_status", "new_status", "created_at")
    list_filter = ("action", "new_status")
    search_fields = ("finding__code", "action", "comment")


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ("date", "name")
    search_fields = ("name",)


@admin.register(MasterArea)
class MasterAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(MasterProcess)
class MasterProcessAdmin(admin.ModelAdmin):
    list_display = ("name", "allows_custom_text", "order", "is_active")
    list_filter = ("is_active", "allows_custom_text")
    search_fields = ("name",)


@admin.register(MasterSource)
class MasterSourceAdmin(admin.ModelAdmin):
    list_display = ("value", "name", "allows_custom_text", "order", "is_active")
    list_filter = ("is_active", "allows_custom_text")
    search_fields = ("value", "name")


@admin.register(DeadlineSetting)
class DeadlineSettingAdmin(admin.ModelAdmin):
    list_display = (
        "validation_days",
        "correction_major_days",
        "correction_minor_days",
        "correction_review_days",
        "corrective_action_days",
        "corrective_action_review_days",
        "verification_days",
    )
