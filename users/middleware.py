"""
Session tracking middleware for Issue #143: User Session Management and Security.

This middleware automatically tracks user sessions and provides security monitoring
by creating UserSession records for authenticated users and detecting suspicious
activity patterns.
"""

import logging
from typing import Optional

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils.deprecation import MiddlewareMixin

from .models.session_models import UserSession
from .services.session_security import SessionSecurityService

User = get_user_model()
logger = logging.getLogger(__name__)


class SessionTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to automatically track user sessions and provide security monitoring.

    This middleware:
    1. Creates UserSession records for authenticated users
    2. Updates session activity timestamps
    3. Monitors for suspicious activity
    4. Handles session security events
    """

    def __init__(self, get_response):
        """Initialize the middleware."""
        super().__init__(get_response)
        self.session_service = SessionSecurityService()

    def process_request(self, request):
        """Process incoming request for session tracking."""
        # Skip processing for non-authenticated users
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return None

        # Skip if no session
        if not hasattr(request, "session") or not request.session.session_key:
            return None

        # Get or create UserSession
        user_session = self._get_or_create_user_session(request)
        if not user_session:
            return None

        # Store user_session on request for views to access
        request.user_session = user_session

        # Check for suspicious activity
        self._check_session_security(request, user_session)

        return None

    def process_response(self, request, response):
        """Process outgoing response to update session activity."""
        # Update session activity if we have a user session
        if hasattr(request, "user_session") and request.user_session:
            try:
                request.user_session.update_activity()
            except Exception as e:
                logger.error(f"Error updating session activity: {e}")

        return response

    def _get_or_create_user_session(self, request) -> Optional[UserSession]:
        """Get or create UserSession for the current request."""
        try:
            # Try to get existing UserSession
            django_session = Session.objects.get(
                session_key=request.session.session_key
            )
            user_session, created = UserSession.objects.get_or_create(
                session=django_session,
                defaults={
                    "user": request.user,
                    "ip_address": self._get_client_ip(request),
                    "user_agent": request.META.get("HTTP_USER_AGENT", "")[
                        :500
                    ],  # Truncate if too long
                },
            )

            if created:
                # Parse device information for new sessions
                self._populate_device_info(user_session, request)
                logger.info(
                    f"Created new UserSession {user_session.id} for user {request.user.id}"
                )

            return user_session

        except Session.DoesNotExist:
            logger.warning(
                f"Django session not found for key {request.session.session_key}"
            )
            return None
        except Exception as e:
            logger.error(f"Error getting/creating UserSession: {e}")
            return None

    def _populate_device_info(self, user_session: UserSession, request):
        """Populate device information for a new UserSession."""
        try:
            # Use the session service to create the session with device info
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get("HTTP_USER_AGENT", "")

            # Parse device information
            device_info = self.session_service._parse_user_agent(user_agent)
            location = self.session_service._get_location_from_ip(ip_address)

            # Update the user session
            user_session.device_type = device_info.get("device_type", "")
            user_session.browser = device_info.get("browser", "")
            user_session.operating_system = device_info.get("os", "")
            user_session.location = location
            user_session.save(
                update_fields=["device_type", "browser", "operating_system", "location"]
            )

        except Exception as e:
            logger.error(
                f"Error populating device info for UserSession {user_session.id}: {e}"
            )

    def _check_session_security(self, request, user_session: UserSession):
        """Check for suspicious session activity."""
        try:
            ip_address = self._get_client_ip(request)
            user_agent = request.META.get("HTTP_USER_AGENT", "")

            # Let the security service handle the check
            security_result = self.session_service.handle_request_security_check(
                user_session=user_session, new_ip=ip_address, new_user_agent=user_agent
            )

            # If security issues were detected and session was terminated,
            # we should log the user out
            if security_result and "session_terminated" in security_result.get(
                "actions_taken", []
            ):
                logger.warning(
                    f"Session {user_session.id} terminated due to security concerns. "
                    f"Risk score: {security_result.get('risk_score', 'unknown')}"
                )
                # Note: We don't actually log out here as that would interfere with the response
                # The session has been deactivated, so subsequent requests will fail

        except Exception as e:
            logger.error(f"Error checking session security: {e}")

    def _get_client_ip(self, request) -> str:
        """Get the client IP address from the request."""
        # Check for forwarded IP first (for reverse proxies)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Take the first IP in the list
            ip = x_forwarded_for.split(",")[0].strip()
            return ip

        # Check for real IP header
        x_real_ip = request.META.get("HTTP_X_REAL_IP")
        if x_real_ip:
            return x_real_ip.strip()

        # Fallback to REMOTE_ADDR
        return request.META.get("REMOTE_ADDR", "127.0.0.1")


class SessionCleanupMiddleware(MiddlewareMixin):
    """
    Middleware to periodically clean up expired sessions.

    This runs cleanup operations occasionally to remove expired UserSessions
    and their associated Django sessions.
    """

    def __init__(self, get_response):
        """Initialize the middleware."""
        super().__init__(get_response)
        self.cleanup_counter = 0
        self.cleanup_frequency = 100  # Run cleanup every 100 requests

    def process_response(self, request, response):
        """Occasionally run session cleanup."""
        self.cleanup_counter += 1

        if self.cleanup_counter >= self.cleanup_frequency:
            self.cleanup_counter = 0
            try:
                self._cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"Error during session cleanup: {e}")

        return response

    def _cleanup_expired_sessions(self):
        """Clean up expired UserSessions."""
        try:
            cleaned_count = UserSession.objects.cleanup_expired()
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired UserSessions")
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
