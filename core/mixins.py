"""
Core mixins for campaign management views.

These mixins provide common functionality for campaign-scoped views across different apps.
"""

from typing import Optional

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView

from campaigns.models import Campaign


class CampaignFilterMixin(LoginRequiredMixin):
    """
    Mixin to filter views by campaign and handle permissions.

    This mixin provides:
    1. Campaign retrieval from URL slug
    2. Permission checking based on user role
    3. Campaign context for templates
    4. Proper error handling for missing campaigns
    """

    campaign: Optional[Campaign] = None

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Get campaign and check permissions before processing request."""
        campaign_slug = kwargs.get("slug")

        if not campaign_slug:
            raise Http404("Campaign slug is required")

        # Get campaign or 404
        self.campaign = get_object_or_404(Campaign, slug=campaign_slug, is_active=True)

        # Check if user has access to this campaign
        user_role = self.campaign.get_user_role(request.user)

        if not self._has_permission(user_role):
            raise Http404(
                "Campaign not found"
            )  # Hide existence from unauthorized users

        return super().dispatch(request, *args, **kwargs)

    def _has_permission(self, user_role: Optional[str]) -> bool:
        """
        Check if user has permission to access this view.

        Override this method in subclasses to implement specific permission logic.
        Default: Allow OWNER, GM, PLAYER, OBSERVER
        """
        return user_role in ["OWNER", "GM", "PLAYER", "OBSERVER"]

    def get_context_data(self, **kwargs):
        """Add campaign to template context."""
        context = super().get_context_data(**kwargs)
        context["campaign"] = self.campaign
        context["user_role"] = self.campaign.get_user_role(self.request.user)
        return context

    def get_queryset(self):
        """
        Filter queryset by campaign.

        Override this method to customize filtering logic for specific models.
        """
        if hasattr(super(), "get_queryset"):
            queryset = super().get_queryset()
            if hasattr(queryset.model, "campaign"):
                return queryset.filter(campaign=self.campaign)
        return super().get_queryset()


class CampaignManagementMixin(CampaignFilterMixin):
    """
    Mixin for campaign management views that require OWNER or GM permissions.
    """

    def _has_permission(self, user_role: Optional[str]) -> bool:
        """Only allow OWNER and GM to access management views."""
        return user_role in ["OWNER", "GM"]


class CampaignCharacterMixin(CampaignFilterMixin):
    """
    Mixin for character views with player-specific filtering.
    """

    def _has_permission(self, user_role: Optional[str]) -> bool:
        """Allow all campaign members to view characters."""
        return user_role in ["OWNER", "GM", "PLAYER", "OBSERVER"]

    def get_queryset(self):
        """Filter characters by campaign and user permissions."""
        if not hasattr(super(), "get_queryset"):
            raise NotImplementedError("get_queryset must be implemented")

        queryset = super().get_queryset()

        # Filter by campaign
        queryset = queryset.filter(campaign=self.campaign)

        # For players, only show their own characters
        user_role = self.campaign.get_user_role(self.request.user)
        if user_role == "PLAYER":
            queryset = queryset.filter(player_owner=self.request.user)

        return queryset


class CampaignListView(CampaignFilterMixin, ListView):
    """
    Base ListView for campaign-scoped content.

    Provides common functionality for listing campaign content like
    characters, scenes, locations, and items.
    """

    template_name_suffix = "_campaign_list"
    context_object_name = "objects"
    paginate_by = 20

    def get_context_data(self, **kwargs):
        """Add campaign-specific context."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "campaign": self.campaign,
                "user_role": self.campaign.get_user_role(self.request.user),
                "page_title": f"{self.campaign.name} - {self.get_content_type_name()}",
            }
        )
        return context

    def get_content_type_name(self) -> str:
        """Get human-readable name for the content type being listed."""
        if hasattr(self, "model") and self.model:
            return self.model._meta.verbose_name_plural.title()
        return "Items"
