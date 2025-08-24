from typing import List

from django.urls import URLPattern, path

from scenes.views import (
    CampaignScenesView,
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
]
