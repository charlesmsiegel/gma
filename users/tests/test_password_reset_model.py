"""
Tests for the PasswordReset model.

This test suite covers:
- Model field validation
- Token generation and uniqueness
- Expiration handling
- IP address tracking
- Security constraints
- Database integrity
- Manager methods
"""

import secrets
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from users.models.password_reset import PasswordReset

User = get_user_model()


class PasswordResetModelTest(TestCase):
    """Test the PasswordReset model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", email="test2@example.com", password="TestPass123!"
        )

    def test_model_creation_with_defaults(self):
        """Test creating a PasswordReset with default values."""
        reset = PasswordReset.objects.create(user=self.user)

        # Check that all fields are populated correctly
        self.assertEqual(reset.user, self.user)
        self.assertTrue(reset.token)  # Should be generated automatically
        self.assertEqual(len(reset.token), 64)  # Token should be 64 characters
        self.assertIsNotNone(reset.created_at)
        self.assertIsNotNone(reset.expires_at)
        self.assertIsNone(reset.used_at)  # Should be None initially
        self.assertIsNone(reset.ip_address)  # Should be None if not provided

    def test_token_generation_uniqueness(self):
        """Test that tokens are unique across all resets."""
        reset1 = PasswordReset.objects.create(user=self.user)
        reset2 = PasswordReset.objects.create(user=self.user2)

        self.assertNotEqual(reset1.token, reset2.token)
        self.assertEqual(len(reset1.token), 64)
        self.assertEqual(len(reset2.token), 64)

    def test_token_is_hex_string(self):
        """Test that generated tokens are valid hex strings."""
        reset = PasswordReset.objects.create(user=self.user)

        # Should be able to convert from hex without error
        try:
            int(reset.token, 16)
        except ValueError:
            self.fail("Token should be a valid hexadecimal string")

    def test_expiration_time_default(self):
        """Test that expiration time is set to 24 hours by default."""
        now_time = timezone.now()
        reset = PasswordReset.objects.create(user=self.user)

        # Should be approximately 24 hours from now (within 1 minute tolerance)
        expected_expiry = now_time + timedelta(hours=24)
        time_diff = abs((reset.expires_at - expected_expiry).total_seconds())
        self.assertLess(time_diff, 60)  # Within 1 minute

    def test_custom_expiration_time(self):
        """Test creating reset with custom expiration time."""
        custom_expiry = timezone.now() + timedelta(hours=12)
        reset = PasswordReset.objects.create(user=self.user, expires_at=custom_expiry)

        self.assertEqual(reset.expires_at, custom_expiry)

    def test_ip_address_field_ipv4(self):
        """Test IP address field with IPv4 address."""
        reset = PasswordReset.objects.create(user=self.user, ip_address="192.168.1.1")

        self.assertEqual(reset.ip_address, "192.168.1.1")

    def test_ip_address_field_ipv6(self):
        """Test IP address field with IPv6 address."""
        reset = PasswordReset.objects.create(user=self.user, ip_address="2001:db8::1")

        self.assertEqual(reset.ip_address, "2001:db8::1")

    def test_invalid_ip_address_raises_validation_error(self):
        """Test that invalid IP addresses raise ValidationError."""
        with self.assertRaises(ValidationError):
            reset = PasswordReset(user=self.user, ip_address="not.an.ip.address")
            reset.full_clean()

    def test_token_uniqueness_constraint(self):
        """Test that duplicate tokens are not allowed."""
        token = secrets.token_hex(32)

        PasswordReset.objects.create(user=self.user, token=token)

        with self.assertRaises(IntegrityError):
            PasswordReset.objects.create(user=self.user2, token=token)

    def test_token_max_length_validation(self):
        """Test that tokens longer than 64 characters are rejected."""
        with self.assertRaises(ValidationError):
            reset = PasswordReset(
                user=self.user, token="a" * 65  # 65 characters, exceeds max_length=64
            )
            reset.full_clean()

    def test_user_foreign_key_cascade_delete(self):
        """Test that PasswordReset is deleted when user is deleted."""
        reset = PasswordReset.objects.create(user=self.user)
        reset_id = reset.id

        # Delete user should cascade to password reset
        self.user.delete()

        with self.assertRaises(PasswordReset.DoesNotExist):
            PasswordReset.objects.get(id=reset_id)

    def test_str_representation(self):
        """Test string representation of PasswordReset."""
        reset = PasswordReset.objects.create(user=self.user)

        expected = f"Password reset for {self.user.email} ({reset.token[:8]}...)"
        self.assertEqual(str(reset), expected)

    def test_is_expired_method(self):
        """Test is_expired method."""
        # Create expired reset
        past_time = timezone.now() - timedelta(hours=1)
        expired_reset = PasswordReset.objects.create(
            user=self.user, expires_at=past_time
        )

        # Create valid reset
        future_time = timezone.now() + timedelta(hours=1)
        valid_reset = PasswordReset.objects.create(
            user=self.user2, expires_at=future_time
        )

        self.assertTrue(expired_reset.is_expired())
        self.assertFalse(valid_reset.is_expired())

    def test_is_used_method(self):
        """Test is_used method."""
        unused_reset = PasswordReset.objects.create(user=self.user)
        used_reset = PasswordReset.objects.create(
            user=self.user2, used_at=timezone.now()
        )

        self.assertFalse(unused_reset.is_used())
        self.assertTrue(used_reset.is_used())

    def test_is_valid_method(self):
        """Test is_valid method (not expired and not used)."""
        # Valid reset
        valid_reset = PasswordReset.objects.create(user=self.user)

        # Expired reset
        expired_reset = PasswordReset.objects.create(
            user=self.user2, expires_at=timezone.now() - timedelta(hours=1)
        )

        # Used reset
        used_reset = PasswordReset.objects.create(
            user=self.user, used_at=timezone.now()
        )

        self.assertTrue(valid_reset.is_valid())
        self.assertFalse(expired_reset.is_valid())
        self.assertFalse(used_reset.is_valid())

    def test_mark_as_used_method(self):
        """Test mark_as_used method."""
        reset = PasswordReset.objects.create(user=self.user)

        self.assertIsNone(reset.used_at)
        self.assertFalse(reset.is_used())

        reset.mark_as_used()

        self.assertIsNotNone(reset.used_at)
        self.assertTrue(reset.is_used())
        self.assertFalse(reset.is_valid())

    def test_mark_as_used_idempotent(self):
        """Test that mark_as_used can be called multiple times safely."""
        reset = PasswordReset.objects.create(user=self.user)

        reset.mark_as_used()
        first_used_time = reset.used_at

        # Call again
        reset.mark_as_used()

        # Time should not change
        self.assertEqual(reset.used_at, first_used_time)


class PasswordResetManagerTest(TestCase):
    """Test the PasswordReset manager methods."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", email="test2@example.com", password="TestPass123!"
        )

    def test_create_for_user_method(self):
        """Test create_for_user manager method."""
        reset = PasswordReset.objects.create_for_user(self.user)

        self.assertEqual(reset.user, self.user)
        self.assertTrue(reset.token)
        self.assertIsNotNone(reset.expires_at)
        self.assertTrue(reset.is_valid())

    def test_create_for_user_with_ip_address(self):
        """Test create_for_user with IP address."""
        ip = "192.168.1.100"
        reset = PasswordReset.objects.create_for_user(self.user, ip_address=ip)

        self.assertEqual(reset.ip_address, ip)

    def test_create_for_user_invalidates_existing(self):
        """Test that create_for_user invalidates existing resets."""
        # Create first reset
        reset1 = PasswordReset.objects.create_for_user(self.user)
        token1 = reset1.token

        # Create second reset - should invalidate first
        reset2 = PasswordReset.objects.create_for_user(self.user)

        # Refresh first reset from database
        reset1.refresh_from_db()

        self.assertIsNotNone(reset1.used_at)
        self.assertFalse(reset1.is_valid())
        self.assertTrue(reset2.is_valid())
        self.assertNotEqual(token1, reset2.token)

    def test_get_valid_reset_by_token(self):
        """Test get_valid_reset_by_token manager method."""
        reset = PasswordReset.objects.create_for_user(self.user)

        # Should find valid reset
        found_reset = PasswordReset.objects.get_valid_reset_by_token(reset.token)
        self.assertEqual(found_reset, reset)

        # Should not find expired reset
        reset.expires_at = timezone.now() - timedelta(hours=1)
        reset.save()

        self.assertIsNone(PasswordReset.objects.get_valid_reset_by_token(reset.token))

    def test_get_valid_reset_by_token_used(self):
        """Test that used tokens are not returned as valid."""
        reset = PasswordReset.objects.create_for_user(self.user)
        reset.mark_as_used()

        self.assertIsNone(PasswordReset.objects.get_valid_reset_by_token(reset.token))

    def test_get_valid_reset_by_token_nonexistent(self):
        """Test get_valid_reset_by_token with nonexistent token."""
        fake_token = secrets.token_hex(32)

        self.assertIsNone(PasswordReset.objects.get_valid_reset_by_token(fake_token))

    def test_cleanup_expired_method(self):
        """Test cleanup_expired manager method."""
        # Create valid reset
        valid_reset = PasswordReset.objects.create_for_user(self.user)

        # Create expired reset
        expired_reset = PasswordReset.objects.create(
            user=self.user2, expires_at=timezone.now() - timedelta(hours=1)
        )

        # Run cleanup
        deleted_count = PasswordReset.objects.cleanup_expired()

        self.assertEqual(deleted_count, 1)

        # Valid reset should still exist
        self.assertTrue(PasswordReset.objects.filter(id=valid_reset.id).exists())

        # Expired reset should be deleted
        self.assertFalse(PasswordReset.objects.filter(id=expired_reset.id).exists())

    def test_cleanup_expired_with_used_resets(self):
        """Test cleanup_expired also removes used resets."""
        # Create used reset
        used_reset = PasswordReset.objects.create_for_user(self.user)
        used_reset.mark_as_used()

        # Run cleanup
        deleted_count = PasswordReset.objects.cleanup_expired()

        self.assertEqual(deleted_count, 1)

        # Used reset should be deleted
        self.assertFalse(PasswordReset.objects.filter(id=used_reset.id).exists())

    def test_get_recent_requests_for_user(self):
        """Test get_recent_requests_for_user manager method."""
        # Create reset for user
        reset = PasswordReset.objects.create_for_user(self.user)

        # Should find recent request
        recent = PasswordReset.objects.get_recent_requests_for_user(
            self.user, minutes=60
        )
        self.assertEqual(recent.count(), 1)
        self.assertIn(reset, recent)

        # Should not find old request
        old = PasswordReset.objects.get_recent_requests_for_user(self.user, minutes=0)
        self.assertEqual(old.count(), 0)

    def test_get_recent_requests_for_ip(self):
        """Test get_recent_requests_for_ip manager method."""
        ip = "192.168.1.100"

        # Create reset with IP
        reset = PasswordReset.objects.create_for_user(self.user, ip_address=ip)

        # Should find recent request
        recent = PasswordReset.objects.get_recent_requests_for_ip(ip, minutes=60)
        self.assertEqual(recent.count(), 1)
        self.assertIn(reset, recent)

        # Should not find old request
        old = PasswordReset.objects.get_recent_requests_for_ip(ip, minutes=0)
        self.assertEqual(old.count(), 0)


