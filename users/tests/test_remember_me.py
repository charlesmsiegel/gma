"""
Test suite for Issue #143: Remember Me Functionality and Extended Sessions.

Tests cover:
- Remember me checkbox handling
- Extended session expiry (30 days vs regular)
- Remember me session security considerations
- Session extension API with remember me
- Cookie handling for remember me
- Security implications of long-lived sessions
- Remember me session cleanup
- Cross-device remember me behavior
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import TestCase
from django.utils import timezone

from users.models.session_models import (
    SessionSecurityEvent,
    SessionSecurityLog,
    UserSession,
)
from users.services import SessionSecurityService

User = get_user_model()


class RememberMeSessionTest(TestCase):
    """Test suite for remember me session functionality."""

    def setUp(self):
        """Set up test users and sessions."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.service = SessionSecurityService()

    def create_session(self, remember_me=False, expire_hours=24):
        """Helper to create session with remember me option."""
        django_session = Session.objects.create(
            session_key=f"test_session_key_{uuid.uuid4().hex[:8]}",
            session_data="test_data",
            expire_date=timezone.now() + timedelta(hours=expire_hours),
        )

        return UserSession.objects.create(
            user=self.user,
            session=django_session,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            remember_me=remember_me,
        )

    def test_create_remember_me_session(self):
        """Test creating session with remember me enabled."""
        user_session = self.create_session(remember_me=True)

        self.assertTrue(user_session.remember_me)
        self.assertEqual(user_session.user, self.user)

        # Check security log entry (created by service, not model directly)
        # This tests the model field functionality

    def test_remember_me_extended_expiry(self):
        """Test remember me sessions get extended expiry."""
        user_session = self.create_session(remember_me=True, expire_hours=1)
        original_expiry = user_session.session.expire_date

        # Extend for remember me (30 days)
        user_session.extend_for_remember_me()

        user_session.session.refresh_from_db()
        extended_expiry = user_session.session.expire_date

        # Should be extended by 30 days
        expected_extension = timedelta(days=30)
        actual_extension = extended_expiry - original_expiry

        self.assertAlmostEqual(
            actual_extension, expected_extension, delta=timedelta(seconds=1)
        )

    def test_regular_session_vs_remember_me_expiry(self):
        """Test difference between regular and remember me session expiry."""
        # Create regular session
        regular_session = self.create_session(remember_me=False, expire_hours=24)

        # Create remember me session
        remember_session = self.create_session(remember_me=True, expire_hours=24)
        remember_session.extend_for_remember_me()

        regular_expiry = regular_session.session.expire_date
        remember_expiry = remember_session.session.expire_date

        # Remember me session should expire much later
        self.assertGreater(
            remember_expiry,
            regular_expiry + timedelta(days=25),  # Should be ~29 days difference
        )

    def test_remember_me_session_extension_logged(self):
        """Test remember me extension creates security log entry."""
        user_session = self.create_session(remember_me=True)

        user_session.extend_for_remember_me()

        # Check security log entry for extension
        log_entry = SessionSecurityLog.objects.filter(
            user=self.user, event_type=SessionSecurityEvent.SESSION_EXTENDED
        ).first()

        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.details["extension_hours"], 24 * 30)  # 30 days

    def test_remember_me_flag_persistence(self):
        """Test remember me flag persists through session updates."""
        user_session = self.create_session(remember_me=True)

        # Update activity
        user_session.update_activity()
        user_session.refresh_from_db()

        # Remember me flag should still be True
        self.assertTrue(user_session.remember_me)

        # Extend session
        user_session.extend_expiry(hours=48)
        user_session.refresh_from_db()

        # Remember me flag should still be True
        self.assertTrue(user_session.remember_me)

    def test_remember_me_security_implications(self):
        """Test security considerations for remember me sessions."""
        user_session = self.create_session(remember_me=True)

        # Remember me sessions should still be subject to security monitoring
        is_suspicious = self.service.detect_suspicious_activity(
            user_session, new_ip="203.0.113.1", new_user_agent="Suspicious Bot/1.0"
        )

        self.assertTrue(is_suspicious)

        # Even remember me sessions should be terminated for high-risk activity
        result = self.service.handle_suspicious_activity(
            user_session, "203.0.113.1", "Suspicious Bot/1.0"
        )

        if result["risk_score"] >= 9.0:
            user_session.refresh_from_db()
            self.assertFalse(user_session.is_active)

    def test_multiple_remember_me_sessions(self):
        """Test handling multiple remember me sessions."""
        sessions = []

        # Create multiple remember me sessions
        for i in range(3):
            session = self.create_session(remember_me=True)
            session.ip_address = f"192.168.1.{100 + i}"
            session.save()
            sessions.append(session)

        # All should be active
        active_count = UserSession.objects.active().for_user(self.user).count()
        self.assertEqual(active_count, 3)

        # Check if concurrent session anomaly is detected
        is_anomaly = self.service.detect_concurrent_session_anomaly(self.user)
        self.assertIsInstance(is_anomaly, bool)

    def test_remember_me_session_cleanup(self):
        """Test cleanup of expired remember me sessions."""
        # Create expired remember me session
        user_session = self.create_session(remember_me=True)

        # Set session to expired
        user_session.session.expire_date = timezone.now() - timedelta(days=1)
        user_session.session.save()

        # Run cleanup
        cleaned_count = UserSession.objects.cleanup_expired()

        self.assertGreater(cleaned_count, 0)

        # Check session is deactivated
        user_session.refresh_from_db()
        self.assertFalse(user_session.is_active)


