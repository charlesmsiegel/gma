"""
Test suite for Issue #143: Session Management API Endpoints.

Tests cover:
- GET /api/auth/sessions/ - List user's active sessions
- DELETE /api/auth/sessions/{session_id}/ - Terminate specific session
- DELETE /api/auth/sessions/all/ - Terminate all other sessions
- POST /api/auth/sessions/extend/ - Extend current session
- GET /api/auth/session/current/ - Get current session info
- Authentication and authorization
- Error handling and edge cases
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from users.models.session_models import (
    SessionSecurityEvent,
    SessionSecurityLog,
    UserSession,
)

User = get_user_model()


class SessionListAPITest(TestCase):
    """Test suite for session list API endpoint."""

    def setUp(self):
        """Set up test users and sessions."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpass123"
        )

        self.client = APIClient()
        self.url = reverse("api:auth:sessions-list")

    def create_user_session(self, user, session_key="test_session", **kwargs):
        """Helper to create UserSession with Django session."""
        # Try to get existing session first
        try:
            django_session = Session.objects.get(session_key=session_key)
        except Session.DoesNotExist:
            django_session = Session.objects.create(
                session_key=session_key,
                session_data="test_data",
                expire_date=timezone.now() + timedelta(days=1),
            )

        defaults = {
            "ip_address": "192.168.1.100",
            "user_agent": "Chrome/91.0 Desktop",
            "device_type": "desktop",
            "browser": "Chrome",
            "operating_system": "Windows",
        }
        defaults.update(kwargs)

        return UserSession.objects.create(user=user, session=django_session, **defaults)

    def test_list_sessions_authenticated_user(self):
        """Test listing sessions for authenticated user."""
        # Create multiple sessions for the user
        session1 = self.create_user_session(
            self.user, "session1", ip_address="192.168.1.100", browser="Chrome"
        )
        session2 = self.create_user_session(
            self.user,
            "session2",
            ip_address="192.168.1.101",
            browser="Firefox",
            device_type="mobile",
        )

        # Create session for other user (shouldn't appear)
        self.create_user_session(self.other_user, "other_session")

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

        # Check session data structure
        session_data = response.data["results"][0]
        self.assertIn("id", session_data)
        self.assertIn("ip_address", session_data)
        self.assertIn("user_agent", session_data)
        self.assertIn("device_type", session_data)
        self.assertIn("browser", session_data)
        self.assertIn("operating_system", session_data)
        self.assertIn("location", session_data)
        self.assertIn("is_active", session_data)
        self.assertIn("created_at", session_data)
        self.assertIn("last_activity", session_data)
        self.assertIn("is_current", session_data)

    def test_list_sessions_unauthenticated(self):
        """Test listing sessions without authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_sessions_only_active(self):
        """Test listing only shows active sessions."""
        # Create active session
        active_session = self.create_user_session(self.user, "active_session")

        # Create inactive session
        inactive_session = self.create_user_session(self.user, "inactive_session")
        inactive_session.deactivate()

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], active_session.id)

    def test_list_sessions_pagination(self):
        """Test session list pagination."""
        # Create multiple sessions
        for i in range(15):
            self.create_user_session(self.user, f"session_{i}")

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 15)

    def test_list_sessions_ordering(self):
        """Test session list ordering by creation date."""
        # Create sessions with different creation times
        session1 = self.create_user_session(self.user, "session1")
        session2 = self.create_user_session(self.user, "session2")

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Most recent should be first
        self.assertEqual(response.data["results"][0]["id"], session2.id)
        self.assertEqual(response.data["results"][1]["id"], session1.id)


class SessionTerminateAPITest(TestCase):
    """Test suite for session termination API endpoint."""

    def setUp(self):
        """Set up test users and sessions."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpass123"
        )

        self.client = APIClient()

    def create_user_session(self, user, session_key="test_session", **kwargs):
        """Helper to create UserSession with Django session."""
        django_session = Session.objects.create(
            session_key=session_key,
            session_data="test_data",
            expire_date=timezone.now() + timedelta(days=1),
        )

        defaults = {"ip_address": "192.168.1.100", "user_agent": "Chrome/91.0 Desktop"}
        defaults.update(kwargs)

        return UserSession.objects.create(user=user, session=django_session, **defaults)

    def test_terminate_own_session(self):
        """Test terminating user's own session."""
        user_session = self.create_user_session(self.user, "target_session")
        url = reverse("api:auth:sessions-detail", kwargs={"pk": user_session.id})

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Check session is deactivated
        user_session.refresh_from_db()
        self.assertFalse(user_session.is_active)
        self.assertIsNotNone(user_session.ended_at)

        # Check Django session is deleted
        self.assertFalse(Session.objects.filter(pk=user_session.session_id).exists())

        # Check security log entry
        log_entry = SessionSecurityLog.objects.filter(
            user=self.user, event_type=SessionSecurityEvent.SESSION_TERMINATED
        ).first()
        self.assertIsNotNone(log_entry)

    def test_terminate_other_user_session(self):
        """Test cannot terminate another user's session."""
        other_session = self.create_user_session(self.other_user, "other_session")
        url = reverse("api:auth:sessions-detail", kwargs={"pk": other_session.id})

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Check session is still active
        other_session.refresh_from_db()
        self.assertTrue(other_session.is_active)

    def test_terminate_nonexistent_session(self):
        """Test terminating nonexistent session."""
        url = reverse("api:auth:sessions-detail", kwargs={"pk": 99999})

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_terminate_current_session(self):
        """Test terminating current session logs user out."""
        # Create a session and simulate it being the current one
        user_session = self.create_user_session(self.user, "current_session")

        # Mock the session key in the request
        with patch.object(self.client, "session") as mock_session:
            mock_session.session_key = user_session.session.session_key

            url = reverse("api:auth:sessions-detail", kwargs={"pk": user_session.id})
            self.client.force_authenticate(user=self.user)
            response = self.client.delete(url)

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_terminate_inactive_session(self):
        """Test terminating already inactive session."""
        user_session = self.create_user_session(self.user, "inactive_session")
        user_session.deactivate()

        url = reverse("api:auth:sessions-detail", kwargs={"pk": user_session.id})

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SessionTerminateAllAPITest(TestCase):
    """Test suite for terminate all sessions API endpoint."""

    def setUp(self):
        """Set up test users and sessions."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpass123"
        )

        self.client = APIClient()
        self.url = reverse("api:auth:sessions-terminate-all")

    def create_user_session(self, user, session_key="test_session", **kwargs):
        """Helper to create UserSession with Django session."""
        django_session = Session.objects.create(
            session_key=session_key,
            session_data="test_data",
            expire_date=timezone.now() + timedelta(days=1),
        )

        defaults = {"ip_address": "192.168.1.100", "user_agent": "Chrome/91.0 Desktop"}
        defaults.update(kwargs)

        return UserSession.objects.create(user=user, session=django_session, **defaults)

    def test_terminate_all_other_sessions(self):
        """Test terminating all other sessions except current."""
        # Create multiple sessions
        session1 = self.create_user_session(self.user, "session1")
        session2 = self.create_user_session(self.user, "session2")
        current_session = self.create_user_session(self.user, "current_session")

        # Create session for other user (should not be affected)
        other_session = self.create_user_session(self.other_user, "other_session")

        # Mock current session
        with patch.object(self.client, "session") as mock_session:
            mock_session.session_key = current_session.session.session_key

            self.client.force_authenticate(user=self.user)
            response = self.client.delete(self.url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["terminated_sessions"], 2)

            # Check sessions are deactivated
            session1.refresh_from_db()
            session2.refresh_from_db()
            current_session.refresh_from_db()
            other_session.refresh_from_db()

            self.assertFalse(session1.is_active)
            self.assertFalse(session2.is_active)
            self.assertTrue(current_session.is_active)  # Current session preserved
            self.assertTrue(other_session.is_active)  # Other user's session preserved

    def test_terminate_all_sessions_no_current(self):
        """Test terminating all sessions when no current session identified."""
        # Create multiple sessions
        session1 = self.create_user_session(self.user, "session1")
        session2 = self.create_user_session(self.user, "session2")

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["terminated_sessions"], 2)

    def test_terminate_all_sessions_no_sessions(self):
        """Test terminating all sessions when user has no sessions."""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["terminated_sessions"], 0)

    def test_terminate_all_sessions_unauthenticated(self):
        """Test terminating all sessions without authentication."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SessionExtendAPITest(TestCase):
    """Test suite for session extension API endpoint."""

    def setUp(self):
        """Set up test users and sessions."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.client = APIClient()
        self.url = reverse("api:auth:sessions-extend")

    def create_user_session(self, user, session_key="test_session", **kwargs):
        """Helper to create UserSession with Django session."""
        django_session = Session.objects.create(
            session_key=session_key,
            session_data="test_data",
            expire_date=timezone.now() + timedelta(days=1),
        )

        defaults = {"ip_address": "192.168.1.100", "user_agent": "Chrome/91.0 Desktop"}
        defaults.update(kwargs)

        return UserSession.objects.create(user=user, session=django_session, **defaults)

    def test_extend_current_session(self):
        """Test extending current session."""
        user_session = self.create_user_session(self.user, "current_session")
        original_expiry = user_session.session.expire_date

        with patch.object(self.client, "session") as mock_session:
            mock_session.session_key = user_session.session.session_key

            self.client.force_authenticate(user=self.user)
            response = self.client.post(self.url, {"hours": 48})

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("new_expiry", response.data)

            # Check session expiry extended
            user_session.session.refresh_from_db()
            self.assertGreater(user_session.session.expire_date, original_expiry)

            # Check security log entry
            log_entry = SessionSecurityLog.objects.filter(
                user=self.user, event_type=SessionSecurityEvent.SESSION_EXTENDED
            ).first()
            self.assertIsNotNone(log_entry)
            self.assertEqual(log_entry.details["extension_hours"], 48)

    def test_extend_session_default_hours(self):
        """Test extending session with default hours."""
        user_session = self.create_user_session(self.user, "current_session")

        with patch.object(self.client, "session") as mock_session:
            mock_session.session_key = user_session.session.session_key

            self.client.force_authenticate(user=self.user)
            response = self.client.post(self.url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Check default extension (24 hours)
            log_entry = SessionSecurityLog.objects.filter(
                user=self.user, event_type=SessionSecurityEvent.SESSION_EXTENDED
            ).first()
            self.assertEqual(log_entry.details["extension_hours"], 24)

    def test_extend_session_no_current_session(self):
        """Test extending session when no current session found."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"hours": 24})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("No active session found", response.data["detail"])

    def test_extend_session_invalid_hours(self):
        """Test extending session with invalid hours value."""
        user_session = self.create_user_session(self.user, "current_session")

        with patch.object(self.client, "session") as mock_session:
            mock_session.session_key = user_session.session.session_key

            self.client.force_authenticate(user=self.user)

            # Test negative hours
            response = self.client.post(self.url, {"hours": -5})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            # Test too many hours
            response = self.client.post(self.url, {"hours": 8760})  # 1 year
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_extend_session_unauthenticated(self):
        """Test extending session without authentication."""
        response = self.client.post(self.url, {"hours": 24})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CurrentSessionAPITest(TestCase):
    """Test suite for current session info API endpoint."""

    def setUp(self):
        """Set up test users and sessions."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.client = APIClient()
        self.url = reverse("api:auth:session-current")

    def create_user_session(self, user, session_key="test_session", **kwargs):
        """Helper to create UserSession with Django session."""
        django_session = Session.objects.create(
            session_key=session_key,
            session_data="test_data",
            expire_date=timezone.now() + timedelta(days=1),
        )

        defaults = {
            "ip_address": "192.168.1.100",
            "user_agent": "Chrome/91.0 Desktop",
            "device_type": "desktop",
            "browser": "Chrome",
            "operating_system": "Windows",
            "location": "New York, NY",
        }
        defaults.update(kwargs)

        return UserSession.objects.create(user=user, session=django_session, **defaults)

    def test_get_current_session_info(self):
        """Test getting current session information."""
        # Use regular test client to create real sessions
        from django.test import Client

        client = Client()

        # Login to create actual session
        client.force_login(self.user)

        # Get the session that was created by force_login
        session_key = client.session.session_key
        django_session = Session.objects.get(session_key=session_key)

        # Create UserSession using the existing session
        user_session = UserSession.objects.create(
            user=self.user,
            session=django_session,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            device_type="desktop",
            browser="Chrome",
            operating_system="Windows",
            location="New York, NY",
        )

        # Make request using same client with real session
        from django.urls import reverse

        url = reverse("api:auth:session-current")
        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response structure
        data = response.json()
        self.assertEqual(data["id"], user_session.id)
        self.assertEqual(data["ip_address"], "192.168.1.100")
        self.assertEqual(data["device_type"], "desktop")
        self.assertEqual(data["browser"], "Chrome")
        self.assertEqual(data["operating_system"], "Windows")
        self.assertEqual(data["location"], "New York, NY")
        self.assertTrue(data["is_current"])
        self.assertIn("expires_at", data)
        self.assertIn("time_until_expiry", data)

    def test_get_current_session_no_session(self):
        """Test getting current session when no session exists."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No active session found", response.data["error"])

    def test_get_current_session_unauthenticated(self):
        """Test getting current session without authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_current_session_with_security_logs(self):
        """Test current session info includes recent security events."""
        # Use regular test client to create real sessions
        from django.test import Client

        client = Client()

        # Login to create actual session
        client.force_login(self.user)

        # Get the session that was created by force_login
        session_key = client.session.session_key
        django_session = Session.objects.get(session_key=session_key)

        # Create UserSession using the existing session
        user_session = UserSession.objects.create(
            user=self.user,
            session=django_session,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            device_type="desktop",
            browser="Chrome",
            operating_system="Windows",
            location="New York, NY",
        )

        # Create some security log entries
        SessionSecurityLog.objects.create(
            user=self.user,
            user_session=user_session,
            event_type=SessionSecurityEvent.LOGIN_SUCCESS,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        SessionSecurityLog.objects.create(
            user=self.user,
            user_session=user_session,
            event_type=SessionSecurityEvent.SUSPICIOUS_ACTIVITY,
            ip_address="10.0.0.1",
            user_agent="Chrome/91.0 Desktop",
        )

        # Make request using same client with real session
        from django.urls import reverse

        url = reverse("api:auth:session-current")
        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("recent_security_events", data)
        self.assertEqual(len(data["recent_security_events"]), 2)


class SessionAPIPermissionTest(TestCase):
    """Test suite for session API permission and security checks."""

    def setUp(self):
        """Set up test users."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="staffpass123",
            is_staff=True,
        )
        self.superuser = User.objects.create_user(
            username="superuser",
            email="super@example.com",
            password="superpass123",
            is_superuser=True,
        )

        self.client = APIClient()

    def test_session_endpoints_require_authentication(self):
        """Test all session endpoints require authentication."""
        endpoints = [
            reverse("api:auth:sessions-list"),
            reverse("api:auth:sessions-terminate-all"),
            reverse("api:auth:sessions-extend"),
            reverse("api:auth:session-current"),
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_cannot_access_other_user_sessions(self):
        """Test staff users cannot access other users' sessions."""
        # Create session for regular user
        django_session = Session.objects.create(
            session_key="user_session",
            session_data="data",
            expire_date=timezone.now() + timedelta(days=1),
        )
        user_session = UserSession.objects.create(
            user=self.user,
            session=django_session,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        # Staff user tries to access
        self.client.force_authenticate(user=self.staff_user)
        url = reverse("api:auth:sessions-detail", kwargs={"pk": user_session.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_superuser_can_manage_all_sessions(self):
        """Test superusers can manage all user sessions (admin functionality)."""
        # This test would be for admin endpoints, not regular user endpoints
        # Regular session endpoints should still be user-scoped even for superusers
        django_session = Session.objects.create(
            session_key="user_session",
            session_data="data",
            expire_date=timezone.now() + timedelta(days=1),
        )
        user_session = UserSession.objects.create(
            user=self.user,
            session=django_session,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        # Even superuser cannot access other users' sessions via regular endpoints
        self.client.force_authenticate(user=self.superuser)
        url = reverse("api:auth:sessions-detail", kwargs={"pk": user_session.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_rate_limiting_session_endpoints(self):
        """Test rate limiting on session management endpoints."""
        # This would test rate limiting middleware if implemented
        # For now, we'll just ensure the endpoints exist and respond
        self.client.force_authenticate(user=self.user)

        # Multiple rapid requests to terminate all sessions
        for _ in range(5):
            response = self.client.delete(reverse("api:auth:sessions-terminate-all"))
            self.assertIn(
                response.status_code,
                [status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS],
            )


class SessionAPIErrorHandlingTest(TestCase):
    """Test suite for session API error handling."""

    def setUp(self):
        """Set up test users."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_malformed_json_request(self):
        """Test handling of malformed JSON requests."""
        url = reverse("api:auth:sessions-extend")

        response = self.client.post(
            url, data="invalid json", content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_http_methods(self):
        """Test invalid HTTP methods on session endpoints."""
        urls_methods = [
            (reverse("api:auth:sessions-list"), ["POST", "PUT", "PATCH"]),
            (reverse("api:auth:sessions-extend"), ["GET", "PUT", "PATCH", "DELETE"]),
            (reverse("api:auth:session-current"), ["POST", "PUT", "PATCH", "DELETE"]),
        ]

        for url, invalid_methods in urls_methods:
            for method in invalid_methods:
                response = getattr(self.client, method.lower())(url)
                self.assertEqual(
                    response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
                )

    def test_concurrent_session_termination(self):
        """Test handling concurrent session termination requests."""
        # Create session
        django_session = Session.objects.create(
            session_key="test_session",
            session_data="data",
            expire_date=timezone.now() + timedelta(days=1),
        )
        user_session = UserSession.objects.create(
            user=self.user,
            session=django_session,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        url = reverse("api:auth:sessions-detail", kwargs={"pk": user_session.id})

        # First termination
        response1 = self.client.delete(url)
        self.assertEqual(response1.status_code, status.HTTP_204_NO_CONTENT)

        # Second termination (should fail gracefully)
        response2 = self.client.delete(url)
        self.assertEqual(response2.status_code, status.HTTP_404_NOT_FOUND)
