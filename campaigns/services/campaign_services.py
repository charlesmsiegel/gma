"""
Service layer for campaign business logic.

This module provides service classes that handle complex business operations,
separating concerns from Django forms and views.
"""

from typing import Dict, List, Optional, Set

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet

from ..models import Campaign, CampaignInvitation, CampaignMembership

# Use AbstractUser for typing - our User model extends this


class MembershipService:
    """Service for handling campaign membership operations."""

    def __init__(self, campaign: Campaign):
        """Initialize service for a specific campaign."""
        self.campaign = campaign

    def get_available_users_for_invitation(self) -> QuerySet:
        """Get users who can be invited to the campaign.

        Excludes:
        - Campaign owner
        - Current members
        - Users with pending invitations

        Returns:
            QuerySet of User objects available for invitation
        """
        # Get IDs of users who cannot be invited
        excluded_users = self._get_excluded_user_ids()

        return get_user_model().objects.exclude(id__in=excluded_users)

    def get_campaign_members(self) -> QuerySet:
        """Get all campaign members with user information."""
        return self.campaign.memberships.select_related("user")

    def change_member_role(
        self, membership: CampaignMembership, new_role: str
    ) -> CampaignMembership:
        """Change a member's role in the campaign.

        Args:
            membership: The membership to update
            new_role: The new role for the member

        Returns:
            The updated membership

        Raises:
            ValidationError: If role is invalid
        """
        if new_role not in dict(CampaignMembership.ROLE_CHOICES):
            raise ValidationError(f"Invalid role: {new_role}")

        membership.role = new_role
        membership.save()
        return membership

    def remove_member(self, user: AbstractUser) -> bool:
        """Remove a user from the campaign.

        Args:
            user: The user to remove

        Returns:
            True if member was removed, False if not a member
        """
        try:
            membership = CampaignMembership.objects.get(
                campaign=self.campaign, user=user
            )
            membership.delete()
            return True
        except CampaignMembership.DoesNotExist:
            return False

    def add_member(self, user: AbstractUser, role: str) -> CampaignMembership:
        """Add a new member to the campaign.

        Args:
            user: The user to add
            role: The role to assign

        Returns:
            The created membership

        Raises:
            ValidationError: If user is already a member or role is invalid
        """
        # Validate role
        if role not in dict(CampaignMembership.ROLE_CHOICES):
            raise ValidationError(f"Invalid role: {role}")

        # Check if user is already a member
        if CampaignMembership.objects.filter(
            campaign=self.campaign, user=user
        ).exists():
            raise ValidationError("User is already a member of this campaign")

        # Check if user is the owner
        if self.campaign.owner == user:
            raise ValidationError("Cannot add campaign owner as a member")

        return CampaignMembership.objects.create(
            campaign=self.campaign, user=user, role=role
        )

    @transaction.atomic
    def bulk_operation(
        self, action: str, users: List[AbstractUser], role: Optional[str] = None
    ) -> Dict[str, int]:
        """Perform bulk membership operations.

        Args:
            action: The action to perform ('add', 'remove', 'change_role')
            users: List of users to process
            role: Role for add/change operations

        Returns:
            Dictionary with operation results:
            {'added': int, 'removed': int, 'updated': int}
        """
        results = {"added": 0, "removed": 0, "updated": 0}

        if action == "add" and role:
            for user in users:
                try:
                    self.add_member(user, role)
                    results["added"] += 1
                except ValidationError:
                    # Skip users who can't be added (already members, etc.)
                    continue

        elif action == "remove":
            memberships = CampaignMembership.objects.filter(
                campaign=self.campaign, user__in=users
            )
            results["removed"] = memberships.count()
            memberships.delete()

        elif action == "change_role" and role:
            memberships = CampaignMembership.objects.filter(
                campaign=self.campaign, user__in=users
            )
            results["updated"] = memberships.update(role=role)

        return results

    def _get_excluded_user_ids(self) -> Set[int]:
        """Get IDs of users who should be excluded from invitation lists."""
        excluded_users = {self.campaign.owner.id}

        # Add existing members
        excluded_users.update(
            self.campaign.memberships.values_list("user_id", flat=True)
        )

        # Add users with pending invitations
        excluded_users.update(
            CampaignInvitation.objects.filter(
                campaign=self.campaign, status="PENDING"
            ).values_list("invited_user_id", flat=True)
        )

        return excluded_users


