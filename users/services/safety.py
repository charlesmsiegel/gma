"""
Safety preferences service for user safety management.

This module provides the SafetyPreferencesService class that handles
user safety preferences management and access control.
"""

import logging
from typing import Any, Dict, List, Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import transaction

logger = logging.getLogger(__name__)

User = get_user_model()


class SafetyPreferencesService:
    """Service for managing user safety preferences."""

    def __init__(self):
        """Initialize the safety preferences service."""
        pass

    def get_user_safety_preferences(
        self, user: AbstractUser, create_if_missing: bool = True
    ) -> Optional["UserSafetyPreferences"]:
        """
        Get user's safety preferences, optionally creating if missing.

        Args:
            user: The user whose preferences to retrieve
            create_if_missing: Whether to create preferences if they don't exist

        Returns:
            UserSafetyPreferences instance or None if not found and not created
        """
        from users.models.safety import UserSafetyPreferences

        try:
            return UserSafetyPreferences.objects.get(user=user)
        except UserSafetyPreferences.DoesNotExist:
            if create_if_missing:
                logger.info(
                    f"Creating default safety preferences for user {user.username}"
                )
                return UserSafetyPreferences.objects.create(
                    user=user,
                    lines=[],
                    veils=[],
                    privacy_level="gm_only",
                    consent_required=True,
                )
            return None

    @transaction.atomic
    def update_safety_preferences(
        self,
        user: AbstractUser,
        lines: Optional[List[str]] = None,
        veils: Optional[List[str]] = None,
        privacy_level: Optional[str] = None,
        consent_required: Optional[bool] = None,
    ) -> "UserSafetyPreferences":
        """
        Update user's safety preferences.

        Args:
            user: The user whose preferences to update
            lines: Hard boundaries (optional)
            veils: Soft boundaries (optional)
            privacy_level: Privacy level (optional)
            consent_required: Whether consent is required (optional)

        Returns:
            Updated UserSafetyPreferences instance

        Raises:
            ValidationError: If privacy_level is invalid
        """
        from users.models.safety import UserSafetyPreferences

        # Get or create preferences
        preferences = self.get_user_safety_preferences(user, create_if_missing=True)

        # Validate privacy level if provided
        if privacy_level is not None:
            valid_levels = [
                choice[0] for choice in UserSafetyPreferences.PRIVACY_LEVEL_CHOICES
            ]
            if privacy_level not in valid_levels:
                raise ValidationError(f"Invalid privacy level: {privacy_level}")

        # Update fields if provided
        if lines is not None:
            # Ensure lines is a list and clean up empty/whitespace entries
            if not isinstance(lines, list):
                raise ValidationError("Lines must be a list")
            cleaned_lines = []
            for line in lines:
                if isinstance(line, str):
                    # String items - strip whitespace
                    if line and line.strip():
                        cleaned_lines.append(line.strip())
                elif line:
                    # Non-string items (dict, etc.) - keep as is if truthy
                    cleaned_lines.append(line)
            preferences.lines = cleaned_lines

        if veils is not None:
            # Ensure veils is a list and clean up empty/whitespace entries
            if not isinstance(veils, list):
                raise ValidationError("Veils must be a list")
            cleaned_veils = []
            for veil in veils:
                if isinstance(veil, str):
                    # String items - strip whitespace
                    if veil and veil.strip():
                        cleaned_veils.append(veil.strip())
                elif veil:
                    # Non-string items (dict, etc.) - keep as is if truthy
                    cleaned_veils.append(veil)
            preferences.veils = cleaned_veils

        if privacy_level is not None:
            preferences.privacy_level = privacy_level

        if consent_required is not None:
            preferences.consent_required = consent_required

        # Save with validation
        preferences.full_clean()
        preferences.save()

        logger.info(
            f"Updated safety preferences for user {user.username}: "
            f"lines={len(preferences.lines)}, veils={len(preferences.veils)}, "
            f"privacy={preferences.privacy_level}"
        )

        return preferences

    def can_view_safety_preferences(
        self,
        viewer: AbstractUser,
        target_user: AbstractUser,
        campaign: Optional["Campaign"] = None,
    ) -> bool:
        """
        Check if viewer can view target user's safety preferences.

        Args:
            viewer: The user trying to view preferences
            target_user: The user whose preferences are being viewed
            campaign: Optional campaign context for permission checking

        Returns:
            True if viewer can access the preferences
        """
        # Users can always view their own preferences
        if viewer == target_user:
            return True

        # Get target user's preferences
        preferences = self.get_user_safety_preferences(
            target_user, create_if_missing=False
        )
        if not preferences:
            # No preferences exist, so nothing to hide
            return True

        privacy_level = preferences.privacy_level

        # Private preferences can only be viewed by the user themselves
        if privacy_level == "private":
            return False

        # GM-only preferences can be viewed by campaign owners and GMs
        if privacy_level == "gm_only":
            if not campaign:
                return False

            # Check if viewer is campaign owner or GM
            return campaign.has_role(viewer, "OWNER", "GM")

        # Campaign member preferences can be viewed by any campaign member
        if privacy_level == "campaign_members":
            if not campaign:
                return False

            # Check if both users are members of the campaign
            viewer_is_member = campaign.is_member(viewer)
            target_is_member = campaign.is_member(target_user)

            return viewer_is_member and target_is_member

        # Default to not allowing access for unknown privacy levels
        return False

    def get_filtered_safety_data(
        self,
        user: AbstractUser,
        viewer: AbstractUser,
        campaign: Optional["Campaign"] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get privacy-filtered safety data for a user.

        Args:
            user: The user whose safety data to retrieve
            viewer: The user requesting the data
            campaign: Optional campaign context

        Returns:
            Dictionary with filtered safety data or None if not accessible
        """
        # Check if viewer can access preferences
        if not self.can_view_safety_preferences(viewer, user, campaign):
            return None

        # Get preferences
        preferences = self.get_user_safety_preferences(user, create_if_missing=False)
        if not preferences:
            return {
                "has_preferences": False,
                "privacy_level": None,
                "lines": [],
                "veils": [],
                "consent_required": True,  # Default assumption for safety
            }

        return {
            "has_preferences": True,
            "privacy_level": preferences.privacy_level,
            "lines": preferences.lines,
            "veils": preferences.veils,
            "consent_required": preferences.consent_required,
            "created_at": preferences.created_at,
            "updated_at": preferences.updated_at,
        }

    def get_privacy_summary(self, user: AbstractUser) -> Dict[str, Any]:
        """
        Get a summary of user's privacy settings without revealing content.

        Args:
            user: The user whose privacy summary to get

        Returns:
            Dictionary with privacy summary
        """
        preferences = self.get_user_safety_preferences(user, create_if_missing=False)

        if not preferences:
            return {
                "has_preferences": False,
                "privacy_level": None,
                "has_lines": False,
                "has_veils": False,
                "consent_required": True,
            }

        return {
            "has_preferences": True,
            "privacy_level": preferences.privacy_level,
            "has_lines": len(preferences.lines) > 0,
            "has_veils": len(preferences.veils) > 0,
            "lines_count": len(preferences.lines),
            "veils_count": len(preferences.veils),
            "consent_required": preferences.consent_required,
            "last_updated": preferences.updated_at,
        }

    def delete_safety_preferences(self, user: AbstractUser) -> bool:
        """
        Delete user's safety preferences.

        Args:
            user: The user whose preferences to delete

        Returns:
            True if preferences were deleted, False if none existed
        """
        from users.models.safety import UserSafetyPreferences

        try:
            preferences = UserSafetyPreferences.objects.get(user=user)
            preferences.delete()
            logger.info(f"Deleted safety preferences for user {user.username}")
            return True
        except UserSafetyPreferences.DoesNotExist:
            return False

    def bulk_update_privacy_level(
        self, users: List[AbstractUser], new_privacy_level: str
    ) -> Dict[str, int]:
        """
        Bulk update privacy level for multiple users.

        Args:
            users: List of users to update
            new_privacy_level: The new privacy level to set

        Returns:
            Dictionary with results: {'updated': int, 'created': int}
        """
        from users.models.safety import UserSafetyPreferences

        # Validate privacy level
        valid_levels = [
            choice[0] for choice in UserSafetyPreferences.PRIVACY_LEVEL_CHOICES
        ]
        if new_privacy_level not in valid_levels:
            raise ValidationError(f"Invalid privacy level: {new_privacy_level}")

        results = {"updated": 0, "created": 0}

        with transaction.atomic():
            for user in users:
                preferences = self.get_user_safety_preferences(
                    user, create_if_missing=False
                )

                if preferences:
                    preferences.privacy_level = new_privacy_level
                    preferences.save()
                    results["updated"] += 1
                else:
                    # Create with default settings and specified privacy level
                    UserSafetyPreferences.objects.create(
                        user=user, privacy_level=new_privacy_level
                    )
                    results["created"] += 1

        logger.info(
            f"Bulk updated privacy level to {new_privacy_level}: "
            f"updated={results['updated']}, created={results['created']}"
        )

        return results

    def get_users_with_preferences_in_campaign(
        self, campaign: "Campaign"
    ) -> List[Dict[str, Any]]:
        """
        Get list of users with safety preferences in a campaign.

        Args:
            campaign: The campaign to check

        Returns:
            List of dictionaries with user and preference info
        """
        from campaigns.services import MembershipService
        from users.models.safety import UserSafetyPreferences

        # Get all campaign participants
        membership_service = MembershipService(campaign)
        participants = [campaign.owner]

        for membership in membership_service.get_campaign_members():
            participants.append(membership.user)

        results = []

        for user in participants:
            user_info = {
                "user": user,
                "username": user.username,
                "has_preferences": False,
                "privacy_level": None,
                "preference_summary": None,
            }

            try:
                preferences = UserSafetyPreferences.objects.get(user=user)
                user_info.update(
                    {
                        "has_preferences": True,
                        "privacy_level": preferences.privacy_level,
                        "preference_summary": {
                            "lines_count": len(preferences.lines),
                            "veils_count": len(preferences.veils),
                            "consent_required": preferences.consent_required,
                            "last_updated": preferences.updated_at,
                        },
                    }
                )
            except UserSafetyPreferences.DoesNotExist:
                pass

            results.append(user_info)

        # Sort by username for consistent ordering
        results.sort(key=lambda x: x["username"])

        return results
