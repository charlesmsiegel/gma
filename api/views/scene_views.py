"""
API views for scene management operations.

This module provides REST API endpoints for scene CRUD operations
with proper permission checks, filtering, and participant management.

Key Features:
- Role-based access control (OWNER, GM can manage; all members can view)
- Campaign membership filtering
- Scene participant management
- Status transition validation
- Audit trail integration
- Pagination and search functionality
"""

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from api.serializers import (
    SceneCreateUpdateSerializer,
    SceneDetailSerializer,
    SceneSerializer,
)
from campaigns.models import Campaign
from characters.models import Character
from scenes.models import Scene

User = get_user_model()


class SceneAuthenticated(permissions.BasePermission):
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


class ScenePagination(PageNumberPagination):
    """Custom pagination for scene API endpoints."""

    page_size = 20  # Default page size
    page_size_query_param = "page_size"  # Allow user to control page size
    max_page_size = 100  # Maximum allowed page size


class SceneViewSet(viewsets.ModelViewSet):
    """
    ViewSet for scene CRUD operations with role-based permissions.

    Features:
    - List scenes (filtered by campaign and user permissions)
    - Create scenes (OWNER/GM only)
    - Retrieve scene details (with permission checks)
    - Update scenes (OWNER/GM only)
    - Delete scenes (OWNER/GM only)
    - Participant management endpoints
    - Status change validation
    - Search and filtering support
    """

    serializer_class = SceneSerializer
    pagination_class = ScenePagination
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "status", "created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_permissions(self):
        """Override to use custom permission that returns 401."""
        return [SceneAuthenticated()]

    def get_queryset(self) -> QuerySet[Scene]:
        """
        Get scenes based on user permissions with optimized queries.

        Uses custom manager methods for cleaner, more performant queries.
        """
        user = self.request.user

        # Start with base queryset (without distinct until after all filters)
        queryset = (
            Scene.objects.filter(
                Q(campaign__owner=user) | Q(campaign__memberships__user=user)
            )
            .select_related("campaign", "created_by")
            .prefetch_related("participants")
        )

        # Apply filters using queryset methods - support both 'campaign' and
        # 'campaign_id'
        campaign_id = (
            self.request.query_params.get("campaign_id")
            or self.request.query_params.get("campaign")
        )
        if campaign_id:
            try:
                queryset = queryset.filter(campaign_id=int(campaign_id))
            except (ValueError, TypeError):
                return Scene.objects.none()

        status_filter = self.request.query_params.get("status")
        if status_filter in dict(Scene.STATUS_CHOICES):
            queryset = queryset.filter(status=status_filter)

        # Support both 'participant' and 'participant_id' for backwards compatibility
        participant_id = self.request.query_params.get(
            "participant_id"
        ) or self.request.query_params.get("participant")
        if participant_id:
            try:
                queryset = queryset.filter(participants__id=int(participant_id))
            except (ValueError, TypeError):
                return Scene.objects.none()

        # Apply distinct after all filters to avoid duplicates from joins
        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        """List scenes with proper security-focused permission checking."""
        user = request.user

        # Check if user has access to any campaigns for security
        campaign_id = request.query_params.get(
            "campaign_id"
        ) or request.query_params.get("campaign")

        if campaign_id:
            # Check specific campaign access
            try:
                campaign_id = int(campaign_id)
                has_access = Campaign.objects.filter(
                    Q(id=campaign_id) & (Q(owner=user) | Q(memberships__user=user))
                ).exists()
                if not has_access:
                    from rest_framework.exceptions import NotFound

                    raise NotFound("No scenes found.")
            except (ValueError, TypeError):
                from rest_framework.exceptions import NotFound

                raise NotFound("No scenes found.")
        else:
            # Check general campaign access
            has_campaigns = Campaign.objects.filter(
                Q(owner=user) | Q(memberships__user=user)
            ).exists()
            if not has_campaigns:
                from rest_framework.exceptions import NotFound

                raise NotFound("No scenes found.")

        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == "retrieve":
            return SceneDetailSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return SceneCreateUpdateSerializer
        return SceneSerializer

    def get_serializer_context(self):
        """Add campaign_id to serializer context for validation."""
        context = super().get_serializer_context()

        # Add campaign_id if available
        campaign_id = self.request.query_params.get("campaign_id")
        if campaign_id:
            try:
                context["campaign_id"] = int(campaign_id)
            except (ValueError, TypeError):
                pass

        return context

    def create(self, request, *args, **kwargs):
        """Create scene with proper permission checks."""
        # Get campaign from the request data for permission check
        campaign_id = request.data.get("campaign")
        if campaign_id:
            try:
                campaign_id = int(campaign_id)
                campaign = Campaign.objects.get(pk=campaign_id)
                user_role = campaign.get_user_role(request.user)

                if user_role not in ["OWNER", "GM"]:
                    if user_role in ["PLAYER", "OBSERVER"]:
                        from rest_framework.exceptions import PermissionDenied

                        raise PermissionDenied(
                            "Only campaign owners and GMs can create scenes."
                        )
                    else:
                        from rest_framework.exceptions import NotFound

                        raise NotFound("Campaign not found.")

            except (ValueError, TypeError, Campaign.DoesNotExist):
                pass  # Let serializer handle this validation error

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Save scene with proper audit user."""
        serializer.save()

    def perform_update(self, serializer):
        """Update scene with proper permissions check."""
        scene = self.get_object()
        user = self.request.user

        # Check if user can update this scene
        user_role = scene.campaign.get_user_role(user)
        if user_role not in ["OWNER", "GM"]:
            if user_role in ["PLAYER", "OBSERVER"]:
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied("Only campaign owners and GMs can edit scenes.")
            else:
                from rest_framework.exceptions import NotFound

                raise NotFound("Scene not found.")

        serializer.save()

    def perform_destroy(self, instance):
        """Delete scene with proper permissions check."""
        user = self.request.user

        # Check if user can delete this scene
        user_role = instance.campaign.get_user_role(user)
        if user_role not in ["OWNER", "GM"]:
            if user_role in ["PLAYER", "OBSERVER"]:
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied(
                    "Only campaign owners and GMs can delete scenes."
                )
            else:
                from rest_framework.exceptions import NotFound

                raise NotFound("Scene not found.")

        instance.delete()

    def retrieve(self, request, *args, **kwargs):
        """Retrieve scene with permission checks."""
        instance = self.get_object()
        user = request.user

        # Check if user has access to this scene
        user_role = instance.campaign.get_user_role(user)
        if user_role not in ["OWNER", "GM", "PLAYER", "OBSERVER"]:
            from rest_framework.exceptions import NotFound

            raise NotFound("Scene not found.")

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_participant(self, request, pk=None):
        """Add a participant to the scene."""
        scene = self.get_object()
        user = request.user

        # Check if user can manage participants
        user_role = scene.campaign.get_user_role(user)
        if user_role not in ["OWNER", "GM", "PLAYER", "OBSERVER"]:
            from rest_framework.exceptions import NotFound

            raise NotFound("Scene not found.")

        character_id = request.data.get("character_id")
        if not character_id:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"character_id": ["Character ID is required."]})

        try:
            character = Character.objects.get(pk=character_id)
        except Character.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Character not found.")

        # Verify character is in the same campaign
        if character.campaign != scene.campaign:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {
                    "character_id": [
                        "Character must be in the same campaign as the scene."
                    ]
                }
            )

        # Check if user can add this specific character
        can_add = False
        if user_role in ["OWNER", "GM"]:
            can_add = True
        elif user_role in ["PLAYER", "OBSERVER"] and character.player_owner == user:
            can_add = True

        if not can_add:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You can only add your own characters to scenes.")

        # Check if character is already participating
        if scene.participants.filter(pk=character.pk).exists():
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {"character_id": ["Character is already participating in this scene."]}
            )

        # Add participant
        scene.participants.add(character)

        return Response(
            {
                "detail": f"{character.name} added to scene.",
                "character": {
                    "id": character.pk,
                    "name": character.name,
                    "npc": character.npc,
                    "player_owner": {
                        "id": character.player_owner.pk,
                        "username": character.player_owner.username,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path="participants/(?P<character_id>[0-9]+)",
    )
    def remove_participant(self, request, pk=None, character_id=None):
        """Remove a participant from the scene."""
        scene = self.get_object()
        user = request.user

        # Check if user has access to this scene
        user_role = scene.campaign.get_user_role(user)
        if user_role not in ["OWNER", "GM", "PLAYER", "OBSERVER"]:
            from rest_framework.exceptions import NotFound

            raise NotFound("Scene not found.")

        if not character_id:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"character_id": ["Character ID is required."]})

        try:
            character = Character.objects.get(pk=character_id)
        except Character.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Character not found.")

        # Check if character is actually participating
        if not scene.participants.filter(pk=character.pk).exists():
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {"character_id": ["Character is not participating in this scene."]}
            )

        # Check if user can remove this specific character
        can_remove = False
        if user_role in ["OWNER", "GM"]:
            can_remove = True
        elif user_role in ["PLAYER", "OBSERVER"] and character.player_owner == user:
            can_remove = True

        if not can_remove:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "You can only remove your own characters from scenes."
            )

        # Remove participant
        scene.participants.remove(character)

        return Response(
            {
                "detail": f"{character.name} removed from scene.",
                "character_id": character.pk,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def change_status(self, request, pk=None):
        """Change scene status with validation."""
        scene = self.get_object()
        user = request.user

        # Check if user can change status
        user_role = scene.campaign.get_user_role(user)
        if user_role not in ["OWNER", "GM"]:
            if user_role in ["PLAYER", "OBSERVER"]:
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied(
                    "Only campaign owners and GMs can change scene status."
                )
            else:
                from rest_framework.exceptions import NotFound

                raise NotFound("Scene not found.")

        new_status = request.data.get("status")
        if not new_status:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"status": ["Status is required."]})

        # Use the serializer to validate status transition
        serializer = SceneCreateUpdateSerializer(
            scene,
            data={"status": new_status},
            partial=True,
            context=self.get_serializer_context(),
        )

        if not serializer.is_valid():
            from rest_framework.exceptions import ValidationError

            raise ValidationError(serializer.errors)

        # Check if status actually changed
        if serializer.validated_data.get("status") == scene.status:
            return Response(
                {
                    "detail": "Status unchanged.",
                    "status": scene.status,
                    "status_display": scene.get_status_display(),
                },
                status=status.HTTP_200_OK,
            )

        # Save the change
        serializer.save()

        return Response(
            {
                "detail": f"Scene status changed to {scene.get_status_display()}.",
                "status": scene.status,
                "status_display": scene.get_status_display(),
            },
            status=status.HTTP_200_OK,
        )
