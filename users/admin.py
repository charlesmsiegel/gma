from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""

    list_display = (
        "username",
        "email",
        "display_name",
        "timezone",
        "is_staff",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "timezone")
    search_fields = ("username", "email", "display_name", "first_name", "last_name")
    ordering = ("username",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Additional Info",
            {
                "fields": ("display_name", "timezone"),
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
