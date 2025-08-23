"""
URL configuration for item API endpoints.
"""

from django.urls import path

from api.views.item_views import ItemDetailAPIView, ItemListCreateAPIView

# Note: No app_name here since these are accessed as api:items-list

urlpatterns = [
    # Item CRUD operations
    path("", ItemListCreateAPIView.as_view(), name="items-list"),
    path("<int:pk>/", ItemDetailAPIView.as_view(), name="items-detail"),
]
