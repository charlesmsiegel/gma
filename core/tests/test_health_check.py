"""
Tests for the health_check management command and core functionality.
"""

from io import StringIO
from unittest.mock import MagicMock, patch

import redis
from django.core.cache import caches
from django.core.management import call_command
from django.db import connections
from django.test import TestCase, override_settings

from core.models import HealthCheckLog


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
)
class HealthCheckCommandTest(TestCase):
    """Test the health_check management command."""

    def setUp(self):
        """Set up test fixtures."""
        self.stdout = StringIO()
        self.stderr = StringIO()

    @patch("core.management.commands.health_check.settings")
    def test_successful_health_check_both_services(self, mock_settings):
        """Test successful health check for both database and Redis."""
        # Mock settings to return predictable values
        mock_settings.DATABASES = {
            "default": {
                "NAME": "test_db",
                "HOST": "localhost",
                "PORT": "5432",
                "USER": "test_user",
            }
        }
        mock_settings.CACHES = {"default": {"LOCATION": "redis://localhost:6379/0"}}

        call_command("health_check", stdout=self.stdout, stderr=self.stderr)

        output = self.stdout.getvalue()
        self.assertIn("Testing database connection...", output)
        self.assertIn("✅ Database connection: OK", output)
        self.assertIn("Testing Redis connection...", output)
        self.assertIn("✅ Redis connection: OK", output)
        self.assertIn("✅ All health checks passed!", output)

    @patch("core.management.commands.health_check.settings")
    def test_database_only_option(self, mock_settings):
        """Test --database option to check database only."""
        mock_settings.DATABASES = {
            "default": {
                "NAME": "test_db",
                "HOST": "localhost",
                "PORT": "5432",
                "USER": "test_user",
            }
        }

        call_command(
            "health_check", database=True, stdout=self.stdout, stderr=self.stderr
        )

        output = self.stdout.getvalue()
        self.assertIn("Testing database connection...", output)
        self.assertIn("✅ Database connection: OK", output)
        self.assertNotIn("Testing Redis connection...", output)
        self.assertIn("✅ All health checks passed!", output)

    @patch("core.management.commands.health_check.settings")
    def test_redis_only_option(self, mock_settings):
        """Test --redis option to check Redis only."""
        mock_settings.CACHES = {"default": {"LOCATION": "redis://localhost:6379/0"}}

        call_command("health_check", redis=True, stdout=self.stdout, stderr=self.stderr)

        output = self.stdout.getvalue()
        self.assertNotIn("Testing database connection...", output)
        self.assertIn("Testing Redis connection...", output)
        self.assertIn("✅ Redis connection: OK", output)
        self.assertIn("✅ All health checks passed!", output)

    @patch("core.management.commands.health_check.settings")
    def test_logging_option_success(self, mock_settings):
        """Test --log option creates database records on success."""
        # Mock settings
        mock_settings.DATABASES = {
            "default": {
                "NAME": "test_db",
                "HOST": "localhost",
                "PORT": "5432",
                "USER": "test_user",
            }
        }
        mock_settings.CACHES = {"default": {"LOCATION": "redis://localhost:6379/0"}}

        # Ensure no existing logs
        HealthCheckLog.objects.all().delete()

        call_command("health_check", log=True, stdout=self.stdout, stderr=self.stderr)

        # Check that logs were created
        db_logs = HealthCheckLog.objects.filter(service="database")
        redis_logs = HealthCheckLog.objects.filter(service="redis")

        self.assertEqual(db_logs.count(), 1)
        self.assertEqual(redis_logs.count(), 1)

        db_log = db_logs.first()
        redis_log = redis_logs.first()

        self.assertEqual(db_log.status, "success")
        self.assertEqual(redis_log.status, "success")
        self.assertIn("test_db", db_log.details)
        # In test, we might not have Redis URL, just check it has some details
        self.assertTrue(len(redis_log.details) > 0)

    @patch("core.management.commands.health_check.connections")
    def test_database_connection_failure(self, mock_connections):
        """Test database connection failure scenario."""
        # Mock database connection to raise an exception
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Connection refused")
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connections.__getitem__.return_value = mock_connection

        with self.assertRaises(SystemExit) as cm:
            call_command(
                "health_check", database=True, stdout=self.stdout, stderr=self.stderr
            )

        self.assertEqual(cm.exception.code, 1)
        output = self.stdout.getvalue()
        self.assertIn("❌ Database connection: Failed", output)
        self.assertIn("Connection refused", output)
        self.assertIn("❌ Some health checks failed!", output)

    @patch("core.management.commands.health_check.connections")
    def test_database_connection_failure_with_logging(self, mock_connections):
        """Test database connection failure with logging enabled."""
        # Mock database connection to raise an exception
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Connection refused")
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connections.__getitem__.return_value = mock_connection

        # Clear existing logs
        HealthCheckLog.objects.all().delete()

        with self.assertRaises(SystemExit):
            call_command(
                "health_check",
                database=True,
                log=True,
                stdout=self.stdout,
                stderr=self.stderr,
            )

        # Check that failure was logged
        db_logs = HealthCheckLog.objects.filter(service="database")
        self.assertEqual(db_logs.count(), 1)

        db_log = db_logs.first()
        self.assertEqual(db_log.status, "failure")
        self.assertIn("Connection refused", db_log.details)

    @patch("core.management.commands.health_check.caches")
    def test_redis_connection_failure(self, mock_caches):
        """Test Redis connection failure scenario."""
        # Mock Redis cache to raise an exception
        mock_cache = MagicMock()
        mock_cache.set.side_effect = Exception("Redis connection failed")
        mock_caches.__getitem__.return_value = mock_cache

        with self.assertRaises(SystemExit) as cm:
            call_command(
                "health_check", redis=True, stdout=self.stdout, stderr=self.stderr
            )

        self.assertEqual(cm.exception.code, 1)
        output = self.stdout.getvalue()
        self.assertIn("❌ Redis connection: Failed", output)
        self.assertIn("Redis connection failed", output)
        self.assertIn("❌ Some health checks failed!", output)

    @patch("core.management.commands.health_check.caches")
    def test_redis_connection_failure_with_logging(self, mock_caches):
        """Test Redis connection failure with logging enabled."""
        # Mock Redis cache to raise an exception
        mock_cache = MagicMock()
        mock_cache.set.side_effect = Exception("Redis connection failed")
        mock_caches.__getitem__.return_value = mock_cache

        # Clear existing logs
        HealthCheckLog.objects.all().delete()

        with self.assertRaises(SystemExit):
            call_command(
                "health_check",
                redis=True,
                log=True,
                stdout=self.stdout,
                stderr=self.stderr,
            )

        # Check that failure was logged
        redis_logs = HealthCheckLog.objects.filter(service="redis")
        self.assertEqual(redis_logs.count(), 1)

        redis_log = redis_logs.first()
        self.assertEqual(redis_log.status, "failure")
        self.assertIn("Redis connection failed", redis_log.details)

    @patch("core.management.commands.health_check.connections")
    def test_database_unexpected_result(self, mock_connections):
        """Test database connection with unexpected query result."""
        # Mock database connection to return unexpected result
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (2,)  # Should be (1,)
        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connections.__getitem__.return_value = mock_connection

        with self.assertRaises(SystemExit) as cm:
            call_command(
                "health_check", database=True, stdout=self.stdout, stderr=self.stderr
            )

        self.assertEqual(cm.exception.code, 1)
        output = self.stdout.getvalue()
        self.assertIn("❌ Database connection: Failed (unexpected result)", output)

    @patch("core.management.commands.health_check.caches")
    def test_redis_cache_test_failure(self, mock_caches):
        """Test Redis connection where cache test fails."""
        # Mock Redis cache where set works but get returns wrong value
        mock_cache = MagicMock()
        mock_cache.set.return_value = None
        mock_cache.get.return_value = "wrong_value"  # Should be "ok"
        mock_caches.__getitem__.return_value = mock_cache

        with self.assertRaises(SystemExit) as cm:
            call_command(
                "health_check", redis=True, stdout=self.stdout, stderr=self.stderr
            )

        self.assertEqual(cm.exception.code, 1)
        output = self.stdout.getvalue()
        self.assertIn("❌ Redis connection: Failed (cache test failed)", output)

    @patch("core.management.commands.health_check.settings")
    def test_health_check_displays_connection_info(self, mock_settings):
        """Test that health check displays connection information."""
        mock_settings.DATABASES = {
            "default": {
                "NAME": "test_db",
                "HOST": "localhost",
                "PORT": "5432",
                "USER": "test_user",
            }
        }
        mock_settings.CACHES = {"default": {"LOCATION": "redis://localhost:6379/0"}}

        call_command("health_check", stdout=self.stdout, stderr=self.stderr)

        output = self.stdout.getvalue()
        # Database info
        self.assertIn("📊 Database: test_db", output)
        self.assertIn("🏠 Host: localhost:5432", output)
        self.assertIn("👤 User: test_user", output)

        # Redis info
        self.assertIn("✅ Redis connection: OK", output)

    @patch("core.management.commands.health_check.settings")
    @patch("redis.Redis")
    def test_redis_info_gathering_failure(self, mock_redis, mock_settings):
        """Test that Redis info gathering failure doesn't break the health check."""
        mock_settings.CACHES = {"default": {"LOCATION": "redis://localhost:6379/0"}}

        # Mock Redis.info() to raise an exception
        mock_redis_instance = MagicMock()
        mock_redis_instance.info.side_effect = Exception("Info failed")
        mock_redis.return_value = mock_redis_instance

        # Health check should still pass even if Redis info gathering fails
        call_command("health_check", redis=True, stdout=self.stdout, stderr=self.stderr)

        output = self.stdout.getvalue()
        self.assertIn("✅ Redis connection: OK", output)
        self.assertIn("✅ All health checks passed!", output)


