"""
Views for the invitations app.

Handles AJAX endpoints for invitation responses.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST


@login_required
@require_POST
def ajax_accept_invitation(request, pk):
    """AJAX endpoint to accept an invitation."""
    try:
        from campaigns.models import CampaignInvitation

        invitation = get_object_or_404(
            CampaignInvitation, pk=pk, invited_user=request.user, status="PENDING"
        )

        invitation.accept()

        return JsonResponse(
            {
                "success": True,
                "message": f"Successfully joined {invitation.campaign.name}",
                "campaign_name": invitation.campaign.name,
                "role": invitation.role,
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@login_required
@require_POST
def ajax_decline_invitation(request, pk):
    """AJAX endpoint to decline an invitation."""
    try:
        from campaigns.models import CampaignInvitation

        invitation = get_object_or_404(
            CampaignInvitation, pk=pk, invited_user=request.user, status="PENDING"
        )

        invitation.decline()

        return JsonResponse(
            {
                "success": True,
                "message": f"Declined invitation to {invitation.campaign.name}",
                "campaign_name": invitation.campaign.name,
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
