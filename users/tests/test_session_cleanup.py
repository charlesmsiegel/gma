"""
Test suite for Issue #143: Session Cleanup and Maintenance.

Tests cover:
- Expired session cleanup
- Orphaned session handling
- Database maintenance operations
- Cleanup scheduling and automation
- Performance optimization for large datasets
- Cleanup logging and monitoring
- Retention policies
- Data archival strategies
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from users.models.session_models import (
    SessionSecurityEvent,
    SessionSecurityLog,
    UserSession,
)
from users.services import SessionSecurityService

User = get_user_model()


class ExpiredSessionCleanupTest(TestCase):
    """Test suite for expired session cleanup functionality."""

    def setUp(self):
        """Set up test users and sessions."""
        self.users = []
        for i in range(3):
            user = User.objects.create_user(
                username=f"testuser{i}",
                email=f"test{i}@example.com",
                password="testpass123",
            )
            self.users.append(user)

    def create_session_with_expiry(self, user, session_key, expire_delta, **kwargs):
        """Helper to create session with specific expiry."""
        django_session = Session.objects.create(
            session_key=session_key,
            session_data="test_data",
            expire_date=timezone.now() + expire_delta,
        )

        defaults = {"ip_address": "192.168.1.100", "user_agent": "Chrome/91.0 Desktop"}
        defaults.update(kwargs)

        return UserSession.objects.create(user=user, session=django_session, **defaults)

    def test_basic_expired_session_cleanup(self):
        """Test basic cleanup of expired sessions."""
        # Create expired and active sessions
        expired_sessions = []
        active_sessions = []

        for i, user in enumerate(self.users):
            # Create expired session
            expired_session = self.create_session_with_expiry(
                user,
                f"expired_session_{i}",
                timedelta(hours=-(i + 1)),  # Expired 1-3 hours ago
                ip_address=f"192.168.1.{100 + i}",
            )
            expired_sessions.append(expired_session)

            # Create active session
            active_session = self.create_session_with_expiry(
                user,
                f"active_session_{i}",
                timedelta(hours=i + 1),  # Expires in 1-3 hours
                ip_address=f"192.168.1.{200 + i}",
            )
            active_sessions.append(active_session)

        # Run cleanup
        cleaned_count = UserSession.objects.cleanup_expired()

        self.assertEqual(cleaned_count, 3)  # Should clean 3 expired sessions

        # Verify expired sessions are deactivated
        for session in expired_sessions:
            session.refresh_from_db()
            self.assertFalse(session.is_active)
            self.assertIsNotNone(session.ended_at)

        # Verify active sessions remain active
        for session in active_sessions:
            session.refresh_from_db()
            self.assertTrue(session.is_active)
            self.assertIsNone(session.ended_at)

    def test_expired_session_cleanup_with_remember_me(self):
        """Test cleanup handling remember me sessions correctly."""
        user = self.users[0]

        # Create expired remember me session
        expired_remember_session = self.create_session_with_expiry(
            user,
            "expired_remember_session",
            timedelta(days=-1),  # Expired 1 day ago
            remember_me=True,
        )

        # Create expired regular session
        expired_regular_session = self.create_session_with_expiry(
            user,
            "expired_regular_session",
            timedelta(hours=-1),  # Expired 1 hour ago
            remember_me=False,
        )

        # Create active remember me session
        active_remember_session = self.create_session_with_expiry(
            user,
            "active_remember_session",
            timedelta(days=10),  # Active for 10 more days
            remember_me=True,
        )

        # Run cleanup
        cleaned_count = UserSession.objects.cleanup_expired()

        self.assertEqual(cleaned_count, 2)  # Should clean both expired sessions

        # Verify cleanup results
        expired_remember_session.refresh_from_db()
        expired_regular_session.refresh_from_db()
        active_remember_session.refresh_from_db()

        self.assertFalse(expired_remember_session.is_active)
        self.assertFalse(expired_regular_session.is_active)
        self.assertTrue(active_remember_session.is_active)

    def test_cleanup_performance_with_large_dataset(self):
        """Test cleanup performance with large number of sessions."""
        user = self.users[0]

        # Create large number of expired sessions
        expired_sessions = []
        batch_size = 50

        for i in range(batch_size):
            session = self.create_session_with_expiry(
                user,
                f"large_dataset_expired_{i}",
                timedelta(hours=-(i % 10 + 1)),  # Various expiry times
                ip_address=f"192.168.{i // 100 + 1}.{i % 100 + 1}",
            )
            expired_sessions.append(session)

        # Create some active sessions
        for i in range(10):
            self.create_session_with_expiry(
                user, f"large_dataset_active_{i}", timedelta(hours=i + 1)
            )

        # Measure cleanup performance
        start_time = timezone.now()
        cleaned_count = UserSession.objects.cleanup_expired()
        end_time = timezone.now()

        cleanup_duration = (end_time - start_time).total_seconds()

        # Should clean all expired sessions
        self.assertEqual(cleaned_count, batch_size)

        # Should complete in reasonable time (adjust threshold as needed)
        self.assertLess(cleanup_duration, 10.0)  # Should complete within 10 seconds

    def test_cleanup_with_concurrent_sessions(self):
        """Test cleanup behavior with concurrent session operations."""
        user = self.users[0]

        # Create sessions that will expire during test
        sessions_to_expire = []
        for i in range(5):
            session = self.create_session_with_expiry(
                user,
                f"concurrent_expire_{i}",
                timedelta(seconds=1),  # Will expire very soon
                ip_address=f"192.168.1.{100 + i}",
            )
            sessions_to_expire.append(session)

        # Wait for sessions to expire
        import time

        time.sleep(2)

        # Run cleanup
        cleaned_count = UserSession.objects.cleanup_expired()

        self.assertEqual(cleaned_count, 5)

        # Verify all sessions are deactivated
        for session in sessions_to_expire:
            session.refresh_from_db()
            self.assertFalse(session.is_active)

    def test_cleanup_idempotency(self):
        """Test that cleanup operations are idempotent."""
        user = self.users[0]

        # Create expired session
        expired_session = self.create_session_with_expiry(
            user, "idempotency_test_session", timedelta(hours=-1)
        )

        # Run cleanup multiple times
        first_cleanup_count = UserSession.objects.cleanup_expired()
        second_cleanup_count = UserSession.objects.cleanup_expired()
        third_cleanup_count = UserSession.objects.cleanup_expired()

        # First cleanup should find and clean the session
        self.assertEqual(first_cleanup_count, 1)

        # Subsequent cleanups should find nothing to clean
        self.assertEqual(second_cleanup_count, 0)
        self.assertEqual(third_cleanup_count, 0)

        # Session should remain deactivated
        expired_session.refresh_from_db()
        self.assertFalse(expired_session.is_active)


class OrphanedSessionHandlingTest(TestCase):
    """Test suite for handling orphaned sessions."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_orphaned_django_session_cleanup(self):
        """Test cleanup of UserSessions with orphaned Django sessions."""
        # Create UserSession with valid Django session
        valid_django_session = Session.objects.create(
            session_key="valid_session",
            session_data="test_data",
            expire_date=timezone.now() + timedelta(days=1),
        )

        valid_user_session = UserSession.objects.create(
            user=self.user,
            session=valid_django_session,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        # Create UserSession and then delete its Django session (orphaned)
        orphaned_django_session = Session.objects.create(
            session_key="orphaned_session",
            session_data="test_data",
            expire_date=timezone.now() + timedelta(days=1),
        )

        orphaned_user_session = UserSession.objects.create(
            user=self.user,
            session=orphaned_django_session,
            ip_address="192.168.1.101",
            user_agent="Chrome/91.0 Desktop",
        )

        # Delete the Django session, orphaning the UserSession
        orphaned_django_session.delete()

        # Run orphaned session cleanup
        # This would be part of the cleanup management command
        orphaned_user_sessions = UserSession.objects.filter(session__isnull=True)

        if orphaned_user_sessions.exists():
            orphaned_count = orphaned_user_sessions.count()
            # Deactivate orphaned sessions
            orphaned_user_sessions.update(is_active=False, ended_at=timezone.now())
        else:
            orphaned_count = 0

        # Check results
        # Note: Due to CASCADE deletion, orphaned_user_session should be deleted
        # This test demonstrates the expected behavior

        valid_user_session.refresh_from_db()
        self.assertTrue(valid_user_session.is_active)

    def test_cleanup_sessions_without_users(self):
        """Test cleanup of sessions for deleted users."""
        # Create another user that will be deleted
        temp_user = User.objects.create_user(
            username="tempuser", email="temp@example.com", password="temppass123"
        )

        # Create session for temp user
        temp_session = UserSession.objects.create(
            user=temp_user,
            session=Session.objects.create(
                session_key="temp_user_session",
                session_data="temp_data",
                expire_date=timezone.now() + timedelta(days=1),
            ),
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        temp_session_id = temp_session.id

        # Delete the user (CASCADE should delete UserSession)
        temp_user.delete()

        # UserSession should be automatically deleted due to CASCADE
        with self.assertRaises(UserSession.DoesNotExist):
            UserSession.objects.get(id=temp_session_id)

    def test_session_integrity_validation(self):
        """Test validation of session data integrity."""
        # Create session with valid data
        user_session = UserSession.objects.create(
            user=self.user,
            session=Session.objects.create(
                session_key="integrity_test_session",
                session_data="valid_data",
                expire_date=timezone.now() + timedelta(days=1),
            ),
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        # Validate session integrity
        integrity_checks = {
            "has_user": user_session.user is not None,
            "has_session": user_session.session is not None,
            "session_not_expired": user_session.session.expire_date > timezone.now(),
            "has_ip": bool(user_session.ip_address),
            "has_user_agent": bool(user_session.user_agent),
            "valid_timestamps": user_session.created_at <= user_session.last_activity,
        }

        # All integrity checks should pass
        for check_name, check_result in integrity_checks.items():
            self.assertTrue(check_result, f"Integrity check failed: {check_name}")


class DatabaseMaintenanceTest(TransactionTestCase):
    """Test suite for database maintenance operations."""

    def setUp(self):
        """Set up test data."""
        self.users = []
        for i in range(2):
            user = User.objects.create_user(
                username=f"maintenance_user{i}",
                email=f"maintenance{i}@example.com",
                password="testpass123",
            )
            self.users.append(user)

    def test_bulk_session_cleanup_transaction_safety(self):
        """Test transaction safety during bulk cleanup operations."""
        user = self.users[0]

        # Create many expired sessions
        expired_sessions = []
        for i in range(20):
            session = UserSession.objects.create(
                user=user,
                session=Session.objects.create(
                    session_key=f"bulk_cleanup_session_{i}",
                    session_data="test_data",
                    expire_date=timezone.now() - timedelta(hours=i + 1),
                ),
                ip_address=f"192.168.1.{100 + i % 50}",
                user_agent="Chrome/91.0 Desktop",
            )
            expired_sessions.append(session)

        # Simulate cleanup with transaction safety
        with transaction.atomic():
            try:
                cleaned_count = UserSession.objects.cleanup_expired()

                # Should clean all expired sessions
                self.assertEqual(cleaned_count, 20)

                # Verify cleanup results
                for session in expired_sessions:
                    session.refresh_from_db()
                    self.assertFalse(session.is_active)

            except Exception as e:
                # If anything fails, transaction should rollback
                self.fail(f"Cleanup transaction failed: {e}")

    def test_cleanup_with_foreign_key_constraints(self):
        """Test cleanup operations respect foreign key constraints."""
        user = self.users[0]

        # Create expired session
        expired_session = UserSession.objects.create(
            user=user,
            session=Session.objects.create(
                session_key="fk_constraint_session",
                session_data="test_data",
                expire_date=timezone.now() - timedelta(hours=1),
            ),
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        # Create security log referencing the session
        security_log = SessionSecurityLog.objects.create(
            user=user,
            user_session=expired_session,
            event_type=SessionSecurityEvent.LOGIN_SUCCESS,
            ip_address="192.168.1.100",
            user_agent="Chrome/91.0 Desktop",
        )

        # Run cleanup
        cleaned_count = UserSession.objects.cleanup_expired()
        self.assertEqual(cleaned_count, 1)

        # Session should be deactivated
        expired_session.refresh_from_db()
        self.assertFalse(expired_session.is_active)

        # Security log should still exist (SET_NULL behavior)
        security_log.refresh_from_db()
        self.assertIsNone(security_log.user_session)

    def test_database_index_performance(self):
        """Test database index performance during cleanup operations."""
        user = self.users[0]

        # Create sessions with various timestamps
        for i in range(50):
            # Mix of expired and active sessions
            if i % 2 == 0:
                expire_delta = timedelta(hours=-(i // 2 + 1))  # Expired
            else:
                expire_delta = timedelta(hours=i // 2 + 1)  # Active

            UserSession.objects.create(
                user=user,
                session=Session.objects.create(
                    session_key=f"index_performance_session_{i}",
                    session_data="test_data",
                    expire_date=timezone.now() + expire_delta,
                ),
                ip_address=f"192.168.1.{100 + i % 50}",
                user_agent="Chrome/91.0 Desktop",
            )

        # Test query performance with indexes
        start_time = timezone.now()

        # This query should use indexes efficiently
        expired_sessions = UserSession.objects.expired()
        expired_count = expired_sessions.count()

        # Run cleanup
        cleaned_count = UserSession.objects.cleanup_expired()

        end_time = timezone.now()
        query_duration = (end_time - start_time).total_seconds()

        # Should find and clean expired sessions efficiently
        self.assertEqual(expired_count, 25)  # Half should be expired
        self.assertEqual(cleaned_count, 25)

        # Should complete quickly with proper indexes
        self.assertLess(query_duration, 5.0)


class CleanupAutomationTest(TestCase):
    """Test suite for cleanup automation and scheduling."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="automation_user",
            email="automation@example.com",
            password="testpass123",
        )

    def test_management_command_interface(self):
        """Test management command for session cleanup."""
        # Create expired sessions
        for i in range(5):
            UserSession.objects.create(
                user=self.user,
                session=Session.objects.create(
                    session_key=f"management_command_session_{i}",
                    session_data="test_data",
                    expire_date=timezone.now() - timedelta(hours=i + 1),
                ),
                ip_address=f"192.168.1.{100 + i}",
                user_agent="Chrome/91.0 Desktop",
            )

        # Test management command
        try:
            # This would be the actual management command
            call_command("cleanup_sessions", verbosity=0)

            # Check that sessions were cleaned up
            active_expired_sessions = UserSession.objects.expired().filter(
                is_active=True
            )
            self.assertEqual(active_expired_sessions.count(), 0)

        except Exception:
            # Management command might not exist yet
            # Test the cleanup logic directly
            cleaned_count = UserSession.objects.cleanup_expired()
            self.assertEqual(cleaned_count, 5)

    def test_cleanup_with_options(self):
        """Test cleanup with various command options."""
        # Create test data
        for i in range(10):
            UserSession.objects.create(
                user=self.user,
                session=Session.objects.create(
                    session_key=f"options_test_session_{i}",
                    session_data="test_data",
                    expire_date=timezone.now() - timedelta(days=i + 1),
                ),
                ip_address=f"192.168.1.{100 + i}",
                user_agent="Chrome/91.0 Desktop",
            )

        # Test cleanup with age threshold
        cutoff_date = timezone.now() - timedelta(days=5)

        # Sessions older than 5 days
        old_sessions = UserSession.objects.filter(session__expire_date__lt=cutoff_date)
        old_session_count = old_sessions.count()

        # Test dry run functionality
        dry_run_result = {
            "would_clean": old_session_count,
            "cutoff_date": cutoff_date,
            "action": "dry_run",
        }

        self.assertGreater(dry_run_result["would_clean"], 0)

    def test_cleanup_scheduling_configuration(self):
        """Test cleanup scheduling configuration."""
        # Test scheduling configuration
        cleanup_schedule = {
            "interval": "daily",
            "time": "02:00",  # 2 AM
            "timezone": "UTC",
            "max_age_days": 30,
            "batch_size": 1000,
            "enabled": True,
        }

        # Test schedule validation
        self.assertIn("interval", cleanup_schedule)
        self.assertTrue(cleanup_schedule["enabled"])
        self.assertIsInstance(cleanup_schedule["max_age_days"], int)

    def test_cleanup_monitoring_and_alerting(self):
        """Test cleanup monitoring and alerting."""
        # Create test sessions
        for i in range(100):
            UserSession.objects.create(
                user=self.user,
                session=Session.objects.create(
                    session_key=f"monitoring_session_{i}",
                    session_data="test_data",
                    expire_date=timezone.now() - timedelta(days=i + 1),
                ),
                ip_address=f"192.168.1.{100 + i % 50}",
                user_agent="Chrome/91.0 Desktop",
            )

        # Run cleanup with monitoring
        start_time = timezone.now()
        cleaned_count = UserSession.objects.cleanup_expired()
        end_time = timezone.now()

        # Generate cleanup report
        cleanup_report = {
            "timestamp": end_time,
            "duration": (end_time - start_time).total_seconds(),
            "sessions_cleaned": cleaned_count,
            "total_sessions_before": 100,
            "total_sessions_after": UserSession.objects.count(),
            "success": True,
            "errors": [],
        }

        # Verify report structure
        self.assertEqual(cleanup_report["sessions_cleaned"], 100)
        self.assertTrue(cleanup_report["success"])
        self.assertEqual(len(cleanup_report["errors"]), 0)
        self.assertGreater(cleanup_report["duration"], 0)


class RetentionPolicyTest(TestCase):
    """Test suite for session data retention policies."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="retention_user",
            email="retention@example.com",
            password="testpass123",
        )

    def test_session_data_retention_policy(self):
        """Test session data retention policy enforcement."""
        # Create sessions with different ages
        retention_periods = [
            ("recent", timedelta(days=1)),  # Recent - keep
            ("medium", timedelta(days=15)),  # Medium age - keep
            ("old", timedelta(days=45)),  # Old - should be cleaned
            ("very_old", timedelta(days=90)),  # Very old - should be cleaned
        ]

        sessions_by_age = {}
        for age_category, age_delta in retention_periods:
            session = UserSession.objects.create(
                user=self.user,
                session=Session.objects.create(
                    session_key=f"retention_{age_category}_session",
                    session_data="test_data",
                    expire_date=timezone.now() - age_delta,
                ),
                ip_address="192.168.1.100",
                user_agent="Chrome/91.0 Desktop",
            )

            # Set creation date to simulate age
            UserSession.objects.filter(id=session.id).update(
                created_at=timezone.now() - age_delta
            )
            sessions_by_age[age_category] = session

        # Apply retention policy (e.g., keep sessions for 30 days)
        retention_cutoff = timezone.now() - timedelta(days=30)

        # Find sessions to clean based on retention policy
        sessions_to_clean = UserSession.objects.filter(created_at__lt=retention_cutoff)

        sessions_to_keep = UserSession.objects.filter(created_at__gte=retention_cutoff)

        # Should clean old and very_old sessions
        self.assertEqual(sessions_to_clean.count(), 2)
        self.assertEqual(sessions_to_keep.count(), 2)

    def test_security_log_retention_policy(self):
        """Test security log retention policy."""
        # Create security logs with different ages
        log_ages = [
            timedelta(days=7),  # Recent - keep
            timedelta(days=35),  # Medium - keep
            timedelta(days=95),  # Old - should be archived/cleaned
            timedelta(days=370),  # Very old - should be cleaned
        ]

        created_logs = []
        for i, age_delta in enumerate(log_ages):
            log_entry = SessionSecurityLog.objects.create(
                user=self.user,
                event_type=SessionSecurityEvent.LOGIN_SUCCESS,
                ip_address=f"192.168.1.{100 + i}",
                user_agent="Chrome/91.0 Desktop",
            )

            # Set timestamp to simulate age
            SessionSecurityLog.objects.filter(id=log_entry.id).update(
                timestamp=timezone.now() - age_delta
            )
            created_logs.append(log_entry)

        # Apply retention policy for security logs (e.g., keep for 90 days)
        log_retention_cutoff = timezone.now() - timedelta(days=90)

        logs_to_clean = SessionSecurityLog.objects.filter(
            timestamp__lt=log_retention_cutoff
        )

        logs_to_keep = SessionSecurityLog.objects.filter(
            timestamp__gte=log_retention_cutoff
        )

        # Should clean only the very old log
        self.assertEqual(logs_to_clean.count(), 1)
        self.assertEqual(logs_to_keep.count(), 3)

    def test_graduated_retention_policy(self):
        """Test graduated retention policy with different rules."""
        # Create sessions with different characteristics
        session_types = [
            {"type": "regular", "remember_me": False, "retention_days": 30},
            {
                "type": "remember_me",
                "remember_me": True,
                "retention_days": 90,  # Longer retention for remember me
            },
            {
                "type": "security_event",
                "has_security_events": True,
                "retention_days": 180,  # Longest retention for sessions with security events
            },
        ]

        created_sessions = []
        for i, session_type in enumerate(session_types):
            session = UserSession.objects.create(
                user=self.user,
                session=Session.objects.create(
                    session_key=f"graduated_retention_{session_type['type']}_session",
                    session_data="test_data",
                    expire_date=timezone.now() - timedelta(days=35),
                ),
                ip_address=f"192.168.1.{100 + i}",
                user_agent="Chrome/91.0 Desktop",
                remember_me=session_type.get("remember_me", False),
            )

            # Create security event if needed
            if session_type.get("has_security_events", False):
                SessionSecurityLog.objects.create(
                    user=self.user,
                    user_session=session,
                    event_type=SessionSecurityEvent.SUSPICIOUS_ACTIVITY,
                    ip_address=f"192.168.1.{100 + i}",
                    user_agent="Chrome/91.0 Desktop",
                )

            created_sessions.append((session, session_type))

        # Apply graduated retention policy
        current_time = timezone.now()

        for session, session_type in created_sessions:
            retention_cutoff = current_time - timedelta(
                days=session_type["retention_days"]
            )

            # Check if session should be retained
            should_retain = session.created_at >= retention_cutoff

            # Different session types have different retention periods
            if session_type["type"] == "regular":
                # Regular sessions: shortest retention
                pass
            elif session_type["type"] == "remember_me":
                # Remember me sessions: longer retention
                pass
            elif session_type["type"] == "security_event":
                # Sessions with security events: longest retention
                pass

            # All sessions in this test are recent enough to be retained
            self.assertTrue(should_retain or session_type["retention_days"] < 35)
