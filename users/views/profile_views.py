"""
Views for user profile management and settings (Issue #137).

These views handle comprehensive profile management including
bio, avatar, privacy settings, and social links.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from ..forms import UserPrivacySettingsForm, UserProfileForm, UserProfileManagementForm

User = get_user_model()


class UserProfileView(LoginRequiredMixin, TemplateView):
    """Display user profile information."""

    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        """Add user data to context."""
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        # Get public profile data (all fields visible to self)
        context["profile_data"] = self.request.user.get_public_profile_data(
            viewer_user=self.request.user
        )
        return context


class UserProfileEditView(LoginRequiredMixin, UpdateView):
    """
    Edit user profile information using the comprehensive profile form.

    This view handles all profile fields including bio, avatar, privacy settings,
    and social links with proper validation.
    """

    form_class = UserProfileManagementForm
    template_name = "users/profile_edit.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self, queryset=None):
        """Return the current user."""
        return self.request.user

    def form_valid(self, form):
        """Add success message on valid form submission."""
        messages.success(self.request, "Your profile has been updated successfully.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)
        context["profile_section"] = "general"
        return context


class UserPrivacySettingsView(LoginRequiredMixin, UpdateView):
    """
    Edit user privacy settings separately from general profile.

    This view provides focused privacy controls for users who want
    to adjust visibility and tracking settings independently.
    """

    form_class = UserPrivacySettingsForm
    template_name = "users/privacy_settings.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self, queryset=None):
        """Return the current user."""
        return self.request.user

    def form_valid(self, form):
        """Add success message on valid form submission."""
        messages.success(
            self.request, "Your privacy settings have been updated successfully."
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add additional context for the template."""
        context = super().get_context_data(**kwargs)
        context["profile_section"] = "privacy"
        return context


class PublicUserProfileView(TemplateView):
    """
    Display public user profile with privacy controls.

    This view shows user profiles to other users based on the
    profile owner's privacy settings and relationship to the viewer.
    """

    template_name = "users/public_profile.html"

    def get_object(self):
        """Get the user being viewed."""
        username = self.kwargs.get("username")
        return get_object_or_404(User, username=username)

    def get_context_data(self, **kwargs):
        """Add profile data filtered by privacy settings."""
        context = super().get_context_data(**kwargs)

        profile_user = self.get_object()
        viewer_user = self.request.user if self.request.user.is_authenticated else None

        # Get privacy-filtered profile data
        profile_data = profile_user.get_public_profile_data(viewer_user=viewer_user)

        # If profile is not visible, raise 404 instead of showing empty profile
        if not profile_data.get("profile_visible", False):
            raise Http404("This user profile is not publicly accessible.")

        context["profile_user"] = profile_user
        context["profile_data"] = profile_data
        context["can_view_full_profile"] = profile_data.get("profile_visible", False)
        context["is_own_profile"] = viewer_user and viewer_user.id == profile_user.id

        return context


class UserProfileLegacyEditView(LoginRequiredMixin, UpdateView):
    """
    Legacy profile edit view for backward compatibility.

    This view maintains the original UserProfileForm for users
    or systems that depend on the simpler profile editing interface.
    """

    form_class = UserProfileForm
    template_name = "users/profile_edit_simple.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self, queryset=None):
        """Return the current user."""
        return self.request.user

    def form_valid(self, form):
        """Add success message on valid form submission."""
        messages.success(self.request, "Your profile has been updated successfully.")
        return super().form_valid(form)
