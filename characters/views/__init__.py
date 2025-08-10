"""
Views for character management.

Provides campaign-scoped character management views with proper permission checking.
"""

from django.shortcuts import render
from django.views.generic import ListView

from characters.models import Character
from core.mixins import CampaignCharacterMixin, CampaignListView


class CampaignCharactersView(CampaignCharacterMixin, CampaignListView):
    """
    List characters in a campaign with role-based filtering.

    - OWNER/GM: See all characters in the campaign
    - PLAYER: See only their own characters
    - OBSERVER: See all characters (read-only)
    """

    model = Character
    template_name = "characters/campaign_characters.html"
    context_object_name = "characters"

    def get_context_data(self, **kwargs):
        """Add character-specific context."""
        context = super().get_context_data(**kwargs)

        user_role = self.campaign.get_user_role(self.request.user)

        context.update(
            {
                "page_title": f"{self.campaign.name} - Characters",
                "can_create_character": user_role in ["OWNER", "GM", "PLAYER"],
                "can_manage_all": user_role in ["OWNER", "GM"],
                "is_player": user_role == "PLAYER",
            }
        )

        return context
