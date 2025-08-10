from typing import List

from django.urls import URLPattern, path

from characters.views import CampaignCharactersView

app_name = "characters"

urlpatterns: List[URLPattern] = [
    # Campaign-scoped character management
    path(
        "campaigns/<slug:campaign_slug>/",
        CampaignCharactersView.as_view(),
        name="campaign_characters",
    ),
]
