from django.urls import path

from ..views.auth_views import (
    csrf_token_view,
    login_view,
    logout_view,
    password_reset_confirm_view,
    password_reset_request_view,
    password_reset_validate_view,
    register_view,
    resend_verification_view,
    user_info_view,
    verify_email_view,
)

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
]
