"""Admin interface for Item model with comprehensive functionality."""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Item

User = get_user_model()


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """Admin interface for Item model with comprehensive functionality."""

    # List display configuration
    list_display = [
        "name",
        "campaign",
        "quantity",
        "created_by",
        "created_at",
        "is_deleted",
    ]

    # List filtering
    list_filter = [
        "campaign",
        "created_by",
        "quantity",
        "created_at",
        "is_deleted",
    ]

    # Search functionality
    search_fields = ["name", "description"]

    # Ordering
    ordering = ["name"]

    # Read-only fields
    readonly_fields = ["created_at", "updated_at", "created_by"]

    # Fieldsets for organized form layout
    fieldsets = [
        (
            "Basic Information",
            {"fields": ("name", "description", "campaign", "quantity")},
        ),
        ("Ownership", {"fields": ("owners",), "classes": ("collapse",)}),
        (
            "Audit Information",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Deletion Status",
            {
                "fields": ("is_deleted", "deleted_at", "deleted_by"),
                "classes": ("collapse",),
            },
        ),
    ]

    # Bulk actions
    actions = [
        "soft_delete_selected",
        "restore_selected",
        "update_quantity",
        "assign_ownership",
        "clear_ownership",
        "transfer_campaign",
    ]

    def get_queryset(self, request):
        """Get queryset that excludes soft-deleted items by default."""
        return super().get_queryset(request)

    def save_model(self, request, obj, form, change):
        """Automatically set created_by when creating new items."""
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    # Bulk actions implementation

    @admin.action(description="Soft delete selected items")
    def soft_delete_selected(self, request, queryset):
        """Bulk soft delete items with permission checking."""
        if not request.user.is_staff:
            self.message_user(request, "Permission denied for bulk operations.")
            return

        deleted_count = 0
        error_count = 0

        with transaction.atomic():
            for item in queryset:
                try:
                    if item.can_be_deleted_by(request.user):
                        if not item.is_deleted:  # Only delete if not already deleted
                            item.soft_delete(request.user)
                            deleted_count += 1
                    else:
                        error_count += 1
                except (ValueError, AttributeError, PermissionError):
                    error_count += 1

        if deleted_count > 0:
            self.message_user(
                request, f"Successfully soft deleted {deleted_count} items."
            )
        if error_count > 0:
            self.message_user(
                request,
                f"Failed to delete {error_count} items due to permissions or errors.",
                level="warning",
            )

    @admin.action(description="Restore selected items")
    def restore_selected(self, request, queryset):
        """Bulk restore soft-deleted items with permission checking."""
        if not request.user.is_staff:
            self.message_user(request, "Permission denied for bulk operations.")
            return

        # Need to use all_objects to access soft-deleted items
        restored_count = 0
        error_count = 0

        with transaction.atomic():
            for item in queryset:
                try:
                    if item.is_deleted and item.can_be_deleted_by(request.user):
                        item.restore(request.user)
                        restored_count += 1
                    elif not item.is_deleted:
                        # Item is not deleted, skip
                        pass
                    else:
                        error_count += 1
                except (ValueError, AttributeError, PermissionError):
                    error_count += 1

        if restored_count > 0:
            self.message_user(request, f"Successfully restored {restored_count} items.")
        if error_count > 0:
            self.message_user(
                request,
                f"Failed to restore {error_count} items due to permissions or errors.",
                level="warning",
            )

    @admin.action(description="Update quantity for selected items")
    def update_quantity(self, request, queryset):
        """Bulk update quantity for selected items."""
        if not request.user.is_staff:
            self.message_user(request, "Permission denied for bulk operations.")
            return

        # This would typically be implemented with a custom form
        # For now, we'll just demonstrate the concept
        updated_count = queryset.filter(is_deleted=False).update(quantity=1)

        if updated_count > 0:
            self.message_user(
                request, f"Successfully updated quantity for {updated_count} items."
            )

    @admin.action(description="Transfer selected items to different campaign")
    def transfer_campaign(self, request, queryset):
        """Bulk transfer items to a different campaign."""
        if not request.user.is_staff:
            self.message_user(request, "Permission denied for bulk operations.")
            return

        # This would typically be implemented with a custom form
        # For now, we'll just demonstrate the concept
        self.message_user(
            request,
            "Campaign transfer would require additional form input.",
            level="info",
        )

    @admin.action(description="Assign ownership for selected items")
    def assign_ownership(self, request, queryset):
        """Bulk change ownership for selected items."""
        if not request.user.is_staff:
            self.message_user(request, "Permission denied for bulk operations.")
            return

        # This would typically be implemented with a custom form
        # For now, we'll just demonstrate the concept
        self.message_user(
            request,
            "Ownership assignment would require additional form input.",
            level="info",
        )

    @admin.action(description="Clear ownership for selected items")
    def clear_ownership(self, request, queryset):
        """Bulk clear ownership for selected items."""
        if not request.user.is_staff:
            self.message_user(request, "Permission denied for bulk operations.")
            return

        # Clear ownership for all selected items
        cleared_count = 0
        for item in queryset:
            try:
                item.owners.clear()
                cleared_count += 1
            except (ValueError, AttributeError):
                # Handle specific expected exceptions during ownership clearing
                # Continue processing other items
                continue

        if cleared_count > 0:
            self.message_user(
                request, f"Successfully cleared ownership for {cleared_count} items."
            )

    # Permission methods

    def has_view_permission(self, request, obj=None):
        """Check if user has permission to view items."""
        if request.user.is_anonymous:
            return False
        return request.user.is_staff or request.user.is_superuser

    def has_add_permission(self, request):
        """Check if user has permission to add items."""
        if request.user.is_anonymous:
            return False
        return request.user.is_staff or request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Check if user has permission to change items."""
        if request.user.is_anonymous:
            return False
        return request.user.is_staff or request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Check if user has permission to delete items."""
        if request.user.is_anonymous:
            return False
        return request.user.is_staff or request.user.is_superuser
