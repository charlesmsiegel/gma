"""
Test suite for Issue #143: User Session Management Models.

Tests cover:
- UserSession model with device/browser tracking
- SessionSecurityLog model for security events
- Session model functionality and validation
- Device fingerprinting and identification
- Session cleanup and maintenance
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from users.models.session_models import (
    SessionSecurityEvent,
    SessionSecurityLog,
    UserSession,
)

User = get_user_model()


class UserSessionModelTest(TestCase):
    """Test suite for UserSession model functionality."""

    def setUp(self):
        """Set up test users and session data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpass123"
        )

        # Create Django session
        self.session = Session.objects.create(
            session_key=f"test_session_key_{uuid.uuid4().hex[:8]}",
            session_data="encoded_session_data",
            expire_date=timezone.now() + timedelta(days=1),
        )

        self.user_agent_chrome = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        )
        self.user_agent_firefox = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) "
            "Gecko/20100101 Firefox/89.0"
        )

    def test_user_session_creation(self):
        """Test basic UserSession creation."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
            device_type="desktop",
            browser="Chrome",
            operating_system="Windows",
            location="New York, NY",
        )

        self.assertEqual(user_session.user, self.user)
        self.assertEqual(user_session.session, self.session)
        self.assertEqual(user_session.ip_address, "192.168.1.100")
        self.assertEqual(user_session.device_type, "desktop")
        self.assertEqual(user_session.browser, "Chrome")
        self.assertEqual(user_session.operating_system, "Windows")
        self.assertTrue(user_session.is_active)
        self.assertIsNotNone(user_session.created_at)
        self.assertIsNotNone(user_session.last_activity)

    def test_user_session_str_representation(self):
        """Test UserSession string representation."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
            device_type="desktop",
            browser="Chrome",
        )

        expected = "testuser - Chrome/desktop from 192.168.1.100"
        self.assertEqual(str(user_session), expected)

    def test_user_session_device_fingerprint(self):
        """Test device fingerprint generation."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
            device_type="desktop",
            browser="Chrome",
            operating_system="Windows",
        )

        fingerprint = user_session.device_fingerprint
        self.assertIsNotNone(fingerprint)
        self.assertIsInstance(fingerprint, str)
        self.assertEqual(len(fingerprint), 64)  # SHA-256 hex length

        # Test fingerprint consistency
        same_fingerprint = user_session.device_fingerprint
        self.assertEqual(fingerprint, same_fingerprint)

    def test_user_session_is_suspicious_activity(self):
        """Test suspicious activity detection."""
        # Create initial session
        user_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
            device_type="desktop",
            browser="Chrome",
            operating_system="Windows",
        )

        # Test with same details - not suspicious
        self.assertFalse(
            user_session.is_suspicious_activity(
                ip_address="192.168.1.100", user_agent=self.user_agent_chrome
            )
        )

        # Test with different IP - suspicious
        self.assertTrue(
            user_session.is_suspicious_activity(
                ip_address="10.0.0.1", user_agent=self.user_agent_chrome
            )
        )

        # Test with different user agent - suspicious
        self.assertTrue(
            user_session.is_suspicious_activity(
                ip_address="192.168.1.100", user_agent=self.user_agent_firefox
            )
        )

    def test_user_session_update_activity(self):
        """Test session activity update."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
        )

        original_activity = user_session.last_activity

        # Wait a moment and update activity
        future_time = timezone.now() + timedelta(seconds=10)
        with patch("django.utils.timezone.now", return_value=future_time):
            user_session.update_activity()

        user_session.refresh_from_db()
        self.assertGreater(user_session.last_activity, original_activity)
        self.assertEqual(user_session.last_activity, future_time)

    def test_user_session_manager_active_sessions(self):
        """Test UserSession manager for active sessions."""
        # Create active session
        active_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
            is_active=True,
        )

        # Create inactive session
        inactive_session_django = Session.objects.create(
            session_key="inactive_session_key",
            session_data="data",
            expire_date=timezone.now() + timedelta(days=1),
        )
        UserSession.objects.create(
            user=self.user,
            session=inactive_session_django,
            ip_address="192.168.1.101",
            user_agent=self.user_agent_chrome,
            is_active=False,
        )

        active_sessions = UserSession.objects.active()
        self.assertEqual(active_sessions.count(), 1)
        self.assertEqual(active_sessions.first(), active_session)

    def test_user_session_manager_for_user(self):
        """Test UserSession manager for specific user."""
        # Create sessions for different users
        user_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
        )

        other_session_django = Session.objects.create(
            session_key="other_session_key",
            session_data="data",
            expire_date=timezone.now() + timedelta(days=1),
        )
        UserSession.objects.create(
            user=self.other_user,
            session=other_session_django,
            ip_address="192.168.1.101",
            user_agent=self.user_agent_chrome,
        )

        user_sessions = UserSession.objects.for_user(self.user)
        self.assertEqual(user_sessions.count(), 1)
        self.assertEqual(user_sessions.first(), user_session)

    def test_user_session_manager_expired_sessions(self):
        """Test UserSession manager for expired sessions."""
        # Create expired Django session
        expired_session = Session.objects.create(
            session_key="expired_session_key",
            session_data="data",
            expire_date=timezone.now() - timedelta(hours=1),
        )

        expired_user_session = UserSession.objects.create(
            user=self.user,
            session=expired_session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
        )

        # Create active session
        UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.101",
            user_agent=self.user_agent_chrome,
        )

        expired_sessions = UserSession.objects.expired()
        self.assertEqual(expired_sessions.count(), 1)
        self.assertEqual(expired_sessions.first(), expired_user_session)

    def test_user_session_deactivate(self):
        """Test session deactivation."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
            is_active=True,
        )

        user_session.deactivate()
        user_session.refresh_from_db()

        self.assertFalse(user_session.is_active)
        self.assertIsNotNone(user_session.ended_at)

    def test_user_session_extend_expiry(self):
        """Test session expiry extension."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
        )

        original_expiry = self.session.expire_date
        user_session.extend_expiry(hours=24)

        self.session.refresh_from_db()
        self.assertGreater(self.session.expire_date, original_expiry)

    def test_user_session_remember_me_functionality(self):
        """Test remember me session extension."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
            remember_me=True,
        )

        self.assertTrue(user_session.remember_me)

        # Test extended expiry for remember me sessions
        original_expiry = self.session.expire_date
        user_session.extend_for_remember_me()

        self.session.refresh_from_db()
        expected_extension = timedelta(days=30)  # Default remember me period
        self.assertAlmostEqual(
            self.session.expire_date - original_expiry,
            expected_extension,
            delta=timedelta(seconds=1),
        )

    def test_user_session_unique_session_constraint(self):
        """Test unique constraint on session field."""
        UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
        )

        # Attempt to create another UserSession with the same session
        with self.assertRaises(ValidationError):
            UserSession.objects.create(
                user=self.other_user,
                session=self.session,
                ip_address="192.168.1.101",
                user_agent=self.user_agent_firefox,
            )

    def test_user_session_cascade_on_user_delete(self):
        """Test UserSession deletion when user is deleted."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
        )

        session_id = user_session.id
        self.user.delete()

        # UserSession should be deleted
        with self.assertRaises(UserSession.DoesNotExist):
            UserSession.objects.get(id=session_id)

    def test_user_session_cascade_on_session_delete(self):
        """Test UserSession deletion when session is deleted."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent=self.user_agent_chrome,
        )

        session_id = user_session.id
        self.session.delete()

        # UserSession should be deleted
        with self.assertRaises(UserSession.DoesNotExist):
            UserSession.objects.get(id=session_id)


class SessionSecurityLogModelTest(TestCase):
    """Test suite for SessionSecurityLog model functionality."""

    def setUp(self):
        """Set up test users and session data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.session = Session.objects.create(
            session_key=f"test_session_key_{uuid.uuid4().hex[:8]}",
            session_data="encoded_session_data",
            expire_date=timezone.now() + timedelta(days=1),
        )

        self.user_session = UserSession.objects.create(
            user=self.user,
            session=self.session,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

    def test_session_security_log_creation(self):
        """Test basic SessionSecurityLog creation."""
        log_entry = SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self.user_session,
            event_type=SessionSecurityEvent.LOGIN_SUCCESS,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            details={"login_method": "password"},
        )

        self.assertEqual(log_entry.user, self.user)
        self.assertEqual(log_entry.user_session, self.user_session)
        self.assertEqual(log_entry.event_type, SessionSecurityEvent.LOGIN_SUCCESS)
        self.assertEqual(log_entry.ip_address, "192.168.1.100")
        self.assertEqual(log_entry.details["login_method"], "password")
        self.assertIsNotNone(log_entry.timestamp)

    def test_session_security_log_str_representation(self):
        """Test SessionSecurityLog string representation."""
        log_entry = SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self.user_session,
            event_type=SessionSecurityEvent.SUSPICIOUS_ACTIVITY,
            ip_address="10.0.0.1",
            user_agent="Chrome/91.0 Desktop",
        )

        expected = "testuser - SUSPICIOUS_ACTIVITY from 10.0.0.1"
        self.assertEqual(str(log_entry), expected)

    def test_session_security_log_all_event_types(self):
        """Test all SessionSecurityEvent types."""
        event_types = [
            SessionSecurityEvent.LOGIN_SUCCESS,
            SessionSecurityEvent.LOGIN_FAILED,
            SessionSecurityEvent.LOGOUT,
            SessionSecurityEvent.SESSION_HIJACK_ATTEMPT,
            SessionSecurityEvent.SUSPICIOUS_ACTIVITY,
            SessionSecurityEvent.IP_ADDRESS_CHANGED,
            SessionSecurityEvent.USER_AGENT_CHANGED,
            SessionSecurityEvent.SESSION_EXTENDED,
            SessionSecurityEvent.SESSION_TERMINATED,
            SessionSecurityEvent.CONCURRENT_SESSION_LIMIT,
            SessionSecurityEvent.PASSWORD_CHANGED,
            SessionSecurityEvent.ACCOUNT_LOCKED,
        ]

        for event_type in event_types:
            log_entry = SessionSecurityLog.objects.create(
                user=self.user,
                user_session=self.user_session,
                event_type=event_type,
                ip_address="192.168.1.100",
                user_agent="Chrome/91.0 Desktop",
            )
            self.assertEqual(log_entry.event_type, event_type)

    def test_session_security_log_manager_for_user(self):
        """Test SessionSecurityLog manager for specific user."""
        other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpass123"
        )

        # Create logs for different users
        user_log = SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self.user_session,
            event_type=SessionSecurityEvent.LOGIN_SUCCESS,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        other_session = Session.objects.create(
            session_key="other_session_key",
            session_data="data",
            expire_date=timezone.now() + timedelta(days=1),
        )
        other_user_session = UserSession.objects.create(
            user=other_user,
            session=other_session,
            ip_address="192.168.1.101",
            user_agent="Firefox/89.0 Desktop",
        )

        SessionSecurityLog.objects.create(
            user=other_user,
            user_session=other_user_session,
            event_type=SessionSecurityEvent.LOGIN_SUCCESS,
            ip_address="192.168.1.101",
            user_agent="Firefox/89.0 Desktop",
        )

        user_logs = SessionSecurityLog.objects.for_user(self.user)
        self.assertEqual(user_logs.count(), 1)
        self.assertEqual(user_logs.first(), user_log)

    def test_session_security_log_manager_security_events(self):
        """Test SessionSecurityLog manager for security events."""
        # Create normal log
        SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self.user_session,
            event_type=SessionSecurityEvent.LOGIN_SUCCESS,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        # Create security event logs
        suspicious_log = SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self.user_session,
            event_type=SessionSecurityEvent.SUSPICIOUS_ACTIVITY,
            ip_address="10.0.0.1",
            user_agent="Chrome/91.0 Desktop",
        )

        hijack_log = SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self.user_session,
            event_type=SessionSecurityEvent.SESSION_HIJACK_ATTEMPT,
            ip_address="10.0.0.2",
            user_agent="Chrome/91.0 Desktop",
        )

        security_logs = SessionSecurityLog.objects.security_events()
        self.assertEqual(security_logs.count(), 2)
        self.assertIn(suspicious_log, security_logs)
        self.assertIn(hijack_log, security_logs)

    def test_session_security_log_manager_recent_logs(self):
        """Test SessionSecurityLog manager for recent logs."""
        # Create old log
        old_log = SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self.user_session,
            event_type=SessionSecurityEvent.LOGIN_SUCCESS,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        # Manually set old timestamp
        SessionSecurityLog.objects.filter(id=old_log.id).update(
            timestamp=timezone.now() - timedelta(hours=2)
        )

        # Create recent log
        recent_log = SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self.user_session,
            event_type=SessionSecurityEvent.LOGOUT,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        recent_logs = SessionSecurityLog.objects.recent(hours=1)
        self.assertEqual(recent_logs.count(), 1)
        self.assertEqual(recent_logs.first(), recent_log)

    def test_session_security_log_details_json_field(self):
        """Test SessionSecurityLog details JSON field functionality."""
        details = {
            "reason": "IP address changed",
            "old_ip": "192.168.1.100",
            "new_ip": "10.0.0.1",
            "geolocation": "Unknown",
            "risk_score": 8.5,
        }

        log_entry = SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self.user_session,
            event_type=SessionSecurityEvent.IP_ADDRESS_CHANGED,
            ip_address="10.0.0.1",
            user_agent="Chrome/91.0 Desktop",
            details=details,
        )

        log_entry.refresh_from_db()
        self.assertEqual(log_entry.details["reason"], "IP address changed")
        self.assertEqual(log_entry.details["old_ip"], "192.168.1.100")
        self.assertEqual(log_entry.details["risk_score"], 8.5)

    def test_session_security_log_cascade_behavior(self):
        """Test SessionSecurityLog cascade behavior."""
        log_entry = SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self.user_session,
            event_type=SessionSecurityEvent.LOGIN_SUCCESS,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        log_id = log_entry.id

        # Delete user_session - log should remain (SET_NULL behavior)
        self.user_session.delete()
        log_entry.refresh_from_db()
        self.assertIsNone(log_entry.user_session)

        # Delete user - log should be deleted (CASCADE behavior)
        self.user.delete()
        with self.assertRaises(SessionSecurityLog.DoesNotExist):
            SessionSecurityLog.objects.get(id=log_id)

    def test_session_security_log_ordering(self):
        """Test SessionSecurityLog default ordering."""
        # Create logs with different timestamps
        first_log = SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self.user_session,
            event_type=SessionSecurityEvent.LOGIN_SUCCESS,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        second_log = SessionSecurityLog.objects.create(
            user=self.user,
            user_session=self.user_session,
            event_type=SessionSecurityEvent.LOGOUT,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        logs = list(SessionSecurityLog.objects.all())
        # Should be ordered by timestamp descending (most recent first)
        self.assertEqual(logs[0], second_log)
        self.assertEqual(logs[1], first_log)


class SessionSecurityEventTest(TestCase):
    """Test suite for SessionSecurityEvent enum functionality."""

    def test_all_security_event_types(self):
        """Test all security event types are properly defined."""
        expected_events = {
            "LOGIN_SUCCESS": "login_success",
            "LOGIN_FAILED": "login_failed",
            "LOGOUT": "logout",
            "SESSION_HIJACK_ATTEMPT": "session_hijack_attempt",
            "SUSPICIOUS_ACTIVITY": "suspicious_activity",
            "IP_ADDRESS_CHANGED": "ip_address_changed",
            "USER_AGENT_CHANGED": "user_agent_changed",
            "SESSION_EXTENDED": "session_extended",
            "SESSION_TERMINATED": "session_terminated",
            "CONCURRENT_SESSION_LIMIT": "concurrent_session_limit",
            "PASSWORD_CHANGED": "password_changed",
            "ACCOUNT_LOCKED": "account_locked",
        }

        for attr_name, expected_value in expected_events.items():
            self.assertTrue(hasattr(SessionSecurityEvent, attr_name))
            self.assertEqual(getattr(SessionSecurityEvent, attr_name), expected_value)

    def test_security_events_subset(self):
        """Test security events subset classification."""
        security_events = {
            SessionSecurityEvent.SESSION_HIJACK_ATTEMPT,
            SessionSecurityEvent.SUSPICIOUS_ACTIVITY,
            SessionSecurityEvent.IP_ADDRESS_CHANGED,
            SessionSecurityEvent.USER_AGENT_CHANGED,
            SessionSecurityEvent.CONCURRENT_SESSION_LIMIT,
            SessionSecurityEvent.ACCOUNT_LOCKED,
        }

        all_events = {
            SessionSecurityEvent.LOGIN_SUCCESS,
            SessionSecurityEvent.LOGIN_FAILED,
            SessionSecurityEvent.LOGOUT,
            SessionSecurityEvent.SESSION_EXTENDED,
            SessionSecurityEvent.SESSION_TERMINATED,
            SessionSecurityEvent.PASSWORD_CHANGED,
        }
        all_events.update(security_events)

        # All security events should be in the complete set
        for event in security_events:
            self.assertIn(event, all_events)

        # Non-security events should not be in security set
        non_security = all_events - security_events
        for event in non_security:
            self.assertNotIn(event, security_events)
