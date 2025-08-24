from typing import List

from django.urls import URLPattern, path

from scenes.views import (
    AddParticipantView,
    BulkAddParticipantsView,
    CampaignScenesView,
    GetAvailableCharactersView,
    RemoveParticipantView,
    SceneCreateView,
    SceneDetailView,
    SceneEditView,
    SceneStatusChangeView,
)

app_name = "scenes"

urlpatterns: List[URLPattern] = [
    # Campaign-scoped scene management
    path(
        "campaigns/<slug:campaign_slug>/",
        CampaignScenesView.as_view(),
        name="campaign_scenes",
    ),
    # Scene creation
    path(
        "campaigns/<slug:campaign_slug>/scenes/create/",
        SceneCreateView.as_view(),
        name="scene_create",
    ),
    # Character filtering for scene participant selection
    path(
        "campaigns/<slug:campaign_slug>/characters/",
        GetAvailableCharactersView.as_view(),
        name="get_available_characters",
    ),
    # Individual scene management
    path(
        "scenes/<int:pk>/",
        SceneDetailView.as_view(),
        name="scene_detail",
    ),
    path(
        "scenes/<int:pk>/edit/",
        SceneEditView.as_view(),
        name="scene_edit",
    ),
    # Character participation management (Issue 38)
    path(
        "scenes/<int:pk>/participants/add/",
        AddParticipantView.as_view(),
        name="add_participant",
    ),
    path(
        "scenes/<int:pk>/participants/bulk-add/",
        BulkAddParticipantsView.as_view(),
        name="bulk_add_participants",
    ),
    path(
        "scenes/<int:pk>/participants/remove/<int:character_id>/",
        RemoveParticipantView.as_view(),
        name="remove_participant",
    ),
    # Scene status management (Issue 40)
    path(
        "scenes/<int:pk>/change-status/",
        SceneStatusChangeView.as_view(),
        name="change_status",
    ),
]
