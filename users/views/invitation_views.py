"""
Views for user invitation management.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class UserInvitationsView(LoginRequiredMixin, TemplateView):
    """View for displaying user's invitations."""

    template_name = "users/invitations.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user's invitations
        try:
            from campaigns.models import CampaignInvitation

            invitations = (
                CampaignInvitation.objects.filter(invited_user=self.request.user)
                .select_related("campaign", "invited_by")
                .order_by("-created_at")
            )
            context["invitations"] = invitations
        except ImportError:
            # If CampaignInvitation model doesn't exist yet
            context["invitations"] = []

        return context
