"""
Admin configuration for prerequisites (Issue #190).

This module configures the Django admin interface for prerequisites
with visual builder widget integration.
"""

from django.contrib import admin

from .forms import AdminPrerequisiteForm
from .models import Prerequisite


@admin.register(Prerequisite)
class PrerequisiteAdmin(admin.ModelAdmin):
    """Admin interface for prerequisites with visual builder."""

    form = AdminPrerequisiteForm
    list_display = ["description", "content_type", "object_id", "created_at"]
    list_filter = ["content_type", "created_at"]
    search_fields = ["description"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Basic Information", {"fields": ("description",)}),
        (
            "Requirements",
            {
                "fields": ("requirements",),
                "description": (
                    "Use the visual builder to create complex prerequisite logic."
                ),
            },
        ),
        (
            "Associated Object",
            {
                "fields": ("content_type", "object_id"),
                "classes": ("collapse",),
                "description": "Optional: Link this prerequisite to a specific object.",
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        """Customize form for admin interface."""
        form = super().get_form(request, obj, **kwargs)
        return form

    class Media:
        css = {"all": ("admin/css/prerequisite-builder.css",)}
        js = ("admin/js/prerequisite-builder.js",)
