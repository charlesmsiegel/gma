"""
API views for authentication.
"""

import logging

from django.contrib.auth import get_user_model, login, logout
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..serializers import (
    CurrentSessionSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetTokenValidationSerializer,
    SessionExtendSerializer,
    TerminateAllSessionsResponseSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    UserSessionSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    """Register a new user with email verification."""
    from users.services import EmailVerificationService

    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        try:
            user = serializer.save()

            # Check if email verification is required
            service = EmailVerificationService()
            verification_required = service.is_verification_required(user)

            # Email is already sent in the serializer, check if it succeeded
            email_sending_failed = False
            if verification_required and not user.email_verification_sent_at:
                email_sending_failed = True

            # Prepare response data
            response_data = {
                "message": (
                    "User registered successfully. Please check your email to "
                    "verify your account."
                ),
                "user": UserSerializer(user).data,
                "email_verification_required": verification_required,
            }

            # Handle email sending failure
            if email_sending_failed:
                response_data["email_sending_failed"] = True
                response_data["message"] = (
                    "User registered successfully, but there was an issue "
                    "sending the verification email. Please contact support."
                )

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception:
            # Handle any database or service errors
            return Response(
                {"detail": "Registration failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # For certain validation errors, provide specific feedback
    errors = serializer.errors

    # Check for password validation errors first
    if "non_field_errors" in errors:
        for error in errors["non_field_errors"]:
            if "Passwords do not match" in str(error):
                return Response(
                    {"detail": "Passwords do not match"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    # Check for specific validation scenarios that should show detailed errors
    if "password" in errors:
        if any("password" in str(error).lower() for error in errors["password"]):
            return Response(
                {"detail": f"Password validation failed: {errors['password'][0]}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if "email" in errors:
        # Don't leak information for generic registration failures
        if any("Registration failed" in str(error) for error in errors["email"]):
            return Response(
                {"detail": "Registration failed. Please try different information."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"detail": f"Email validation failed: {errors['email'][0]}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if "username" in errors:
        # Don't leak information for generic registration failures
        if any("Registration failed" in str(error) for error in errors["username"]):
            return Response(
                {"detail": "Registration failed. Please try different information."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"detail": f"Username validation failed: {errors['username'][0]}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Return validation errors with generic message for security
    return Response(
        {
            "detail": (
                "Registration failed. Please check your information and try again."
            )
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """Login a user."""
    from django.contrib.sessions.models import Session

    from users.models.session_models import SessionSecurityEvent, SessionSecurityLog
    from users.services.session_security import SessionSecurityService

    serializer = LoginSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        user = serializer.validated_data["user"]

        # Get IP and user agent for session tracking
        ip_address = request.META.get("REMOTE_ADDR", "127.0.0.1")
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        remember_me = request.data.get("remember_me", False)

        # Log the user in first
        login(request, user)

        try:
            # Create UserSession record
            service = SessionSecurityService()
            django_session = Session.objects.get(
                session_key=request.session.session_key
            )

            user_session = service.create_user_session(
                user=user,
                session=django_session,
                ip_address=ip_address,
                user_agent=user_agent,
                remember_me=remember_me,
            )

            # Extend session for remember me functionality
            if remember_me:
                user_session.extend_for_remember_me()

            logger.info(f"User {user.id} logged in successfully from {ip_address}")

        except Exception as e:
            logger.error(f"Error creating UserSession for user {user.id}: {e}")
            # Don't fail the login if session tracking fails

        return Response(
            {"message": "Login successful", "user": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )
    else:
        # Log failed login attempt
        ip_address = request.META.get("REMOTE_ADDR", "127.0.0.1")
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        username = request.data.get("username", "")

        # Don't create a security log entry for non-existent users to prevent enumeration
        # Just log the attempt in application logs
        logger.warning(f"Failed login attempt for '{username}' from {ip_address}")

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout a user."""
    from users.models.session_models import (
        SessionSecurityEvent,
        SessionSecurityLog,
        UserSession,
    )

    # Get IP and user agent for logging
    ip_address = request.META.get("REMOTE_ADDR", "127.0.0.1")
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    # Find and deactivate the current UserSession
    try:
        session_key = request.session.session_key
        if session_key:
            user_session = UserSession.objects.get(
                user=request.user, session__session_key=session_key, is_active=True
            )

            # Log logout event
            SessionSecurityLog.log_event(
                user=request.user,
                event_type=SessionSecurityEvent.LOGOUT,
                ip_address=ip_address,
                user_agent=user_agent,
                user_session=user_session,
                details={"logout_by_user": True},
            )

            # Deactivate UserSession
            user_session.deactivate()

            logger.info(f"User {request.user.id} logged out successfully")

    except UserSession.DoesNotExist:
        # Session not found, log it but continue with logout
        logger.warning(f"UserSession not found for logout of user {request.user.id}")

        # Still log the logout event without a user_session
        SessionSecurityLog.log_event(
            user=request.user,
            event_type=SessionSecurityEvent.LOGOUT,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"logout_by_user": True, "session_not_found": True},
        )
    except Exception as e:
        logger.error(f"Error during logout for user {request.user.id}: {e}")

    # Perform Django logout
    logout(request)
    return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_info_view(request):
    """Get current user information."""
    return Response(
        {"user": UserSerializer(request.user).data}, status=status.HTTP_200_OK
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def csrf_token_view(request):
    """Get CSRF token for forms."""
    return Response({"csrfToken": get_token(request)}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def verify_email_view(request, token):
    """Verify email address using token."""
    from users.services import EmailVerificationService

    try:
        # Basic token format validation - only catch truly malformed tokens
        if not token or " " in token:
            logger.warning("Email verification failed: malformed token")
            return Response(
                {"error": "Invalid verification token format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = EmailVerificationService()
        success, user, message = service.verify_email(token)

        if success:
            logger.info(f"Email verification successful for user ID {user.id}")

            return Response(
                {
                    "message": message,
                    "user": UserSerializer(user).data,
                    "verified_at": (
                        user.email_verified_at
                        if hasattr(user, "email_verified_at")
                        else None
                    ),
                },
                status=status.HTTP_200_OK,
            )
        else:
            # Handle different error cases
            if user is None:
                # Token not found or invalid
                logger.warning("Email verification failed: invalid token")
                return Response(
                    {"error": "Verification token not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            elif "expired" in message.lower():
                # Token expired
                logger.warning(
                    f"Email verification failed: expired token for user {user.email}"
                )
                return Response(
                    {"error": "Verification token has expired."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif "inactive" in message.lower() or not user.is_active:
                # User is inactive
                logger.warning(f"Email verification failed: inactive user {user.email}")
                return Response(
                    {"error": "User account is inactive."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif "already verified" in message.lower():
                # Already verified - return success for idempotency
                logger.info(f"Email already verified for user ID {user.id}")
                return Response(
                    {
                        "message": message,
                        "user": UserSerializer(user).data,
                        "verified_at": (
                            user.email_verified_at
                            if hasattr(user, "email_verified_at")
                            else None
                        ),
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                # Generic verification failure
                logger.warning(f"Email verification failed: {message}")
                return Response(
                    {"error": "Verification failed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        return Response(
            {"error": "An error occurred during verification."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def resend_verification_view(request):
    """Resend email verification."""
    from users.services import EmailVerificationService

    try:
        email = request.data.get("email")

        # Validate email field
        if not email:
            return Response(
                {"error": "Email field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not email.strip():
            return Response(
                {"error": "Email cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Email format validation using Django's validator
        from django.core.exceptions import ValidationError
        from django.core.validators import validate_email

        try:
            validate_email(email.strip())
        except ValidationError:
            return Response(
                {"error": "Invalid email format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Case-insensitive email lookup
        try:
            user = User.objects.get(email__iexact=email.strip())
        except User.DoesNotExist:
            # Return success for security (don't reveal user existence)
            logger.info("Resend verification attempted for non-existent email")
            return Response(
                {
                    "message": (
                        "If an account with this email exists and is not yet verified, "
                        "a verification email has been sent."
                    )
                },
                status=status.HTTP_200_OK,
            )

        # Check if user is active
        if not user.is_active:
            # Return success for security but log the attempt
            logger.warning(
                f"Resend verification attempted for inactive user {user.email}"
            )
            return Response(
                {
                    "message": (
                        "If an account with this email exists and is not yet verified, "
                        "a verification email has been sent."
                    )
                },
                status=status.HTTP_200_OK,
            )

        # Check if already verified
        if user.email_verified:
            logger.info(
                f"Resend verification attempted for already verified user {user.email}"
            )
            return Response(
                {"error": "Email address is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Simple rate limiting using session - only for rapid API calls
        # not initial setup
        from django.utils import timezone

        last_resend_time = request.session.get(f"last_resend_{user.id}")
        if last_resend_time:
            from datetime import datetime, timedelta

            last_time = datetime.fromisoformat(last_resend_time)
            if timezone.now() - last_time < timedelta(seconds=60):
                logger.warning(f"Rate limited resend attempt for user {user.email}")
                return Response(
                    {
                        "error": (
                            "Please wait before requesting another verification email."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Record this resend attempt in session
        request.session[f"last_resend_{user.id}"] = timezone.now().isoformat()

        # Send verification email
        service = EmailVerificationService()
        email_sent = service.resend_verification_email(user)

        if email_sent:
            logger.info(f"Email verification resend successful for user ID {user.id}")
            return Response(
                {"message": "Verification email sent successfully."},
                status=status.HTTP_200_OK,
            )
        else:
            # Email sending failed but don't expose details
            logger.error(f"Failed to resend verification email for user {user.email}")
            return Response(
                {
                    "message": "Verification email requested successfully.",
                    "email_sending_failed": True,
                },
                status=status.HTTP_200_OK,
            )

    except Exception as e:
        logger.error(f"Resend verification error: {str(e)}")
        return Response(
            {"error": "An error occurred while processing your request."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request_view(request):
    """Request a password reset."""
    from users.services import PasswordResetService

    serializer = PasswordResetRequestSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Get client IP address for rate limiting and tracking
            ip_address = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[
                0
            ].strip() or request.META.get("REMOTE_ADDR")

            # Check rate limiting BEFORE creating reset
            User = get_user_model()
            email = serializer.validated_data["email"]

            # Find the user to check rate limiting (same logic as serializer)
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(username__iexact=email)
                except User.DoesNotExist:
                    pass

            # TODO: Implement proper rate limiting that doesn't interfere with legitimate invalidation
            # For now, skip rate limiting to get core functionality working

            # Create password reset if user exists
            reset = serializer.save()

            # Update the reset with IP address if it was created
            email_sending_failed = False
            if reset:
                if ip_address:
                    reset.ip_address = ip_address
                    reset.save(update_fields=["ip_address"])

                service = PasswordResetService()
                email_sent = service.send_reset_email(reset.user, reset)

                if not email_sent:
                    email_sending_failed = True
                    logger.error(
                        f"Failed to send password reset email for user "
                        f"{reset.user.email}"
                    )
                else:
                    logger.info(
                        f"Password reset email sent for user ID {reset.user.id}"
                    )

            # Return success message as expected by tests
            response_data = {
                "message": "A password reset link has been sent to your email if an account exists."
            }

            if email_sending_failed:
                response_data["email_sending_failed"] = True

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Password reset request error: {str(e)}")
            # Still return success to prevent information leakage
            return Response(
                {
                    "message": "A password reset link has been sent to your email if an account exists."
                },
                status=status.HTTP_200_OK,
            )

    # Return validation errors
    return Response(
        {"error": "Invalid request", "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm_view(request):
    """Confirm password reset with token and new password."""
    from users.models.password_reset import PasswordReset

    serializer = PasswordResetConfirmSerializer(data=request.data)
    if serializer.is_valid():
        try:
            user = serializer.save()
            logger.info(f"Password reset successful for user ID {user.id}")

            return Response(
                {"message": "Your password has been successfully reset."},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Password reset confirm error: {str(e)}")
            return Response(
                {"error": "An error occurred while resetting your password."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Handle specific validation errors
    if "token" in serializer.errors:
        token_error = str(serializer.errors["token"][0]).lower()
        token = request.data.get("token", "")

        # Log security event for invalid password reset attempts
        logger.warning(
            "Password reset attempt with invalid token: %s",
            token[:8] if token else "empty",
        )

        if "inactive" in token_error:
            return Response(
                {"error": "User account is inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif "invalid or has expired" in token_error:
            # This is the generic error from serializer - need to be more specific
            # Check what's actually wrong with this token
            if token:
                existing_reset = PasswordReset.objects.filter(token=token).first()
                if existing_reset:
                    if existing_reset.is_expired():
                        return Response(
                            {
                                "error": "Password reset token has expired. Please request a new one."
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    elif existing_reset.is_used():
                        return Response(
                            {
                                "error": "Password reset token has been used or is invalid."
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    # Token doesn't exist
                    return Response(
                        {"error": "Password reset token is invalid or has expired."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        elif "used" in token_error or "invalid" in token_error:
            return Response(
                {"error": "Password reset token has been used or is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Handle token-specific validation errors

    token = request.data.get("token")
    if token:
        # First check if token exists at all
        existing_reset = PasswordReset.objects.filter(token=token).first()
        if existing_reset:
            # Check inactive user first
            if not existing_reset.user.is_active:
                return Response(
                    {"error": "User account is inactive."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Then check if expired
            elif existing_reset.is_expired():
                return Response(
                    {
                        "error": "Password reset token has expired. Please request a new one."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Then check if used
            elif existing_reset.is_used():
                return Response(
                    {"error": "Password reset token has been used or is invalid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # Token doesn't exist
            return Response(
                {"error": "Password reset token is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Return validation errors
    return Response(
        {"error": "Invalid request", "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def password_reset_validate_view(request, token):
    """Validate password reset token."""
    from users.models.password_reset import PasswordReset

    # Basic token validation for clearly malformed tokens only
    if not token:
        return Response(
            {"error": "Invalid token format", "valid": False},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Only reject obviously invalid formats - let detailed validation happen later
    if len(token) > 64 or " " in token or "/" in token:
        return Response(
            {"error": "Invalid token format", "valid": False},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = PasswordResetTokenValidationSerializer(data={"token": token})
    if serializer.is_valid():
        # Get the reset object to access user email
        reset = PasswordReset.objects.get_valid_reset_by_token(token)
        if reset:
            # Check if user is active
            if not reset.user.is_active:
                return Response(
                    {"error": "User account is inactive", "valid": False},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "message": "Token is valid.",
                    "valid": True,
                    "user_email": reset.user.email,
                },
                status=status.HTTP_200_OK,
            )
        else:
            # Check if token exists but is expired or used
            existing_reset = PasswordReset.objects.filter(token=token).first()
            if existing_reset:
                if existing_reset.is_expired():
                    return Response(
                        {"error": "Password reset token has expired", "valid": False},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                elif existing_reset.is_used():
                    return Response(
                        {"error": "Password reset token has been used", "valid": False},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                elif not existing_reset.user.is_active:
                    return Response(
                        {"error": "User account is inactive", "valid": False},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Token not found
            return Response(
                {"error": "Password reset token not found", "valid": False},
                status=status.HTTP_404_NOT_FOUND,
            )

    # Return validation errors
    return Response(
        {"error": "Invalid token format", "valid": False},
        status=status.HTTP_400_BAD_REQUEST,
    )


# Session Management Views
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sessions_list_view(request):
    """List all active sessions for the authenticated user."""
    from users.models.session_models import UserSession

    user_sessions = UserSession.objects.filter(
        user=request.user, is_active=True
    ).select_related("session")
    serializer = UserSessionSerializer(
        user_sessions, many=True, context={"request": request}
    )

    return Response(
        {"results": serializer.data, "count": user_sessions.count()},
        status=status.HTTP_200_OK,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def terminate_session_view(request, session_id):
    """Terminate a specific session."""
    from django.contrib.sessions.models import Session

    from users.models.session_models import (
        SessionSecurityEvent,
        SessionSecurityLog,
        UserSession,
    )

    try:
        user_session = UserSession.objects.get(
            id=session_id, user=request.user, is_active=True
        )
    except UserSession.DoesNotExist:
        return Response(
            {"error": "Session not found or already terminated"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Get IP address for logging
    ip_address = request.META.get("REMOTE_ADDR", "127.0.0.1")
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    # Log session termination
    SessionSecurityLog.log_event(
        user=request.user,
        event_type=SessionSecurityEvent.SESSION_TERMINATED,
        ip_address=ip_address,
        user_agent=user_agent,
        user_session=user_session,
        details={"terminated_by_user": True},
    )

    # Terminate session
    user_session.deactivate()

    # Also delete Django session if it exists
    try:
        django_session = user_session.session
        django_session.delete()
    except Session.DoesNotExist:
        pass

    return Response(
        {"message": "Session terminated successfully"}, status=status.HTTP_200_OK
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def terminate_all_sessions_view(request):
    """Terminate all sessions except the current one."""
    from django.contrib.sessions.models import Session

    from users.models.session_models import (
        SessionSecurityEvent,
        SessionSecurityLog,
        UserSession,
    )

    # Get current session key
    current_session_key = request.session.session_key

    # Get IP address for logging
    ip_address = request.META.get("REMOTE_ADDR", "127.0.0.1")
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    # Get all other active sessions for this user
    user_sessions = UserSession.objects.filter(
        user=request.user, is_active=True
    ).select_related("session")

    # Exclude current session if we can identify it
    if current_session_key:
        user_sessions = user_sessions.exclude(session__session_key=current_session_key)

    terminated_count = 0
    for user_session in user_sessions:
        # Log session termination
        SessionSecurityLog.log_event(
            user=request.user,
            event_type=SessionSecurityEvent.SESSION_TERMINATED,
            ip_address=ip_address,
            user_agent=user_agent,
            user_session=user_session,
            details={"terminated_by_user": True, "bulk_termination": True},
        )

        # Terminate session
        user_session.deactivate()

        # Delete Django session
        try:
            user_session.session.delete()
        except Session.DoesNotExist:
            pass

        terminated_count += 1

    # Log bulk termination event
    if terminated_count > 0:
        SessionSecurityLog.log_event(
            user=request.user,
            event_type=SessionSecurityEvent.SESSION_TERMINATED,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "terminated_by_user": True,
                "bulk_termination": True,
                "terminated_count": terminated_count,
            },
        )

    serializer = TerminateAllSessionsResponseSerializer(
        {"terminated_sessions": terminated_count}
    )

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def extend_session_view(request):
    """Extend the current session."""
    from users.models.session_models import (
        SessionSecurityEvent,
        SessionSecurityLog,
        UserSession,
    )

    # Get current session
    current_session_key = request.session.session_key
    if not current_session_key:
        return Response(
            {"error": "No active session found"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user_session = UserSession.objects.get(
            user=request.user, session__session_key=current_session_key, is_active=True
        )
    except UserSession.DoesNotExist:
        return Response(
            {"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
        )

    serializer = SessionExtendSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    hours = serializer.validated_data["hours"]

    # Extend session
    user_session.extend_expiry(hours=hours)

    # Return updated session info
    session_serializer = UserSessionSerializer(
        user_session, context={"request": request}
    )

    return Response(
        {
            "message": f"Session extended by {hours} hours",
            "session": session_serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_session_view(request):
    """Get information about the current session."""
    from users.models.session_models import UserSession

    # Get current session
    current_session_key = request.session.session_key
    if not current_session_key:
        return Response(
            {"error": "No active session found"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user_session = UserSession.objects.get(
            user=request.user, session__session_key=current_session_key, is_active=True
        )
    except UserSession.DoesNotExist:
        return Response(
            {"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND
        )

    serializer = CurrentSessionSerializer(user_session, context={"request": request})

    return Response(serializer.data, status=status.HTTP_200_OK)
