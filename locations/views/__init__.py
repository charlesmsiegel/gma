"""
Views for location management.

Provides campaign-scoped location management views with proper permission checking.
"""

from django.shortcuts import render
from django.views.generic import ListView

from core.mixins import CampaignFilterMixin, CampaignListView
from locations.models import Location


class CampaignLocationsView(CampaignListView):
    """
    List locations in a campaign.

    - OWNER/GM: See all locations and can manage them
    - PLAYER/OBSERVER: See all locations (read-only access)
    """

    model = Location
    template_name = "locations/campaign_locations.html"
    context_object_name = "locations"

    def get_context_data(self, **kwargs):
        """Add location-specific context."""
        context = super().get_context_data(**kwargs)

        user_role = self.campaign.get_user_role(self.request.user)

        context.update(
            {
                "page_title": f"{self.campaign.name} - Locations",
                "can_create_location": user_role in ["OWNER", "GM"],
                "can_manage_locations": user_role in ["OWNER", "GM"],
            }
        )

        return context
