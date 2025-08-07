from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""

    list_display = (
        "username",
        "display_name",
        "email",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "is_staff", "created_at")
    search_fields = ("username", "display_name", "email")
    ordering = ("username",)
    actions = ["activate_users", "deactivate_users"]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Additional Info",
            {
                "fields": ("display_name", "timezone", "created_at", "updated_at"),
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Additional Info",
            {
                "fields": ("display_name", "timezone"),
            },
        ),
    )

    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")

    def activate_users(self, request, queryset):
        """Bulk action to activate selected users."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request, f"Successfully activated {updated} user(s).", messages.SUCCESS
        )

    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        """Bulk action to deactivate selected users, but protect superusers."""
        # Filter out superusers to protect them
        users_to_deactivate = queryset.filter(is_superuser=False)
        superusers_protected = queryset.filter(is_superuser=True).count()

        updated = users_to_deactivate.update(is_active=False)

        if updated > 0:
            self.message_user(
                request,
                f"Successfully deactivated {updated} user(s).",
                messages.SUCCESS,
            )

        if superusers_protected > 0:
            self.message_user(
                request,
                f"{superusers_protected} superuser(s) were protected from "
                "deactivation.",
                messages.WARNING,
            )

    deactivate_users.short_description = "Deactivate selected users"

    def has_delete_permission(self, request, obj=None):
        """Disable delete permission to prevent accidental user deletion."""
        return False
