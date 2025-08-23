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
        """Get queryset with optimizations for performance."""
        return (
            super()
            .get_queryset(request)
            .select_related("campaign", "created_by", "deleted_by")
        )

    def save_model(self, request, obj, form, change):
        """Automatically set created_by when creating new items."""
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    # Bulk actions implementation

    @admin.action(description="Soft delete selected items")
    def soft_delete_selected(self, request, queryset):
        """Bulk soft delete items with optimized queries."""
        if not request.user.is_staff:
            self.message_user(request, "Permission denied for bulk operations.")
            return

        # Optimize queryset to avoid N+1 queries
        queryset = queryset.select_related("campaign", "created_by").filter(
            is_deleted=False
        )

        deleted_count = 0
        error_count = 0

        with transaction.atomic():
            for item in queryset:
                try:
                    if item.can_be_deleted_by(request.user):
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
        """Bulk restore soft-deleted items with optimized queries."""
        if not request.user.is_staff:
            self.message_user(request, "Permission denied for bulk operations.")
            return

        # Optimize queryset to avoid N+1 queries and only get deleted items
        queryset = queryset.select_related("campaign", "created_by").filter(
            is_deleted=True
        )

        restored_count = 0
        error_count = 0

        with transaction.atomic():
            for item in queryset:
                try:
                    if item.can_be_deleted_by(request.user):
                        item.restore(request.user)
                        restored_count += 1
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
        """Bulk update quantity with proper permission checking."""
        if not request.user.is_staff:
            self.message_user(request, "Permission denied for bulk operations.")
            return

        # Optimize queryset and add proper permission checking
        queryset = queryset.select_related("campaign", "created_by").filter(
            is_deleted=False
        )

        updated_count = 0
        error_count = 0

        with transaction.atomic():
            for item in queryset:
                try:
                    # Check if user has permission to modify this item
                    user_role = item.campaign.get_user_role(request.user)
                    if (
                        request.user.is_superuser
                        or user_role in ["OWNER", "GM"]
                        or item.created_by_id == request.user.id
                    ):
                        # This would typically be implemented with a custom form
                        # For now, setting to 1 as demonstration
                        item.quantity = 1
                        item.save(update_fields=["quantity"])
                        updated_count += 1
                    else:
                        error_count += 1
                except (ValueError, AttributeError):
                    error_count += 1

        if updated_count > 0:
            self.message_user(
                request, f"Successfully updated quantity for {updated_count} items."
            )
        if error_count > 0:
            self.message_user(
                request,
                f"Failed to update {error_count} items due to permissions.",
                level="warning",
            )

    @admin.action(description="Transfer selected items to different campaign")
    def transfer_campaign(self, request, queryset):
        """Bulk transfer items to a different campaign."""
        if not request.user.is_staff:
            self.message_user(request, "Permission denied for bulk operations.")
            return

        # This operation requires a custom admin form for security
        # that would allow selecting the target campaign and validate permissions
        # This is a placeholder implementation that could be expanded with custom forms

        # Count items that could potentially be transferred (with permission checks)
        queryset = queryset.select_related("campaign", "created_by").filter(
            is_deleted=False
        )
        transferable_count = 0
        error_count = 0

        for item in queryset:
            user_role = item.campaign.get_user_role(request.user)
            if (
                request.user.is_superuser
                or user_role in ["OWNER", "GM"]
                or item.created_by_id == request.user.id
            ):
                transferable_count += 1
            else:
                error_count += 1

        self.message_user(
            request,
            f"Campaign transfer operation would affect {transferable_count} items. "
            f"This requires a custom form to select target campaign. "
            f"{error_count} items would be skipped due to permissions.",
            level="info",
        )

    @admin.action(description="Assign ownership for selected items")
    def assign_ownership(self, request, queryset):
        """Bulk change ownership for selected items."""
        if not request.user.is_staff:
            self.message_user(request, "Permission denied for bulk operations.")
            return

        # This operation requires a custom admin form for security
        # to allow selecting characters and validate they belong to campaigns
        # This is a placeholder implementation that could be expanded with custom forms

        # Count items that could potentially be assigned (with permission checks)
        queryset = queryset.select_related("campaign", "created_by").filter(
            is_deleted=False
        )
        assignable_count = 0
        error_count = 0

        for item in queryset:
            user_role = item.campaign.get_user_role(request.user)
            if (
                request.user.is_superuser
                or user_role in ["OWNER", "GM"]
                or item.created_by_id == request.user.id
            ):
                assignable_count += 1
            else:
                error_count += 1

        self.message_user(
            request,
            f"Ownership assignment would affect {assignable_count} items. "
            f"This requires a custom form to select target characters. "
            f"{error_count} items would be skipped due to permissions.",
            level="info",
        )

    @admin.action(description="Clear ownership for selected items")
    def clear_ownership(self, request, queryset):
        """Bulk clear ownership with proper permission checking."""
        if not request.user.is_staff:
            self.message_user(request, "Permission denied for bulk operations.")
            return

        # Optimize queryset and add proper permission checking
        queryset = queryset.select_related("campaign", "created_by").filter(
            is_deleted=False
        )

        cleared_count = 0
        error_count = 0

        with transaction.atomic():
            for item in queryset:
                try:
                    # Check if user has permission to modify this item
                    user_role = item.campaign.get_user_role(request.user)
                    if (
                        request.user.is_superuser
                        or user_role in ["OWNER", "GM"]
                        or item.created_by_id == request.user.id
                    ):
                        item.owners.clear()
                        cleared_count += 1
                    else:
                        error_count += 1
                except (ValueError, AttributeError):
                    # Handle specific expected exceptions during ownership clearing
                    error_count += 1
                    continue

        if cleared_count > 0:
            self.message_user(
                request, f"Successfully cleared ownership for {cleared_count} items."
            )
        if error_count > 0:
            self.message_user(
                request,
                f"Failed to clear ownership for {error_count} items.",
                level="warning",
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
