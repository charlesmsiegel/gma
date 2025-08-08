"""
API URL patterns for notifications.
"""

from django.urls import path

from api.views import notification_views

app_name = "notifications"

urlpatterns = [
    path("", notification_views.list_notifications, name="list"),
    path("<int:pk>/read/", notification_views.mark_notification_read, name="mark_read"),
]
