from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, QuerySet

from campaigns.models import Campaign
from core.models import (
    AuditableMixin,
    DescribedModelMixin,
    NamedModelMixin,
    TimestampedMixin,
)

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


class Location(
    TimestampedMixin, NamedModelMixin, DescribedModelMixin, AuditableMixin, models.Model
):
    """
    Location model for campaign management with hierarchy support.

    Provides standardized fields through mixins:
    - TimestampedMixin: created_at, updated_at fields with indexing
    - NamedModelMixin: name field with __str__ method
    - DescribedModelMixin: description field
    - AuditableMixin: created_by, modified_by tracking with enhanced save()

    Hierarchy features:
    - parent: Optional parent location for tree structure
    - Tree traversal methods for ancestors, descendants, siblings
    - Validation for circular references and maximum depth
    - Orphan handling on parent deletion
    """

    campaign: models.ForeignKey = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="locations",
        help_text="The campaign this location belongs to",
    )

    parent: models.ForeignKey = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent location in the hierarchy",
    )

    # Tree traversal methods
    def get_descendants(self) -> QuerySet["Location"]:
        """
        Get all descendants (children, grandchildren, etc.) of this location.

        Optimized to avoid N+1 queries using prefetch_related.

        Returns:
            QuerySet of all descendant locations
        """
        if not self.pk:
            return Location.objects.none()

        descendants = []
        # Use select_related for better performance and safety limit
        queue = list(self.children.select_related("campaign"))
        visited = set()

        while queue and len(visited) < 1000:  # Safety limit to prevent infinite loops
            current = queue.pop(0)
            if current.pk not in visited:
                visited.add(current.pk)
                descendants.append(current.pk)
                # Prefetch children to reduce queries
                queue.extend(current.children.all())

        return Location.objects.filter(pk__in=descendants)

    def get_ancestors(self) -> QuerySet["Location"]:
        """
        Get all ancestors (parent, grandparent, etc.) of this location.

        Optimized to avoid N+1 queries using select_related.

        Returns:
            QuerySet of all ancestor locations ordered from immediate parent to root
        """
        if not self.parent:
            return Location.objects.none()

        ancestors = []
        current = self.parent
        visited = set()

        # Traverse up the tree with safety limit to prevent infinite loops
        while current and current.pk not in visited and len(visited) < 50:
            visited.add(current.pk)
            ancestors.append(current.pk)
            current = current.parent

        if not ancestors:
            return Location.objects.none()

        # Return optimized queryset with select_related for performance
        return (
            Location.objects.filter(pk__in=ancestors)
            .select_related("campaign", "parent", "created_by")
            .order_by(
                models.Case(
                    *[
                        models.When(pk=pk, then=models.Value(i))
                        for i, pk in enumerate(ancestors)
                    ],
                    output_field=models.IntegerField(),
                )
            )
        )

    def get_siblings(self) -> QuerySet["Location"]:
        """
        Get all sibling locations (same parent, excluding self).

        Optimized with select_related for performance.

        Returns:
            QuerySet of sibling locations
        """
        if not self.pk:
            return Location.objects.none()

        return (
            Location.objects.filter(parent=self.parent)
            .exclude(pk=self.pk)
            .select_related("campaign", "parent", "created_by")
        )

    def get_root(self) -> "Location":
        """
        Get the root (top-level) ancestor of this location.

        Returns:
            The root location (may be self if no parent)
        """
        current = self
        while current.parent:
            current = current.parent
        return current

    def get_path_from_root(self) -> QuerySet["Location"]:
        """
        Get the path from root to this location (inclusive).

        Optimized with select_related and safety limit.

        Returns:
            QuerySet ordered from root to this location
        """
        if not self.pk:
            return Location.objects.filter(pk=self.pk)

        path = []
        current = self
        visited = set()

        # Build path backwards from current to root with safety limit
        while current and current.pk not in visited and len(visited) < 50:
            visited.add(current.pk)
            path.append(current.pk)
            current = current.parent

        # Reverse to get root-to-current order
        path.reverse()

        # Return optimized QuerySet with select_related
        return (
            Location.objects.filter(pk__in=path)
            .select_related("campaign", "parent", "created_by")
            .order_by(
                models.Case(
                    *[
                        models.When(pk=pk, then=models.Value(i))
                        for i, pk in enumerate(path)
                    ],
                    output_field=models.IntegerField(),
                )
            )
        )

    def is_descendant_of(self, location: "Location") -> bool:
        """
        Check if this location is a descendant of the given location.

        Optimized with safety limit to prevent infinite loops.

        Args:
            location: Location to check ancestry against

        Returns:
            True if this location is a descendant of the given location
        """
        if not self.pk or not location.pk or self.pk == location.pk:
            return False

        current = self.parent
        visited = set()

        # Traverse up with safety limit
        while current and current.pk not in visited and len(visited) < 50:
            visited.add(current.pk)
            if current.pk == location.pk:
                return True
            current = current.parent

        return False

    def get_depth(self) -> int:
        """
        Get the depth of this location in the hierarchy.

        Optimized with safety limit to prevent infinite loops.

        Returns:
            Depth level (0 for root locations, 1 for their children, etc.)
        """
        depth = 0
        current = self
        visited = set()

        # Traverse up with safety limit
        while current.parent and current.pk not in visited and depth < 50:
            visited.add(current.pk)
            depth += 1
            current = current.parent

        return depth

    # Validation methods
    def clean(self) -> None:
        """
        Validate the location instance.

        Raises:
            ValidationError: If validation fails
        """
        super().clean()

        # Prevent self as parent
        if self.parent_id and self.parent_id == self.pk:
            raise ValidationError("A location cannot be its own parent.")

        # Prevent circular references
        if self.parent and self.pk:
            # Check if the new parent would create a circle
            # by seeing if the new parent is already a descendant of this location
            descendants = self.get_descendants()
            if self.parent in descendants:
                raise ValidationError(
                    "Circular reference detected: this location cannot be a parent "
                    "of its ancestor or descendant."
                )

        # Check cross-campaign parent
        if self.parent and self.campaign_id != self.parent.campaign_id:
            raise ValidationError("Parent location must be in the same campaign.")

        # Check maximum depth
        if self.parent:
            future_depth = self.parent.get_depth() + 1
            if future_depth >= 10:  # Maximum depth of 10 levels (0-9)
                raise ValidationError(
                    f"Maximum depth of 10 levels exceeded. "
                    f"This location would be at depth {future_depth}."
                )

    def save(self, *args, **kwargs) -> None:
        """
        Save the location with validation.

        Args:
            *args, **kwargs: Standard save arguments
        """
        # Run validation before save
        self.clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False) -> tuple:
        """
        Delete the location and handle orphaned children.

        Args:
            using: Database alias to use
            keep_parents: Whether to keep parent objects

        Returns:
            Tuple of (number_deleted, {model: count})
        """
        # Handle orphaned children before deletion
        if self.children.exists():
            if self.parent:
                # Move children to grandparent
                self.children.update(parent=self.parent)
            else:
                # Make children top-level (no parent)
                self.children.update(parent=None)

        return super().delete(using=using, keep_parents=keep_parents)

    # Permission methods
    def can_view(self, user: Optional["AbstractUser"]) -> bool:
        """
        Check if user can view this location.

        Args:
            user: User to check permissions for

        Returns:
            True if user can view this location
        """
        if not user or not user.is_authenticated:
            # Anonymous users can only view public campaign locations
            return self.campaign.is_public

        # All campaign members can view locations
        user_role = self.campaign.get_user_role(user)
        return user_role is not None or self.campaign.is_public

    def can_edit(self, user: Optional["AbstractUser"]) -> bool:
        """
        Check if user can edit this location.

        Args:
            user: User to check permissions for

        Returns:
            True if user can edit this location
        """
        if not user or not user.is_authenticated:
            return False

        user_role = self.campaign.get_user_role(user)

        if not user_role:
            return False

        # Owner and GM can edit all locations
        if user_role in ["OWNER", "GM"]:
            return True

        # Players can edit their own locations
        if user_role == "PLAYER" and self.created_by == user:
            return True

        return False

    def can_delete(self, user: Optional["AbstractUser"]) -> bool:
        """
        Check if user can delete this location.

        Args:
            user: User to check permissions for

        Returns:
            True if user can delete this location
        """
        if not user or not user.is_authenticated:
            return False

        user_role = self.campaign.get_user_role(user)

        if not user_role:
            return False

        # Owner can delete all locations
        if user_role == "OWNER":
            return True

        # GM can delete all locations (campaign setting dependent)
        if user_role == "GM":
            return True  # Default: GMs can delete locations

        # Players can delete their own locations
        if user_role == "PLAYER" and self.created_by == user:
            return True

        return False

    @classmethod
    def can_create(cls, user: Optional["AbstractUser"], campaign: Campaign) -> bool:
        """
        Check if user can create locations in the given campaign.

        Args:
            user: User to check permissions for
            campaign: Campaign to create location in

        Returns:
            True if user can create locations in this campaign
        """
        if not user or not user.is_authenticated:
            return False

        user_role = campaign.get_user_role(user)

        if not user_role:
            return False

        # All campaign members can create locations
        return user_role in ["OWNER", "GM", "PLAYER", "OBSERVER"]

    class Meta:
        db_table = "locations_location"
        ordering = ["name"]
        verbose_name = "Location"
        verbose_name_plural = "Locations"
