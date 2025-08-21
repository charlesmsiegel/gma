"""
Views for location management.

Provides campaign-scoped location management views with proper permission checking.
"""

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import CampaignFilterMixin
from locations.forms import LocationCreateForm, LocationEditForm
from locations.models import Location


class CampaignSlugMappingMixin:
    """
    Mixin to map campaign_slug parameter to slug for CampaignFilterMixin compatibility.

    This handles the URL parameter mismatch between location URLs (campaign_slug)
    and the core mixins (slug). Also ensures proper authentication flow.
    """

    def dispatch(self, request, *args, **kwargs):
        """Map campaign_slug to slug parameter and ensure authentication."""
        # Map parameter for CampaignFilterMixin
        if "campaign_slug" in kwargs:
            kwargs["slug"] = kwargs["campaign_slug"]

        # Let authentication happen first if needed
        return super().dispatch(request, *args, **kwargs)


class CampaignLocationsView(CampaignSlugMappingMixin, CampaignFilterMixin, ListView):
    """
    List locations in a campaign with hierarchical tree display.

    Features:
    - Hierarchical tree structure display
    - Search by name functionality
    - Filter by owner (character-owned or unowned)
    - Role-based permissions and management options
    """

    model = Location
    template_name = "locations/campaign_locations.html"
    context_object_name = "locations"
    paginate_by = 50  # Higher limit for location trees

    def get_queryset(self):
        """Get locations for this campaign with search and filtering."""
        # Base queryset with optimized queries to prevent N+1
        queryset = (
            Location.objects.filter(campaign=self.campaign)
            .select_related(
                "parent", "owned_by", "created_by", "campaign", "owned_by__player_owner"
            )
            .prefetch_related("children")
        )

        # Apply search filter
        search = self.request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)

        # Apply ownership filter
        owner_filter = self.request.GET.get("owner")
        if owner_filter:
            try:
                # Filter by specific character owner
                from characters.models import Character

                character = Character.objects.get(
                    id=owner_filter, campaign=self.campaign
                )
                queryset = queryset.filter(owned_by=character)
            except (Character.DoesNotExist, ValueError):
                # Invalid character ID, return empty queryset
                queryset = queryset.none()

        # Apply unowned filter
        if self.request.GET.get("unowned") == "true":
            queryset = queryset.filter(owned_by__isnull=True)

        return queryset.order_by("name")

    def get_context_data(self, **kwargs):
        """Add location-specific context."""
        context = super().get_context_data(**kwargs)

        user_role = self.get_user_role()

        # Add permission checking for each location (optimized to avoid N+1 queries)
        locations = list(context.get("locations", []))
        user = self.request.user

        # Optimize permission checking to avoid repeated campaign.get_user_role calls
        for location in locations:
            if user_role in ["OWNER", "GM"]:
                location.user_can_edit = True
            elif user_role == "PLAYER":
                # Check if location is owned by user's character or created by user
                if location.owned_by:
                    # Use the prefetched data to avoid additional queries
                    location.user_can_edit = (
                        hasattr(location.owned_by, "player_owner")
                        and location.owned_by.player_owner == user
                    )
                else:
                    location.user_can_edit = location.created_by == user
            else:
                location.user_can_edit = False

        context.update(
            {
                "page_title": f"{self.campaign.name} - Locations",
                "can_create_location": Location.can_create(
                    self.request.user, self.campaign
                ),
                "can_manage_locations": user_role in ["OWNER", "GM"],
                # Search and filter context
                "search_query": self.request.GET.get("search", ""),
                "owner_filter": self.request.GET.get("owner", ""),
                "unowned_filter": self.request.GET.get("unowned") == "true",
                # Characters for owner filter dropdown
                "characters": self.campaign.characters.select_related(
                    "player_owner"
                ).order_by("name"),
            }
        )

        return context


class LocationDetailView(CampaignSlugMappingMixin, CampaignFilterMixin, DetailView):
    """
    Location detail view with sub-locations and breadcrumbs.

    Features:
    - Shows location basic info (name, description, owner)
    - Lists all sub-locations (children)
    - Breadcrumb navigation: Campaign → Location Hierarchy → Current Location
    - Permission-based access control
    """

    model = Location
    template_name = "locations/location_detail.html"
    context_object_name = "location"
    pk_url_kwarg = "location_id"

    def get_object(self):
        """Get location ensuring it belongs to the campaign."""
        return get_object_or_404(
            Location.objects.select_related(
                "campaign", "parent", "owned_by", "created_by"
            ).prefetch_related("children__owned_by", "owned_by__player_owner"),
            id=self.kwargs["location_id"],
            campaign=self.campaign,
        )

    def get_context_data(self, **kwargs):
        """Add location detail context."""
        context = super().get_context_data(**kwargs)
        location = self.object
        context.update(
            {
                "page_title": f"{self.campaign.name} - {location.name}",
                "sub_locations": location.sub_locations.select_related(
                    "owned_by", "created_by"
                ).order_by("name"),
                "breadcrumb_path": location.get_path_from_root(),
                "full_path": location.get_full_path(),
                "can_edit": location.can_edit(self.request.user),
                "can_delete": location.can_delete(self.request.user),
                "owner_display": location.owner_display,
            }
        )

        return context


class LocationCreateView(CampaignSlugMappingMixin, CampaignFilterMixin, CreateView):
    """
    Location create view with parent selection and validation.

    Features:
    - Form with parent selection dropdown (campaign-scoped)
    - Permission checks (campaign members can create)
    - Set created_by to current user
    """

    model = Location
    form_class = LocationCreateForm
    template_name = "locations/location_form.html"

    def _has_permission(self, user_role):
        """Allow all campaign members to create locations."""
        return user_role in ["OWNER", "GM", "PLAYER", "OBSERVER"]

    def get_form_kwargs(self):
        """Add campaign and user to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs.update({"campaign": self.campaign, "user": self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        """Add create context."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": f"{self.campaign.name} - Create Location",
                "form_title": "Create New Location",
                "submit_text": "Create Location",
            }
        )
        return context

    def get_success_url(self):
        """Redirect to location detail after creation."""
        return reverse(
            "locations:location_detail",
            kwargs={"campaign_slug": self.campaign.slug, "location_id": self.object.id},
        )


class LocationEditView(CampaignSlugMappingMixin, CampaignFilterMixin, UpdateView):
    """
    Location edit view with hierarchy validation and permission checks.

    Features:
    - Use existing LocationEditForm
    - Permission checks (owner/GM/creator can edit)
    - Pre-populated with current values
    """

    model = Location
    form_class = LocationEditForm
    template_name = "locations/location_form.html"
    pk_url_kwarg = "location_id"

    def get_object(self):
        """Get location ensuring it belongs to the campaign."""
        location = get_object_or_404(
            Location.objects.select_related(
                "campaign", "parent", "owned_by", "created_by"
            ),
            id=self.kwargs["location_id"],
            campaign=self.campaign,
        )

        # Check edit permissions
        if not location.can_edit(self.request.user):
            raise Http404("Location not found")

        return location

    def get_form_kwargs(self):
        """Add user to form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Add edit context."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": f"{self.campaign.name} - Edit {self.object.name}",
                "form_title": f"Edit {self.object.name}",
                "submit_text": "Update Location",
            }
        )
        return context

    def get_success_url(self):
        """Redirect to location detail after editing."""
        return reverse(
            "locations:location_detail",
            kwargs={"campaign_slug": self.campaign.slug, "location_id": self.object.id},
        )
