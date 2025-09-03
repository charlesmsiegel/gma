from typing import List

from django.urls import URLPattern, path

from items.views import (
    CampaignItemsView,
    ItemCreateView,
    ItemDeleteView,
    ItemDetailView,
    ItemEditView,
)

app_name = "items"

urlpatterns: List[URLPattern] = [
    # Campaign-scoped item management
    path(
        "campaigns/<slug:slug>/",
        CampaignItemsView.as_view(),
        name="campaign_items",
    ),
    path(
        "campaigns/<slug:slug>/create/",
        ItemCreateView.as_view(),
        name="create",
    ),
    path(
        "campaigns/<slug:slug>/<int:item_id>/",
        ItemDetailView.as_view(),
        name="detail",
    ),
    path(
        "campaigns/<slug:slug>/<int:item_id>/edit/",
        ItemEditView.as_view(),
        name="edit",
    ),
    path(
        "campaigns/<slug:slug>/<int:item_id>/delete/",
        ItemDeleteView.as_view(),
        name="delete",
    ),
]
