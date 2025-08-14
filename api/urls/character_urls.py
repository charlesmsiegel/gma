"""
URL configuration for Character API endpoints.

Provides REST API routes for character CRUD operations with both
ViewSet-based routes and explicit URL patterns for expected test patterns.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views.character_views import CharacterViewSet

# Create router for character viewset
router = DefaultRouter()
router.register(r"", CharacterViewSet, basename="characters")

urlpatterns = [
    # Include all ViewSet routes
    path("", include(router.urls)),
]
