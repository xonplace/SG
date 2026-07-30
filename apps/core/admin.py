from django.contrib import admin

from .models import (
    AuditLog,
    AuthenticationSettings,
    CompanyProfile,
    NotificationSettings,
    RolePermission,
    SystemHelpContent,
    TrainingAssignment,
    TrainingAttempt,
    TrainingCompletion,
    TrainingQuestion,
)


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "system_name", "iso_standard", "primary_color", "updated_at")
    fieldsets = (
        (
            "Empresa",
            {
                "fields": (
                    "company_name",
                    "system_name",
                    "quality_system_name",
                    "iso_standard",
                    "scope",
                    "representative_email",
                )
            },
        ),
        (
            "Identidad del SGC",
            {
                "fields": (
                    "commitment_card_title",
                    "commitment_card_text",
                    "commitment_dialog_title",
                    "commitment_dialog_text",
                    "quality_policy",
                    "mission",
                    "vision",
                    "quality_commitment_image",
                    "commitment_image_caption",
                )
            },
        ),
        (
            "Apariencia y textos",
            {
                "fields": (
                    "primary_color",
                    "secondary_color",
                    "accent_color",
                    "page_background_color",
                    "button_color",
                    "welcome_text",
                    "public_portal_title",
                    "public_portal_text",
                    "public_action_title",
                    "public_entry_title",
                    "public_entry_text",
                    "sgc_home_title",
                    "sgc_home_subtitle",
                    "finding_callout_title",
                    "finding_callout_text",
                    "login_title",
                    "login_help_text",
                    "sgc_menu_label",
                    "sgc_home_label",
                    "documents_label",
                    "forms_label",
                    "certificate_label",
                    "processes_label",
                    "updates_label",
                    "training_label",
                    "findings_label",
                    "findings_board_label",
                    "new_finding_label",
                    "my_tasks_label",
                    "due_label",
                    "reports_label",
                    "maintainers_label",
                    "logo",
                    "header_logo",
                )
            },
        ),
        (
            "Modulos",
            {
                "fields": (
                    "show_findings_module",
                    "show_documents_module",
                    "show_certificate_module",
                    "show_updates_module",
                    "show_processes_module",
                    "show_training_module",
                )
            },
        ),
    )


@admin.register(SystemHelpContent)
class SystemHelpContentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "section",
        "training_category",
        "estimated_minutes",
        "passing_percentage",
        "has_video",
        "valid_until",
        "is_active",
        "show_on_training",
        "order",
        "updated_at",
    )
    list_filter = ("section", "training_category", "is_active", "show_on_training")
    search_fields = ("title", "summary", "content")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "module", "action", "object_repr", "ip_address")
    list_filter = ("module", "action")
    search_fields = ("action", "module", "object_repr", "details", "user__username")
    readonly_fields = ("created_at", "user", "action", "module", "object_repr", "details", "ip_address")


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role_name", "permission_code", "is_allowed", "updated_at")
    list_filter = ("role_name", "is_allowed")
    search_fields = ("role_name", "permission_code")


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "email_alerts_enabled",
        "notify_finding_created",
        "notify_assignments",
        "notify_due_24h",
        "sender_email",
        "smtp_host",
        "smtp_username",
        "updated_at",
    )
    readonly_fields = ("smtp_password_encrypted",)


@admin.register(AuthenticationSettings)
class AuthenticationSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "local_login_enabled",
        "sso_enabled",
        "provider",
        "allowed_domain",
        "client_id",
        "tenant_id",
        "auto_create_users",
        "force_sso_for_internal_users",
        "updated_at",
    )
    readonly_fields = ("client_secret_encrypted",)


@admin.register(TrainingCompletion)
class TrainingCompletionAdmin(admin.ModelAdmin):
    list_display = ("completed_at", "user", "content")
    list_filter = ("completed_at",)
    search_fields = ("user__username", "content__title")


@admin.register(TrainingAssignment)
class TrainingAssignmentAdmin(admin.ModelAdmin):
    list_display = ("content", "user", "due_date", "assigned_by", "assigned_at")
    list_filter = ("due_date", "assigned_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "content__title")


@admin.register(TrainingQuestion)
class TrainingQuestionAdmin(admin.ModelAdmin):
    list_display = ("content", "question", "correct_option", "order", "is_active")
    list_filter = ("content", "is_active")
    search_fields = ("content__title", "question")


@admin.register(TrainingAttempt)
class TrainingAttemptAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "content", "score", "total_questions", "passed")
    list_filter = ("passed", "created_at")
    search_fields = ("user__username", "content__title")
