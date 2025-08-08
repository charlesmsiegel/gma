"""
Campaign views for web interface.

This module provides Django views for campaign creation, editing, and management
through the web interface, including proper authentication and permission checks.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView, ListView

from ..forms import CampaignForm
from ..models import Campaign


class CampaignListView(ListView):
    """
    View for listing campaigns with advanced visibility, filtering, and search.

    Features:
    - Show public campaigns to everyone
    - Show private campaigns only to members
    - Member campaigns appear first
    - Role-based filtering via ?role=owner|gm|player|observer
    - Search functionality via ?q=search_term
    - Configurable pagination via ?per_page=N (max 100)
    - Exclude inactive campaigns by default, include with ?show_inactive=true
    """

    model = Campaign
    template_name = "campaigns/campaign_list.html"
    context_object_name = "campaigns"
    paginate_by = 25

    def get_paginate_by(self, queryset):
        """Get pagination count, user-configurable with max limit."""
        try:
            per_page = int(self.request.GET.get("per_page", self.paginate_by))
            # Cap at 100 to prevent performance issues
            return min(max(per_page, 1), 100)
        except (ValueError, TypeError):
            return self.paginate_by

    def get_queryset(self):
        """Return campaigns visible to the user with proper ordering and filtering."""
        user = self.request.user

        # Start with base queryset
        queryset = Campaign.objects.select_related("owner").prefetch_related(
            "memberships"
        )

        # Handle active/inactive filtering
        show_inactive = self.request.GET.get("show_inactive", "").lower() == "true"
        if not show_inactive:
            queryset = queryset.filter(is_active=True)

        # Apply visibility logic
        if user.is_authenticated:
            # Authenticated users see:
            # 1. Public campaigns
            # 2. Private campaigns where they are members (including owner)
            queryset = queryset.filter(
                Q(is_public=True)  # Public campaigns
                | Q(owner=user)  # Campaigns they own
                | Q(memberships__user=user)  # Campaigns they're members of
            ).distinct()
        else:
            # Unauthenticated users see only public campaigns
            queryset = queryset.filter(is_public=True)

        # Apply role filtering if requested
        role_filter = self.request.GET.get("role", "").lower()
        if role_filter and user.is_authenticated:
            if role_filter == "owner":
                queryset = queryset.filter(owner=user)
            elif role_filter in ["gm", "player", "observer"]:
                role_upper = role_filter.upper()
                queryset = queryset.filter(
                    memberships__user=user, memberships__role=role_upper
                )

        # Apply search filtering
        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(game_system__icontains=search_query)
            )

        # Order results: member campaigns first, then by last updated
        if user.is_authenticated:
            # Create custom ordering to put member campaigns first
            queryset = queryset.extra(
                select={
                    "is_user_member": """
                        CASE
                            WHEN campaigns_campaign.owner_id = %s THEN 1
                            WHEN EXISTS(
                                SELECT 1 FROM campaigns_membership
                                WHERE campaigns_membership.campaign_id = campaigns_campaign.id
                                AND campaigns_membership.user_id = %s
                            ) THEN 1
                            ELSE 0
                        END
                    """  # noqa: E501
                },
                select_params=[user.id, user.id],
                order_by=["-is_user_member", "-created_at", "name"],
            )
        else:
            # For unauthenticated users, simple ordering
            queryset = queryset.order_by("-created_at", "name")

        return queryset

    def get_context_data(self, **kwargs):
        """Add additional context for template rendering."""
        context = super().get_context_data(**kwargs)

        # Add search query to context for form persistence
        context["search_query"] = self.request.GET.get("q", "")

        # Add current role filter to context
        context["current_role_filter"] = self.request.GET.get("role", "")

        return context


class CampaignDetailView(DetailView):
    """View for displaying campaign details."""

    model = Campaign
    template_name = "campaigns/campaign_detail.html"
    context_object_name = "campaign"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        """Return campaigns visible to the user with proper permission filtering."""
        user = self.request.user
        queryset = Campaign.objects.select_related("owner").prefetch_related(
            "memberships"
        )

        if user.is_authenticated:
            # Authenticated users can see:
            # 1. All public campaigns
            # 2. Private campaigns where they are members (including owner)
            queryset = queryset.filter(
                Q(is_public=True)  # Public campaigns
                | Q(owner=user)  # Campaigns they own
                | Q(memberships__user=user)  # Campaigns they're members of
            ).distinct()
        else:
            # Unauthenticated users can only see public campaigns
            queryset = queryset.filter(is_public=True)

        return queryset

    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)
        campaign = self.get_object()
        user = self.request.user

        # Add user permissions for this campaign
        if user.is_authenticated:
            context["user_role"] = campaign.get_user_role(user)
            context["is_owner"] = campaign.is_owner(user)
            context["is_member"] = campaign.is_member(user)
        else:
            context["user_role"] = None
            context["is_owner"] = False
            context["is_member"] = False

        return context


class CampaignCreateView(LoginRequiredMixin, CreateView):
    """View for creating new campaigns."""

    model = Campaign
    form_class = CampaignForm
    template_name = "campaigns/campaign_create.html"

    def form_valid(self, form):
        """Handle valid form submission by setting the owner."""
        campaign = form.save(owner=self.request.user)
        messages.success(
            self.request, f'Campaign "{campaign.name}" was created successfully!'
        )
        return redirect("campaigns:detail", slug=campaign.slug)

    def form_invalid(self, form):
        """Handle invalid form submission."""
        messages.error(self.request, "Please correct the errors below and try again.")
        return super().form_invalid(form)
