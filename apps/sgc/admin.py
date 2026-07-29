from django.contrib import admin

from .models import (
    IsoCertificate,
    SgcDocument,
    SgcDocumentEvent,
    SgcDocumentType,
    SgcImportantDates,
    SgcOfficialForm,
    SgcProcess,
    SgcProcessVersion,
    SgcUpdate,
)


@admin.register(SgcDocument)
class SgcDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "clause", "document_type", "version", "status", "effective_date", "obsolete_at")
    list_filter = ("clause", "document_type", "status")
    search_fields = ("title", "code", "summary", "obsolete_reason")


@admin.register(SgcDocumentEvent)
class SgcDocumentEventAdmin(admin.ModelAdmin):
    list_display = ("document_label", "version", "event_type", "performed_by", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("document_label", "version", "detail", "family_key")
    readonly_fields = (
        "document",
        "family_key",
        "document_label",
        "version",
        "event_type",
        "detail",
        "performed_by",
        "created_at",
    )


@admin.register(SgcDocumentType)
class SgcDocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "value", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "value")


@admin.register(SgcOfficialForm)
class SgcOfficialFormAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "version", "is_active", "show_on_home", "uploaded_by")
    list_filter = ("is_active", "show_on_home", "processes")
    search_fields = ("name", "code", "version")
    filter_horizontal = ("processes",)


@admin.register(IsoCertificate)
class IsoCertificateAdmin(admin.ModelAdmin):
    list_display = ("title", "standard", "certification_body", "expiry_date", "is_active")
    list_filter = ("is_active", "standard")
    search_fields = ("title", "standard", "certification_body", "scope")


@admin.register(SgcUpdate)
class SgcUpdateAdmin(admin.ModelAdmin):
    list_display = ("title", "published_at", "is_published", "show_on_home", "created_by")
    list_filter = ("is_published", "show_on_home")
    search_fields = ("title", "body")


@admin.register(SgcImportantDates)
class SgcImportantDatesAdmin(admin.ModelAdmin):
    list_display = ("external_audit_date", "internal_audit_date", "management_review_date")


class SgcProcessVersionInline(admin.StackedInline):
    model = SgcProcessVersion
    extra = 0


@admin.register(SgcProcess)
class SgcProcessAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "owner", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("code", "name", "owner", "description")
    inlines = [SgcProcessVersionInline]


@admin.register(SgcProcessVersion)
class SgcProcessVersionAdmin(admin.ModelAdmin):
    list_display = ("process", "version", "published_at", "is_current", "published_by")
    list_filter = ("is_current", "published_at")
    search_fields = ("process__code", "process__name", "version", "change_summary")
