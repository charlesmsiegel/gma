"""
API views for notifications.
"""

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_notifications(request):
    """List notifications for the authenticated user."""
    # Placeholder implementation
    return JsonResponse({"notifications": [], "unread_count": 0})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    """Mark a notification as read."""
    # Placeholder implementation
    return JsonResponse({"success": True, "message": "Notification marked as read"})
