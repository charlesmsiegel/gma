from django.urls import path

from campaigns.views import (
    AjaxChangeMemberRoleView,
    AjaxRemoveMemberView,
    AjaxUserSearchView,
    BulkMemberManagementView,
    CampaignCreateView,
    CampaignDetailView,
    CampaignInvitationsView,
    CampaignListView,
    ChangeMemberRoleView,
    ManageMembersView,
    SendInvitationView,
)

app_name = "campaigns"

urlpatterns = [
    # Campaign listing and creation
    path("", CampaignListView.as_view(), name="list"),
    path("create/", CampaignCreateView.as_view(), name="create"),
    # Campaign detail
    path("<slug:slug>/", CampaignDetailView.as_view(), name="detail"),
    # Campaign invitations
    path(
        "<slug:slug>/invitations/",
        CampaignInvitationsView.as_view(),
        name="invitations",
    ),
    # Member management
    path(
        "<slug:slug>/members/",
        ManageMembersView.as_view(),
        name="manage_members",
    ),
    path(
        "<slug:slug>/send-invitation/",
        SendInvitationView.as_view(),
        name="send_invitation",
    ),
    path(
        "<slug:slug>/change-role/",
        ChangeMemberRoleView.as_view(),
        name="change_member_role",
    ),
    path(
        "<slug:slug>/bulk-manage/",
        BulkMemberManagementView.as_view(),
        name="bulk_member_management",
    ),
    # AJAX endpoints
    path(
        "<slug:slug>/ajax/search-users/",
        AjaxUserSearchView.as_view(),
        name="ajax_user_search",
    ),
    path(
        "<slug:slug>/ajax/change-role/",
        AjaxChangeMemberRoleView.as_view(),
        name="ajax_change_role",
    ),
    path(
        "<slug:slug>/ajax/remove-member/",
        AjaxRemoveMemberView.as_view(),
        name="ajax_remove_member",
    ),
]
