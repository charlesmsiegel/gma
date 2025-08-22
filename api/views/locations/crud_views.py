"""
Location API CRUD views.

This module provides the core CRUD operations for location management including
list, create, detail, update, delete, and children endpoints with proper
permission checking and hierarchy support.
"""

import logging

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.errors import APIError, SecurityResponseHelper
from api.serializers import (
    LocationCreateUpdateSerializer,
    LocationDetailSerializer,
    LocationSerializer,
)
from campaigns.models import Campaign
from locations.models import Location
from locations.services import LocationService

logger = logging.getLogger(__name__)


class LocationPagination(PageNumberPagination):
    """Custom pagination for location API."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class LocationPermissionMixin:
    """Mixin to standardize location permission checking across views."""

    def check_location_permission(self, location, user, action):
        """
        Standardized permission checking for location operations.

        Args:
            location: Location instance to check
            user: User to check permissions for
            action: Action to check ('view', 'edit', 'delete')

        Returns:
            None if permitted, Response if denied
        """
        if not LocationService.check_permission(location, user, action):
            return SecurityResponseHelper.resource_access_denied()
        return None


class LocationListCreateAPIView(APIView, LocationPermissionMixin):
    """
    API view for listing and creating locations.

    GET: List locations in a campaign with filtering support
    POST: Create a new location
    """

    def get_permissions(self):
        """Set permissions based on method."""
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return []  # Allow anonymous for public campaigns

    def get(self, request):
        """
        List locations with campaign filtering.

        Query parameters:
        - campaign (required): Campaign ID to filter by
        - parent: Parent location ID to filter by
        - owner: Character owner ID to filter by
        - search: Search in name and description
        """
        # Campaign filter is required
        campaign_id = request.GET.get("campaign")
        if not campaign_id:
            return APIError.validation_error({"campaign": ["Campaign ID is required."]})

        try:
            campaign_id = int(campaign_id)
        except ValueError:
            return APIError.validation_error({"campaign": ["Invalid campaign ID."]})

        # Get campaign and check permissions
        try:
            campaign = Campaign.objects.get(pk=campaign_id)
        except Campaign.DoesNotExist:
            return SecurityResponseHelper.resource_access_denied()

        # Check if user can view locations in this campaign
        if not request.user.is_authenticated:
            if not campaign.is_public:
                return SecurityResponseHelper.resource_access_denied()
        else:
            # For authenticated users, check campaign membership or public status
            user_role = campaign.get_user_role(request.user)
            if not user_role and not campaign.is_public:
                return SecurityResponseHelper.resource_access_denied()

        # Build queryset with optimizations and annotations
        queryset = (
            Location.objects.filter(campaign=campaign)
            .select_related("campaign", "parent", "owned_by", "created_by")
            .annotate(
                children_count=Count("children"),
                siblings_count=Count("parent__children") - 1,
            )
        )

        # Apply additional filters
        parent_id = request.GET.get("parent")
        if parent_id is not None:
            if parent_id == "null":
                # Filter for root locations (no parent)
                queryset = queryset.filter(parent__isnull=True)
            else:
                try:
                    parent_id = int(parent_id)

                    # Validate parent exists and is in same campaign
                    try:
                        parent_location = Location.objects.get(pk=parent_id)
                        if parent_location.campaign_id != campaign_id:
                            return APIError.validation_error(
                                {
                                    "parent": [
                                        "Parent location must be in the same campaign."
                                    ]
                                }
                            )
                    except Location.DoesNotExist:
                        return SecurityResponseHelper.resource_access_denied()

                    queryset = queryset.filter(parent_id=parent_id)
                except ValueError:
                    return APIError.validation_error({"parent": ["Invalid parent ID."]})

        owner_id = request.GET.get("owner")
        if owner_id is not None:
            if owner_id == "null":
                # Filter for unowned locations
                queryset = queryset.filter(owned_by__isnull=True)
            else:
                try:
                    owner_id = int(owner_id)

                    # Validate owner exists and is in same campaign
                    try:
                        from characters.models import Character

                        owner_character = Character.objects.get(pk=owner_id)
                        if owner_character.campaign_id != campaign_id:
                            return APIError.validation_error(
                                {
                                    "owner": [
                                        "Owner character must be in the same campaign."
                                    ]
                                }
                            )
                    except Character.DoesNotExist:
                        return SecurityResponseHelper.resource_access_denied()

                    queryset = queryset.filter(owned_by_id=owner_id)
                except ValueError:
                    return APIError.validation_error({"owner": ["Invalid owner ID."]})

        # Search filter
        search = request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        # Ordering
        ordering = request.GET.get("ordering")
        if ordering:
            # Validate ordering field to prevent invalid field errors
            valid_fields = [
                "name",
                "-name",
                "created_at",
                "-created_at",
                "updated_at",
                "-updated_at",
                "id",
                "-id",
            ]
            # Note: depth is computed in serializer, so we can't order by it in DB
            if ordering in valid_fields:
                queryset = queryset.order_by(ordering)
            else:
                # Invalid field - return error
                return APIError.validation_error(
                    {"ordering": [f"Invalid ordering field: {ordering}"]}
                )
        else:
            # Default ordering by name (as expected by tests)
            queryset = queryset.order_by("name")

        # Apply pagination
        paginator = LocationPagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = LocationSerializer(
                page, many=True, context={"request": request}
            )
            return paginator.get_paginated_response(serializer.data)

        # Fallback without pagination (shouldn't happen but for safety)
        serializer = LocationSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request):
        """Create a new location."""
        # Check authentication
        if not request.user.is_authenticated:
            return APIError.create_unauthorized_response()

        # Get campaign from request data for permission checking
        campaign_id = request.data.get("campaign")
        if not campaign_id:
            return APIError.validation_error({"campaign": ["Campaign ID is required."]})

        try:
            campaign = Campaign.objects.get(pk=campaign_id)
        except Campaign.DoesNotExist:
            return SecurityResponseHelper.resource_access_denied()

        # Check campaign membership first
        user_role = campaign.get_user_role(request.user)
        if not user_role:
            # Non-member - return 404 for security (hide campaign existence)
            return SecurityResponseHelper.resource_access_denied()

        # Check if user can create locations in this campaign
        if not Location.can_create(request.user, campaign):
            # Campaign member with insufficient permissions - return 403
            return APIError.create_permission_denied_response()

        # Create serializer with campaign context
        serializer = LocationCreateUpdateSerializer(
            data=request.data,
            context={
                "request": request,
                "campaign_id": campaign_id,
            },
        )

        if serializer.is_valid():
            location = serializer.save()
            logger.info(
                f"User {request.user.username} (ID: {request.user.id}) created "
                f"location '{location.name}' (ID: {location.id}) in campaign "
                f"'{campaign.name}' (ID: {campaign.id})"
            )
            return Response(
                LocationSerializer(location, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        return APIError.validation_error(serializer.errors)


class LocationDetailAPIView(APIView, LocationPermissionMixin):
    """
    API view for location detail, update, and delete operations.

    GET: Retrieve location details with hierarchy info
    PUT: Update location
    DELETE: Delete location
    """

    def get_permissions(self):
        """Set permissions based on method."""
        if self.request.method in ["PUT", "DELETE"]:
            return [IsAuthenticated()]
        return []  # Allow anonymous for public campaigns

    def get_object(self, pk, user=None):
        """Get location object with permission checking and annotations."""
        try:
            location = (
                Location.objects.select_related(
                    "campaign", "parent", "owned_by", "created_by"
                )
                .prefetch_related(
                    "children", "children__owned_by", "children__created_by"
                )
                .annotate(
                    children_count=Count("children"),
                    siblings_count=Count("parent__children") - 1,
                )
                .get(pk=pk)
            )
        except Location.DoesNotExist:
            return None

        # Use standardized permission checking
        permission_error = self.check_location_permission(location, user, "view")
        if permission_error:
            return None

        return location

    def get(self, request, pk):
        """Retrieve location details."""
        location = self.get_object(pk, request.user)
        if not location:
            # Check if this is an authentication issue vs permission issue
            if not request.user.is_authenticated:
                try:
                    # Check if location exists at all to determine response type
                    raw_location = Location.objects.get(pk=pk)
                    # Location exists but user not authenticated for private campaign
                    if not raw_location.campaign.is_public:
                        return APIError.create_unauthorized_response()
                except Location.DoesNotExist:
                    pass
            return SecurityResponseHelper.resource_access_denied()

        serializer = LocationDetailSerializer(location, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        """Update location."""
        if not request.user.is_authenticated:
            return APIError.create_unauthorized_response()

        location = self.get_object(pk, request.user)
        if not location:
            return SecurityResponseHelper.resource_access_denied()

        # Check edit permission using standardized method
        permission_error = self.check_location_permission(
            location, request.user, "edit"
        )
        if permission_error:
            return permission_error

        serializer = LocationCreateUpdateSerializer(
            location, data=request.data, context={"request": request}, partial=True
        )

        if serializer.is_valid():
            location = serializer.save()
            logger.info(
                f"User {request.user.username} (ID: {request.user.id}) updated "
                f"location '{location.name}' (ID: {location.id}) in campaign "
                f"'{location.campaign.name}'"
            )
            return Response(
                LocationSerializer(location, context={"request": request}).data
            )

        return APIError.validation_error(serializer.errors)

    def delete(self, request, pk):
        """Delete location."""
        if not request.user.is_authenticated:
            return APIError.create_unauthorized_response()

        location = self.get_object(pk, request.user)
        if not location:
            return SecurityResponseHelper.resource_access_denied()

        # Check delete permission using standardized method
        permission_error = self.check_location_permission(
            location, request.user, "delete"
        )
        if permission_error:
            return permission_error

        location_name = location.name
        location_id = location.id
        campaign_name = location.campaign.name
        location.delete()
        logger.info(
            f"User {request.user.username} (ID: {request.user.id}) deleted location "
            f"'{location_name}' (ID: {location_id}) from campaign '{campaign_name}'"
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class LocationChildrenAPIView(APIView, LocationPermissionMixin):
    """
    API view for retrieving location children.

    GET: Get immediate children of a location
    """

    def get_permissions(self):
        """No authentication required for public campaigns."""
        return []

    def get_object(self, pk, user=None):
        """Get location object with permission checking."""
        try:
            location = Location.objects.select_related("campaign").get(pk=pk)
        except Location.DoesNotExist:
            return None

        # Use standardized permission checking
        permission_error = self.check_location_permission(location, user, "view")
        if permission_error:
            return None

        return location

    def get(self, request, pk):
        """Get children of a location."""
        location = self.get_object(pk, request.user)
        if not location:
            # Check if this is an authentication issue vs permission issue
            if not request.user.is_authenticated:
                try:
                    # Check if location exists at all to determine response type
                    raw_location = Location.objects.get(pk=pk)
                    # Location exists but user not authenticated for private campaign
                    if not raw_location.campaign.is_public:
                        return APIError.create_unauthorized_response()
                except Location.DoesNotExist:
                    pass
            return SecurityResponseHelper.resource_access_denied()

        # Get children with optimizations
        children = location.children.select_related(
            "campaign", "parent", "owned_by", "created_by"
        ).prefetch_related("children")

        serializer = LocationSerializer(
            children, many=True, context={"request": request}
        )
        return Response(serializer.data)


class LocationDescendantsAPIView(APIView, LocationPermissionMixin):
    """API view for getting location descendants."""

    def get_permissions(self):
        """Allow anonymous for public campaigns."""
        return []

    def get(self, request, pk):
        """Get all descendants of a location."""
        try:
            location = Location.objects.select_related("campaign").get(pk=pk)

            # Use standardized permission checking
            permission_error = self.check_location_permission(
                location, request.user, "view"
            )
            if permission_error:
                return permission_error

            descendants = (
                location.get_descendants()
                .select_related("campaign", "parent", "created_by")
                .prefetch_related("children")
            )

            serializer = LocationSerializer(
                descendants, many=True, context={"request": request}
            )
            return Response(serializer.data)

        except Location.DoesNotExist:
            return SecurityResponseHelper.resource_access_denied()


class LocationAncestorsAPIView(APIView, LocationPermissionMixin):
    """API view for getting location ancestors."""

    def get_permissions(self):
        """Allow anonymous for public campaigns."""
        return []

    def get(self, request, pk):
        """Get all ancestors of a location."""
        try:
            location = Location.objects.select_related("campaign").get(pk=pk)

            # Use standardized permission checking
            permission_error = self.check_location_permission(
                location, request.user, "view"
            )
            if permission_error:
                return permission_error

            ancestors = location.get_ancestors()

            serializer = LocationSerializer(
                ancestors, many=True, context={"request": request}
            )
            return Response(serializer.data)

        except Location.DoesNotExist:
            return SecurityResponseHelper.resource_access_denied()


class LocationSiblingsAPIView(APIView, LocationPermissionMixin):
    """API view for getting location siblings."""

    def get_permissions(self):
        """Allow anonymous for public campaigns."""
        return []

    def get(self, request, pk):
        """Get all siblings of a location."""
        try:
            location = Location.objects.select_related("campaign").get(pk=pk)

            # Use standardized permission checking
            permission_error = self.check_location_permission(
                location, request.user, "view"
            )
            if permission_error:
                return permission_error

            siblings = location.get_siblings()

            serializer = LocationSerializer(
                siblings, many=True, context={"request": request}
            )
            return Response(serializer.data)

        except Location.DoesNotExist:
            return SecurityResponseHelper.resource_access_denied()


class LocationPathFromRootAPIView(APIView, LocationPermissionMixin):
    """API view for getting path from root to location."""

    def get_permissions(self):
        """Allow anonymous for public campaigns."""
        return []

    def get(self, request, pk):
        """Get path from root to a location."""
        try:
            location = Location.objects.select_related("campaign").get(pk=pk)

            # Use standardized permission checking
            permission_error = self.check_location_permission(
                location, request.user, "view"
            )
            if permission_error:
                return permission_error

            path = location.get_path_from_root()

            serializer = LocationSerializer(
                path, many=True, context={"request": request}
            )
            return Response(serializer.data)

        except Location.DoesNotExist:
            return SecurityResponseHelper.resource_access_denied()


class LocationMoveAPIView(APIView, LocationPermissionMixin):
    """API view for moving a location to a different parent."""

    def get_permissions(self):
        """Require authentication for move operations."""
        return [IsAuthenticated()]

    def post(self, request, pk):
        """Move a location to a different parent."""
        try:
            location = Location.objects.select_related("campaign").get(pk=pk)

            # Use standardized permission checking
            permission_error = self.check_location_permission(
                location, request.user, "edit"
            )
            if permission_error:
                return permission_error

            new_parent_id = request.data.get("new_parent")

            # Validate new parent if provided
            new_parent = None
            if new_parent_id:
                try:
                    new_parent = Location.objects.get(pk=new_parent_id)

                    # Must be in same campaign
                    if new_parent.campaign != location.campaign:
                        return APIError.validation_error(
                            {
                                "new_parent": [
                                    "Parent location must be in the same campaign."
                                ]
                            }
                        )

                    # Check for circular reference
                    ancestors = [ancestor.pk for ancestor in new_parent.get_ancestors()]
                    if location.pk in ancestors or new_parent.pk == location.pk:
                        return APIError.validation_error(
                            {
                                "new_parent": [
                                    "Circular reference detected: cannot move "
                                    "location to its own descendant or itself."
                                ]
                            }
                        )

                except Location.DoesNotExist:
                    return APIError.validation_error(
                        {"new_parent": ["Parent location does not exist."]}
                    )

            # Perform the move
            old_parent_name = location.parent.name if location.parent else "root"
            location.parent = new_parent
            location.save()

            logger.info(
                f"User {request.user.username} (ID: {request.user.id}) moved "
                f"location '{location.name}' (ID: {location.id}) from "
                f"'{old_parent_name}' to '{new_parent.name if new_parent else 'root'}' "
                f"in campaign '{location.campaign.name}'"
            )

            # Return updated location
            serializer = LocationDetailSerializer(
                location, context={"request": request}
            )
            return Response(serializer.data)

        except Location.DoesNotExist:
            return SecurityResponseHelper.resource_access_denied()
