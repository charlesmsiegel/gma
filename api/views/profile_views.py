"""
API views for user profile management.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import Theme

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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def theme_update_view(request):
    """Update user theme preference."""
    try:
        theme_name = request.data.get("theme")

        if not theme_name:
            return Response(
                {"error": "Theme name is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate theme exists and is active
        try:
            theme = Theme.objects.get(name=theme_name, is_active=True)
        except Theme.DoesNotExist:
            return Response(
                {"error": "Invalid or inactive theme"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update user theme using the new theme system
        from users.models.theme import UserThemePreference

        # Get or create the user's theme preference
        theme_preference, created = UserThemePreference.objects.get_or_create(
            user=request.user, defaults={"current_theme": theme}
        )

        # Update the current theme if it already exists
        if not created:
            theme_preference.current_theme = theme
            theme_preference.save(update_fields=["current_theme", "updated_at"])

        # Also update the legacy field for backward compatibility
        request.user.theme = theme_name
        request.user.save(update_fields=["theme"])

        return Response(
            {
                "message": "Theme updated successfully",
                "theme": theme_name,
                "theme_display_name": theme.display_name,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": f"Failed to update theme: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
