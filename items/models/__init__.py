from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from polymorphic.managers import PolymorphicManager  # type: ignore[import-untyped]
from polymorphic.models import PolymorphicModel  # type: ignore[import-untyped]
from polymorphic.query import PolymorphicQuerySet  # type: ignore[import-untyped]

from campaigns.models import Campaign
from core.models import (
    AuditableMixin,
    DescribedModelMixin,
    NamedModelMixin,
    TimestampedMixin,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

    from characters.models import Character

User = get_user_model()


class ItemQuerySet(PolymorphicQuerySet):
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


class ItemManager(PolymorphicManager):
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

    def active(self) -> ItemQuerySet:
        """Filter to only active (non-deleted) items."""
        return self.get_queryset().active()

    def deleted(self) -> ItemQuerySet:
        """Filter to only soft-deleted items."""
        # Use all_objects to include deleted items, then filter to only deleted ones
        return ItemQuerySet(self.model, using=self._db).filter(is_deleted=True)


class AllItemManager(PolymorphicManager):
    """Manager that includes soft-deleted items."""

    def get_queryset(self):
        """Return the QuerySet including all items."""
        return ItemQuerySet(self.model, using=self._db)


class Item(
    TimestampedMixin,
    NamedModelMixin,
    DescribedModelMixin,
    AuditableMixin,
    PolymorphicModel,
):
    """
    Item model for campaign management with comprehensive functionality.

    Provides:
    - Basic item information (name via NamedModelMixin, description)
    - Campaign association
    - Quantity tracking
    - Character ownership (many-to-many)
    - User audit tracking (created_by, modified_by via AuditableMixin)
    - Timestamps (created_at, updated_at via TimestampedMixin)
    - Soft delete functionality
    """

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
        indexes = [
            models.Index(
                fields=["campaign", "is_deleted"], name="items_campaign_deleted_idx"
            ),  # Common filter combo
            models.Index(
                fields=["created_by", "is_deleted"], name="items_creator_deleted_idx"
            ),  # Admin filtering
            models.Index(
                fields=["is_deleted", "created_at"], name="items_deleted_created_idx"
            ),  # Soft delete queries by date
        ]

    def clean(self) -> None:
        """Validate the item data."""
        super().clean()

        # Note: Quantity validation is handled by MinValueValidator(1)
        # Note: Name validation is handled by NamedModelMixin
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
        if self.created_by_id and self.created_by_id == user.id:
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
        # Use proper model save to ensure signals and validation are triggered
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

        return self
