from django.urls import path

from ..views.auth_views import (
    csrf_token_view,
    current_session_view,
    extend_session_view,
    login_view,
    logout_view,
    password_reset_confirm_view,
    password_reset_request_view,
    password_reset_validate_view,
    privacy_settings_view,
    profile_view,
    public_profile_by_username_view,
    public_profile_view,
    register_view,
    resend_verification_view,
    sessions_list_view,
    terminate_all_sessions_view,
    terminate_session_view,
    user_info_view,
    verify_email_view,
)

app_name = "auth"

urlpatterns = [
    path("register/", register_view, name="api_register"),
    path("login/", login_view, name="api_login"),
    path("logout/", logout_view, name="api_logout"),
    path("user/", user_info_view, name="api_user_info"),
    path("csrf/", csrf_token_view, name="api_csrf_token"),
    path("verify-email/<str:token>/", verify_email_view, name="verify_email"),
    path("resend-verification/", resend_verification_view, name="resend_verification"),
    path("password-reset/", password_reset_request_view, name="password_reset_request"),
    path(
        "password-reset-confirm/",
        password_reset_confirm_view,
        name="password_reset_confirm",
    ),
    path(
        "password-reset-validate/<path:token>",
        password_reset_validate_view,
        name="password_reset_validate",
    ),
    path(
        "password-reset-validate/",
        password_reset_validate_view,
        name="password_reset_validate_empty",
        kwargs={"token": ""},
    ),
    # Session Management URLs
    path("sessions/", sessions_list_view, name="sessions-list"),
    path("sessions/<int:session_id>/", terminate_session_view, name="sessions-detail"),
    path("sessions/all/", terminate_all_sessions_view, name="sessions-terminate-all"),
    path("sessions/extend/", extend_session_view, name="sessions-extend"),
    path("session/current/", current_session_view, name="session-current"),
    # Profile Management URLs
    path("profile/", profile_view, name="profile"),
    path("profile/privacy/", privacy_settings_view, name="privacy-settings"),
    path("users/<int:user_id>/profile/", public_profile_view, name="public-profile"),
    path(
        "users/<str:username>/profile/",
        public_profile_by_username_view,
        name="public-profile-username",
    ),
]
