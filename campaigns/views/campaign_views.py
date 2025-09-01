"""
Campaign views for web interface.

This module provides Django views for campaign creation, editing, and management
through the web interface, including proper authentication and permission checks.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from ..forms import CampaignForm, CampaignSettingsForm
from ..models import Campaign


class CampaignListView(ListView):
    """
    View for listing campaigns with advanced visibility, filtering, and search.

    Features:
    - Show public campaigns to everyone
    - Show private campaigns only to members
    - Role-based filtering via ?role=owner|gm|player|observer
    - Search functionality via ?q=search_term
    - Configurable pagination via ?page_size=N (max 100)
    - Exclude inactive campaigns by default, include with ?show_inactive=true
    """

    model = Campaign
    template_name = "campaigns/campaign_list.html"
    context_object_name = "campaigns"
    paginate_by = 25

    def get_paginate_by(self, queryset):
        """Get pagination count, user-configurable with max limit."""
        try:
            page_size = int(self.request.GET.get("page_size", self.paginate_by))
            # Cap at 100 to prevent performance issues
            return min(max(page_size, 1), 100)
        except (ValueError, TypeError):
            return self.paginate_by

    def get_queryset(self):
        """Return campaigns visible to the user with proper ordering and filtering."""
        user = self.request.user

        # Start with visibility-filtered queryset using custom manager
        queryset = (
            Campaign.objects.visible_to_user(user)
            .select_related("owner")
            .prefetch_related("memberships")
        )

        # Handle active/inactive filtering
        show_inactive = self.request.GET.get("show_inactive", "").lower() == "true"
        if not show_inactive:
            queryset = queryset.filter(is_active=True)

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

        # Simple ordering by creation date
        # TODO: Add member prioritization later if users request it
        queryset = queryset.order_by("-created_at", "name")

        return queryset

    def get_context_data(self, **kwargs):
        """Add additional context for template rendering."""
        context = super().get_context_data(**kwargs)

        # Add search query to context for form persistence
        context["search_query"] = self.request.GET.get("q", "")

        # Add current role filter to context
        context["current_role_filter"] = self.request.GET.get("role", "")

        # Add email verification status for template
        if self.request.user.is_authenticated:
            context["email_verified"] = self.request.user.email_verified
            context["show_verification_notice"] = not self.request.user.email_verified

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
        return (
            Campaign.objects.visible_to_user(user)
            .select_related("owner")
            .prefetch_related("memberships")
        )

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

        # Handle member search filtering
        member_search = self.request.GET.get("member_search", "").strip()
        memberships = campaign.memberships.select_related("user").order_by("joined_at")

        if member_search:
            # Filter memberships by username containing the search term
            memberships = memberships.filter(user__username__icontains=member_search)
            context["member_search"] = member_search

        # Pass filtered memberships as separate context variable
        context["filtered_memberships"] = memberships

        return context


class CampaignCreateView(LoginRequiredMixin, CreateView):
    """View for creating new campaigns."""

    model = Campaign
    form_class = CampaignForm
    template_name = "campaigns/campaign_create.html"

    def get_context_data(self, **kwargs):
        """Add game systems list to context."""
        context = super().get_context_data(**kwargs)
        context["game_systems"] = CampaignForm.GAME_SYSTEMS
        return context

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


class CampaignSettingsView(LoginRequiredMixin, UpdateView):
    """
    View for editing campaign settings.

    Only campaign owners can access this view.
    Provides form-based editing of campaign settings including:
    - Basic information (name, description, game_system, is_active)
    - Visibility settings (is_public)
    - Membership settings (allow_observer_join, allow_player_join)
    """

    model = Campaign
    form_class = CampaignSettingsForm
    template_name = "campaigns/campaign_settings.html"
    slug_url_kwarg = "slug"
    context_object_name = "campaign"

    def get_object(self, queryset=None):
        """Get campaign and verify user is owner."""
        campaign = super().get_object(queryset)

        # Only campaign owners can access settings
        if not campaign.is_owner(self.request.user):
            raise PermissionDenied("Only campaign owners can edit settings.")

        return campaign

    def get_success_url(self):
        """Redirect to campaign detail after successful update."""
        return reverse("campaigns:detail", kwargs={"slug": self.object.slug})

    def form_valid(self, form):
        """Handle successful form submission."""
        messages.success(
            self.request,
            f"Settings for '{form.instance.name}' have been updated successfully.",
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle invalid form submission."""
        messages.error(self.request, "Please correct the errors below and try again.")
        return super().form_invalid(form)
