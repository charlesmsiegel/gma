from django.urls import include, path

# Import campaign views directly for main api namespace
from api.views.campaigns import CampaignDetailAPIView, CampaignListAPIView

app_name = "api"

urlpatterns = [
    path("auth/", include("api.urls.auth_urls")),
    path("profile/", include("api.urls.profile_urls")),
    path("campaigns/", include("api.urls.campaign_urls")),
    path("invitations/", include("api.urls.invitation_urls")),
    path("notifications/", include("api.urls.notification_urls")),
    path("characters/", include("api.urls.character_urls")),
    path("locations/", include("api.urls.location_urls")),
    path("items/", include("api.urls.item_urls")),
    path("scenes/", include("api.urls.scene_urls")),
    # Direct campaign endpoints for expected URL names
    path("campaign-list/", CampaignListAPIView.as_view(), name="campaign-list"),
    path(
        "campaign-detail/<int:pk>/",
        CampaignDetailAPIView.as_view(),
        name="campaign-detail",
    ),
]
