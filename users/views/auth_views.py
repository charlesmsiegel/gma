"""
Authentication views for user registration, login, logout, and password management.
"""

from django.contrib import messages
from django.contrib.auth.views import LoginView as BaseLoginView
from django.contrib.auth.views import LogoutView as BaseLogoutView
from django.contrib.auth.views import (
    PasswordChangeDoneView as BasePasswordChangeDoneView,
)
from django.contrib.auth.views import PasswordChangeView as BasePasswordChangeView
from django.contrib.auth.views import (
    PasswordResetCompleteView as BasePasswordResetCompleteView,
)
from django.contrib.auth.views import (
    PasswordResetConfirmView as BasePasswordResetConfirmView,
)
from django.contrib.auth.views import PasswordResetDoneView as BasePasswordResetDoneView
from django.contrib.auth.views import PasswordResetView as BasePasswordResetView
from django.urls import reverse_lazy
from django.views.generic import CreateView

from ..forms import CustomUserCreationForm, EmailAuthenticationForm


class RegisterView(CreateView):
    """User registration view."""

    form_class = CustomUserCreationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("users:login")

    def form_valid(self, form):
        """Handle successful form submission."""
        response = super().form_valid(form)
        username = form.cleaned_data.get("username")
        messages.success(
            self.request,
            f"Account created successfully for {username}! "
            f"Please check your email to verify your account.",
        )
        return response

    def get_context_data(self, **kwargs):
        """Add context data for template."""
        context = super().get_context_data(**kwargs)
        context["title"] = "Register"
        return context


class LoginView(BaseLoginView):
    """User login view with email/username support."""

    form_class = EmailAuthenticationForm
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        """Redirect to next URL or default."""
        return self.get_redirect_url() or reverse_lazy("core:index")

    def form_valid(self, form):
        """Handle successful login."""
        username = form.get_user().username
        messages.success(self.request, f"Welcome back, {username}!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add context data for template."""
        context = super().get_context_data(**kwargs)
        context["title"] = "Login"
        return context


class LogoutView(BaseLogoutView):
    """User logout view."""

    template_name = "registration/logout.html"
    next_page = reverse_lazy("core:index")
    http_method_names = ["get", "post"]

    def dispatch(self, request, *args, **kwargs):
        """Handle logout with success message."""
        if request.method == "POST":
            messages.success(request, "You have been logged out successfully.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add context data for template."""
        context = super().get_context_data(**kwargs)
        context["title"] = "Logout"
        return context


class PasswordChangeView(BasePasswordChangeView):
    """Password change view for authenticated users."""

    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("users:password_change_done")

    def form_valid(self, form):
        """Handle successful password change."""
        messages.success(self.request, "Your password has been changed successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add context data for template."""
        context = super().get_context_data(**kwargs)
        context["title"] = "Change Password"
        return context


class PasswordChangeDoneView(BasePasswordChangeDoneView):
    """Password change success page."""

    template_name = "registration/password_change_done.html"

    def get_context_data(self, **kwargs):
        """Add context data for template."""
        context = super().get_context_data(**kwargs)
        context["title"] = "Password Changed"
        return context


class PasswordResetView(BasePasswordResetView):
    """Password reset request view."""

    template_name = "registration/password_reset_form.html"
    success_url = reverse_lazy("users:password_reset_done")
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"

    def form_valid(self, form):
        """Handle successful password reset request."""
        messages.success(
            self.request,
            "If an account with this email exists, "
            "you will receive password reset instructions.",
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add context data for template."""
        context = super().get_context_data(**kwargs)
        context["title"] = "Password Reset"
        return context


class PasswordResetDoneView(BasePasswordResetDoneView):
    """Password reset email sent confirmation."""

    template_name = "registration/password_reset_done.html"

    def get_context_data(self, **kwargs):
        """Add context data for template."""
        context = super().get_context_data(**kwargs)
        context["title"] = "Password Reset Sent"
        return context


class PasswordResetConfirmView(BasePasswordResetConfirmView):
    """Password reset confirmation view."""

    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("users:password_reset_complete")

    def form_valid(self, form):
        """Handle successful password reset."""
        messages.success(self.request, "Your password has been reset successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add context data for template."""
        context = super().get_context_data(**kwargs)
        context["title"] = "Enter New Password"
        return context


class PasswordResetCompleteView(BasePasswordResetCompleteView):
    """Password reset complete confirmation."""

    template_name = "registration/password_reset_complete.html"

    def get_context_data(self, **kwargs):
        """Add context data for template."""
        context = super().get_context_data(**kwargs)
        context["title"] = "Password Reset Complete"
        return context
