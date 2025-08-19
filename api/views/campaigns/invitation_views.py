"""
API views for campaign invitation management.

This module provides REST API endpoints for sending, accepting, declining, and
canceling campaign invitations with proper permission controls.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.errors import (
    APIError,
    FieldValidator,
    SecurityResponseHelper,
    handle_django_validation_error,
)
from api.serializers import (
    CampaignInvitationSerializer,
    InvitationAcceptResponseSerializer,
    InvitationCreateSerializer,
)
from campaigns.models import CampaignInvitation
from campaigns.permissions import CampaignLookupMixin
from campaigns.services import InvitationService

User = get_user_model()


class CampaignPermissionHelper(CampaignLookupMixin):
    """Helper class for function-based views to use CampaignLookupMixin."""

    def __init__(self, request):
        self.request = request


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def send_campaign_invitation(request, campaign_id):
    """
    Send an invitation to a user to join a campaign.

    Only campaign owners and GMs can send invitations.
    """
    # Use helper to check campaign permissions
    helper = CampaignPermissionHelper(request)
    result = helper.get_campaign_with_permissions(campaign_id, ["OWNER", "GM"])

    # If result is a Response object, it means an error occurred
    if isinstance(result, Response):
        return result

    campaign, _ = result

    # Get invitation data
    invited_user_id = request.data.get("invited_user_id")
    role = request.data.get("role")
    message = request.data.get("message", "")

    # Validate required fields
    errors = {}

    invited_user_id_error = FieldValidator.required_field(
        "invited_user_id", invited_user_id
    )
    if invited_user_id_error:
        errors.update(invited_user_id_error)

    role_error = FieldValidator.required_field("role", role)
    if role_error:
        errors.update(role_error)

    if errors:
        return APIError.validation_error(errors)

    # Get invited user
    invited_user = FieldValidator.validate_user_exists(invited_user_id)
    if not invited_user:
        return APIError.validation_error(
            FieldValidator.build_field_errors(invited_user_id="User not found.")
        )

    # Create invitation using service
    try:
        invitation_service = InvitationService(campaign)
        invitation = invitation_service.create_invitation(
            invited_user=invited_user,
            invited_by=request.user,
            role=role,
            message=message,
        )

        # TODO: Send notification to invited user

        serializer = InvitationCreateSerializer(invitation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except DjangoValidationError as e:
        return handle_django_validation_error(e)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_campaign_invitations(request, campaign_id):
    """
    List all invitations for a campaign.

    Only campaign owners and GMs can view all campaign invitations.
    """
    # Use helper to check campaign permissions
    helper = CampaignPermissionHelper(request)
    result = helper.get_campaign_with_permissions(campaign_id, ["OWNER", "GM"])

    # If result is a Response object, it means an error occurred
    if isinstance(result, Response):
        return result

    campaign, user_role = result

    # Get invitations using service
    invitation_service = InvitationService(campaign)
    status_filter = request.GET.get("status")
    invitations = invitation_service.get_campaign_invitations(status=status_filter)

    serializer = CampaignInvitationSerializer(invitations, many=True)
    results = serializer.data

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
    invitation, error_response = SecurityResponseHelper.safe_get_or_404(
        CampaignInvitation.objects,
        request.user,
        lambda user, inv: inv.invited_user == user,  # Permission check
        id=pk,
    )
    if error_response:
        return error_response

    try:
        membership = invitation.accept()

        # Build response data using serializers
        membership_data = {
            "campaign": membership.campaign,
            "role": membership.role,
            "joined_at": membership.joined_at,
        }

        response_data = {
            "detail": "Invitation accepted successfully.",
            "membership": membership_data,
        }

        serializer = InvitationAcceptResponseSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except DjangoValidationError as e:
        return handle_django_validation_error(e)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def decline_campaign_invitation(request, pk):
    """
    Decline a campaign invitation.

    Only the invited user can decline their own invitation.
    """
    invitation, error_response = SecurityResponseHelper.safe_get_or_404(
        CampaignInvitation.objects,
        request.user,
        lambda user, inv: inv.invited_user == user,  # Permission check
        id=pk,
    )
    if error_response:
        return error_response

    try:
        invitation.decline()

        return Response(
            {"detail": "Invitation declined successfully."}, status=status.HTTP_200_OK
        )

    except DjangoValidationError as e:
        return handle_django_validation_error(e)


@api_view(["POST", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def cancel_campaign_invitation(request, pk):
    """
    Cancel a campaign invitation.

    Only the invitation sender or campaign owner/GM can cancel invitations.
    """

    # Define permission check for cancellation
    def can_cancel_invitation(user, invitation):
        """Check if user can cancel this invitation."""
        user_role = invitation.campaign.get_user_role(user)
        return user == invitation.invited_by or user_role in ["OWNER", "GM"]

    invitation, error_response = SecurityResponseHelper.safe_get_or_404(
        CampaignInvitation.objects, request.user, can_cancel_invitation, id=pk
    )
    if error_response:
        return error_response

    try:
        invitation.cancel()

        return Response(
            {"detail": "Invitation cancelled successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )

    except DjangoValidationError as e:
        return handle_django_validation_error(e)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_user_invitations(request):
    """
    List all invitations for the current user.

    Users can see their own received invitations.
    """
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

    serializer = CampaignInvitationSerializer(invitations, many=True)
    results = serializer.data

    return Response(
        {"results": results, "count": len(results), "next": None, "previous": None}
    )