class HealthCheckLogModelTest(TestCase):
    """Test the HealthCheckLog model."""

    def test_model_creation(self):
        """Test creating HealthCheckLog instances."""
        log = HealthCheckLog.objects.create(
            service="database", status="success", details="Test connection successful"
        )

        self.assertEqual(log.service, "database")
        self.assertEqual(log.status, "success")
        self.assertEqual(log.details, "Test connection successful")
        self.assertIsNotNone(log.timestamp)

    def test_model_string_representation(self):
        """Test the string representation of HealthCheckLog."""
        log = HealthCheckLog.objects.create(
            service="redis", status="failure", details="Connection timeout"
        )

        expected = f"redis - failure at {log.timestamp}"
        self.assertEqual(str(log), expected)

    def test_model_ordering(self):
        """Test that logs are ordered by timestamp (newest first)."""
        # Create multiple logs
        log1 = HealthCheckLog.objects.create(
            service="database", status="success", details="First log"
        )
        log2 = HealthCheckLog.objects.create(
            service="redis", status="success", details="Second log"
        )
        log3 = HealthCheckLog.objects.create(
            service="database", status="failure", details="Third log"
        )

        # Get all logs (should be ordered by timestamp desc)
        logs = list(HealthCheckLog.objects.all())

        self.assertEqual(logs[0], log3)  # Most recent first
        self.assertEqual(logs[1], log2)
        self.assertEqual(logs[2], log1)  # Oldest last

    def test_model_choices(self):
        """Test that model field choices are properly defined."""
        # Test service choices
        log = HealthCheckLog()
        service_choices = dict(log._meta.get_field("service").choices)
        self.assertEqual(service_choices["database"], "Database")
        self.assertEqual(service_choices["redis"], "Redis")

        # Test status choices
        status_choices = dict(log._meta.get_field("status").choices)
        self.assertEqual(status_choices["success"], "Success")
        self.assertEqual(status_choices["failure"], "Failure")


