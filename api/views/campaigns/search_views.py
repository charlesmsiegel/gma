"""
API views for campaign user search functionality.

This module provides REST API endpoints for searching users to invite to campaigns
with proper permission controls and result filtering.
"""

from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.errors import APIError
from api.serializers import UserSerializer
from campaigns.permissions import CampaignLookupMixin
from campaigns.services import CampaignService

User = get_user_model()


class CampaignPermissionHelper(CampaignLookupMixin):
    """Helper class for function-based views to use CampaignLookupMixin."""

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
    # Use helper to check campaign permissions
    helper = CampaignPermissionHelper(request)
    result = helper.get_campaign_with_permissions(campaign_id, ["OWNER", "GM"])

    # If result is a Response object, it means an error occurred
    if isinstance(result, Response):
        return result

    campaign, _ = result

    # Get search query
    query = request.GET.get("q", "").strip()
    if not query:
        return APIError.bad_request("Search query parameter 'q' is required.")

    # Check minimum query length
    if len(query) < 2:
        return Response(
            {"results": [], "count": 0, "query": query, "next": None, "previous": None}
        )

    # Use service to search for users (get all matches for pagination)
    campaign_service = CampaignService(campaign)
    users = campaign_service.search_users_for_invitation(
        query, limit=100
    )  # Get enough for pagination

    # Pagination
    page_size = min(int(request.GET.get("page_size", 10)), 20)  # Max 20 results
    page_number = int(request.GET.get("page", 1))

    paginator = Paginator(users, page_size)
    page = paginator.get_page(page_number)

    # Use DRF serializer for consistent data handling
    serializer = UserSerializer(page, many=True, context={"request": request})

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
            "results": serializer.data,
            "count": paginator.count,
            "query": query,
            "next": next_url,
            "previous": previous_url,
            "page_size": page_size,
            "current_page": page_number,
            "total_pages": paginator.num_pages,
        }
    )
