"""
Item API CRUD views.

This module provides the core CRUD operations for item management including
list, create, detail, update, and soft delete endpoints with proper
permission checking and single character ownership support.
"""

import logging

from django.db.models import Q
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.errors import APIError, SecurityResponseHelper
from api.serializers import ItemCreateUpdateSerializer, ItemSerializer
from campaigns.models import Campaign
from characters.models import Character
from items.models import Item

logger = logging.getLogger(__name__)


class ItemPagination(PageNumberPagination):
    """Custom pagination for item API."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ItemPermissionMixin:
    """Mixin to standardize item permission checking across views."""

    def check_item_permission(self, item, user, action):
        """
        Standardized permission checking for item operations.

        Args:
            item: Item instance to check
            user: User to check permissions for
            action: Action to check ('view', 'edit', 'delete')

        Returns:
            None if permitted, Response if denied
        """
        if action == "view":
            # Users can view items if they're campaign members
            user_role = item.campaign.get_user_role(user)
            if user_role is None and not user.is_superuser:
                return SecurityResponseHelper.resource_access_denied()
        elif action in ["edit", "delete"]:
            # Users can edit/delete if they can delete the item per model logic
            if not item.can_be_deleted_by(user):
                return SecurityResponseHelper.resource_access_denied()

        return None


class ItemListCreateAPIView(APIView, ItemPermissionMixin):
    """
    API view for listing and creating items.

    GET: List items in a campaign with filtering support
    POST: Create a new item
    """

    def get_permissions(self):
        """Set permissions based on method."""
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [IsAuthenticated()]  # Always require auth for items

    def get(self, request):
        """
        List items with campaign filtering.

        Query parameters:
        - campaign_id (required): Campaign ID to filter by
        - owner: Character owner ID to filter by
        - created_by: User creator ID to filter by
        - quantity_min: Minimum quantity filter
        - quantity_max: Maximum quantity filter
        - q: Search in name and description
        - include_deleted: Include soft-deleted items (default false)
        """
        # Check authentication
        if not request.user.is_authenticated:
            return APIError.create_unauthorized_response()

        # Validate and get campaign
        campaign_result = self._validate_campaign_access(request)
        if isinstance(campaign_result, Response):
            return campaign_result

        campaign, campaign_id = campaign_result

        # Build base queryset
        include_deleted = request.GET.get("include_deleted", "").lower() == "true"
        if include_deleted:
            queryset = Item.all_objects.filter(campaign=campaign)
        else:
            queryset = Item.objects.filter(campaign=campaign)

        # Optimize with select_related and prefetch_related
        queryset = queryset.select_related(
            "campaign", "owner", "created_by", "deleted_by"
        )

        # Apply filters
        filter_result = self._apply_item_filters(request, queryset, campaign_id)
        if isinstance(filter_result, Response):
            return filter_result

        queryset = filter_result

        # Apply ordering
        order_result = self._apply_ordering(request, queryset)
        if isinstance(order_result, Response):
            return order_result

        queryset = order_result

        # Return paginated response
        return self._create_paginated_response(request, queryset)

    def _validate_campaign_access(self, request):
        """Validate campaign ID and check user access permissions."""
        campaign_id = request.GET.get("campaign_id")
        if not campaign_id:
            return APIError.validation_error(
                {"campaign_id": ["Campaign ID is required."]}
            )

        try:
            campaign_id = int(campaign_id)
        except ValueError:
            return APIError.validation_error({"campaign_id": ["Invalid campaign ID."]})

        try:
            campaign = Campaign.objects.get(pk=campaign_id)
        except Campaign.DoesNotExist:
            return SecurityResponseHelper.resource_access_denied()

        # Check access permissions - users must be campaign members
        user_role = campaign.get_user_role(request.user)
        if not user_role and not request.user.is_superuser:
            return SecurityResponseHelper.resource_access_denied()

        return campaign, campaign_id

    def _apply_item_filters(self, request, queryset, campaign_id):
        """Apply owner, created_by, quantity, and search filters to the queryset."""
        # Apply owner filter
        owner_result = self._apply_owner_filter(request, queryset, campaign_id)
        if isinstance(owner_result, Response):
            return owner_result
        queryset = owner_result

        # Apply created_by filter
        created_by_result = self._apply_created_by_filter(request, queryset)
        if isinstance(created_by_result, Response):
            return created_by_result
        queryset = created_by_result

        # Apply quantity filters
        quantity_result = self._apply_quantity_filters(request, queryset)
        if isinstance(quantity_result, Response):
            return quantity_result
        queryset = quantity_result

        # Apply search filter (support both 'q' and 'search' for compatibility)
        search = request.GET.get("q") or request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        return queryset

    def _apply_owner_filter(self, request, queryset, campaign_id):
        """Apply character owner filter to the queryset."""
        owner_id = request.GET.get("owner")
        if owner_id is None:
            return queryset

        if owner_id == "null":
            return queryset.filter(owner__isnull=True)

        try:
            owner_id = int(owner_id)
            # Validate owner exists and is in same campaign
            try:
                owner_character = Character.objects.get(pk=owner_id)
                if owner_character.campaign_id != campaign_id:
                    return APIError.validation_error(
                        {"owner": ["Owner character must be in the same campaign."]}
                    )
            except Character.DoesNotExist:
                return SecurityResponseHelper.resource_access_denied()

            return queryset.filter(owner_id=owner_id)

        except ValueError:
            return APIError.validation_error({"owner": ["Invalid owner ID."]})

    def _apply_created_by_filter(self, request, queryset):
        """Apply created_by user filter to the queryset."""
        created_by_id = request.GET.get("created_by")
        if created_by_id is None:
            return queryset

        try:
            created_by_id = int(created_by_id)
            return queryset.filter(created_by_id=created_by_id)
        except ValueError:
            return APIError.validation_error({"created_by": ["Invalid created_by ID."]})

    def _apply_quantity_filters(self, request, queryset):
        """Apply quantity range filters to the queryset."""
        quantity_min = request.GET.get("quantity_min")
        quantity_max = request.GET.get("quantity_max")

        if quantity_min is not None:
            try:
                quantity_min = int(quantity_min)
                if quantity_min < 1:
                    return APIError.validation_error(
                        {"quantity_min": ["Minimum quantity must be at least 1."]}
                    )
                queryset = queryset.filter(quantity__gte=quantity_min)
            except ValueError:
                return APIError.validation_error(
                    {"quantity_min": ["Invalid quantity_min value."]}
                )

        if quantity_max is not None:
            try:
                quantity_max = int(quantity_max)
                if quantity_max < 1:
                    return APIError.validation_error(
                        {"quantity_max": ["Maximum quantity must be at least 1."]}
                    )
                queryset = queryset.filter(quantity__lte=quantity_max)
            except ValueError:
                return APIError.validation_error(
                    {"quantity_max": ["Invalid quantity_max value."]}
                )

        # Validate range
        if (
            quantity_min is not None
            and quantity_max is not None
            and quantity_min > quantity_max
        ):
            return APIError.validation_error(
                {
                    "quantity_range": [
                        "Minimum quantity cannot be greater than maximum quantity."
                    ]
                }
            )

        return queryset

    def _apply_ordering(self, request, queryset):
        """Apply ordering to the queryset."""
        ordering = request.GET.get("ordering")
        if not ordering:
            return queryset.order_by("name")

        valid_fields = [
            "name",
            "-name",
            "quantity",
            "-quantity",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
            "id",
            "-id",
        ]

        if ordering in valid_fields:
            return queryset.order_by(ordering)
        else:
            return APIError.validation_error(
                {"ordering": [f"Invalid ordering field: {ordering}"]}
            )

    def _create_paginated_response(self, request, queryset):
        """Create the final paginated response."""
        paginator = ItemPagination()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = ItemSerializer(page, many=True, context={"request": request})
            return paginator.get_paginated_response(serializer.data)

        # Fallback without pagination
        serializer = ItemSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        """Create a new item."""
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
        if not user_role and not request.user.is_superuser:
            # Non-member - return 404 for security (hide campaign existence)
            return SecurityResponseHelper.resource_access_denied()

        # Check if user can create items in this campaign (observers can't create)
        if user_role == "OBSERVER":
            # Campaign member with insufficient permissions - return 403
            return APIError.create_permission_denied_response(
                "Observers cannot create items."
            )

        # Create serializer with campaign context
        serializer = ItemCreateUpdateSerializer(
            data=request.data,
            context={
                "request": request,
                "campaign_id": campaign_id,
            },
        )

        if serializer.is_valid():
            item = serializer.save()
            logger.info(
                f"User {request.user.username} (ID: {request.user.id}) created "
                f"item '{item.name}' (ID: {item.id}) in campaign "
                f"'{campaign.name}' (ID: {campaign.id})"
            )
            return Response(
                ItemSerializer(item, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        return APIError.validation_error(serializer.errors)


class ItemDetailAPIView(APIView, ItemPermissionMixin):
    """
    API view for item detail, update, and delete operations.

    GET: Retrieve item details
    PUT: Update item
    DELETE: Soft delete item
    """

    def get_permissions(self):
        """Require authentication for all operations."""
        return [IsAuthenticated()]

    def get_object(self, pk, user=None):
        """
        Get item object with permission checking, including soft-deleted items
        for authorized users.
        """
        try:
            # Always use all_objects to include soft-deleted items
            # We'll filter them based on permissions below
            item = Item.all_objects.select_related(
                "campaign", "owner", "created_by", "deleted_by"
            ).get(pk=pk)
        except Item.DoesNotExist:
            return None

        # Use standardized permission checking
        permission_error = self.check_item_permission(item, user, "view")
        if permission_error:
            return None

        # For soft-deleted items, only users with delete permission can see them
        if item.is_deleted and not item.can_be_deleted_by(user):
            return None

        return item

    def get(self, request, pk):
        """Retrieve item details."""
        if not request.user.is_authenticated:
            return APIError.create_unauthorized_response()

        item = self.get_object(pk, request.user)
        if not item:
            return SecurityResponseHelper.resource_access_denied()

        serializer = ItemSerializer(item, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        """Update item."""
        if not request.user.is_authenticated:
            return APIError.create_unauthorized_response()

        item = self.get_object(pk, request.user)
        if not item:
            return SecurityResponseHelper.resource_access_denied()

        # Check if item is soft-deleted
        if item.is_deleted:
            return SecurityResponseHelper.resource_access_denied()

        # Check edit permission using standardized method
        permission_error = self.check_item_permission(item, request.user, "edit")
        if permission_error:
            return permission_error

        serializer = ItemCreateUpdateSerializer(
            item, data=request.data, context={"request": request}, partial=True
        )

        if serializer.is_valid():
            item = serializer.save()
            logger.info(
                f"User {request.user.username} (ID: {request.user.id}) updated "
                f"item '{item.name}' (ID: {item.id}) in campaign "
                f"'{item.campaign.name}'"
            )
            return Response(ItemSerializer(item, context={"request": request}).data)

        return APIError.validation_error(serializer.errors)

    def delete(self, request, pk):
        """Soft delete item."""
        if not request.user.is_authenticated:
            return APIError.create_unauthorized_response()

        item = self.get_object(pk, request.user)
        if not item:
            return SecurityResponseHelper.resource_access_denied()

        # Check if item is already soft-deleted
        if item.is_deleted:
            return SecurityResponseHelper.resource_access_denied()

        # Check delete permission using standardized method
        permission_error = self.check_item_permission(item, request.user, "delete")
        if permission_error:
            return permission_error

        # Perform soft delete
        try:
            item_name = item.name
            item_id = item.id
            campaign_name = item.campaign.name
            item.soft_delete(request.user)

            logger.info(
                f"User {request.user.username} (ID: {request.user.id}) "
                f"soft-deleted item '{item_name}' (ID: {item_id}) "
                f"from campaign '{campaign_name}'"
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        except (PermissionError, ValueError) as e:
            return APIError.create_bad_request_response(str(e))
