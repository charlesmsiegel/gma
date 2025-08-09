"""
URL configuration for campaign API endpoints.
"""

from django.urls import path

from api.views.campaigns import (
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
from api.views.memberships import (
    bulk_add_members,
    bulk_change_roles,
    bulk_remove_members,
    change_member_role,
    list_campaign_members,
    remove_campaign_member,
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
    # Enhanced membership management endpoints
    path(
        "<int:campaign_id>/members/list/",
        list_campaign_members,
        name="list_members",
    ),
    path(
        "<int:campaign_id>/members/<int:user_id>/remove/",
        remove_campaign_member,
        name="remove_member",
    ),
    path(
        "<int:campaign_id>/members/<int:user_id>/role/",
        change_member_role,
        name="change_member_role",
    ),
    # Bulk operations
    path(
        "<int:campaign_id>/members/bulk-add/",
        bulk_add_members,
        name="bulk_add_members",
    ),
    path(
        "<int:campaign_id>/members/bulk-change-roles/",
        bulk_change_roles,
        name="bulk_change_roles",
    ),
    path(
        "<int:campaign_id>/members/bulk-remove/",
        bulk_remove_members,
        name="bulk_remove_members",
    ),
]
