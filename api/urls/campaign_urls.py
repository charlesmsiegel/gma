"""
URL configuration for campaign API endpoints.
"""

from django.urls import path

from api.views.campaign_views import (
    CampaignDetailAPIView,
    CampaignListCreateAPIView,
    CampaignMembershipListAPIView,
    UserCampaignListAPIView,
    campaign_detail_api,
    campaign_list_api,
    create_campaign_api,
)

app_name = "campaigns"

urlpatterns = [
    # Campaign CRUD operations
    path("", CampaignListCreateAPIView.as_view(), name="list_create"),
    path("<int:pk>/", CampaignDetailAPIView.as_view(), name="detail"),
    # Alternative function-based endpoints
    path("create/", create_campaign_api, name="create"),
    path("list/", campaign_list_api, name="list"),
    path("<int:pk>/detail/", campaign_detail_api, name="detail_function"),
    # User's campaigns
    path("my-campaigns/", UserCampaignListAPIView.as_view(), name="my_campaigns"),
    # Campaign membership management
    path(
        "<int:campaign_pk>/members/",
        CampaignMembershipListAPIView.as_view(),
        name="members",
    ),
]