class HealthCheckLogAdminTest(TestCase):
    """Test the HealthCheckLog admin interface."""

    def setUp(self):
        """Set up test fixtures."""
        from django.contrib.admin.sites import site

        from core.admin import HealthCheckLogAdmin
        from core.models import HealthCheckLog

        self.admin_class = HealthCheckLogAdmin
        self.admin_instance = self.admin_class(HealthCheckLog, site)

    def test_admin_registration(self):
        """Test that HealthCheckLog is properly registered in admin."""
        from django.contrib.admin.sites import site

        from core.models import HealthCheckLog

        # Check that the model is registered
        self.assertIn(HealthCheckLog, site._registry)

    def test_list_display_configuration(self):
        """Test admin list display configuration."""
        expected_list_display = ["timestamp", "service", "status", "short_details"]
        self.assertEqual(list(self.admin_instance.list_display), expected_list_display)

    def test_list_filter_configuration(self):
        """Test admin list filter configuration."""
        expected_list_filter = ["service", "status", "timestamp"]
        self.assertEqual(list(self.admin_instance.list_filter), expected_list_filter)

    def test_search_fields_configuration(self):
        """Test admin search fields configuration."""
        expected_search_fields = ["details"]
        self.assertEqual(
            list(self.admin_instance.search_fields), expected_search_fields
        )

    def test_readonly_fields_configuration(self):
        """Test admin readonly fields configuration."""
        expected_readonly_fields = ["timestamp"]
        self.assertEqual(
            list(self.admin_instance.readonly_fields), expected_readonly_fields
        )

    def test_ordering_configuration(self):
        """Test admin ordering configuration."""
        expected_ordering = ["-timestamp"]
        self.assertEqual(list(self.admin_instance.ordering), expected_ordering)

    def test_short_details_method_long_text(self):
        """Test short_details method with long text."""
        log = HealthCheckLog.objects.create(
            service="database",
            status="success",
            details="This is a very long details text that should be truncated in the admin interface because it exceeds fifty characters",
        )

        result = self.admin_instance.short_details(log)
        self.assertEqual(len(result), 50)  # 47 chars + "..."
        self.assertTrue(result.endswith("..."))
        self.assertEqual(result, "This is a very long details text that should be...")

    def test_short_details_method_short_text(self):
        """Test short_details method with short text."""
        log = HealthCheckLog.objects.create(
            service="redis", status="failure", details="Short details text"
        )

        result = self.admin_instance.short_details(log)
        self.assertEqual(result, "Short details text")

    def test_short_details_description(self):
        """Test short_details method description."""
        self.assertEqual(self.admin_instance.short_details.short_description, "Details")
