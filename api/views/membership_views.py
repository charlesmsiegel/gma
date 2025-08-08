"""
API views for campaign membership management.

This module provides REST API endpoints for managing campaign memberships,
including adding, removing, changing roles, and bulk operations.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from campaigns.models import Campaign, CampaignMembership

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
    except Exception:
        # Handle database connection errors and other unexpected errors
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Check if user is a member
    if not campaign.is_member(request.user):
        return Response(
            {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Get members
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
    memberships = (
        CampaignMembership.objects.filter(campaign=campaign)
        .select_related("user")
        .order_by("role", "user__username")
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

    # Get target membership
    try:
        membership = CampaignMembership.objects.get(campaign=campaign, user_id=user_id)
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
        if membership.role == "GM":
            return Response(
                {"detail": "Member not found."}, status=status.HTTP_404_NOT_FOUND
            )
    else:
        return Response(
            {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Remove member
    membership.delete()

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

    # Get target membership
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

    # Update role
    membership.role = new_role
    membership.save()

    # Notification removed for simplicity

    return Response({"detail": "Role updated successfully.", "role": new_role})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def bulk_add_members(request, campaign_id):
    """
    Bulk add members to a campaign.

    Only owners and GMs can add members.
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id, is_active=True)
    except Campaign.DoesNotExist:
        return Response(
            {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Check permissions
    user_role = campaign.get_user_role(request.user)
    if user_role not in ["OWNER", "GM"]:
        return Response(
            {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
        )

    # Get members data
    members = request.data.get("members", [])
    if not members:
        return Response(
            {"members": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST
        )

    # Validate and add members
    added = []
    errors = []

    with transaction.atomic():
        for member_data in members:
            user_id = member_data.get("user_id")
            role = member_data.get("role", "PLAYER")

            if not user_id:
                errors.append({"user_id": "This field is required."})
                continue

            if role not in ["GM", "PLAYER", "OBSERVER"]:
                errors.append({"user_id": user_id, "error": "Invalid role."})
                continue

            # Check if user exists
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                errors.append({"user_id": user_id, "error": "User not found."})
                continue

            # Check if already a member
            if (
                user == campaign.owner
                or CampaignMembership.objects.filter(
                    campaign=campaign, user=user
                ).exists()
            ):
                errors.append(
                    {"user_id": user_id, "error": "User is already a member."}
                )
                continue

            # Add member
            CampaignMembership.objects.create(campaign=campaign, user=user, role=role)
            added.append({"user_id": user.id, "username": user.username, "role": role})

    if errors and not added:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {"added": added, "failed": errors if errors else []},
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def bulk_change_roles(request, campaign_id):
    """
    Bulk change member roles in a campaign.

    Only owners and GMs can change roles.
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id, is_active=True)
    except Campaign.DoesNotExist:
        return Response(
            {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Check permissions
    user_role = campaign.get_user_role(request.user)
    if user_role not in ["OWNER", "GM"]:
        return Response(
            {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
        )

    # Get changes data
    changes = request.data.get("changes", [])
    if not changes:
        return Response(
            {"changes": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST
        )

    # Apply changes
    updated = []
    errors = []

    with transaction.atomic():
        for change in changes:
            user_id = change.get("user_id")
            new_role = change.get("role")

            if not user_id or not new_role:
                errors.append({"error": "user_id and role are required."})
                continue

            if new_role not in ["GM", "PLAYER", "OBSERVER"]:
                errors.append({"user_id": user_id, "error": "Invalid role."})
                continue

            # Cannot change owner's role
            if user_id == campaign.owner.id:
                errors.append(
                    {"user_id": user_id, "error": "Cannot change owner's role."}
                )
                continue

            # Get membership
            try:
                membership = CampaignMembership.objects.get(
                    campaign=campaign, user_id=user_id
                )
            except CampaignMembership.DoesNotExist:
                errors.append({"user_id": user_id, "error": "Member not found."})
                continue

            # Check permission for this change
            if user_role == "GM" and membership.role == "GM":
                # Permission errors should fail the entire operation
                return Response(
                    {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
                )

            # Update role
            membership.role = new_role
            membership.save()

            # Notification removed for simplicity

            updated.append({"user_id": user_id, "role": new_role})

    if errors and not updated:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"updated": updated, "errors": errors if errors else None})


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def bulk_remove_members(request, campaign_id):
    """
    Bulk remove members from a campaign.

    Only owners and GMs can remove members.
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id, is_active=True)
    except Campaign.DoesNotExist:
        return Response(
            {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
        )

    # Check permissions
    user_role = campaign.get_user_role(request.user)
    if user_role not in ["OWNER", "GM"]:
        return Response(
            {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
        )

    # Get user IDs to remove
    user_ids = request.data.get("user_ids", [])
    if not user_ids:
        return Response(
            {"user_ids": ["This field is required."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Remove members
    removed = []
    errors = []

    with transaction.atomic():
        for user_id in user_ids:
            # Cannot remove owner
            if user_id == campaign.owner.id:
                errors.append({"user_id": user_id, "error": "Cannot remove owner."})
                continue

            # Get membership
            try:
                membership = CampaignMembership.objects.get(
                    campaign=campaign, user_id=user_id
                )
            except CampaignMembership.DoesNotExist:
                errors.append({"user_id": user_id, "error": "Member not found."})
                continue

            # Check permission for this removal
            if user_role == "GM" and membership.role == "GM":
                # Permission errors should fail the entire operation
                return Response(
                    {"detail": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND
                )

            # Remove member
            membership.delete()

            # Notification removed for simplicity

            removed.append({"user_id": user_id})

    if errors and not removed:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {"removed": removed, "errors": errors if errors else None},
        status=status.HTTP_204_NO_CONTENT,
    )
