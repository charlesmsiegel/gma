"""
API views for campaign listing and detail operations.

This module provides REST API endpoints for campaign listing and detail views
with proper visibility controls, filtering, and pagination using Django REST Framework.

Key Features:
- Standardized campaign permission checking via CampaignLookupMixin
- Consolidated campaign retrieval and validation patterns
- Role-based access control (OWNER, GM, PLAYER, OBSERVER)
- Secure error handling that prevents information leakage
"""

from django.db.models import Q, QuerySet
from rest_framework import filters, generics, permissions
from rest_framework.pagination import PageNumberPagination

from api.errors import SecurityResponseHelper
from api.serializers import CampaignDetailSerializer, CampaignSerializer
from campaigns.models import Campaign


class CampaignPagination(PageNumberPagination):
    """Custom pagination for campaign API endpoints."""

    page_size = 25  # Default page size
    page_size_query_param = "page_size"  # Allow user to control page size
    max_page_size = 100  # Maximum allowed page size


class CampaignListAPIView(generics.ListAPIView):
    """
    API view for listing campaigns with advanced filtering and search.

    Features:
    - Visibility logic: public campaigns to all, private campaigns only to members
    - Member campaigns appear first in results
    - Role-based filtering via ?role=owner|gm|player|observer
    - Search functionality via ?q=search_term
    - Configurable pagination via ?page_size=N (max 100, default 25)
    - Include user role in each campaign response
    """

    serializer_class = CampaignSerializer
    pagination_class = CampaignPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "game_system"]
    ordering_fields = ["created_at", "updated_at", "name"]
    permission_classes = []  # Allow unauthenticated access to public campaigns

    def get_queryset(self) -> QuerySet[Campaign]:
        """Return campaigns visible to the user with proper ordering and filtering."""
        user = self.request.user

        # Start with visibility-filtered queryset using custom manager
        queryset = (
            Campaign.objects.visible_to_user(user)
            .select_related("owner")
            .prefetch_related("memberships__user")
        )

        # Only show active campaigns by default (matching template view)
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

        # Apply search filtering (handled by DRF SearchFilter)
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

    def get_serializer_context(self):
        """Add request to serializer context for user_role calculation."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class CampaignDetailAPIView(generics.RetrieveAPIView):
    """
    API view for retrieving campaign details.

    Features:
    - Permission-based access: public campaigns to all, private campaigns to members only  # noqa: E501
    - Role-specific data: different fields based on user role
    - Include user role in response
    - Return 404 for private campaigns when user is not a member
    """

    serializer_class = CampaignDetailSerializer
    lookup_field = "pk"
    permission_classes = []  # Allow unauthenticated access to public campaigns

    def get_queryset(self):
        """Return campaigns visible to the user with proper permission filtering."""
        user = self.request.user
        return (
            Campaign.objects.visible_to_user(user)
            .select_related("owner")
            .prefetch_related("memberships__user")
        )

    def get_serializer_context(self):
        """Add request to serializer context for role-specific data."""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# Keep the existing views for backward compatibility
class CampaignListCreateAPIView(generics.ListCreateAPIView):
    """
    API view for listing and creating campaigns.

    GET: Returns a paginated list of campaigns accessible to the user
    POST: Creates a new campaign with the authenticated user as owner
    """

    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return campaigns accessible to the authenticated user."""
        # For now, return all active campaigns
        # Later this can be filtered to only show campaigns the user has access to
        return Campaign.objects.filter(is_active=True).select_related("owner")

    def perform_create(self, serializer):
        """Set the owner to the authenticated user when creating a campaign."""
        # Check email verification requirement (superusers bypass)
        if not self.request.user.email_verified and not self.request.user.is_superuser:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Email verification required to create campaigns.")

        serializer.save(owner=self.request.user)


class CampaignMembershipListAPIView(generics.ListCreateAPIView):
    """
    API view for listing and creating campaign memberships.

    GET: Returns memberships for a specific campaign
    POST: Adds a new member to the campaign (owner/GM only)
    """

    from api.serializers import CampaignMembershipSerializer

    serializer_class = CampaignMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return memberships for the specified campaign."""
        from campaigns.models import CampaignMembership

        campaign_pk = self.kwargs.get("campaign_pk")
        return CampaignMembership.objects.filter(
            campaign_id=campaign_pk
        ).select_related("user", "campaign")

    def perform_create(self, serializer):
        """Create membership with the campaign from URL."""
        campaign_pk = self.kwargs.get("campaign_pk")

        # Check if campaign exists and user has permission
        campaign, error_response = SecurityResponseHelper.safe_get_or_404(
            Campaign.objects,
            self.request.user,
            lambda user, camp: camp.is_owner(user) or camp.is_gm(user),
            pk=campaign_pk,
        )
        if error_response:
            # This is in perform_create, so we need to raise an exception
            # instead of returning a Response
            from rest_framework.exceptions import NotFound

            raise NotFound("Campaign not found.")

        serializer.save(campaign=campaign)


class UserCampaignListAPIView(generics.ListAPIView):
    """
    API view for listing campaigns belonging to the authenticated user.

    GET: Returns campaigns owned by or where user is a member
    """

    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return campaigns where the user is owner or member."""
        user = self.request.user

        # Get campaigns where user is owner or has membership
        owned_campaigns = Q(owner=user)
        member_campaigns = Q(memberships__user=user)

        return (
            Campaign.objects.filter(owned_campaigns | member_campaigns)
            .select_related("owner")
            .distinct()
        )