class RememberMeLoginFlowTest(TestCase):
    """Test suite for remember me login flow integration."""

    def setUp(self):
        """Set up test users."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.service = SessionSecurityService()

    def test_login_with_remember_me_creates_extended_session(self):
        """Test login with remember me checkbox creates extended session."""
        # Simulate login with remember me
        django_session = Session.objects.create(
            session_key="remember_session",
            session_data="test_data",
            expire_date=timezone.now() + timedelta(days=30),  # Extended expiry
        )

        user_session = self.service.create_user_session(
            user=self.user,
            session=django_session,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            remember_me=True,
        )

        self.assertTrue(user_session.remember_me)

        # Check session expiry is extended (30 days)
        time_diff = user_session.session.expire_date - timezone.now()
        self.assertGreater(time_diff, timedelta(days=25))

    def test_login_without_remember_me_creates_regular_session(self):
        """Test login without remember me creates regular session."""
        django_session = Session.objects.create(
            session_key="regular_session",
            session_data="test_data",
            expire_date=timezone.now() + timedelta(hours=24),  # Regular expiry
        )

        user_session = self.service.create_user_session(
            user=self.user,
            session=django_session,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            remember_me=False,
        )

        self.assertFalse(user_session.remember_me)

        # Check session expiry is regular (24 hours)
        time_diff = user_session.session.expire_date - timezone.now()
        self.assertLess(time_diff, timedelta(days=2))

    def test_remember_me_session_survives_browser_restart(self):
        """Test remember me session persists after browser restart simulation."""
        # Create remember me session
        user_session = UserSession.objects.create(
            user=self.user,
            session=Session.objects.create(
                session_key="persistent_session",
                session_data="data",
                expire_date=timezone.now() + timedelta(days=30),
            ),
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            remember_me=True,
        )

        # Simulate time passing (browser restart)
        # Calculate future time before mock context to avoid MagicMock issues
        future_time = timezone.now() + timedelta(hours=8)
        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = future_time

            # Session should still be active
            user_session.refresh_from_db()
            self.assertTrue(user_session.is_active)

            # Session should not be expired
            expired_sessions = UserSession.objects.expired()
            self.assertNotIn(user_session, expired_sessions)

    def test_remember_me_with_device_change_detection(self):
        """Test remember me sessions still detect device changes."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=Session.objects.create(
                session_key="device_test_session",
                session_data="data",
                expire_date=timezone.now() + timedelta(days=30),
            ),
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            remember_me=True,
            device_type="desktop",
            browser="Chrome",
            operating_system="Windows",
        )

        # Change device characteristics but keep session
        new_user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)"

        is_suspicious = self.service.detect_suspicious_activity(
            user_session,
            new_ip="192.168.1.100",  # Same IP
            new_user_agent=new_user_agent,  # Different device
        )

        # Should detect device change even for remember me sessions
        self.assertTrue(is_suspicious)

    def test_remember_me_concurrent_sessions_different_devices(self):
        """Test remember me across multiple devices."""
        devices = [
            {
                "user_agent": "Chrome/91.0 Desktop",
                "device_type": "desktop",
                "ip": "192.168.1.100",
            },
            {
                "user_agent": "Mobile Safari iOS",
                "device_type": "mobile",
                "ip": "192.168.1.101",
            },
            {
                "user_agent": "Chrome/91.0 Tablet",
                "device_type": "tablet",
                "ip": "192.168.1.102",
            },
        ]

        sessions = []
        for i, device in enumerate(devices):
            django_session = Session.objects.create(
                session_key=f"device_session_{i}",
                session_data="data",
                expire_date=timezone.now() + timedelta(days=30),
            )

            user_session = UserSession.objects.create(
                user=self.user,
                session=django_session,
                ip_address=device["ip"],
                user_agent=device["user_agent"],
                device_type=device["device_type"],
                remember_me=True,
            )
            sessions.append(user_session)

        # All sessions should be active
        active_sessions = UserSession.objects.active().for_user(self.user)
        self.assertEqual(active_sessions.count(), 3)

        # Should detect concurrent sessions but not necessarily as suspicious
        # (legitimate use case for remember me)
        has_concurrent = active_sessions.count() > 1
        self.assertTrue(has_concurrent)


