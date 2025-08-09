"""
API views for campaign management.

This module provides REST API endpoints for campaign listing and detail views
with proper visibility controls, filtering, and pagination using Django REST Framework.

Key Features:
- Standardized campaign permission checking via CampaignLookupMixin
- Consolidated campaign retrieval and validation patterns
- Role-based access control (OWNER, GM, PLAYER, OBSERVER)
- Secure error handling that prevents information leakage
"""

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import filters, generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from api.serializers import CampaignDetailSerializer, CampaignSerializer
from campaigns.models import Campaign


class CampaignLookupMixin:
    """
    Mixin to handle campaign retrieval and permission validation for API views.

    Provides standardized campaign lookup with proper error handling and
    permission checking for campaign management operations.
    """

    def get_campaign_with_permissions(self, campaign_id, required_roles=None):
        """
        Retrieve campaign and validate user permissions.

        Args:
            campaign_id: The campaign ID to retrieve
            required_roles: List of roles required (e.g. ['OWNER', 'GM'])

        Returns:
            tuple: (campaign, user_role) if authorized

        Raises:
            Response: 404 if campaign not found or user lacks permission
        """
        if required_roles is None:
            required_roles = ["OWNER", "GM"]

        try:
            campaign = Campaign.objects.get(id=campaign_id, is_active=True)
        except Campaign.DoesNotExist:
            return Response(
                {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
            )

        user_role = campaign.get_user_role(self.request.user)
        if user_role not in required_roles:
            # Hide existence for security - return same 404
            return Response(
                {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return campaign, user_role


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


User = get_user_model()


class CampaignPermissionHelper(CampaignLookupMixin):
    """
    Helper class for function-based views to use CampaignLookupMixin.

    Since function-based views can't inherit from mixins directly,
    this helper provides the same functionality.
    """

    def __init__(self, request):
        self.request = request


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def campaign_user_search(request, campaign_id):
    """
    Search for users to invite to a campaign.

    Only campaign owners and GMs can search for users to invite.
    Excludes campaign owner, existing members, and users with pending invitations.
    """
    from django.core.paginator import Paginator
    from django.utils.html import escape

    # Use helper to check campaign permissions
    helper = CampaignPermissionHelper(request)
    result = helper.get_campaign_with_permissions(campaign_id, ["OWNER", "GM"])

    # If result is a Response object, it means an error occurred
    if isinstance(result, Response):
        return result

    campaign, user_role = result

    # Get search query
    query = request.GET.get("q", "").strip()
    if not query:
        return Response(
            {"detail": "Search query parameter 'q' is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check minimum query length
    if len(query) < 2:
        return Response(
            {"results": [], "count": 0, "query": query, "next": None, "previous": None}
        )

    # Start with all users
    users = User.objects.all()

    # Exclude campaign owner
    users = users.exclude(id=campaign.owner.id)

    # Exclude existing members
    existing_member_ids = campaign.memberships.values_list("user_id", flat=True)
    users = users.exclude(id__in=existing_member_ids)

    # Exclude users with pending invitations
    from campaigns.models import CampaignInvitation

    pending_invitation_user_ids = CampaignInvitation.objects.filter(
        campaign=campaign, status="PENDING"
    ).values_list("invited_user_id", flat=True)
    users = users.exclude(id__in=pending_invitation_user_ids)

    # Apply search filter (username or email)
    users = users.filter(Q(username__icontains=query) | Q(email__icontains=query))

    # Order by username
    users = users.order_by("username")

    # Pagination
    page_size = min(int(request.GET.get("page_size", 10)), 20)  # Max 20 results
    page_number = int(request.GET.get("page", 1))

    paginator = Paginator(users, page_size)
    page = paginator.get_page(page_number)

    # Serialize user data with XSS protection
    results = []
    for user in page:
        # Additional sanitization: remove javascript-related keywords
        def sanitize(value):
            if not value:
                return value
            # First escape HTML
            escaped = escape(value)
            # Then remove potentially dangerous content
            dangerous_patterns = [
                "alert(",
                "javascript:",
                "onclick=",
                "onerror=",
                "onload=",
            ]
            for pattern in dangerous_patterns:
                escaped = escaped.replace(pattern, "")
            return escaped

        results.append(
            {
                "id": user.id,
                "username": sanitize(user.username),
                "email": sanitize(user.email),
                "display_name": (
                    sanitize(getattr(user, "display_name", ""))
                    if getattr(user, "display_name", None)
                    else None
                ),
            }
        )

    # Build pagination URLs
    request_url = request.build_absolute_uri(request.path)
    next_url = None
    previous_url = None

    if page.has_next():
        next_params = request.GET.copy()
        next_params["page"] = page.next_page_number()
        next_url = f"{request_url}?{next_params.urlencode()}"

    if page.has_previous():
        prev_params = request.GET.copy()
        prev_params["page"] = page.previous_page_number()
        previous_url = f"{request_url}?{prev_params.urlencode()}"

    return Response(
        {
            "results": results,
            "count": paginator.count,
            "query": escape(query),
            "next": next_url,
            "previous": previous_url,
            "page_size": page_size,
            "current_page": page_number,
            "total_pages": paginator.num_pages,
        }
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_campaign_invitation(request, campaign_id):
    """
    Send an invitation to a user to join a campaign.

    Only campaign owners and GMs can send invitations.
    """
    from django.core.exceptions import ValidationError as DjangoValidationError

    from campaigns.models import CampaignInvitation

    # Use helper to check campaign permissions
    helper = CampaignPermissionHelper(request)
    result = helper.get_campaign_with_permissions(campaign_id, ["OWNER", "GM"])

    # If result is a Response object, it means an error occurred
    if isinstance(result, Response):
        return result

    campaign, user_role = result

    # Get invitation data
    invited_user_id = request.data.get("invited_user_id")
    role = request.data.get("role")
    message = request.data.get("message", "")

    # Validate required fields
    if not invited_user_id:
        return Response(
            {"invited_user_id": ["This field is required."]},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not role:
        return Response(
            {"role": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST
        )

    # Get invited user
    try:
        invited_user = User.objects.get(id=invited_user_id)
    except User.DoesNotExist:
        return Response(
            {"invited_user_id": ["User not found."]}, status=status.HTTP_400_BAD_REQUEST
        )

    # Create invitation
    try:
        invitation = CampaignInvitation(
            campaign=campaign,
            invited_user=invited_user,
            invited_by=request.user,
            role=role,
            message=message,
        )
        invitation.full_clean()
        invitation.save()

        # TODO: Send notification to invited user

        return Response(
            {
                "id": invitation.id,
                "campaign": {"id": campaign.id, "name": campaign.name},
                "invited_user": {
                    "id": invited_user.id,
                    "username": invited_user.username,
                    "email": invited_user.email,
                },
                "invited_by": {
                    "id": request.user.id,
                    "username": request.user.username,
                },
                "role": invitation.role,
                "status": invitation.status,
                "message": invitation.message,
                "created_at": invitation.created_at,
                "expires_at": invitation.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )

    except DjangoValidationError as e:
        if hasattr(e, "message_dict"):
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_campaign_invitations(request, campaign_id):
    """
    List all invitations for a campaign.

    Only campaign owners and GMs can view all campaign invitations.
    """
    from campaigns.models import CampaignInvitation

    # Use helper to check campaign permissions
    helper = CampaignPermissionHelper(request)
    result = helper.get_campaign_with_permissions(campaign_id, ["OWNER", "GM"])

    # If result is a Response object, it means an error occurred
    if isinstance(result, Response):
        return result

    campaign, user_role = result

    # Get invitations
    invitations = (
        CampaignInvitation.objects.filter(campaign=campaign)
        .select_related("invited_user", "invited_by")
        .order_by("-created_at")
    )

    # Filter by status if requested
    status_filter = request.GET.get("status")
    if status_filter:
        invitations = invitations.filter(status__iexact=status_filter)

    results = []
    for invitation in invitations:
        results.append(
            {
                "id": invitation.id,
                "invited_user": {
                    "id": invitation.invited_user.id,
                    "username": invitation.invited_user.username,
                    "email": invitation.invited_user.email,
                },
                "invited_by": {
                    "id": invitation.invited_by.id,
                    "username": invitation.invited_by.username,
                },
                "role": invitation.role,
                "status": invitation.status,
                "message": invitation.message,
                "created_at": invitation.created_at,
                "expires_at": invitation.expires_at,
                "is_expired": invitation.is_expired,
            }
        )

    return Response(
        {"results": results, "count": len(results), "next": None, "previous": None}
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def accept_campaign_invitation(request, pk):
    """
    Accept a campaign invitation.

    Only the invited user can accept their own invitation.
    """
    from django.core.exceptions import ValidationError as DjangoValidationError

    from campaigns.models import CampaignInvitation

    try:
        invitation = CampaignInvitation.objects.get(id=pk)
    except CampaignInvitation.DoesNotExist:
        return Response(
            {"detail": "Invitation not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Check if user is the invited user
    if invitation.invited_user != request.user:
        return Response(
            {"detail": "Invitation not found."},
            status=status.HTTP_404_NOT_FOUND,  # Hide existence for security
        )

    try:
        membership = invitation.accept()

        return Response(
            {
                "detail": "Invitation accepted successfully.",
                "membership": {
                    "campaign": {
                        "id": membership.campaign.id,
                        "name": membership.campaign.name,
                    },
                    "role": membership.role,
                    "joined_at": membership.joined_at,
                },
            },
            status=status.HTTP_200_OK,
        )

    except DjangoValidationError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def decline_campaign_invitation(request, pk):
    """
    Decline a campaign invitation.

    Only the invited user can decline their own invitation.
    """
    from django.core.exceptions import ValidationError as DjangoValidationError

    from campaigns.models import CampaignInvitation

    try:
        invitation = CampaignInvitation.objects.get(id=pk)
    except CampaignInvitation.DoesNotExist:
        return Response(
            {"detail": "Invitation not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Check if user is the invited user
    if invitation.invited_user != request.user:
        return Response(
            {"detail": "Invitation not found."},
            status=status.HTTP_404_NOT_FOUND,  # Hide existence for security
        )

    try:
        invitation.decline()

        return Response(
            {"detail": "Invitation declined successfully."}, status=status.HTTP_200_OK
        )

    except DjangoValidationError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def cancel_campaign_invitation(request, pk):
    """
    Cancel a campaign invitation.

    Only the invitation sender or campaign owner/GM can cancel invitations.
    """
    from django.core.exceptions import ValidationError as DjangoValidationError

    from campaigns.models import CampaignInvitation

    try:
        invitation = CampaignInvitation.objects.get(id=pk)
    except CampaignInvitation.DoesNotExist:
        return Response(
            {"detail": "Invitation not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Check permissions - invitation sender or campaign owner/GM
    user_role = invitation.campaign.get_user_role(request.user)
    if request.user != invitation.invited_by and user_role not in ["OWNER", "GM"]:
        return Response(
            {"detail": "Invitation not found."},
            status=status.HTTP_404_NOT_FOUND,  # Hide existence for security
        )

    try:
        invitation.cancel()

        return Response(
            {"detail": "Invitation cancelled successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )

    except DjangoValidationError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_user_invitations(request):
    """
    List all invitations for the current user.

    Users can see their own received invitations.
    """
    from campaigns.models import CampaignInvitation

    # Get user's invitations
    invitations = (
        CampaignInvitation.objects.filter(invited_user=request.user)
        .select_related("campaign", "invited_by")
        .order_by("-created_at")
    )

    # Filter by status if requested
    status_filter = request.GET.get("status")
    if status_filter:
        invitations = invitations.filter(status__iexact=status_filter)

    results = []
    for invitation in invitations:
        results.append(
            {
                "id": invitation.id,
                "campaign": {
                    "id": invitation.campaign.id,
                    "name": invitation.campaign.name,
                    "game_system": invitation.campaign.game_system,
                },
                "invited_by": {
                    "id": invitation.invited_by.id,
                    "username": invitation.invited_by.username,
                },
                "role": invitation.role,
                "status": invitation.status,
                "message": invitation.message,
                "created_at": invitation.created_at,
                "expires_at": invitation.expires_at,
                "is_expired": invitation.is_expired,
            }
        )

    return Response(
        {"results": results, "count": len(results), "next": None, "previous": None}
    )
