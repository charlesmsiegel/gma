from django.urls import path

from ..views import (
    LoginView,
    LogoutView,
    PasswordChangeDoneView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
    RegisterView,
    UserProfileEditView,
    UserProfileView,
)

app_name = "users"

urlpatterns = [
    # Registration
    path("register/", RegisterView.as_view(), name="register"),
    # Authentication
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # Profile management
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("profile/edit/", UserProfileEditView.as_view(), name="profile_edit"),
    # Password change
    path("password/change/", PasswordChangeView.as_view(), name="password_change"),
    path(
        "password/change/done/",
        PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    # Password reset
    path("password/reset/", PasswordResetView.as_view(), name="password_reset"),
    path(
        "password/reset/done/",
        PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/complete/",
        PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
