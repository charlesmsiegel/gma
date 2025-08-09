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

from campaigns.models import CampaignInvitation
from campaigns.permissions import CampaignLookupMixin

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
