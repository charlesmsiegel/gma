"""
Views for item management.

Provides campaign-scoped item management views with proper permission checking.
"""

from django.shortcuts import render
from django.views.generic import ListView

from core.mixins import CampaignFilterMixin, CampaignListView
from items.models import Item


class CampaignItemsView(CampaignListView):
    """
    List items in a campaign.

    - OWNER/GM: See all items and can manage them
    - PLAYER/OBSERVER: See all items (read-only access)
    """

    model = Item
    template_name = "items/campaign_items.html"
    context_object_name = "items"

    def get_context_data(self, **kwargs):
        """Add item-specific context."""
        context = super().get_context_data(**kwargs)

        user_role = self.campaign.get_user_role(self.request.user)

        context.update(
            {
                "page_title": f"{self.campaign.name} - Items",
                "can_create_item": user_role in ["OWNER", "GM"],
                "can_manage_items": user_role in ["OWNER", "GM"],
            }
        )

        return context
