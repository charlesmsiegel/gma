from django.urls import path

from campaigns.views import (
    CampaignCreateView,
    CampaignDetailView,
    CampaignInvitationsView,
    CampaignListView,
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
]
