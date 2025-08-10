from typing import List

from django.urls import URLPattern, path

from scenes.views import CampaignScenesView

app_name = "scenes"

urlpatterns: List[URLPattern] = [
    # Campaign-scoped scene management
    path(
        "campaigns/<slug:campaign_slug>/",
        CampaignScenesView.as_view(),
        name="campaign_scenes",
    ),
]
