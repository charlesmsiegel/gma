from django.urls import path

from ..views.profile_views import profile_update_view, profile_view, theme_update_view

urlpatterns = [
    path("", profile_view, name="api_profile"),
    path("update/", profile_update_view, name="api_profile_update"),
    path("theme/", theme_update_view, name="api_theme_update"),
]
