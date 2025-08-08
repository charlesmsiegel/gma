"""
URL patterns for the invitations app.

This app handles AJAX endpoints for invitation responses.
"""

from django.urls import path

from . import views

app_name = "invitations"

urlpatterns = [
    # AJAX endpoints for invitation responses
    path("<int:pk>/ajax/accept/", views.ajax_accept_invitation, name="ajax_accept"),
    path("<int:pk>/ajax/decline/", views.ajax_decline_invitation, name="ajax_decline"),
]
