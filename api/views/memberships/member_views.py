"""
API views for basic campaign membership operations.

This module provides REST API endpoints for listing, adding, and removing
individual campaign members with proper permission controls.
"""

from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from campaigns.models import Campaign, CampaignMembership
from campaigns.services import MembershipService

User = get_user_model()


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def list_campaign_members(request, campaign_id):
    """
    List all members of a campaign.

    All campaign members can view the member list.
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id, is_active=True)
    except Campaign.DoesNotExist:
        return Response(
            {"error": "Campaign not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        # Handle database connection errors and other unexpected errors
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Database error in list_campaign_members: {str(e)}")
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Check if user is a member
    if not campaign.is_member(request.user):
        return Response(
            {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Get members using service
    membership_service = MembershipService(campaign)
    results = []

    # Apply role filtering if requested
    role_filter = request.GET.get("role")

    # Add owner (only if not filtered or owner role requested)
    if not role_filter or role_filter.upper() == "OWNER":
        results.append(
            {
                "user": {
                    "id": campaign.owner.id,
                    "username": campaign.owner.username,
                    "email": campaign.owner.email,
                },
                "role": "OWNER",
                "joined_at": campaign.created_at,
            }
        )

    # Add other members
    memberships = membership_service.get_campaign_members().order_by(
        "role", "user__username"
    )

    # Apply role filtering to memberships
    if role_filter and role_filter.upper() in ["GM", "PLAYER", "OBSERVER"]:
        memberships = memberships.filter(role=role_filter.upper())

    for membership in memberships:
        results.append(
            {
                "user": {
                    "id": membership.user.id,
                    "username": membership.user.username,
                    "email": membership.user.email,
                },
                "role": membership.role,
                "joined_at": membership.joined_at,
            }
        )

    # Apply pagination
    page_size = min(int(request.GET.get("page_size", 25)), 100)
    page_number = int(request.GET.get("page", 1))

    # Simple pagination
    start = (page_number - 1) * page_size
    end = start + page_size
    paginated_results = results[start:end]

    # Build pagination response
    has_next = end < len(results)
    has_previous = start > 0

    return Response(
        {
            "results": paginated_results,
            "count": len(results),
            "next": f"?page={page_number + 1}" if has_next else None,
            "previous": f"?page={page_number - 1}" if has_previous else None,
        }
    )


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def remove_campaign_member(request, campaign_id, user_id):
    """
    Remove a member from a campaign.

    Owners can remove anyone, GMs can remove players/observers.
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id, is_active=True)
    except Campaign.DoesNotExist:
        return Response(
            {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Check permissions
    user_role = campaign.get_user_role(request.user)

    # Convert user_id to int
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return Response(
            {"detail": "Invalid user ID."}, status=status.HTTP_400_BAD_REQUEST
        )

    # Cannot remove owner
    if user_id == campaign.owner.id:
        return Response(
            {"detail": "Cannot remove campaign owner."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Use service to remove member
    membership_service = MembershipService(campaign)

    # Get the user to remove
    try:
        user_to_remove = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {"detail": "Member not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Check if membership exists and get target role
    try:
        membership = CampaignMembership.objects.get(campaign=campaign, user_id=user_id)
        target_role = membership.role
    except CampaignMembership.DoesNotExist:
        return Response(
            {"detail": "Member not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Check if user has permission to remove this member
    if user_role == "OWNER":
        # Owner can remove anyone
        pass
    elif user_role == "GM":
        # GM can only remove players and observers
        if target_role == "GM":
            return Response(
                {"detail": "Member not found."}, status=status.HTTP_404_NOT_FOUND
            )
    else:
        return Response(
            {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Remove member using service
    membership_service.remove_member(user_to_remove)

    # Notification removed for simplicity

    return Response(
        {"detail": "Member removed successfully."}, status=status.HTTP_204_NO_CONTENT
    )


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def change_member_role(request, campaign_id, user_id):
    """
    Change a member's role in a campaign.

    Owners can change any role, GMs can change players/observers.
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id, is_active=True)
    except Campaign.DoesNotExist:
        return Response(
            {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Check permissions
    user_role = campaign.get_user_role(request.user)

    # Convert user_id to int
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return Response(
            {"detail": "Invalid user ID."}, status=status.HTTP_400_BAD_REQUEST
        )

    # Cannot change owner's role
    if user_id == campaign.owner.id:
        return Response(
            {"detail": "Cannot change campaign owner's role."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get new role
    new_role = request.data.get("role")
    if not new_role:
        return Response(
            {"role": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST
        )

    if new_role not in ["GM", "PLAYER", "OBSERVER"]:
        return Response({"role": ["Invalid role."]}, status=status.HTTP_400_BAD_REQUEST)

    # Get target membership and check permissions
    try:
        membership = CampaignMembership.objects.get(campaign=campaign, user_id=user_id)
    except CampaignMembership.DoesNotExist:
        return Response(
            {"detail": "Member not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Check if user has permission to change this member's role
    if user_role == "OWNER":
        # Owner can change anyone's role
        pass
    elif user_role == "GM":
        # GM can only change players and observers
        if membership.role == "GM":
            return Response(
                {"detail": "Member not found."}, status=status.HTTP_404_NOT_FOUND
            )
    else:
        return Response(
            {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Update role using service
    membership_service = MembershipService(campaign)
    membership_service.change_member_role(membership, new_role)

    # Notification removed for simplicity

    return Response({"detail": "Role updated successfully.", "role": new_role})