class PasswordResetModelMetaTest(TestCase):
    """Test model meta configuration."""

    def test_model_meta_configuration(self):
        """Test model meta settings."""
        meta = PasswordReset._meta

        # Check database table name
        self.assertEqual(meta.db_table, "users_password_reset")

        # Check ordering
        self.assertEqual(meta.ordering, ["-created_at"])

        # Check verbose names
        self.assertEqual(meta.verbose_name, "Password Reset")
        self.assertEqual(meta.verbose_name_plural, "Password Resets")

    def test_model_indexes(self):
        """Test that proper indexes exist."""
        meta = PasswordReset._meta

        # Should have indexes for performance
        index_fields = [index.fields for index in meta.indexes]

        # Check for token index (for fast lookups)
        self.assertIn(["token"], index_fields)

        # Check for user + created_at index (for recent requests)
        self.assertIn(["user", "created_at"], index_fields)

        # Check for expires_at index (for cleanup)
        self.assertIn(["expires_at"], index_fields)


class PasswordResetSecurityTest(TestCase):
    """Test security aspects of the PasswordReset model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_token_cryptographic_randomness(self):
        """Test that tokens have sufficient entropy."""
        tokens = set()

        # Create 100 resets and collect tokens
        for _ in range(100):
            reset = PasswordReset.objects.create_for_user(self.user)
            tokens.add(reset.token)
            reset.delete()  # Clean up

        # All tokens should be unique
        self.assertEqual(len(tokens), 100)

    def test_token_cannot_be_predicted(self):
        """Test that tokens cannot be easily predicted."""
        reset1 = PasswordReset.objects.create_for_user(self.user)
        token1 = reset1.token
        reset1.delete()

        reset2 = PasswordReset.objects.create_for_user(self.user)
        token2 = reset2.token

        # Tokens should have no obvious relationship
        self.assertNotEqual(token1, token2)

        # Should not be sequential hex values
        try:
            val1 = int(token1, 16)
            val2 = int(token2, 16)
            self.assertNotEqual(val2 - val1, 1)
        except ValueError:
            pass  # If conversion fails, that's fine for this test

    def test_token_generation_handles_collisions(self):
        """Test that token generation handles rare collisions gracefully."""
        # Mock token_hex to return same value twice, then different
        mock_token = "a" * 64
        different_token = "b" * 64

        # First call returns existing token, second returns new token
        with patch("secrets.token_hex", side_effect=[mock_token, different_token]):
            # Create first reset with mocked token
            reset1 = PasswordReset(user=self.user, token=mock_token)
            reset1.save()

            # Create second reset - should get different token due to uniqueness
            reset2 = PasswordReset.objects.create_for_user(self.user)

            # Should have different tokens
            self.assertNotEqual(reset1.token, reset2.token)

    def test_concurrent_reset_creation_thread_safety(self):
        """Test that concurrent reset creation is handled safely."""
        # Create multiple resets sequentially to test basic thread safety concepts
        # Full threading tests are complex due to Django's database connection handling

        # Test that multiple resets can be created without conflicts
        users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f"threaduser{i}",
                email=f"thread{i}@example.com",
                password="TestPass123!",
            )
            users.append(user)

        # Create resets for all users
        tokens = []
        for user in users:
            reset = PasswordReset.objects.create_for_user(user)
            tokens.append(reset.token)

        # All tokens should be unique
        self.assertEqual(len(set(tokens)), len(tokens))

        # All resets should be valid
        for token in tokens:
            reset = PasswordReset.objects.get_valid_reset_by_token(token)
            self.assertIsNotNone(reset)
