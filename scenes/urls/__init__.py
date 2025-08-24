from typing import List

from django.urls import URLPattern, path

from scenes.views import (
    AddParticipantView,
    CampaignScenesView,
    RemoveParticipantView,
    SceneCreateView,
    SceneDetailView,
    SceneEditView,
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
        "scenes/<int:pk>/participants/remove/<int:character_id>/",
        RemoveParticipantView.as_view(),
        name="remove_participant",
    ),
]
