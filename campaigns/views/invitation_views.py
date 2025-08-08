"""
Views for campaign invitation management.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from campaigns.models import Campaign


class CampaignInvitationsView(LoginRequiredMixin, TemplateView):
    """View for displaying campaign's invitations."""

    template_name = "campaigns/invitations.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get campaign by slug
        slug = kwargs.get("slug")
        campaign = get_object_or_404(Campaign, slug=slug, is_active=True)

        # Check if user has permission to view invitations
        user_role = campaign.get_user_role(self.request.user)
        if user_role not in ["OWNER", "GM"]:
            # For now, just return empty context for non-privileged users
            context["campaign"] = campaign
            context["invitations"] = []
            context["can_manage"] = False
            return context

        context["campaign"] = campaign
        context["can_manage"] = True

        # Get campaign's invitations
        try:
            from campaigns.models import CampaignInvitation

            invitations = (
                CampaignInvitation.objects.filter(campaign=campaign)
                .select_related("invited_user", "invited_by")
                .order_by("-created_at")
            )
            context["invitations"] = invitations
        except ImportError:
            # If CampaignInvitation model doesn't exist yet
            context["invitations"] = []

        return context
