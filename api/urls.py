"""
API URLs configuration.

Main API URL patterns that include all sub-modules.
"""

from django.urls import include, path
from .views.auth_views import safety_preferences_view, user_safety_preferences_view
from .views.campaign_safety_views import (
    campaign_safety_view,
    campaign_safety_agreement_view, 
    campaign_safety_agreements_view,
    campaign_safety_overview_view,
    campaign_safety_agreements_status_view,
    campaign_safety_check_view,
)
from .views.content_validation_views import (
    validate_content_view,
    validate_content_for_user_view,
    validate_content_for_campaign_view,
    pre_scene_safety_check_view,
    validate_content_batch_view,
)

app_name = "api"

urlpatterns = [
    # Safety preferences endpoints (direct to main namespace for test compatibility)
    path("safety-preferences/", safety_preferences_view, name="safety_preferences"),
    path("users/<int:user_id>/safety-preferences/", user_safety_preferences_view, name="user_safety_preferences"),
    
    # Content validation endpoints (direct to main namespace for test compatibility)
    path("validate-content/", validate_content_view, name="validate_content"),
    path("validate-content-for-user/", validate_content_for_user_view, name="validate_content_for_user"),
    path("validate-content-for-campaign/", validate_content_for_campaign_view, name="validate_content_for_campaign"),
    path("pre-scene-check/", pre_scene_safety_check_view, name="pre_scene_safety_check"),
    path("validate-content-batch/", validate_content_batch_view, name="validate_content_batch"),
    
    # Authentication endpoints
    path("auth/", include("api.urls.auth_urls", namespace="auth")),
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
    # Safety system endpoints (legacy namespace - keeping for future use)
    path("safety/", include("api.urls.safety_urls", namespace="safety")),
    
    # Campaign safety endpoints (MUST be after campaign includes to avoid conflicts)
    path("campaigns/<int:campaign_id>/safety/", campaign_safety_view, name="campaign_safety"),
    path("campaigns/<int:campaign_id>/safety-agreement/", campaign_safety_agreement_view, name="campaign_safety_agreement"),
    path("campaigns/<int:campaign_id>/safety/agreements/", campaign_safety_agreements_view, name="campaign_safety_agreements"),
    path("campaigns/<int:campaign_id>/safety/overview/", campaign_safety_overview_view, name="campaign_safety_overview"),
    path("campaigns/<int:campaign_id>/safety/agreements-status/", campaign_safety_agreements_status_view, name="campaign_safety_agreements_status"),
    path("campaigns/<int:campaign_id>/safety-check/", campaign_safety_check_view, name="campaign_safety_check"),
    
    # Campaign management endpoints (MUST be last to avoid capturing specific safety patterns)
    path("campaigns/", include("api.urls.campaign_urls", namespace="campaigns")),
]
