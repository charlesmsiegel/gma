from typing import List

from django.urls import URLPattern, path

from characters.views import (
    CampaignCharactersView,
    CharacterCreateView,
    CharacterDeleteView,
    CharacterDetailView,
    CharacterEditView,
    UserCharactersView,
)

app_name = "characters"

urlpatterns: List[URLPattern] = [
    # User-scoped character list (all user's characters across campaigns)
    path(
        "",
        UserCharactersView.as_view(),
        name="user_characters",
    ),
    # Character creation
    path(
        "create/",
        CharacterCreateView.as_view(),
        name="create",
    ),
    # Character detail
    path(
        "<int:pk>/",
        CharacterDetailView.as_view(),
        name="detail",
    ),
    # Character edit
    path(
        "<int:pk>/edit/",
        CharacterEditView.as_view(),
        name="edit",
    ),
    # Character delete
    path(
        "<int:pk>/delete/",
        CharacterDeleteView.as_view(),
        name="delete",
    ),
    # Campaign-scoped character management
    path(
        "campaigns/<slug:campaign_slug>/",
        CampaignCharactersView.as_view(),
        name="campaign_characters",
    ),
    # Campaign character list (alias for the delete view redirect)
    path(
        "campaigns/<slug:campaign_slug>/list/",
        CampaignCharactersView.as_view(),
        name="campaign_list",
    ),
]
