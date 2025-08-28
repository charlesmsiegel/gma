"""
API URLs configuration.

Main API URL patterns that include all sub-modules.
"""

from django.urls import include, path

app_name = "api"

urlpatterns = [
    # Authentication endpoints
    path("auth/", include("api.urls.auth_urls", namespace="auth")),
    # Campaign management endpoints
    path("campaigns/", include("api.urls.campaign_urls", namespace="campaigns")),
    # Character management endpoints
    path("characters/", include("api.urls.character_urls", namespace="characters")),
    # Scene management endpoints
    path("scenes/", include("api.urls.scene_urls", namespace="scenes")),
    # Location management endpoints
    path("locations/", include("api.urls.location_urls", namespace="locations")),
    # Item management endpoints
    path("items/", include("api.urls.item_urls", namespace="items")),
    # Campaign invitation endpoints
    path("invitations/", include("api.urls.invitation_urls", namespace="invitations")),
    # User profile endpoints
    path("profile/", include("api.urls.profile_urls", namespace="profile")),
    # Notification endpoints
    path(
        "notifications/",
        include("api.urls.notification_urls", namespace="notifications"),
    ),
]
