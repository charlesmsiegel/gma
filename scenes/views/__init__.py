"""
Views for scene management.

Provides campaign-scoped scene management views with proper permission checking.
"""

from django.shortcuts import render
from django.views.generic import ListView

from core.mixins import CampaignFilterMixin, CampaignListView
from scenes.models import Scene


class CampaignScenesView(CampaignListView):
    """
    List scenes in a campaign.

    - OWNER/GM: See all scenes and can manage them
    - PLAYER/OBSERVER: See all scenes (read-only access)
    """

    model = Scene
    template_name = "scenes/campaign_scenes.html"
    context_object_name = "scenes"

    def get_context_data(self, **kwargs):
        """Add scene-specific context."""
        context = super().get_context_data(**kwargs)

        user_role = self.campaign.get_user_role(self.request.user)

        context.update(
            {
                "page_title": f"{self.campaign.name} - Scenes",
                "can_create_scene": user_role in ["OWNER", "GM"],
                "can_manage_scenes": user_role in ["OWNER", "GM"],
            }
        )

        return context
