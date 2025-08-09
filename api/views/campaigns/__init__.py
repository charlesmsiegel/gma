"""
Campaign API views organized by functional area.

This package contains campaign-related API views split into logical modules:
- list_views: Campaign listing and detail operations
- search_views: User search functionality for invitations
- invitation_views: Campaign invitation management

All views maintain backward compatibility through import re-exports.
"""

# Re-export all views to maintain backward compatibility
from .invitation_views import (
    accept_campaign_invitation,
    cancel_campaign_invitation,
    decline_campaign_invitation,
    list_campaign_invitations,
    list_user_invitations,
    send_campaign_invitation,
)
from .list_views import (
    CampaignDetailAPIView,
    CampaignListAPIView,
    CampaignListCreateAPIView,
    CampaignMembershipListAPIView,
    CampaignPagination,
    UserCampaignListAPIView,
)
from .search_views import campaign_user_search

__all__ = [
    # List views
    "CampaignListAPIView",
    "CampaignDetailAPIView",
    "CampaignListCreateAPIView",
    "CampaignMembershipListAPIView",
    "UserCampaignListAPIView",
    "CampaignPagination",
    # Search views
    "campaign_user_search",
    # Invitation views
    "send_campaign_invitation",
    "list_campaign_invitations",
    "accept_campaign_invitation",
    "decline_campaign_invitation",
    "cancel_campaign_invitation",
    "list_user_invitations",
]
