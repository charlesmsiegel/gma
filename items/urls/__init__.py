from typing import List

from django.urls import URLPattern, path

from items.views import CampaignItemsView

app_name = "items"

urlpatterns: List[URLPattern] = [
    # Campaign-scoped item management
    path(
        "campaigns/<slug:campaign_slug>/",
        CampaignItemsView.as_view(),
        name="campaign_items",
    ),
]
