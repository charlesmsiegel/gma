from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from campaigns.models import Campaign
from core.models import DescribedModelMixin, TimestampedMixin

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

    from characters.models import Character

User = get_user_model()


class ItemQuerySet(models.QuerySet):
    """Custom QuerySet for Item with filtering methods."""

    def active(self) -> "ItemQuerySet":
        """Filter to only active (non-deleted) items."""
        return self.filter(is_deleted=False)

    def deleted(self) -> "ItemQuerySet":
        """Filter to only soft-deleted items."""
        return self.filter(is_deleted=True)

    def for_campaign(self, campaign: Campaign) -> "ItemQuerySet":
        """Filter items belonging to a specific campaign."""
        if campaign is None:
            raise ValueError("Campaign parameter cannot be None")
        return self.filter(campaign=campaign)

    def owned_by_character(self, character: "Character") -> "ItemQuerySet":
        """Filter items owned by a specific character."""
        if character is None:
            return self.none()
        return self.filter(owners=character)


class ItemManager(models.Manager):
    """Custom manager for Item with query methods."""

    def get_queryset(self) -> ItemQuerySet:
        """Return the custom ItemQuerySet, excluding soft-deleted by default."""
        return ItemQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def for_campaign(self, campaign: Campaign) -> ItemQuerySet:
        """Get items for a specific campaign."""
        if campaign is None:
            raise ValueError("Campaign parameter cannot be None")
        return self.get_queryset().filter(campaign=campaign)

    def owned_by_character(self, character: "Character") -> ItemQuerySet:
        """Get items owned by a specific character."""
        if character is None:
            return self.none()
        return self.get_queryset().filter(owners=character)


class AllItemManager(models.Manager):
    """Manager that includes soft-deleted items."""

    def get_queryset(self):
        """Return the QuerySet including all items."""
        return ItemQuerySet(self.model, using=self._db)


class Item(TimestampedMixin, DescribedModelMixin, models.Model):
    """
    Item model for campaign management with comprehensive functionality.

    Provides:
    - Basic item information (name, description)
    - Campaign association
    - Quantity tracking
    - Character ownership (many-to-many)
    - User audit tracking (created_by)
    - Soft delete functionality
    """

    name: models.CharField = models.CharField(
        max_length=200, help_text="Name of the item"
    )
    campaign: models.ForeignKey = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="The campaign this item belongs to",
    )
    quantity: models.PositiveIntegerField = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Quantity of this item",
    )
    created_by: models.ForeignKey = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_items",
        help_text="User who created this item",
    )
    owners: models.ManyToManyField = models.ManyToManyField(
        "characters.Character",
        blank=True,
        related_name="owned_items",
        help_text="Characters who own this item",
    )

    # Soft delete fields
    is_deleted: models.BooleanField = models.BooleanField(
        default=False, help_text="Whether this item has been soft deleted"
    )
    deleted_at: models.DateTimeField = models.DateTimeField(
        null=True, blank=True, help_text="When this item was deleted"
    )
    deleted_by: models.ForeignKey = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_items",
        help_text="User who deleted this item",
    )

    objects = ItemManager()
    all_objects = AllItemManager()

    class Meta:
        db_table = "items_item"
        ordering = ["name"]
        verbose_name = "Item"
        verbose_name_plural = "Items"

    def __str__(self) -> str:
        """Return the item name."""
        return self.name

    def clean(self) -> None:
        """Validate the item data."""
        super().clean()

        # Validate item name is not empty/blank
        if not self.name or not self.name.strip():
            raise ValidationError("Item name cannot be empty.")

        # Validate quantity is positive
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError("Quantity must be a positive number.")

        # Note: created_by can be None after user deletion, so we don't require it

    def can_be_deleted_by(self, user: Optional["AbstractUser"]) -> bool:
        """Check if a user can delete this item.

        Args:
            user: The user to check delete permissions for

        Returns:
            True if the user can delete this item, False otherwise
        """
        if user is None:
            return False

        # Superusers can delete any item
        if user.is_superuser:
            return True

        # Item creator can always delete their items (if creator still exists)
        if self.created_by and self.created_by == user:
            return True

        # Get user's role in the campaign
        user_role = self.campaign.get_user_role(user)

        # Campaign owners and GMs can delete items in their campaign
        return user_role in ["OWNER", "GM"]

    def soft_delete(self, user: "AbstractUser") -> "Item":
        """Soft delete this item.

        Args:
            user: The user performing the deletion

        Returns:
            Item instance if successful

        Raises:
            PermissionError: If user doesn't have permission
            ValueError: If item is already deleted
        """
        if not self.can_be_deleted_by(user):
            raise PermissionError("You don't have permission to delete this item")

        if self.is_deleted:
            raise ValueError("Item is already deleted")

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

        return self

    def restore(self, user: "AbstractUser") -> "Item":
        """Restore a soft-deleted item.

        Args:
            user: The user performing the restoration

        Raises:
            PermissionError: If user doesn't have permission to restore
            ValueError: If item is not deleted
        """
        if not self.can_be_deleted_by(user):
            raise PermissionError("You don't have permission to restore this item")

        if not self.is_deleted:
            raise ValueError("Item is not deleted")

        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        # Use direct SQL update since default manager excludes soft-deleted items
        self.__class__.all_objects.filter(pk=self.pk).update(
            is_deleted=False, deleted_at=None, deleted_by=None
        )

        return self
