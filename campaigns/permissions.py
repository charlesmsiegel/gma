"""Simplified campaign-based permission system.

This module provides simple, readable permission functions for campaign resources.
All permission denials return 404 Not Found to hide resource existence.
"""

from typing import List, Optional, Tuple, Union

from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Campaign


def get_campaign_or_404(view: APIView) -> Campaign:
    """Get the campaign from view kwargs or raise 404."""
    try:
        campaign_id = view.kwargs.get("campaign_id")
        if not campaign_id:
            raise Http404("Campaign not found")
        return Campaign.objects.get(id=campaign_id, is_active=True)
    except (Campaign.DoesNotExist, ValueError, TypeError):
        raise Http404("Campaign not found")


def check_campaign_role(user, campaign: Campaign, required_roles: List[str]) -> bool:
    """Check if user has any of the required roles for the campaign."""
    if isinstance(user, AnonymousUser):
        return False
    return campaign.has_role(user, *required_roles)


class CampaignRolePermission(permissions.BasePermission):
    """Simple permission class for checking campaign roles."""

    def __init__(self, required_roles: List[str]):
        """Initialize with required roles list."""
        self.required_roles = required_roles

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if the user has permission to access the campaign resource."""
        if isinstance(request.user, AnonymousUser):
            return False

        try:
            campaign = get_campaign_or_404(view)
        except Http404:
            return False

        return check_campaign_role(request.user, campaign, self.required_roles)


class CampaignLookupMixin:
    """
    Simple mixin for Django views to handle campaign lookup and permission checks.
    """

    request: Request  # This will be provided by the view class that uses this mixin
    kwargs: dict  # URL kwargs provided by Django views

    def get_campaign(self) -> Campaign:
        """Get the campaign object from the URL kwargs."""
        try:
            campaign_id = self.kwargs.get("campaign_id")
            if not campaign_id:
                raise Http404("Campaign not found")
            return Campaign.objects.get(id=campaign_id, is_active=True)
        except (Campaign.DoesNotExist, ValueError, TypeError):
            raise Http404("Campaign not found")

    def check_campaign_permission(self, user, *roles) -> None:
        """Check if a user has any of the specified roles for the campaign."""
        if isinstance(user, AnonymousUser):
            raise Http404("Campaign not found")

        campaign = self.get_campaign()
        if not check_campaign_role(user, campaign, list(roles)):
            raise Http404("Campaign not found")

    def get_campaign_with_permissions(
        self, campaign_id: int, required_roles: Optional[List[str]] = None
    ) -> Union[Tuple[Campaign, str], Response]:
        """
        Retrieve campaign and validate user permissions for API views.

        Args:
            campaign_id: The campaign ID to retrieve
            required_roles: List of roles required (e.g. ['OWNER', 'GM'])

        Returns:
            tuple: (campaign, user_role) if authorized

        Raises:
            Response: 404 if campaign not found or user lacks permission
        """
        if required_roles is None:
            required_roles = ["OWNER", "GM"]

        try:
            campaign = Campaign.objects.get(id=campaign_id, is_active=True)
        except Campaign.DoesNotExist:
            return Response(
                {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
            )

        user_role = campaign.get_user_role(self.request.user)
        if user_role not in required_roles:
            # Hide existence for security - return same 404
            return Response(
                {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return campaign, user_role


# Simple permission functions for common use cases
def require_campaign_owner(user, campaign: Campaign) -> bool:
    """Check if user is campaign owner."""
    return check_campaign_role(user, campaign, ["OWNER"])


def require_campaign_admin(user, campaign: Campaign) -> bool:
    """Check if user is campaign owner or GM."""
    return check_campaign_role(user, campaign, ["OWNER", "GM"])


def require_campaign_member(user, campaign: Campaign) -> bool:
    """Check if user is any campaign member."""
    return check_campaign_role(user, campaign, ["OWNER", "GM", "PLAYER", "OBSERVER"])


# Convenience permission instances for backward compatibility
IsCampaignOwner = CampaignRolePermission(["OWNER"])
IsCampaignGM = CampaignRolePermission(["GM"])
IsCampaignMember = CampaignRolePermission(["OWNER", "GM", "PLAYER", "OBSERVER"])
IsCampaignOwnerOrGM = CampaignRolePermission(["OWNER", "GM"])

# Backward compatibility aliases
CampaignPermissionMixin = CampaignLookupMixin


# Deprecated class for backward compatibility
class CampaignPermission(CampaignRolePermission):
    """Deprecated: Use CampaignRolePermission instead."""

    def __init__(self, required_roles):
        """Initialize with required roles (backward compatibility)."""
        if isinstance(required_roles, str):
            required_roles = [required_roles]
        super().__init__(required_roles)

    @classmethod
    def any_member(cls):
        """Create permission that allows any campaign member."""
        return cls(["OWNER", "GM", "PLAYER", "OBSERVER"])
