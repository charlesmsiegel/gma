"""
URL configuration for Scene API endpoints.

Provides REST API routes for scene CRUD operations with both
ViewSet-based routes and explicit URL patterns for expected test patterns.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views.scene_views import SceneViewSet

app_name = "scenes"

# Create router for scene viewset
router = DefaultRouter()
router.register(r"", SceneViewSet, basename="scenes")

urlpatterns = [
    # Include all ViewSet routes
    path("", include(router.urls)),
]
