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

from ..serializers import LoginSerializer, UserRegistrationSerializer, UserSerializer

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

            # Prepare response data
            response_data = {
                "message": (
                    "User registered successfully. Please check your email to "
                    "verify your account."
                ),
                "user": UserSerializer(user).data,
                "email_verification_required": verification_required,
            }

            # Email is already sent during user creation in the serializer
            # Just check if there was an issue (which would be rare)
            if verification_required and not user.email_verification_sent_at:
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
    serializer = LoginSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        user = serializer.validated_data["user"]
        login(request, user)
        return Response(
            {"message": "Login successful", "user": UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout a user."""
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
