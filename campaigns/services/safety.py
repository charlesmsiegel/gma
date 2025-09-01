"""
Campaign safety service for safety tools management.

This module provides the CampaignSafetyService class that handles
campaign safety settings and user agreements.
"""

import logging
from typing import Any, Dict, List, Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

User = get_user_model()


class CampaignSafetyService:
    """Service for managing campaign safety settings and agreements."""

    def __init__(self, campaign: Optional["Campaign"] = None):
        """
        Initialize the campaign safety service.

        Args:
            campaign: Optional campaign to associate with this service
        """
        self.campaign = campaign

    @transaction.atomic
    def update_campaign_safety_settings(
        self,
        campaign: "Campaign",
        updated_by: AbstractUser,
        content_warnings: Optional[List[str]] = None,
        safety_tools_enabled: Optional[bool] = None,
    ) -> "Campaign":
        """
        Update campaign safety settings.

        Args:
            campaign: The campaign to update
            updated_by: The user making the update
            content_warnings: List of content warnings (optional)
            safety_tools_enabled: Whether safety tools are enabled (optional)

        Returns:
            Updated Campaign instance

        Raises:
            ValidationError: If user doesn't have permission or settings are invalid
        """
        # Check permissions - only owners and GMs can update safety settings
        if not campaign.has_role(updated_by, "OWNER", "GM"):
            raise ValidationError(
                "Only campaign owners and GMs can update safety settings"
            )

        # Update content warnings if provided
        if content_warnings is not None:
            if not isinstance(content_warnings, list):
                raise ValidationError("Content warnings must be a list")

            # Clean up warnings - remove empty/whitespace entries
            # Handle both string and dict warnings
            cleaned_warnings = []
            for warning in content_warnings:
                if isinstance(warning, str):
                    # String warning - clean up whitespace
                    cleaned = warning.strip()
                    if cleaned:
                        cleaned_warnings.append(cleaned)
                elif isinstance(warning, dict) and warning:
                    # Dictionary warning - keep as-is if not empty
                    cleaned_warnings.append(warning)
                elif warning:
                    # Other non-empty types - keep as-is
                    cleaned_warnings.append(warning)
            campaign.content_warnings = cleaned_warnings

        # Update safety tools setting if provided
        if safety_tools_enabled is not None:
            campaign.safety_tools_enabled = safety_tools_enabled

        # Save the campaign
        campaign.save()

        logger.info(
            f"Updated safety settings for campaign {campaign.name} by {updated_by.username}: "
            f"warnings={len(campaign.content_warnings)}, enabled={campaign.safety_tools_enabled}"
        )

        return campaign

    @transaction.atomic
    def create_safety_agreement(
        self,
        campaign: "Campaign",
        user: AbstractUser,
        acknowledged_warnings: List[str],
        agreed_to_terms: bool = True,
    ) -> "CampaignSafetyAgreement":
        """
        Create or update a safety agreement for a user.

        Args:
            campaign: The campaign
            user: The user agreeing to terms
            acknowledged_warnings: List of warnings user has acknowledged
            agreed_to_terms: Whether user agrees to safety terms

        Returns:
            CampaignSafetyAgreement instance

        Raises:
            ValidationError: If user is not a campaign member or warnings invalid
        """
        from campaigns.models import CampaignSafetyAgreement

        # Check if user is a member of the campaign
        if not campaign.is_member(user):
            raise ValidationError("Only campaign members can create safety agreements")

        # Validate acknowledged warnings against campaign warnings
        if not isinstance(acknowledged_warnings, list):
            raise ValidationError("Acknowledged warnings must be a list")

        # Clean up acknowledged warnings - handle both strings and complex structures
        cleaned_warnings = []
        for warning in acknowledged_warnings:
            if isinstance(warning, str):
                # String warning - clean up whitespace
                cleaned = warning.strip()
                if cleaned:
                    cleaned_warnings.append(cleaned)
            elif isinstance(warning, dict) and warning:
                # Dictionary warning - keep as-is if not empty
                cleaned_warnings.append(warning)
            elif warning:
                # Other non-empty types - keep as-is
                cleaned_warnings.append(warning)

        # Get or create agreement
        agreement, created = CampaignSafetyAgreement.objects.get_or_create(
            campaign=campaign,
            participant=user,
            defaults={
                "agreed_to_terms": agreed_to_terms,
                "acknowledged_warnings": cleaned_warnings,
            },
        )

        if not created:
            # Update existing agreement
            agreement.agreed_to_terms = agreed_to_terms
            agreement.acknowledged_warnings = cleaned_warnings
            agreement.save()

        logger.info(
            f"{'Created' if created else 'Updated'} safety agreement for "
            f"{user.username} in campaign {campaign.name}: "
            f"agreed={agreed_to_terms}, warnings={len(cleaned_warnings)}"
        )

        return agreement

    def get_campaign_safety_overview(
        self, campaign: "Campaign", user: AbstractUser
    ) -> Dict[str, Any]:
        """
        Get safety overview for a campaign from user's perspective.

        Args:
            campaign: The campaign to get overview for
            user: The user requesting the overview

        Returns:
            Dictionary with safety overview
        """
        overview = {
            "campaign_name": campaign.name,
            "safety_tools_enabled": campaign.safety_tools_enabled,
            "content_warnings": campaign.content_warnings,
            "user_agreement_status": None,
            "agreement_required": campaign.safety_tools_enabled,
            "warnings_to_acknowledge": [],
            "user_role": campaign.get_user_role(user),
        }

        # Get user's safety agreement if they are a member
        if campaign.is_member(user):
            agreement = self.get_user_safety_agreement(campaign, user)

            if agreement:
                overview["user_agreement_status"] = {
                    "has_agreement": True,
                    "agreed_to_terms": agreement.agreed_to_terms,
                    "acknowledged_warnings": agreement.acknowledged_warnings,
                    "agreement_date": agreement.created_at,
                    "last_updated": agreement.updated_at,
                }

                # Find warnings that haven't been acknowledged
                unacknowledged = set(campaign.content_warnings) - set(
                    agreement.acknowledged_warnings
                )
                overview["warnings_to_acknowledge"] = list(unacknowledged)
            else:
                overview["user_agreement_status"] = {
                    "has_agreement": False,
                    "agreed_to_terms": False,
                    "acknowledged_warnings": [],
                    "agreement_date": None,
                    "last_updated": None,
                }
                overview["warnings_to_acknowledge"] = campaign.content_warnings

        # GM/Owner specific information
        if campaign.has_role(user, "OWNER", "GM"):
            overview["gm_info"] = self._get_gm_safety_info(campaign)

        return overview

    def check_user_safety_agreement(
        self, campaign: "Campaign", user: AbstractUser
    ) -> Dict[str, Any]:
        """
        Check if user has proper safety agreement for campaign.

        Args:
            campaign: The campaign to check
            user: The user to check

        Returns:
            Dictionary with agreement status
        """
        result = {
            "has_agreement": False,
            "agreement_valid": False,
            "agreed_to_terms": False,
            "warnings_acknowledged": [],
            "missing_warnings": [],
            "needs_update": False,
        }

        # Get user's agreement
        agreement = self.get_user_safety_agreement(campaign, user)

        if agreement:
            result["has_agreement"] = True
            result["agreed_to_terms"] = agreement.agreed_to_terms
            result["warnings_acknowledged"] = agreement.acknowledged_warnings

            # Check if all current warnings are acknowledged
            missing_warnings = set(campaign.content_warnings) - set(
                agreement.acknowledged_warnings
            )
            result["missing_warnings"] = list(missing_warnings)
            result["needs_update"] = len(missing_warnings) > 0

            # Agreement is valid if user agreed to terms and acknowledged all warnings
            result["agreement_valid"] = (
                agreement.agreed_to_terms and len(missing_warnings) == 0
            )
        else:
            result["missing_warnings"] = campaign.content_warnings

        return result

    def get_user_safety_agreement(
        self, campaign: "Campaign", user: AbstractUser
    ) -> Optional["CampaignSafetyAgreement"]:
        """
        Get user's safety agreement for a campaign.

        Args:
            campaign: The campaign
            user: The user

        Returns:
            CampaignSafetyAgreement instance or None
        """
        from campaigns.models import CampaignSafetyAgreement

        try:
            return CampaignSafetyAgreement.objects.get(
                campaign=campaign, participant=user
            )
        except CampaignSafetyAgreement.DoesNotExist:
            return None

    def get_campaign_agreements_summary(
        self, campaign: "Campaign", requesting_user: AbstractUser
    ) -> Dict[str, Any]:
        """
        Get summary of all safety agreements for a campaign (GM/Owner only).

        Args:
            campaign: The campaign
            requesting_user: The user requesting the summary

        Returns:
            Dictionary with agreements summary

        Raises:
            ValidationError: If user doesn't have permission
        """
        # Check permissions
        if not campaign.has_role(requesting_user, "OWNER", "GM"):
            raise ValidationError(
                "Only campaign owners and GMs can view agreements summary"
            )

        from campaigns.models import CampaignSafetyAgreement

        from .campaign_services import MembershipService

        # Get all campaign participants
        membership_service = MembershipService(campaign)
        participants = []
        
        # Add all members
        for membership in membership_service.get_campaign_members():
            participants.append(membership.user)
        
        # Add owner if not already included
        if campaign.owner not in participants:
            participants.append(campaign.owner)

        # Get agreement status for each participant
        agreements_data = []
        stats = {
            "total_participants": len(participants),
            "with_agreements": 0,
            "agreed_to_terms": 0,
            "fully_acknowledged": 0,
            "needs_update": 0,
            "no_agreement": 0,
        }

        for user in participants:
            agreement = self.get_user_safety_agreement(campaign, user)
            agreement_status = self.check_user_safety_agreement(campaign, user)

            participant_data = {
                "username": user.username,
                "user_id": user.id,
                "role": campaign.get_user_role(user),
                "agreement_status": agreement_status,
                "last_updated": agreement.updated_at if agreement else None,
            }

            agreements_data.append(participant_data)

            # Update statistics
            if agreement_status["has_agreement"]:
                stats["with_agreements"] += 1
                if agreement_status["agreed_to_terms"]:
                    stats["agreed_to_terms"] += 1
                if agreement_status["agreement_valid"]:
                    stats["fully_acknowledged"] += 1
                if agreement_status["needs_update"]:
                    stats["needs_update"] += 1
            else:
                stats["no_agreement"] += 1

        return {
            "campaign_name": campaign.name,
            "content_warnings": campaign.content_warnings,
            "safety_tools_enabled": campaign.safety_tools_enabled,
            "participants": agreements_data,
            "statistics": stats,
            "generated_at": timezone.now(),
        }

    def bulk_create_agreements(
        self,
        campaign: "Campaign",
        users: List[AbstractUser],
        acknowledged_warnings: List[str],
        requesting_user: AbstractUser,
        agreed_to_terms: bool = True,
    ) -> Dict[str, int]:
        """
        Bulk create safety agreements for multiple users.

        Args:
            campaign: The campaign
            users: List of users to create agreements for
            acknowledged_warnings: Warnings to acknowledge for all users
            requesting_user: The user performing the bulk operation
            agreed_to_terms: Whether all users agree to terms

        Returns:
            Dictionary with operation results

        Raises:
            ValidationError: If user doesn't have permission
        """
        # Check permissions - only owners and GMs can bulk create agreements
        if not campaign.has_role(requesting_user, "OWNER", "GM"):
            raise ValidationError(
                "Only campaign owners and GMs can bulk create agreements"
            )

        results = {"created": 0, "updated": 0, "skipped": 0}

        with transaction.atomic():
            for user in users:
                try:
                    # Skip if user is not a campaign member
                    if not campaign.is_member(user):
                        results["skipped"] += 1
                        continue

                    agreement = self.create_safety_agreement(
                        campaign, user, acknowledged_warnings, agreed_to_terms
                    )

                    # Check if it was created or updated based on timestamps
                    if agreement.created_at == agreement.updated_at:
                        results["created"] += 1
                    else:
                        results["updated"] += 1

                except ValidationError:
                    results["skipped"] += 1
                    continue

        logger.info(
            f"Bulk safety agreement operation by {requesting_user.username} "
            f"for campaign {campaign.name}: {results}"
        )

        return results

    def delete_safety_agreement(
        self, campaign: "Campaign", user: AbstractUser, requesting_user: AbstractUser
    ) -> bool:
        """
        Delete a user's safety agreement.

        Args:
            campaign: The campaign
            user: The user whose agreement to delete
            requesting_user: The user requesting the deletion

        Returns:
            True if agreement was deleted, False if none existed

        Raises:
            ValidationError: If user doesn't have permission
        """
        # Users can delete their own agreements, or owners/GMs can delete any
        if not (
            user == requesting_user or campaign.has_role(requesting_user, "OWNER", "GM")
        ):
            raise ValidationError("Permission denied to delete safety agreement")

        agreement = self.get_user_safety_agreement(campaign, user)
        if agreement:
            agreement.delete()
            logger.info(
                f"Deleted safety agreement for {user.username} "
                f"in campaign {campaign.name} by {requesting_user.username}"
            )
            return True

        return False

    def _get_gm_safety_info(self, campaign: "Campaign") -> Dict[str, Any]:
        """
        Get GM-specific safety information for a campaign.

        Args:
            campaign: The campaign

        Returns:
            Dictionary with GM safety info
        """
        from campaigns.models import CampaignSafetyAgreement
        from users.services.safety import SafetyPreferencesService

        # Get safety preferences service for additional GM tools
        preferences_service = SafetyPreferencesService()

        # Get participants with their preference summaries
        participants_info = preferences_service.get_users_with_preferences_in_campaign(
            campaign
        )

        # Get agreement completion statistics
        total_agreements = CampaignSafetyAgreement.objects.filter(
            campaign=campaign
        ).count()

        # Get all participants count
        from .campaign_services import MembershipService

        membership_service = MembershipService(campaign)
        total_participants = (
            1 + membership_service.get_campaign_members().count()
        )  # +1 for owner

        return {
            "participants_with_preferences": len(
                [p for p in participants_info if p["has_preferences"]]
            ),
            "total_participants": total_participants,
            "agreement_completion_rate": (
                total_agreements / total_participants * 100
                if total_participants > 0
                else 0
            ),
            "participants_info": participants_info,
        }
