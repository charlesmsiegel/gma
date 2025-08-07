"""
API views for user profile management.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..serializers import UserProfileSerializer, UserSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Get current user profile."""
    return Response(
        {"user": UserSerializer(request.user).data}, status=status.HTTP_200_OK
    )


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def profile_update_view(request):
    """Update current user profile."""
    serializer = UserProfileSerializer(
        request.user, data=request.data, partial=request.method == "PATCH"
    )
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {
                "message": "Profile updated successfully",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
