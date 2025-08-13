from typing import List

from django.urls import URLPattern, path

from characters.views import (
    CampaignCharactersView,
    CharacterCreateView,
    CharacterDetailView,
)

app_name = "characters"

urlpatterns: List[URLPattern] = [
    # Character creation
    path(
        "create/",
        CharacterCreateView.as_view(),
        name="create",
    ),
    # Character detail (placeholder for future implementation)
    path(
        "<int:pk>/",
        CharacterDetailView.as_view(),
        name="detail",
    ),
    # Campaign-scoped character management
    path(
        "campaigns/<slug:campaign_slug>/",
        CampaignCharactersView.as_view(),
        name="campaign_characters",
    ),
]
