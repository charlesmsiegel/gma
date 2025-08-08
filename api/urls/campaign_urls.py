"""
URL configuration for campaign API endpoints.
"""

from django.urls import path

from api.views.campaign_views import (
    CampaignDetailAPIView,
    CampaignListCreateAPIView,
    CampaignMembershipListAPIView,
    UserCampaignListAPIView,
    accept_campaign_invitation,
    campaign_user_search,
    cancel_campaign_invitation,
    decline_campaign_invitation,
    list_campaign_invitations,
    send_campaign_invitation,
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
    # Invitation management
    path(
        "<int:campaign_id>/invitations/send/",
        send_campaign_invitation,
        name="send_invitation",
    ),
    path(
        "<int:campaign_id>/invitations/",
        list_campaign_invitations,
        name="list_invitations",
    ),
    path(
        "invitations/<int:pk>/accept/",
        accept_campaign_invitation,
        name="accept_invitation",
    ),
    path(
        "invitations/<int:pk>/decline/",
        decline_campaign_invitation,
        name="decline_invitation",
    ),
    path(
        "invitations/<int:pk>/cancel/",
        cancel_campaign_invitation,
        name="cancel_invitation",
    ),
]
