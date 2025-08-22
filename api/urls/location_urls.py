"""
URL configuration for location API endpoints.
"""

from django.urls import path

from api.views.locations import (
    LocationAncestorsAPIView,
    LocationBulkAPIView,
    LocationChildrenAPIView,
    LocationDescendantsAPIView,
    LocationDetailAPIView,
    LocationListCreateAPIView,
    LocationMoveAPIView,
    LocationPathFromRootAPIView,
    LocationSiblingsAPIView,
)

# Note: No app_name here since these are accessed as api:locations-list

urlpatterns = [
    # Location CRUD operations
    path("", LocationListCreateAPIView.as_view(), name="locations-list"),
    path("<int:pk>/", LocationDetailAPIView.as_view(), name="locations-detail"),
    # Location hierarchy operations
    path(
        "<int:pk>/children/",
        LocationChildrenAPIView.as_view(),
        name="locations-children",
    ),
    path(
        "<int:pk>/descendants/",
        LocationDescendantsAPIView.as_view(),
        name="locations-descendants",
    ),
    path(
        "<int:pk>/ancestors/",
        LocationAncestorsAPIView.as_view(),
        name="locations-ancestors",
    ),
    path(
        "<int:pk>/siblings/",
        LocationSiblingsAPIView.as_view(),
        name="locations-siblings",
    ),
    path(
        "<int:pk>/path/",
        LocationPathFromRootAPIView.as_view(),
        name="locations-path",
    ),
    path("<int:pk>/move/", LocationMoveAPIView.as_view(), name="locations-move"),
    # Bulk operations
    path("bulk/", LocationBulkAPIView.as_view(), name="locations-bulk"),
]