class InvitationService:
    """Service for handling campaign invitation operations."""

    def __init__(self, campaign: Campaign):
        """Initialize service for a specific campaign."""
        self.campaign = campaign

    def create_invitation(
        self,
        invited_user: AbstractUser,
        invited_by: AbstractUser,
        role: str,
        message: str = "",
    ) -> CampaignInvitation:
        """Create a new campaign invitation.

        Args:
            invited_user: The user being invited
            invited_by: The user sending the invitation
            role: The role being offered
            message: Optional message from inviter

        Returns:
            The created invitation

        Raises:
            ValidationError: If invitation cannot be created
        """
        # Validate role
        if role not in dict(CampaignMembership.ROLE_CHOICES):
            raise ValidationError(f"Invalid role: {role}")

        # Create invitation (model validation will handle duplicates/conflicts)
        invitation = CampaignInvitation(
            campaign=self.campaign,
            invited_user=invited_user,
            invited_by=invited_by,
            role=role,
            message=message,
        )
        invitation.full_clean()  # Run model validation
        invitation.save()

        return invitation

    def get_campaign_invitations(self, status: Optional[str] = None) -> QuerySet:
        """Get invitations for the campaign.

        Args:
            status: Optional status filter

        Returns:
            QuerySet of CampaignInvitation objects
        """
        queryset = self.campaign.invitations.select_related(
            "invited_user", "invited_by"
        ).order_by("-created_at")

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_pending_invitations(self) -> QuerySet:
        """Get pending invitations for the campaign."""
        return self.get_campaign_invitations(status="PENDING")


class CampaignService:
    """Service for general campaign operations."""

    def __init__(self, campaign: Optional[Campaign] = None):
        """Initialize service, optionally for a specific campaign."""
        self.campaign = campaign

    def create_campaign(self, owner: AbstractUser, **campaign_data) -> Campaign:
        """Create a new campaign.

        Args:
            owner: The user who will own the campaign
            **campaign_data: Campaign field data

        Returns:
            The created campaign
        """
        campaign = Campaign(owner=owner, **campaign_data)
        campaign.full_clean()
        campaign.save()
        return campaign

    def update_campaign_settings(self, **settings_data) -> Campaign:
        """Update campaign settings.

        Args:
            **settings_data: Fields to update

        Returns:
            The updated campaign

        Raises:
            ValueError: If no campaign is associated with this service
        """
        if not self.campaign:
            raise ValueError("No campaign associated with this service")

        for field, value in settings_data.items():
            if hasattr(self.campaign, field):
                setattr(self.campaign, field, value)

        self.campaign.full_clean()
        self.campaign.save()
        return self.campaign

    def search_users_for_invitation(self, query: str, limit: int = 10) -> QuerySet:
        """Search for users who can be invited to a campaign.

        Args:
            query: Search query (username or email contains)
            limit: Maximum number of results

        Returns:
            QuerySet of User objects matching the search

        Raises:
            ValueError: If no campaign is associated with this service
        """
        if not self.campaign:
            raise ValueError("No campaign associated with this service")

        if len(query) < 2:
            return get_user_model().objects.none()

        # Get excluded user IDs - optimize by converting to list for better SQL perf
        membership_service = MembershipService(self.campaign)
        excluded_users = list(membership_service._get_excluded_user_ids())

        # Import Q here to avoid circular imports
        from django.db.models import Q

        # Optimize search with more efficient query patterns
        User = get_user_model()

        # Use startswith for better index utilization when possible
        if query.isalnum() and len(query) >= 3:
            # For longer alphanumeric queries, try exact prefix match first
            exact_matches = (
                User.objects.filter(
                    Q(username__istartswith=query) | Q(email__istartswith=query)
                )
                .exclude(id__in=excluded_users)
                .only("id", "username", "email")
                .order_by("username")[: limit // 2 if limit > 2 else limit]
            )

            # If we don't have enough results, supplement with contains search
            if len(exact_matches) < limit:
                remaining_limit = limit - len(exact_matches)
                exact_match_ids = [user.id for user in exact_matches]

                contains_matches = (
                    User.objects.filter(
                        Q(username__icontains=query) | Q(email__icontains=query)
                    )
                    .exclude(id__in=excluded_users + exact_match_ids)
                    .only("id", "username", "email")
                    .order_by("username")[:remaining_limit]
                )

                # Combine results (convert to list to avoid complex querysets)
                all_matches = list(exact_matches) + list(contains_matches)
                return User.objects.filter(
                    id__in=[user.id for user in all_matches]
                ).order_by("username")
            else:
                return exact_matches
        else:
            # For short or non-alphanumeric queries, use regular contains search
            return (
                User.objects.filter(
                    Q(username__icontains=query) | Q(email__icontains=query)
                )
                .exclude(id__in=excluded_users)
                .only("id", "username", "email")
                .order_by("username")[:limit]
            )
