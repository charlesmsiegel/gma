"""
API views for campaign management.

This module provides REST API endpoints for campaign listing and detail views
with proper visibility controls, filtering, and pagination using Django REST Framework.
"""

from django.db.models import Q
from rest_framework import filters, generics, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

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

    def get_queryset(self):
        """Return campaigns visible to the user with proper ordering and filtering."""
        user = self.request.user

        # Start with base queryset with optimized joins
        queryset = Campaign.objects.select_related("owner").prefetch_related(
            "memberships__user"
        )

        # Only show active campaigns by default (matching template view)
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

        # Apply search filtering (handled by DRF SearchFilter)
        search_query = self.request.GET.get("q", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(game_system__icontains=search_query)
            )

        # Order results: member campaigns first, then by creation date
        if user.is_authenticated:
            # Custom ordering to put member campaigns first
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
        queryset = Campaign.objects.select_related("owner").prefetch_related(
            "memberships__user"
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
        serializer.save(owner=self.request.user)


class CampaignDetailAPIView_Old(generics.RetrieveUpdateDestroyAPIView):
    """
    API view for retrieving, updating, and deleting a specific campaign.

    GET: Returns campaign details
    PUT/PATCH: Updates campaign (owner only)
    DELETE: Deletes campaign (owner only)
    """

    serializer_class = CampaignDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        """Return campaigns accessible to the authenticated user."""
        # For now, return all campaigns
        # Later add permission filtering
        return Campaign.objects.select_related("owner").prefetch_related(
            "memberships__user"
        )

    def get_permissions(self):
        """
        Instantiate and return the list of permissions required for this view.
        Only owners can modify or delete campaigns.
        """
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            self.permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
        return super().get_permissions()


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of a campaign to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the campaign
        return obj.owner == request.user


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
        from rest_framework import status

        campaign_pk = self.kwargs.get("campaign_pk")
        try:
            campaign = Campaign.objects.get(pk=campaign_pk)
        except Campaign.DoesNotExist:
            return Response(
                {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if user has permission to add members (owner or GM)
        user = self.request.user
        if not (campaign.is_owner(user) or campaign.is_gm(user)):
            return Response(
                {"detail": "Permission denied to add members to this campaign."},
                status=status.HTTP_403_FORBIDDEN,
            )

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
