"""
Views for user profile management.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from ..forms import UserProfileForm


class UserProfileView(LoginRequiredMixin, TemplateView):
    """Display user profile information."""

    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        """Add user data to context."""
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class UserProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit user profile information."""

    form_class = UserProfileForm
    template_name = "users/profile_edit.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self, queryset=None):
        """Return the current user."""
        return self.request.user

    def form_valid(self, form):
        """Add success message on valid form submission."""
        messages.success(self.request, "Your profile has been updated successfully.")
        return super().form_valid(form)
