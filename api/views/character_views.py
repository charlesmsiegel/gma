"""
API views for character management operations.

This module provides REST API endpoints for character CRUD operations
with proper permission checks, filtering, and polymorphic support.

Key Features:
- Role-based access control (Character owners, GMs, campaign owners)
- Campaign membership filtering
- Soft delete support with admin hard delete
- Polymorphic character serialization
- Audit trail integration
- Pagination and search functionality
"""

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from api.errors import APIError
from api.serializers import CharacterCreateUpdateSerializer, CharacterSerializer
from campaigns.models import Campaign
from characters.models import Character

User = get_user_model()


class CharacterAuthenticated(permissions.BasePermission):
    """
    Custom authentication permission that returns 401 instead of 403.
    Uses custom exception handler to ensure proper status code.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            from rest_framework.exceptions import NotAuthenticated

            raise NotAuthenticated("Authentication credentials were not provided.")
        return True

    def has_object_permission(self, request, view, obj):
        # For object-level permissions, also check authentication
        if not request.user or not request.user.is_authenticated:
            from rest_framework.exceptions import NotAuthenticated

            raise NotAuthenticated("Authentication credentials were not provided.")
        return True


class CharacterPagination(PageNumberPagination):
    """Custom pagination for character API endpoints."""

    page_size = 20  # Default page size
    page_size_query_param = "page_size"  # Allow user to control page size
    max_page_size = 100  # Maximum allowed page size


class CharacterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for character CRUD operations with role-based permissions.

    Features:
    - List characters (filtered by campaign and user permissions)
    - Create characters (with campaign membership validation)
    - Retrieve character details (with permission checks)
    - Update characters (owners, GMs, campaign owners only)
    - Soft delete characters (with configurable permissions)
    - Hard delete endpoint for admins
    - Search and filtering support
    - Audit trail integration
    """

    serializer_class = CharacterSerializer
    pagination_class = CharacterPagination
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["name"]

    def get_permissions(self):
        """Override to use custom permission that returns 401."""
        return [CharacterAuthenticated()]

    def get_queryset(self) -> QuerySet[Character]:
        """Get characters based on user permissions and filters."""
        user = self.request.user

        try:
            # Start with base queryset - use all_objects for soft-deleted chars
            # if requested
            include_deleted = (
                self.request.query_params.get("include_deleted", "").lower() == "true"
            )
            if include_deleted:
                queryset = Character.all_objects.all()
            else:
                queryset = Character.objects.all()
        except Exception as e:
            # Handle database errors gracefully in production
            from rest_framework.exceptions import APIException

            class ServerErrorException(APIException):
                status_code = 500
                default_detail = "A server error occurred."
                default_code = "server_error"

            raise ServerErrorException(f"Database error: {str(e)}")

        # Optimize with select_related and prefetch_related
        queryset = queryset.select_related(
            "campaign", "player_owner", "deleted_by"
        ).prefetch_related("campaign__memberships__user")

        # Apply campaign filtering
        campaign_id = self.request.query_params.get("campaign")
        if campaign_id:
            try:
                campaign = Campaign.objects.get(pk=campaign_id)

                # Check if user has access to this campaign
                user_role = campaign.get_user_role(user)
                if user_role is None and not user.is_superuser:
                    # Non-members see no characters
                    return queryset.none()

                queryset = queryset.filter(campaign=campaign)

                # Apply role-based filtering within the campaign
                if user_role == "PLAYER" and not user.is_superuser:
                    # Players see only their own characters by default
                    user_filter = self.request.query_params.get("user")
                    if user_filter:
                        # If user filter is specified, check if they can see
                        # that user's chars
                        if int(user_filter) == user.id:
                            queryset = queryset.filter(player_owner=user)
                        else:
                            # Players can't see other players' characters
                            queryset = queryset.none()
                    else:
                        # Default: players see only their own characters
                        queryset = queryset.filter(player_owner=user)
                elif user_role in ["GM", "OWNER", "OBSERVER"] or user.is_superuser:
                    # GMs, owners, and observers see all characters in campaign
                    # Apply user filter if specified
                    user_filter = self.request.query_params.get("user")
                    if user_filter:
                        try:
                            filtered_user = User.objects.get(pk=user_filter)
                            queryset = queryset.filter(player_owner=filtered_user)
                        except (User.DoesNotExist, ValueError):
                            # Invalid user filter
                            queryset = queryset.none()

            except (Campaign.DoesNotExist, ValueError):
                # Invalid campaign ID
                return queryset.none()
        else:
            # No campaign filter - apply global permissions
            if user.is_superuser:
                # Superusers see all characters
                pass
            else:
                # Regular users see only characters in campaigns they're members of
                user_campaigns = Campaign.objects.filter(
                    Q(owner=user) | Q(memberships__user=user)
                ).distinct()
                queryset = queryset.filter(campaign__in=user_campaigns)

                # For players, further limit to their own characters
                user_roles_dict = {}
                for campaign in user_campaigns:
                    user_roles_dict[campaign.id] = campaign.get_user_role(user)

                # If user is only a player in some campaigns, filter appropriately
                player_only_campaigns = [
                    camp_id
                    for camp_id, role in user_roles_dict.items()
                    if role == "PLAYER"
                ]

                if player_only_campaigns:
                    # For campaigns where user is only a player, show only
                    # their characters
                    # For other campaigns, show all characters
                    player_chars_filter = Q(
                        campaign__id__in=player_only_campaigns, player_owner=user
                    )
                    other_campaigns_filter = Q(
                        campaign__id__in=[
                            camp_id
                            for camp_id in user_roles_dict.keys()
                            if camp_id not in player_only_campaigns
                        ]
                    )
                    queryset = queryset.filter(
                        player_chars_filter | other_campaigns_filter
                    )

        return queryset

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action in ["create", "update", "partial_update"]:
            return CharacterCreateUpdateSerializer
        return CharacterSerializer

    def get_object(self):
        """Get character with permission checking, including soft-deleted ones."""
        # Use all_objects to include soft-deleted characters
        # The API should allow access to soft-deleted characters for certain operations
        queryset = Character.all_objects.all()

        # Apply the same filtering as get_queryset but without permission filtering
        queryset = queryset.select_related(
            "campaign", "player_owner", "deleted_by"
        ).prefetch_related("campaign__memberships__user")

        # Perform the lookup filtering based on pk or slug
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        assert lookup_url_kwarg in self.kwargs, (
            "Expected view %s to be called with a URL keyword argument "
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            "attribute on the view correctly."
            % (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        try:
            obj = queryset.get(**filter_kwargs)
        except Character.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Character not found.")

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        # Check if user has permission to access this character
        user = self.request.user

        if user.is_superuser:
            return obj

        # Check campaign membership
        user_role = obj.campaign.get_user_role(user)
        if user_role is None:
            # Non-members cannot access characters
            from rest_framework.exceptions import NotFound

            raise NotFound("Character not found.")

        # All campaign members can view characters, but only character owners can edit
        # This allows players to see each other's characters in the same campaign
        # Access control for editing happens in the permission methods

        return obj

    def create(self, request, *args, **kwargs):
        """Create character with early permission check."""
        # Check campaign creation permissions before serializer validation
        campaign_id = request.data.get("campaign")
        if campaign_id:
            try:
                campaign = Campaign.objects.get(pk=campaign_id)
                user_role = campaign.get_user_role(request.user)

                # Only campaign members can create characters, but not observers
                if user_role is None:
                    from rest_framework.exceptions import PermissionDenied

                    raise PermissionDenied(
                        "You must be a member of this campaign to create characters."
                    )
                elif user_role == "OBSERVER":
                    from rest_framework.exceptions import PermissionDenied

                    raise PermissionDenied("Observers cannot create characters.")

            except Campaign.DoesNotExist:
                pass  # Let serializer handle this validation error

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Create character with audit trail."""
        serializer.save()

    def perform_update(self, serializer):
        """Update character with permission and audit trail."""
        character = self.get_object()
        user = self.request.user

        # Check edit permissions
        if not character.can_be_edited_by(user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You don't have permission to edit this character.")

        serializer.save()

    def check_object_permissions(self, request, obj):
        """Check object-level permissions."""
        super().check_object_permissions(request, obj)

        # For update operations, check edit permissions
        if request.method in ["PUT", "PATCH"]:
            if not obj.can_be_edited_by(request.user):
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied(
                    "You don't have permission to edit this character."
                )

        # For delete operations, check delete permissions
        elif request.method == "DELETE":
            if not obj.can_be_deleted_by(request.user):
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied(
                    "You don't have permission to delete this character."
                )

    def perform_destroy(self, instance):
        """Soft delete character with permission checks."""
        user = self.request.user

        # Check delete permissions
        if not instance.can_be_deleted_by(user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "You don't have permission to delete this character."
            )

        # Handle already deleted characters gracefully
        try:
            # Perform soft delete
            instance.soft_delete(user)
        except ValueError:
            # Character is already deleted - this is idempotent, so just return success
            pass

    @action(
        detail=True, methods=["delete"], permission_classes=[permissions.IsAdminUser]
    )
    def hard_delete(self, request, pk=None):
        """Hard delete character (admin only)."""
        # Get character including soft-deleted ones for hard delete
        try:
            character = Character.all_objects.get(pk=pk)
        except Character.DoesNotExist:
            return APIError.not_found()

        try:
            character.hard_delete(request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PermissionError as e:
            return APIError.permission_denied(str(e))

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        """Restore a soft-deleted character."""
        # Use all_objects to get soft-deleted characters
        try:
            character = Character.all_objects.get(pk=pk)
        except Character.DoesNotExist:
            return APIError.not_found()

        # Check permissions
        if not character.can_be_deleted_by(request.user):
            return APIError.permission_denied_as_not_found()

        try:
            character.restore(request.user)
            serializer = self.get_serializer(character)
            return Response(serializer.data)
        except (PermissionError, ValueError) as e:
            return APIError.bad_request(str(e))

    # Remove the custom override methods - let DRF handle errors naturally
