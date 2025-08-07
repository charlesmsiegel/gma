"""
API views for campaign management.

This module provides REST API endpoints for campaign creation, listing,
and management using Django REST Framework.
"""

from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from api.serializers import (
    CampaignDetailSerializer,
    CampaignMembershipSerializer,
    CampaignSerializer,
)
from campaigns.models import Campaign, CampaignMembership


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


class CampaignDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
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

    serializer_class = CampaignMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return memberships for the specified campaign."""
        campaign_pk = self.kwargs.get("campaign_pk")
        return CampaignMembership.objects.filter(
            campaign_id=campaign_pk
        ).select_related("user", "campaign")

    def perform_create(self, serializer):
        """Create membership with the campaign from URL."""
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
