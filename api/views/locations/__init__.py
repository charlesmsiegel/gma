"""
Location API views.
"""

from .bulk_views import LocationBulkAPIView
from .crud_views import (
    LocationAncestorsAPIView,
    LocationChildrenAPIView,
    LocationDescendantsAPIView,
    LocationDetailAPIView,
    LocationListCreateAPIView,
    LocationMoveAPIView,
    LocationPathFromRootAPIView,
    LocationSiblingsAPIView,
)

__all__ = [
    "LocationListCreateAPIView",
    "LocationDetailAPIView",
    "LocationChildrenAPIView",
    "LocationDescendantsAPIView",
    "LocationAncestorsAPIView",
    "LocationSiblingsAPIView",
    "LocationPathFromRootAPIView",
    "LocationMoveAPIView",
    "LocationBulkAPIView",
]
