from typing import List

from django.urls import URLPattern, path

from locations.views import (
    CampaignLocationsView,
    LocationCreateView,
    LocationDetailView,
    LocationEditView,
)

app_name = "locations"

urlpatterns: List[URLPattern] = [
    # Campaign-scoped location management
    path(
        "campaigns/<slug:campaign_slug>/",
        CampaignLocationsView.as_view(),
        name="campaign_locations",
    ),
    # Location creation
    path(
        "campaigns/<slug:campaign_slug>/create/",
        LocationCreateView.as_view(),
        name="location_create",
    ),
    # Location detail
    path(
        "campaigns/<slug:campaign_slug>/<int:location_id>/",
        LocationDetailView.as_view(),
        name="location_detail",
    ),
    # Location editing
    path(
        "campaigns/<slug:campaign_slug>/<int:location_id>/edit/",
        LocationEditView.as_view(),
        name="location_edit",
    ),
]
