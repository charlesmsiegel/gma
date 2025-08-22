"""
Location service layer for complex business operations.

This module provides centralized business logic for location operations,
separating concerns from views and maintaining transaction safety.
"""

import logging
from typing import Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Location

User = get_user_model()
logger = logging.getLogger(__name__)


class LocationService:
    """Service class for location business operations."""

    MAX_BULK_OPERATIONS = 50  # Prevent performance issues

    @classmethod
    @transaction.atomic
    def bulk_create_locations(
        cls, user: User, locations_data: List[Dict], campaign_id: int
    ) -> Tuple[List[Location], List[Dict]]:
        """
        Create multiple locations in a single transaction.

        Args:
            user: User performing the operation
            locations_data: List of location data dictionaries
            campaign_id: Campaign ID for all locations

        Returns:
            Tuple of (created_locations, failed_operations)
        """
        if len(locations_data) > cls.MAX_BULK_OPERATIONS:
            raise ValidationError(
                f"Maximum {cls.MAX_BULK_OPERATIONS} locations can be created "
                f"at once."
            )

        logger.info(
            f"User {user.username} (ID: {user.id}) initiating bulk create "
            f"of {len(locations_data)} locations in campaign {campaign_id}"
        )

        created = []
        failed = []

        for i, location_data in enumerate(locations_data):
            try:
                location = Location(
                    name=location_data["name"],
                    description=location_data.get("description", ""),
                    campaign_id=campaign_id,
                    parent_id=location_data.get("parent"),
                    owned_by_id=location_data.get("owned_by"),
                )
                location.full_clean()
                location.save(user=user)
                created.append(location)

                logger.debug(f"Created location: {location.name} (ID: {location.id})")

            except Exception as e:
                failed.append(
                    {
                        "item_index": i,
                        "name": location_data.get("name", ""),
                        "error": str(e),
                    }
                )
                logger.warning(
                    f"Failed to create location {location_data.get('name', '')}: {e}"
                )

        return created, failed

    @classmethod
    @transaction.atomic
    def bulk_update_locations(
        cls, user: User, updates_data: List[Dict]
    ) -> Tuple[List[Location], List[Dict]]:
        """
        Update multiple locations in a single transaction.

        Args:
            user: User performing the operation
            updates_data: List of update data dictionaries with IDs

        Returns:
            Tuple of (updated_locations, failed_operations)
        """
        if len(updates_data) > cls.MAX_BULK_OPERATIONS:
            raise ValidationError(
                f"Maximum {cls.MAX_BULK_OPERATIONS} locations can be updated at once."
            )

        logger.info(
            f"User {user.username} (ID: {user.id}) initiating bulk update "
            f"of {len(updates_data)} locations"
        )

        updated = []
        failed = []

        for i, update_data in enumerate(updates_data):
            try:
                location_id = update_data["id"]
                location = Location.objects.get(pk=location_id)

                # Check permission
                if not location.can_edit(user):
                    failed.append(
                        {
                            "item_index": i,
                            "error": f"Permission denied for location "
                            f"'{location.name}'",
                        }
                    )
                    continue

                # Apply updates
                for field, value in update_data.items():
                    if field != "id" and hasattr(location, field):
                        setattr(location, field, value)

                location.full_clean()
                location.save(user=user)
                updated.append(location)

                logger.debug(f"Updated location: {location.name} (ID: {location.id})")

            except Location.DoesNotExist:
                failed.append(
                    {
                        "item_index": i,
                        "error": f"Location with ID {update_data.get('id')} not found",
                    }
                )
            except Exception as e:
                failed.append(
                    {
                        "item_index": i,
                        "error": str(e),
                    }
                )
                logger.warning(f"Failed to update location: {e}")

        return updated, failed

    @classmethod
    @transaction.atomic
    def move_location(
        cls, user: User, location: Location, new_parent: Optional[Location] = None
    ) -> None:
        """
        Move a location to a different parent with validation.

        Args:
            user: User performing the operation
            location: Location to move
            new_parent: New parent location (None for root level)

        Raises:
            ValidationError: If move is not valid
        """
        logger.info(
            f"User {user.username} (ID: {user.id}) moving location "
            f"'{location.name}' (ID: {location.id}) to parent "
            f"'{new_parent.name if new_parent else 'root'}' "
            f"(ID: {new_parent.id if new_parent else None}) in campaign "
            f"{location.campaign.name}"
        )

        # Check permission
        if not location.can_edit(user):
            raise ValidationError("Permission denied to move this location")

        # Validate new parent
        if new_parent:
            if new_parent.campaign != location.campaign:
                raise ValidationError("Parent must be in the same campaign")

            # Check for circular reference
            ancestors = [ancestor.pk for ancestor in new_parent.get_ancestors()]
            if location.pk in ancestors:
                raise ValidationError("Cannot move location to its own descendant")

            if new_parent.pk == location.pk:
                raise ValidationError("Cannot move location to itself")

        # Perform the move
        old_parent = location.parent
        location.parent = new_parent
        location.full_clean()
        location.save(user=user)

        logger.info(
            f"Successfully moved location '{location.name}' (ID: {location.id}) "
            f"from '{old_parent.name if old_parent else 'root'}' "
            f"(ID: {old_parent.id if old_parent else None}) "
            f"to '{new_parent.name if new_parent else 'root'}' "
            f"(ID: {new_parent.id if new_parent else None})"
        )

    @classmethod
    def check_permission(cls, location: Location, user: User, action: str) -> bool:
        """
        Centralized permission checking for location operations.

        Args:
            location: Location to check permissions for
            user: User to check permissions for
            action: Action to check ('view', 'edit', 'delete')

        Returns:
            Boolean indicating if user has permission
        """
        permission_methods = {
            "view": location.can_view,
            "edit": location.can_edit,
            "delete": location.can_delete,
        }

        if action not in permission_methods:
            return False

        return permission_methods[action](user)
