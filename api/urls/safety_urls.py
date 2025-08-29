"""
URL patterns for safety system API endpoints.
"""

from django.urls import path

from ..views.campaign_safety_views import (
    campaign_safety_view,
    campaign_safety_agreement_view,
    campaign_safety_agreements_view,
    campaign_safety_overview_view,
    campaign_safety_agreements_status_view,
    campaign_safety_check_view,
)

from ..views.content_validation_views import (
    validate_content_view,
    validate_content_for_user_view,
    validate_content_for_campaign_view,
    pre_scene_safety_check_view,
    validate_content_batch_view,
)

app_name = "safety"

urlpatterns = [
    # Content validation endpoints
    path("validate-content/", validate_content_view, name="validate_content"),
    path("validate-content-for-user/", validate_content_for_user_view, name="validate_content_for_user"),
    path("validate-content-for-campaign/", validate_content_for_campaign_view, name="validate_content_for_campaign"),
    path("pre-scene-check/", pre_scene_safety_check_view, name="pre_scene_safety_check"),
    path("validate-content-batch/", validate_content_batch_view, name="validate_content_batch"),
    
    # Campaign safety endpoints
    path("campaigns/<int:campaign_id>/safety/", campaign_safety_view, name="campaign_safety"),
    path("campaigns/<int:campaign_id>/safety-agreement/", campaign_safety_agreement_view, name="campaign_safety_agreement"),
    path("campaigns/<int:campaign_id>/safety/agreements/", campaign_safety_agreements_view, name="campaign_safety_agreements"),
    path("campaigns/<int:campaign_id>/safety/overview/", campaign_safety_overview_view, name="campaign_safety_overview"),
    path("campaigns/<int:campaign_id>/safety/agreements-status/", campaign_safety_agreements_status_view, name="campaign_safety_agreements_status"),
    path("campaigns/<int:campaign_id>/safety-check/", campaign_safety_check_view, name="campaign_safety_check"),
]