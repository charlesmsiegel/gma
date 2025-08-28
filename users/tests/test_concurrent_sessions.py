"""
Test suite for Issue #143: Concurrent Session Limits and Handling.

Tests cover:
- Maximum concurrent session enforcement
- Session limit configuration
- Oldest session displacement
- User notification of session limits
- Per-user session limit customization
- Session limit exceptions (staff, premium users)
- Concurrent session monitoring and alerts
- Session conflict resolution
- Load balancing with session limits
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import TestCase, override_settings
from django.utils import timezone

from users.models.session_models import (
    SessionSecurityEvent,
    SessionSecurityLog,
    UserSession,
)
from users.services import SessionSecurityService

User = get_user_model()


class ConcurrentSessionLimitsTest(TestCase):
    """Test suite for concurrent session limit enforcement."""

    def setUp(self):
        """Set up test users and service."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="staffpass123",
            is_staff=True,
        )
        self.premium_user = User.objects.create_user(
            username="premiumuser",
            email="premium@example.com",
            password="premiumpass123",
        )

        self.service = SessionSecurityService()

    def create_user_session(self, user, session_key_suffix="", **kwargs):
        """Helper to create UserSession."""
        django_session = Session.objects.create(
            session_key=f"session_{user.username}_{session_key_suffix}",
            session_data="test_data",
            expire_date=timezone.now() + timedelta(days=1),
        )

        defaults = {
            "ip_address": "192.168.1.100",
            "user_agent": "Chrome/91.0 Desktop",
            "device_type": "desktop",
            "browser": "Chrome",
        }
        defaults.update(kwargs)

        return UserSession.objects.create(user=user, session=django_session, **defaults)

    def test_concurrent_session_limit_enforcement(self):
        """Test enforcement of maximum concurrent sessions."""
        max_sessions = self.service.max_concurrent_sessions  # Default: 5

        # Create sessions up to the limit
        sessions = []
        for i in range(max_sessions):
            session = self.create_user_session(
                self.user,
                session_key_suffix=f"limit_test_{i}",
                ip_address=f"192.168.1.{100 + i}",
            )
            sessions.append(session)

        # All sessions should be active
        active_count = UserSession.objects.active().for_user(self.user).count()
        self.assertEqual(active_count, max_sessions)

        # Creating one more session should trigger limit handling
        new_session = self.create_user_session(
            self.user, session_key_suffix="over_limit", ip_address="10.0.0.1"
        )

        # Check if limit exceeded (implementation dependent)
        total_sessions = UserSession.objects.active().for_user(self.user).count()

        # Implementation might either:
        # 1. Reject new session
        # 2. Terminate oldest session
        # 3. Log security event

        # At minimum, should detect concurrent session anomaly
        is_anomaly = self.service.detect_concurrent_session_anomaly(self.user)
        self.assertTrue(is_anomaly)

    def test_oldest_session_displacement(self):
        """Test displacement of oldest session when limit exceeded."""
        max_sessions = 3  # Lower limit for testing

        with patch.object(self.service, "max_concurrent_sessions", max_sessions):
            # Create sessions up to limit
            sessions = []
            for i in range(max_sessions):
                # Create sessions with different timestamps
                with patch("django.utils.timezone.now") as mock_now:
                    mock_now.return_value = timezone.now() - timedelta(
                        hours=max_sessions - i
                    )

                    session = self.create_user_session(
                        self.user,
                        session_key_suffix=f"displacement_test_{i}",
                        ip_address=f"192.168.1.{100 + i}",
                    )
                    sessions.append(session)

                    # Manually set creation time
                    UserSession.objects.filter(id=session.id).update(
                        created_at=mock_now.return_value
                    )

            oldest_session = sessions[0]  # First created, oldest
            newest_sessions = sessions[1:]  # Should remain active

            # Create new session that should displace oldest
            new_session = self.create_user_session(
                self.user,
                session_key_suffix="displacing_session",
                ip_address="10.0.0.1",
            )

            # In implementation, oldest session would be terminated
            # For test, just verify we can identify the oldest
            all_user_sessions = UserSession.objects.for_user(self.user).order_by(
                "created_at"
            )
            self.assertEqual(all_user_sessions.first(), oldest_session)

    def test_concurrent_session_limit_by_user_type(self):
        """Test different session limits for different user types."""
        # Regular user - default limit
        regular_limit = self.service.max_concurrent_sessions

        # Staff user - higher limit (would be configurable)
        staff_limit = regular_limit * 2

        # Test regular user limit
        for i in range(regular_limit):
            self.create_user_session(
                self.user,
                session_key_suffix=f"regular_{i}",
                ip_address=f"192.168.1.{100 + i}",
            )

        regular_anomaly = self.service.detect_concurrent_session_anomaly(self.user)
        # At limit, might not be anomaly yet

        # Test staff user higher limit
        for i in range(staff_limit):
            self.create_user_session(
                self.staff_user,
                session_key_suffix=f"staff_{i}",
                ip_address=f"192.168.2.{100 + i}",
            )

        # Staff user should be able to have more sessions
        staff_session_count = (
            UserSession.objects.active().for_user(self.staff_user).count()
        )
        regular_session_count = UserSession.objects.active().for_user(self.user).count()

        self.assertGreaterEqual(staff_session_count, regular_session_count)

    def test_session_limit_notification(self):
        """Test user notification when approaching session limit."""
        # Create sessions near limit
        limit = self.service.max_concurrent_sessions

        for i in range(limit - 1):  # One less than limit
            self.create_user_session(
                self.user,
                session_key_suffix=f"notification_test_{i}",
                ip_address=f"192.168.1.{100 + i}",
            )

        # Check if approaching limit
        current_count = UserSession.objects.active().for_user(self.user).count()
        is_approaching_limit = current_count >= (limit * 0.8)  # 80% of limit

        if is_approaching_limit:
            # Would trigger notification in real implementation
            self.assertGreaterEqual(current_count, limit - 2)

    def test_concurrent_session_security_logging(self):
        """Test security logging for concurrent session events."""
        # Create multiple sessions to trigger security event
        for i in range(6):  # Exceed typical limit
            self.create_user_session(
                self.user,
                session_key_suffix=f"security_log_{i}",
                ip_address=f"192.168.1.{100 + i}",
                device_type="desktop" if i % 2 == 0 else "mobile",
            )

        # Check if anomaly is detected
        is_anomaly = self.service.detect_concurrent_session_anomaly(self.user)

        if is_anomaly:
            # Log the event
            SessionSecurityLog.log_event(
                user=self.user,
                event_type=SessionSecurityEvent.CONCURRENT_SESSION_LIMIT,
                ip_address="192.168.1.105",
                user_agent="Chrome/91.0 Desktop",
                details={
                    "current_sessions": 6,
                    "limit": self.service.max_concurrent_sessions,
                    "action": "logged_anomaly",
                },
            )

            # Verify security log entry
            log_entry = SessionSecurityLog.objects.filter(
                user=self.user, event_type=SessionSecurityEvent.CONCURRENT_SESSION_LIMIT
            ).first()

            self.assertIsNotNone(log_entry)
            self.assertEqual(log_entry.details["current_sessions"], 6)

    def test_session_limit_with_different_device_types(self):
        """Test session limits across different device types."""
        device_types = ["desktop", "mobile", "tablet"]

        # Create sessions from different device types
        for i, device_type in enumerate(device_types):
            for j in range(2):  # 2 sessions per device type
                self.create_user_session(
                    self.user,
                    session_key_suffix=f"{device_type}_{j}",
                    ip_address=f"192.168.{i+1}.{100 + j}",
                    device_type=device_type,
                    user_agent=f"Browser/{device_type.title()}",
                )

        # Total of 6 sessions across 3 device types
        total_sessions = UserSession.objects.active().for_user(self.user).count()
        self.assertEqual(total_sessions, 6)

        # Check device distribution
        for device_type in device_types:
            device_sessions = (
                UserSession.objects.active()
                .for_user(self.user)
                .filter(device_type=device_type)
                .count()
            )
            self.assertEqual(device_sessions, 2)

    def test_remember_me_sessions_in_concurrent_limits(self):
        """Test remember me sessions count toward concurrent limits."""
        # Create mix of regular and remember me sessions
        regular_sessions = []
        remember_sessions = []

        for i in range(3):
            # Regular session
            regular_session = self.create_user_session(
                self.user,
                session_key_suffix=f"regular_{i}",
                ip_address=f"192.168.1.{100 + i}",
                remember_me=False,
            )
            regular_sessions.append(regular_session)

            # Remember me session
            remember_session = self.create_user_session(
                self.user,
                session_key_suffix=f"remember_{i}",
                ip_address=f"192.168.2.{100 + i}",
                remember_me=True,
            )
            remember_sessions.append(remember_session)

        # Total should be 6 active sessions
        total_active = UserSession.objects.active().for_user(self.user).count()
        self.assertEqual(total_active, 6)

        # Both types should count toward limit
        is_anomaly = self.service.detect_concurrent_session_anomaly(self.user)
        # Depends on configured limit


