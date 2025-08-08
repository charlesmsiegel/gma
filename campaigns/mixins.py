"""
Mixins for campaign views to reduce code duplication.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from campaigns.models import Campaign


class CampaignManagementMixin:
    """Mixin to handle campaign permission checking for management operations."""

    def dispatch(self, request, *args, **kwargs):
        """Check campaign management permissions before processing request."""
        slug = kwargs.get("slug")
        if slug:
            campaign = get_object_or_404(Campaign, slug=slug, is_active=True)
            user_role = campaign.get_user_role(request.user)

            if user_role not in ["OWNER", "GM"]:
                messages.error(
                    request, "You don't have permission to manage this campaign."
                )
                return redirect("campaigns:detail", slug=campaign.slug)

            # Store campaign for use in view
            self.campaign = campaign

        return super().dispatch(request, *args, **kwargs)
