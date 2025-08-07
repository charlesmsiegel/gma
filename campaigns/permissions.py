"""
Simplified campaign-based permission system.

This module provides a simple, flexible permission system for campaign resources.
All permission denials return 404 Not Found to hide resource existence.
"""

from typing import Optional, Union

from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from .models import Campaign


class CampaignPermission(permissions.BasePermission):
    """
    Flexible campaign permission class that can check for multiple roles.

    Usage:
        # Single role
        permission_classes = [CampaignPermission("OWNER")]

        # Multiple roles
        permission_classes = [CampaignPermission(["OWNER", "GM"])]

        # Any member
        permission_classes = [CampaignPermission.any_member()]
    """

    def __init__(self, required_roles: Union[str, list] = None):
        """Initialize with required roles."""
        if required_roles is None:
            required_roles = []
        elif isinstance(required_roles, str):
            required_roles = [required_roles]
        self.required_roles = required_roles

    @classmethod
    def any_member(cls):
        """Create permission that allows any campaign member."""
        return cls(["OWNER", "GM", "PLAYER", "OBSERVER"])

    def get_campaign(self, view: APIView) -> Optional[Campaign]:
        """Get the campaign from the view's kwargs."""
        try:
            campaign_id = view.kwargs.get("campaign_id")
            if not campaign_id:
                return None
            return Campaign.objects.get(id=campaign_id, is_active=True)
        except (Campaign.DoesNotExist, ValueError, TypeError):
            return None

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check if the user has permission to access the campaign resource."""
        if isinstance(request.user, AnonymousUser):
            return False

        campaign = self.get_campaign(view)
        if not campaign:
            return False

        return campaign.has_role(request.user, *self.required_roles)


class CampaignPermissionMixin:
    """
    Simple mixin for Django views to handle campaign-based permissions.
    """

    def get_campaign(self):
        """Get the campaign object from the URL kwargs."""
        try:
            campaign_id = self.kwargs.get("campaign_id")
            if not campaign_id:
                raise Http404("Campaign not found")
            return Campaign.objects.get(id=campaign_id, is_active=True)
        except (Campaign.DoesNotExist, ValueError, TypeError):
            raise Http404("Campaign not found")

    def check_campaign_permission(self, user, *roles):
        """Check if a user has any of the specified roles for the campaign."""
        if isinstance(user, AnonymousUser):
            raise Http404("Campaign not found")

        campaign = self.get_campaign()
        if not campaign.has_role(user, *roles):
            raise Http404("Campaign not found")


# Convenience permission instances
IsCampaignOwner = CampaignPermission("OWNER")
IsCampaignGM = CampaignPermission("GM")
IsCampaignMember = CampaignPermission.any_member()
IsCampaignOwnerOrGM = CampaignPermission(["OWNER", "GM"])
