from typing import List

from django.urls import URLPattern, path

from locations.views import CampaignLocationsView

app_name = "locations"

urlpatterns: List[URLPattern] = [
    # Campaign-scoped location management
    path(
        "campaigns/<slug:campaign_slug>/",
        CampaignLocationsView.as_view(),
        name="campaign_locations",
    ),
]