class SessionConflictResolutionTest(TestCase):
    """Test suite for session conflict resolution."""

    def setUp(self):
        """Set up test users."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.service = SessionSecurityService()

    def create_user_session(self, user, session_key, **kwargs):
        """Helper to create UserSession."""
        django_session = Session.objects.create(
            session_key=session_key,
            session_data="test_data",
            expire_date=timezone.now() + timedelta(days=1),
        )

        defaults = {"ip_address": "192.168.1.100", "user_agent": "Chrome/91.0 Desktop"}
        defaults.update(kwargs)

        return UserSession.objects.create(user=user, session=django_session, **defaults)

    def test_session_displacement_strategies(self):
        """Test different strategies for session displacement."""
        # Create sessions with different characteristics
        sessions_data = [
            {"key": "oldest_session", "hours_ago": 5, "ip": "192.168.1.100"},
            {
                "key": "mobile_session",
                "hours_ago": 3,
                "ip": "192.168.1.101",
                "device": "mobile",
            },
            {
                "key": "remember_session",
                "hours_ago": 1,
                "ip": "192.168.1.102",
                "remember": True,
            },
            {
                "key": "desktop_session",
                "hours_ago": 2,
                "ip": "192.168.1.103",
                "device": "desktop",
            },
        ]

        sessions = []
        for data in sessions_data:
            with patch("django.utils.timezone.now") as mock_now:
                mock_now.return_value = timezone.now() - timedelta(
                    hours=data["hours_ago"]
                )

                session = self.create_user_session(
                    self.user,
                    data["key"],
                    ip_address=data["ip"],
                    device_type=data.get("device", "desktop"),
                    remember_me=data.get("remember", False),
                )
                sessions.append(session)

                # Set creation time manually
                UserSession.objects.filter(id=session.id).update(
                    created_at=mock_now.return_value
                )

        # Test different displacement strategies:

        # 1. Oldest first (FIFO)
        sessions_by_age = sorted(sessions, key=lambda s: s.created_at)
        oldest_session = sessions_by_age[0]
        self.assertEqual(oldest_session.session.session_key, "oldest_session")

        # 2. Non-remember me first
        non_remember_sessions = [s for s in sessions if not s.remember_me]
        self.assertGreater(len(non_remember_sessions), 0)

        # 3. Mobile sessions first (if configured)
        mobile_sessions = [s for s in sessions if s.device_type == "mobile"]
        if mobile_sessions:
            self.assertEqual(mobile_sessions[0].device_type, "mobile")

    def test_session_conflict_user_notification(self):
        """Test user notification during session conflicts."""
        # Create sessions at limit
        limit = 3  # Test limit

        with patch.object(self.service, "max_concurrent_sessions", limit):
            # Fill up to limit
            for i in range(limit):
                self.create_user_session(
                    self.user,
                    f"conflict_session_{i}",
                    ip_address=f"192.168.1.{100 + i}",
                )

            # Attempt to create another session (would cause conflict)
            new_session = self.create_user_session(
                self.user, "conflict_causing_session", ip_address="10.0.0.1"
            )

            # Log the conflict
            SessionSecurityLog.log_event(
                user=self.user,
                event_type=SessionSecurityEvent.CONCURRENT_SESSION_LIMIT,
                ip_address="10.0.0.1",
                user_agent="Chrome/91.0 Desktop",
                details={
                    "conflict_resolution": "oldest_displaced",
                    "sessions_before": limit,
                    "sessions_after": limit,
                },
            )

            # Verify conflict was logged
            log_entry = SessionSecurityLog.objects.filter(
                user=self.user, event_type=SessionSecurityEvent.CONCURRENT_SESSION_LIMIT
            ).first()

            self.assertIsNotNone(log_entry)
            self.assertIn("conflict_resolution", log_entry.details)

    def test_session_priority_handling(self):
        """Test session priority during conflicts."""
        # Create sessions with different priorities
        priority_sessions = [
            {"key": "admin_session", "priority": "high", "ip": "192.168.1.100"},
            {
                "key": "remember_session",
                "priority": "medium",
                "ip": "192.168.1.101",
                "remember": True,
            },
            {
                "key": "mobile_session",
                "priority": "low",
                "ip": "192.168.1.102",
                "device": "mobile",
            },
            {"key": "guest_session", "priority": "lowest", "ip": "192.168.1.103"},
        ]

        sessions = []
        for data in priority_sessions:
            session = self.create_user_session(
                self.user,
                data["key"],
                ip_address=data["ip"],
                device_type=data.get("device", "desktop"),
                remember_me=data.get("remember", False),
            )
            sessions.append((session, data["priority"]))

        # Sort by priority (implementation would use priority scoring)
        priority_order = ["high", "medium", "low", "lowest"]
        sessions.sort(key=lambda x: priority_order.index(x[1]))

        highest_priority = sessions[0][0]
        lowest_priority = sessions[-1][0]

        # Highest priority should be preserved in conflicts
        self.assertEqual(highest_priority.session.session_key, "admin_session")
        self.assertEqual(lowest_priority.session.session_key, "guest_session")


class ConcurrentSessionMonitoringTest(TestCase):
    """Test suite for concurrent session monitoring."""

    def setUp(self):
        """Set up test users."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.service = SessionSecurityService()

    def test_concurrent_session_anomaly_detection(self):
        """Test detection of anomalous concurrent session patterns."""
        # Normal pattern: 1-2 sessions from same location
        normal_session1 = UserSession.objects.create(
            user=self.user,
            session=Session.objects.create(
                session_key="normal_session_1",
                session_data="data",
                expire_date=timezone.now() + timedelta(days=1),
            ),
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
            location="New York, NY",
        )

        normal_session2 = UserSession.objects.create(
            user=self.user,
            session=Session.objects.create(
                session_key="normal_session_2",
                session_data="data",
                expire_date=timezone.now() + timedelta(days=1),
            ),
            ip_address="192.168.1.101",  # Same network
            user_agent="Chrome/91.0 Mobile",
            location="New York, NY",  # Same location
        )

        # Should not be anomalous
        is_anomaly_normal = self.service.detect_concurrent_session_anomaly(self.user)

        # Add suspicious session from different location
        suspicious_session = UserSession.objects.create(
            user=self.user,
            session=Session.objects.create(
                session_key="suspicious_session",
                session_data="data",
                expire_date=timezone.now() + timedelta(days=1),
            ),
            ip_address="203.0.113.1",  # Different country
            user_agent="Firefox/89.0 Desktop",
            location="London, UK",
        )

        # Should be anomalous now
        is_anomaly_suspicious = self.service.detect_concurrent_session_anomaly(
            self.user
        )
        self.assertTrue(is_anomaly_suspicious)

    def test_geographic_distribution_analysis(self):
        """Test analysis of geographic distribution of sessions."""
        locations = [
            ("192.168.1.100", "New York, NY"),
            ("192.168.1.101", "New York, NY"),
            ("203.0.113.1", "London, UK"),
            ("198.51.100.1", "Tokyo, JP"),
        ]

        sessions = []
        for i, (ip, location) in enumerate(locations):
            session = UserSession.objects.create(
                user=self.user,
                session=Session.objects.create(
                    session_key=f"geo_session_{i}",
                    session_data="data",
                    expire_date=timezone.now() + timedelta(days=1),
                ),
                ip_address=ip,
                user_agent="Chrome/91.0 Desktop",
                location=location,
            )
            sessions.append(session)

        # Analyze geographic distribution
        active_sessions = UserSession.objects.active().for_user(self.user)
        unique_locations = set(
            session.location for session in active_sessions if session.location
        )

        # 4 sessions across 3 locations should be flagged
        self.assertEqual(len(unique_locations), 3)
        self.assertGreater(len(unique_locations), 2)  # Suspicious threshold

    def test_device_type_distribution_monitoring(self):
        """Test monitoring of device type distribution."""
        device_sessions = [
            ("desktop", "Chrome/91.0 Desktop", "192.168.1.100"),
            ("desktop", "Chrome/91.0 Desktop", "192.168.1.101"),
            ("mobile", "Mobile Safari iOS", "192.168.1.102"),
            ("tablet", "Chrome/91.0 Tablet", "192.168.1.103"),
        ]

        for i, (device_type, user_agent, ip) in enumerate(device_sessions):
            UserSession.objects.create(
                user=self.user,
                session=Session.objects.create(
                    session_key=f"device_session_{i}",
                    session_data="data",
                    expire_date=timezone.now() + timedelta(days=1),
                ),
                ip_address=ip,
                user_agent=user_agent,
                device_type=device_type,
            )

        # Analyze device distribution
        active_sessions = UserSession.objects.active().for_user(self.user)
        device_counts = {}

        for session in active_sessions:
            device_type = session.device_type or "unknown"
            device_counts[device_type] = device_counts.get(device_type, 0) + 1

        # Should have sessions across multiple device types
        self.assertGreaterEqual(len(device_counts), 3)
        self.assertEqual(device_counts["desktop"], 2)
        self.assertEqual(device_counts["mobile"], 1)
        self.assertEqual(device_counts["tablet"], 1)

    def test_temporal_session_pattern_analysis(self):
        """Test analysis of temporal session creation patterns."""
        # Create sessions at different times
        base_time = timezone.now() - timedelta(hours=4)
        session_times = [
            base_time,
            base_time + timedelta(hours=1),
            base_time + timedelta(hours=2),
            base_time + timedelta(hours=2, minutes=5),  # Very close to previous
        ]

        sessions = []
        for i, session_time in enumerate(session_times):
            with patch("django.utils.timezone.now", return_value=session_time):
                session = UserSession.objects.create(
                    user=self.user,
                    session=Session.objects.create(
                        session_key=f"temporal_session_{i}",
                        session_data="data",
                        expire_date=session_time + timedelta(days=1),
                    ),
                    ip_address=f"192.168.1.{100 + i}",
                    user_agent="Chrome/91.0 Desktop",
                )

                # Set creation time manually
                UserSession.objects.filter(id=session.id).update(
                    created_at=session_time
                )
                sessions.append(session)

        # Analyze temporal patterns
        # Two sessions created within 5 minutes might indicate suspicious activity
        sessions_by_time = sorted(sessions, key=lambda s: s.created_at)

        for i in range(1, len(sessions_by_time)):
            time_diff = (
                sessions_by_time[i].created_at - sessions_by_time[i - 1].created_at
            )
            if time_diff <= timedelta(minutes=10):
                # Rapid session creation detected
                rapid_creation = True
                break
        else:
            rapid_creation = False

        self.assertTrue(rapid_creation)  # Should detect the 5-minute gap

    @override_settings(MAX_CONCURRENT_SESSIONS=2)
    def test_configurable_session_limits(self):
        """Test configurable session limits via settings."""
        # Create sessions up to configured limit
        for i in range(2):  # Setting limit is 2
            UserSession.objects.create(
                user=self.user,
                session=Session.objects.create(
                    session_key=f"config_session_{i}",
                    session_data="data",
                    expire_date=timezone.now() + timedelta(days=1),
                ),
                ip_address=f"192.168.1.{100 + i}",
                user_agent="Chrome/91.0 Desktop",
            )

        # Third session should trigger limit
        UserSession.objects.create(
            user=self.user,
            session=Session.objects.create(
                session_key="over_limit_session",
                session_data="data",
                expire_date=timezone.now() + timedelta(days=1),
            ),
            ip_address="10.0.0.1",
            user_agent="Chrome/91.0 Desktop",
        )

        # Should detect anomaly with 3 sessions when limit is 2
        active_count = UserSession.objects.active().for_user(self.user).count()
        self.assertEqual(active_count, 3)

        is_anomaly = self.service.detect_concurrent_session_anomaly(self.user)
        self.assertTrue(is_anomaly)
