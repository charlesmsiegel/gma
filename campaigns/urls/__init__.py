from django.urls import path

from campaigns.views import CampaignCreateView, CampaignDetailView, CampaignListView

app_name = "campaigns"

urlpatterns = [
    # Campaign listing and creation
    path("", CampaignListView.as_view(), name="list"),
    path("create/", CampaignCreateView.as_view(), name="create"),
    # Campaign detail
    path("<slug:slug>/", CampaignDetailView.as_view(), name="detail"),
]
