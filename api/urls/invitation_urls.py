"""
URL configuration for invitation API endpoints.
"""

from django.urls import path

from api.views.campaigns import list_user_invitations

app_name = "invitations"

urlpatterns = [
    # User's own invitations
    path("", list_user_invitations, name="list"),
]
