"""
Campaign-based permission classes and mixins.

This module provides permission classes and mixins to enforce
campaign-based access control throughout the application. Permissions
follow a hierarchical model:
- Owner: Full access to campaign
- GM: Can manage campaign content and players
- Player: Can participate in campaign
- Observer: Can view campaign content

All permission denials return 404 Not Found to hide resource existence.
"""

from typing import Optional

from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.http import Http404
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from .models import Campaign


class BaseCampaignPermission(permissions.BasePermission):
    """Base class for campaign-based permissions."""

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

        return self.check_campaign_access(request.user, campaign)

    def check_campaign_access(self, user: AbstractUser, campaign: Campaign) -> bool:
        """Override this method in subclasses to implement specific access checks."""
        raise NotImplementedError("Subclasses must implement check_campaign_access")


class IsCampaignOwner(BaseCampaignPermission):
    """Permission class that only allows campaign owners to access the resource."""

    def check_campaign_access(self, user: AbstractUser, campaign: Campaign) -> bool:
        """Check if the user is the campaign owner."""
        return campaign.is_owner(user)


class IsCampaignGM(BaseCampaignPermission):
    """Permission class that only allows campaign GMs to access the resource."""

    def check_campaign_access(self, user: AbstractUser, campaign: Campaign) -> bool:
        """Check if the user is a GM of the campaign."""
        return campaign.is_gm(user)


class IsCampaignMember(BaseCampaignPermission):
    """Permission class that allows any campaign member to access resource."""

    def check_campaign_access(self, user: AbstractUser, campaign: Campaign) -> bool:
        """Check if the user is a member of the campaign."""
        return campaign.is_member(user)


class IsCampaignOwnerOrGM(BaseCampaignPermission):
    """Permission class that allows campaign owners or GMs to access the resource."""

    def check_campaign_access(self, user: AbstractUser, campaign: Campaign) -> bool:
        """Check if the user is the owner or a GM of the campaign."""
        return campaign.is_owner(user) or campaign.is_gm(user)


class CampaignPermissionMixin:
    """
    Mixin for Django views to handle campaign-based permissions.

    This mixin provides helper methods for campaign permission checking
    that can be used in Django class-based views.
    """

    def get_campaign(self):
        """
        Get the campaign object from the URL kwargs.

        Returns:
            Campaign: The campaign object

        Raises:
            Http404: If campaign doesn't exist or is not active
        """
        try:
            campaign_id = self.kwargs.get("campaign_id")
            if not campaign_id:
                raise Http404("Campaign not found")
            return Campaign.objects.get(id=campaign_id, is_active=True)
        except (Campaign.DoesNotExist, ValueError, TypeError):
            raise Http404("Campaign not found")

    def check_campaign_permission(self, user, permission_level):
        """
        Check if a user has the specified permission level for the campaign.

        Args:
            user: The user to check permissions for
            permission_level: The required permission level
                - 'owner': Only campaign owner
                - 'gm': Only campaign GMs
                - 'member': Any campaign member (GM, Player, Observer)
                - 'owner_or_gm': Campaign owner or GM

        Raises:
            Http404: If user doesn't have required permission
        """
        if isinstance(user, AnonymousUser):
            raise Http404("Campaign not found")

        campaign = self.get_campaign()

        permission_checks = {
            "owner": campaign.is_owner,
            "gm": campaign.is_gm,
            "member": campaign.is_member,
            "owner_or_gm": lambda u: campaign.is_owner(u) or campaign.is_gm(u),
        }

        if permission_level not in permission_checks:
            raise ValueError(f"Invalid permission level: {permission_level}")

        if not permission_checks[permission_level](user):
            raise Http404("Campaign not found")


def require_campaign_permission(permission_level: str):
    """
    Decorator factory that creates campaign permission decorators.

    Args:
        permission_level: The required permission level ('owner', 'gm',
                         'member', 'owner_or_gm')

    Returns:
        A decorator function that can be applied to view classes.
    """

    def decorator(view_class):
        class WrappedView(CampaignPermissionMixin, view_class):
            def dispatch(self, request, *args, **kwargs):
                self.kwargs = kwargs
                self.check_campaign_permission(request.user, permission_level)
                return super().dispatch(request, *args, **kwargs)

        # Copy class attributes manually to preserve view metadata
        WrappedView.__name__ = view_class.__name__
        WrappedView.__doc__ = view_class.__doc__
        WrappedView.__module__ = view_class.__module__
        WrappedView.__qualname__ = getattr(view_class, "__qualname__", None)

        return WrappedView

    return decorator


# Create specific decorators using the factory
require_campaign_owner = require_campaign_permission("owner")
require_campaign_owner.__doc__ = """
Class decorator that requires the user to be the campaign owner.

Usage:
    @require_campaign_owner
    class MyCampaignView(View):
        def get(self, request, campaign_id):
            # Only campaign owner can access this
            pass
"""

require_campaign_gm = require_campaign_permission("gm")
require_campaign_gm.__doc__ = """
Class decorator that requires the user to be a campaign GM.

Usage:
    @require_campaign_gm
    class MyCampaignView(View):
        def get(self, request, campaign_id):
            # Only campaign GMs can access this
            pass
"""

require_campaign_member = require_campaign_permission("member")
require_campaign_member.__doc__ = """
Class decorator that requires the user to be a campaign member.

Usage:
    @require_campaign_member
    class MyCampaignView(View):
        def get(self, request, campaign_id):
            # Any campaign member can access this
            pass
"""

require_campaign_owner_or_gm = require_campaign_permission("owner_or_gm")
require_campaign_owner_or_gm.__doc__ = """
Class decorator that requires the user to be a campaign owner or GM.

Usage:
    @require_campaign_owner_or_gm
    class MyCampaignView(View):
        def get(self, request, campaign_id):
            # Campaign owner or GM can access this
            pass
"""
