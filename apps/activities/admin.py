from django.contrib import admin

from .models import Activity, ActivityAttachment, ActivityCodeSequence, ActivityHistory, ActivityProgress


class ActivityAttachmentInline(admin.TabularInline):
    model = ActivityAttachment
    extra = 0


class ActivityProgressInline(admin.TabularInline):
    model = ActivityProgress
    extra = 0


class ActivityHistoryInline(admin.TabularInline):
    model = ActivityHistory
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "origin", "status", "assigned_to", "review_assigned_to", "delivery_due_at")
    list_filter = ("origin", "status", "priority")
    search_fields = ("code", "title", "description", "assigned_to__username", "review_assigned_to__username")
    filter_horizontal = ("responsible_users",)
    readonly_fields = ("code", "created_at", "updated_at", "submitted_at", "closed_at")
    inlines = [ActivityProgressInline, ActivityAttachmentInline, ActivityHistoryInline]


admin.site.register(ActivityCodeSequence)