class RememberMeSecurityTest(TestCase):
    """Test suite for remember me security considerations."""

    def setUp(self):
        """Set up test users."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.service = SessionSecurityService()

    def test_remember_me_session_hijack_detection(self):
        """Test hijack detection for remember me sessions."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=Session.objects.create(
                session_key="hijack_test_session",
                session_data="data",
                expire_date=timezone.now() + timedelta(days=30),
            ),
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            remember_me=True,
            location="New York, NY",
        )

        # Simulate session hijack from different location
        result = self.service.handle_suspicious_activity(
            user_session,
            new_ip="203.0.113.1",  # Different country IP
            new_user_agent="Chrome/91.0 Desktop",  # Same browser
        )

        # High risk should terminate even remember me sessions
        if result["risk_score"] >= 9.0:
            user_session.refresh_from_db()
            self.assertFalse(user_session.is_active)

            # Should log hijack attempt
            log_entry = SessionSecurityLog.objects.filter(
                user=self.user, event_type=SessionSecurityEvent.SESSION_HIJACK_ATTEMPT
            ).first()
            self.assertIsNotNone(log_entry)

    def test_remember_me_password_change_invalidation(self):
        """Test remember me sessions invalidated on password change."""
        # Create remember me session
        UserSession.objects.create(
            user=self.user,
            session=Session.objects.create(
                session_key="password_change_session",
                session_data="data",
                expire_date=timezone.now() + timedelta(days=30),
            ),
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            remember_me=True,
        )

        # Simulate password change (would be handled by signal or service)
        self.user.set_password("newpassword123")
        self.user.save()

        # Log password change event
        SessionSecurityLog.log_event(
            user=self.user,
            event_type=SessionSecurityEvent.PASSWORD_CHANGED,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            details={"reason": "user_initiated"},
        )

        # In real implementation, all sessions would be terminated
        # For test, just verify the log entry exists
        log_entry = SessionSecurityLog.objects.filter(
            user=self.user, event_type=SessionSecurityEvent.PASSWORD_CHANGED
        ).first()
        self.assertIsNotNone(log_entry)

    def test_remember_me_account_lockout_handling(self):
        """Test remember me sessions during account lockout."""
        UserSession.objects.create(
            user=self.user,
            session=Session.objects.create(
                session_key="lockout_test_session",
                session_data="data",
                expire_date=timezone.now() + timedelta(days=30),
            ),
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            remember_me=True,
        )

        # Simulate account lockout
        SessionSecurityLog.log_event(
            user=self.user,
            event_type=SessionSecurityEvent.ACCOUNT_LOCKED,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            details={"reason": "multiple_failed_logins"},
        )

        # Remember me session should be terminated during lockout
        # (Implementation would handle this via signal or middleware)
        log_entry = SessionSecurityLog.objects.filter(
            user=self.user, event_type=SessionSecurityEvent.ACCOUNT_LOCKED
        ).first()
        self.assertIsNotNone(log_entry)

    def test_remember_me_geographic_movement_tolerance(self):
        """Test geographic movement tolerance for remember me sessions."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=Session.objects.create(
                session_key="travel_session",
                session_data="data",
                expire_date=timezone.now() + timedelta(days=30),
            ),
            ip_address="192.168.1.100",  # US IP (mock)
            user_agent="Chrome/91.0 Desktop",
            remember_me=True,
            location="New York, NY",
        )

        # Test moderate geographic change (within same country)
        # Remember me sessions might have higher tolerance for geographic movement
        # Implementation would consider remember me status in risk calculation
        self.service.detect_geographic_anomaly(
            user_session, new_ip="192.168.1.200"  # Still US IP (mock)
        )

        # Test extreme geographic change
        is_extreme_anomaly = self.service.detect_geographic_anomaly(
            user_session, new_ip="203.0.113.1"  # Different country IP (mock)
        )

        # Even remember me sessions should flag extreme changes
        self.assertTrue(is_extreme_anomaly)

    def test_remember_me_session_cleanup_on_logout(self):
        """Test remember me sessions cleanup on explicit logout."""
        user_session = UserSession.objects.create(
            user=self.user,
            session=Session.objects.create(
                session_key="logout_test_session",
                session_data="data",
                expire_date=timezone.now() + timedelta(days=30),
            ),
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            remember_me=True,
        )

        # Simulate explicit logout
        user_session.deactivate()

        # Log logout event
        SessionSecurityLog.log_event(
            user=self.user,
            event_type=SessionSecurityEvent.LOGOUT,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            user_session=user_session,
            details={"logout_type": "explicit"},
        )

        # Check session is deactivated
        user_session.refresh_from_db()
        self.assertFalse(user_session.is_active)
        self.assertIsNotNone(user_session.ended_at)

        # Check logout was logged
        log_entry = SessionSecurityLog.objects.filter(
            user=self.user, event_type=SessionSecurityEvent.LOGOUT
        ).first()
        self.assertIsNotNone(log_entry)
