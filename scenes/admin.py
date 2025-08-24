"""Admin registrations for scenes app."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Scene, SceneStatusChangeLog


@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    """Admin interface for Scene model."""

    list_display = ("name", "campaign", "status", "created_by", "created_at")
    list_filter = ("status", "campaign", "created_at")
    search_fields = ("name", "description", "campaign__name")
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("participants",)

    fieldsets = (
        (None, {"fields": ("name", "description", "campaign", "status")}),
        ("Participants", {"fields": ("participants",)}),
        (
            "Metadata",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(SceneStatusChangeLog)
class SceneStatusChangeLogAdmin(admin.ModelAdmin):
    """Admin interface for SceneStatusChangeLog model."""

    list_display = (
        "scene_name",
        "old_status_display",
        "new_status_display",
        "user",
        "timestamp",
    )
    list_filter = ("old_status", "new_status", "timestamp")
    search_fields = ("scene__name", "user__username")
    readonly_fields = ("scene", "user", "old_status", "new_status", "timestamp")
    date_hierarchy = "timestamp"

    def scene_name(self, obj):
        """Display scene name with link."""
        return format_html(
            '<a href="/admin/scenes/scene/{}/change/">{}</a>',
            obj.scene.pk,
            obj.scene.name,
        )

    scene_name.short_description = "Scene"
    scene_name.admin_order_field = "scene__name"

    def old_status_display(self, obj):
        """Display old status with color coding."""
        colors = {"ACTIVE": "green", "CLOSED": "orange", "ARCHIVED": "gray"}
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.old_status, "black"),
            obj.get_old_status_display(),
        )

    old_status_display.short_description = "From Status"
    old_status_display.admin_order_field = "old_status"

    def new_status_display(self, obj):
        """Display new status with color coding."""
        colors = {"ACTIVE": "green", "CLOSED": "orange", "ARCHIVED": "gray"}
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.new_status, "black"),
            obj.get_new_status_display(),
        )

    new_status_display.short_description = "To Status"
    new_status_display.admin_order_field = "new_status"

    def has_add_permission(self, request):
        """Disable manual creation of audit logs."""
        return False

    def has_change_permission(self, request, obj=None):
        """Make audit logs read-only."""
        return False
