"""
URL configuration for campaign API endpoints.
"""

from django.urls import path

from api.views.campaign_views import (
    CampaignDetailAPIView,
    CampaignListCreateAPIView,
    CampaignMembershipListAPIView,
    UserCampaignListAPIView,
    campaign_user_search,
)

app_name = "campaigns"

urlpatterns = [
    # Campaign CRUD operations
    path("", CampaignListCreateAPIView.as_view(), name="list_create"),
    path("<int:pk>/", CampaignDetailAPIView.as_view(), name="detail"),
    # User's campaigns
    path("my-campaigns/", UserCampaignListAPIView.as_view(), name="my_campaigns"),
    # Campaign membership management
    path(
        "<int:campaign_pk>/members/",
        CampaignMembershipListAPIView.as_view(),
        name="members",
    ),
    # User search for invitations
    path(
        "<int:campaign_id>/user-search/",
        campaign_user_search,
        name="user_search",
    ),
]
