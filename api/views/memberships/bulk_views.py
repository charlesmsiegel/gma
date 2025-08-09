"""
API views for bulk campaign membership operations.

This module provides REST API endpoints for bulk adding, removing, and changing
roles of campaign members with proper transaction handling and error reporting.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.serializers import (
    BulkAddMemberResponseSerializer,
    BulkRemoveMemberResponseSerializer,
    BulkRoleChangeResponseSerializer,
)
from campaigns.models import Campaign, CampaignMembership
from campaigns.services import MembershipService

User = get_user_model()


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

    # Use service for bulk operations
    membership_service = MembershipService(campaign)
    added = []
    errors = []

    with transaction.atomic():
        users_to_add = []
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
                users_to_add.append((user, role))
            except User.DoesNotExist:
                errors.append({"user_id": user_id, "error": "User not found."})
                continue

        # Process users to add
        for user, role in users_to_add:
            try:
                membership_service.add_member(user, role)
                added.append(
                    {"user_id": user.id, "username": user.username, "role": role}
                )
            except ValidationError as e:
                # Extract the error message
                error_msg = str(e)
                if "already a member" in error_msg:
                    error_msg = "User is already a member."
                elif "Invalid role" in error_msg:
                    error_msg = "Invalid role."
                elif "Cannot add campaign owner" in error_msg:
                    error_msg = "User is already a member."  # Keep consistent message
                errors.append({"user_id": user.id, "error": error_msg})

    if errors and not added:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    response_data = {"added": added, "failed": errors if errors else []}
    serializer = BulkAddMemberResponseSerializer(response_data)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


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

    # Use service for bulk role changes
    membership_service = MembershipService(campaign)
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

            # Get membership for permission check
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

            # Update role using service
            try:
                membership_service.change_member_role(membership, new_role)
                updated.append({"user_id": user_id, "role": new_role})
            except ValidationError as e:
                errors.append({"user_id": user_id, "error": str(e)})

    if errors and not updated:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    response_data = {"updated": updated, "errors": errors if errors else None}
    serializer = BulkRoleChangeResponseSerializer(response_data)
    return Response(serializer.data)


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

    # Use service for bulk removal
    membership_service = MembershipService(campaign)
    removed = []
    errors = []

    with transaction.atomic():
        for user_id in user_ids:
            # Cannot remove owner
            if user_id == campaign.owner.id:
                errors.append({"user_id": user_id, "error": "Cannot remove owner."})
                continue

            # Get membership for permission check
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

            # Remove member using service
            try:
                user = User.objects.get(id=user_id)
                membership_service.remove_member(user)
                removed.append({"user_id": user_id})
            except User.DoesNotExist:
                errors.append({"user_id": user_id, "error": "User not found."})

    if errors and not removed:
        return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

    response_data = {"removed": removed, "errors": errors if errors else None}
    serializer = BulkRemoveMemberResponseSerializer(response_data)
    return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)
