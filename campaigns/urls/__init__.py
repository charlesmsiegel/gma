from django.urls import path

from campaigns.views import (
    CampaignCreateView,
    CampaignDetailView,
    CampaignListView,
    campaign_create_function_view,
    campaign_detail_function_view,
)

app_name = "campaigns"

urlpatterns = [
    # Campaign listing and creation
    path("", CampaignListView.as_view(), name="list"),
    path("create/", CampaignCreateView.as_view(), name="create"),
    path("create-alt/", campaign_create_function_view, name="create_function"),
    # Campaign detail
    path("<slug:slug>/", CampaignDetailView.as_view(), name="detail"),
    path("<slug:slug>/alt/", campaign_detail_function_view, name="detail_function"),
]
