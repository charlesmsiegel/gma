"""
Tests for EmailVerification model functionality.

Tests the standalone EmailVerification model for Issue #135:
- user: ForeignKey(User, on_delete=CASCADE)
- token: CharField(max_length=64, unique=True)
- created_at: DateTimeField(auto_now_add=True)
- expires_at: DateTimeField()
- verified_at: DateTimeField(null=True, blank=True)
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from users.models import EmailVerification

User = get_user_model()


class EmailVerificationModelTest(TestCase):
    """Test the EmailVerification model structure and basic functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_email_verification_model_fields(self):
        """Test that EmailVerification model has required fields."""
        # Create an EmailVerification instance
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Check field existence and types
        self.assertEqual(verification.user, self.user)
        self.assertEqual(verification.token, "test_token_123")
        self.assertIsNotNone(verification.created_at)
        self.assertIsNotNone(verification.expires_at)
        self.assertIsNone(verification.verified_at)

    def test_user_foreign_key_properties(self):
        """Test user ForeignKey field properties."""
        field = EmailVerification._meta.get_field("user")

        self.assertEqual(field.__class__.__name__, "ForeignKey")
        self.assertEqual(field.related_model, User)
        self.assertEqual(field.remote_field.on_delete.__name__, "CASCADE")

    def test_token_field_properties(self):
        """Test token field properties."""
        field = EmailVerification._meta.get_field("token")

        self.assertEqual(field.__class__.__name__, "CharField")
        self.assertEqual(field.max_length, 64)
        self.assertTrue(field.unique)

    def test_created_at_field_properties(self):
        """Test created_at field properties."""
        field = EmailVerification._meta.get_field("created_at")

        self.assertEqual(field.__class__.__name__, "DateTimeField")
        self.assertTrue(field.auto_now_add)

    def test_expires_at_field_properties(self):
        """Test expires_at field properties."""
        field = EmailVerification._meta.get_field("expires_at")

        self.assertEqual(field.__class__.__name__, "DateTimeField")
        self.assertFalse(getattr(field, "auto_now_add", False))
        self.assertFalse(getattr(field, "auto_now", False))

    def test_verified_at_field_properties(self):
        """Test verified_at field properties."""
        field = EmailVerification._meta.get_field("verified_at")

        self.assertEqual(field.__class__.__name__, "DateTimeField")
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_created_at_auto_populated(self):
        """Test that created_at is automatically set."""
        before_creation = timezone.now()

        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        after_creation = timezone.now()

        self.assertGreaterEqual(verification.created_at, before_creation)
        self.assertLessEqual(verification.created_at, after_creation)

    def test_string_representation(self):
        """Test string representation of EmailVerification."""
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Should include user and token info
        str_repr = str(verification)
        self.assertIn(self.user.username, str_repr)
        # Token should be truncated for security
        self.assertNotIn("test_token_123", str_repr)


class EmailVerificationTokenTest(TestCase):
    """Test token-related functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_token_uniqueness_constraint(self):
        """Test that tokens must be unique across all EmailVerification records."""
        token = "unique_token_123"

        # Create first verification
        EmailVerification.objects.create(
            user=self.user,
            token=token,
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Create second user
        user2 = User.objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="TestPass123!",
        )

        # Try to create verification with same token
        with self.assertRaises(IntegrityError):
            EmailVerification.objects.create(
                user=user2,
                token=token,  # Same token
                expires_at=timezone.now() + timedelta(hours=24),
            )

    def test_generate_unique_token_class_method(self):
        """Test class method to generate unique tokens."""
        # This method should exist
        self.assertTrue(hasattr(EmailVerification, "generate_unique_token"))

        token = EmailVerification.generate_unique_token()

        # Should be a string
        self.assertIsInstance(token, str)
        # Should be reasonable length
        self.assertGreater(len(token), 16)
        self.assertLessEqual(len(token), 64)

    def test_generate_unique_token_avoids_collisions(self):
        """Test that generate_unique_token avoids collisions."""
        # Create a verification with a known token
        existing_token = "existing_token_123"
        EmailVerification.objects.create(
            user=self.user,
            token=existing_token,
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Mock secrets.token_urlsafe to return existing token first, then unique one
        unique_token = "unique_token_456"
        with patch("secrets.token_urlsafe") as mock_token:
            mock_token.side_effect = [existing_token, unique_token]

            new_token = EmailVerification.generate_unique_token()

            # Should return the second (unique) token
            self.assertEqual(new_token, unique_token)
            # Should have called token generation twice
            self.assertEqual(mock_token.call_count, 2)

    def test_token_max_length_validation(self):
        """Test that tokens respect max_length constraint."""
        long_token = "a" * 65  # Longer than 64 chars

        verification = EmailVerification(
            user=self.user,
            token=long_token,
            expires_at=timezone.now() + timedelta(hours=24),
        )

        with self.assertRaises(ValidationError):
            verification.full_clean()


class EmailVerificationExpiryTest(TestCase):
    """Test expiry-related functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_is_expired_method_not_expired(self):
        """Test is_expired method for non-expired verification."""
        future_expiry = timezone.now() + timedelta(hours=1)
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=future_expiry,
        )

        self.assertFalse(verification.is_expired())

    def test_is_expired_method_expired(self):
        """Test is_expired method for expired verification."""
        past_expiry = timezone.now() - timedelta(hours=1)
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=past_expiry,
        )

        self.assertTrue(verification.is_expired())

    def test_is_expired_method_exactly_at_expiry(self):
        """Test is_expired method at exact expiry time."""
        now = timezone.now()
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=now,
        )

        # At exact expiry time, should be considered expired
        with patch("django.utils.timezone.now", return_value=now):
            self.assertTrue(verification.is_expired())

    def test_create_for_user_class_method(self):
        """Test class method to create verification for user."""
        # This method should exist
        self.assertTrue(hasattr(EmailVerification, "create_for_user"))

        verification = EmailVerification.create_for_user(self.user)

        self.assertEqual(verification.user, self.user)
        self.assertIsNotNone(verification.token)
        self.assertIsNotNone(verification.expires_at)
        self.assertIsNone(verification.verified_at)

        # Should expire in 24 hours by default
        expected_expiry = timezone.now() + timedelta(hours=24)
        # Allow 1 minute tolerance for test execution time
        self.assertAlmostEqual(
            verification.expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=60,  # 60 seconds tolerance
        )

    def test_create_for_user_custom_expiry_hours(self):
        """Test create_for_user with custom expiry hours."""
        custom_hours = 48
        verification = EmailVerification.create_for_user(
            self.user, expiry_hours=custom_hours
        )

        expected_expiry = timezone.now() + timedelta(hours=custom_hours)
        self.assertAlmostEqual(
            verification.expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=60,  # 60 seconds tolerance
        )

    def test_get_time_until_expiry_method(self):
        """Test method to get time until expiry."""
        future_expiry = timezone.now() + timedelta(hours=2)
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=future_expiry,
        )

        time_until_expiry = verification.get_time_until_expiry()

        self.assertIsInstance(time_until_expiry, timedelta)
        # Should be close to 2 hours
        self.assertAlmostEqual(
            time_until_expiry.total_seconds(),
            7200,  # 2 hours in seconds
            delta=60,  # 60 seconds tolerance
        )

    def test_get_time_until_expiry_expired(self):
        """Test get_time_until_expiry for expired verification."""
        past_expiry = timezone.now() - timedelta(hours=1)
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=past_expiry,
        )

        time_until_expiry = verification.get_time_until_expiry()

        # Should be negative timedelta
        self.assertLess(time_until_expiry.total_seconds(), 0)


class EmailVerificationVerificationTest(TestCase):
    """Test verification-related functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_mark_verified_method(self):
        """Test method to mark verification as completed."""
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        before_verification = timezone.now()
        verification.mark_verified()
        after_verification = timezone.now()

        # Should set verified_at timestamp
        self.assertIsNotNone(verification.verified_at)
        self.assertGreaterEqual(verification.verified_at, before_verification)
        self.assertLessEqual(verification.verified_at, after_verification)

    def test_is_verified_method(self):
        """Test method to check if verification is completed."""
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Should not be verified initially
        self.assertFalse(verification.is_verified())

        # Should be verified after marking
        verification.mark_verified()
        self.assertTrue(verification.is_verified())

    def test_verify_method_success(self):
        """Test verify method with valid token."""
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Verify should succeed
        result = verification.verify("test_token_123")

        self.assertTrue(result)
        self.assertTrue(verification.is_verified())
        self.assertIsNotNone(verification.verified_at)

    def test_verify_method_wrong_token(self):
        """Test verify method with wrong token."""
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Verify should fail
        result = verification.verify("wrong_token")

        self.assertFalse(result)
        self.assertFalse(verification.is_verified())
        self.assertIsNone(verification.verified_at)

    def test_verify_method_expired_token(self):
        """Test verify method with expired token."""
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=timezone.now() - timedelta(hours=1),  # Expired
        )

        # Verify should fail even with correct token
        result = verification.verify("test_token_123")

        self.assertFalse(result)
        self.assertFalse(verification.is_verified())
        self.assertIsNone(verification.verified_at)

    def test_verify_method_already_verified(self):
        """Test verify method on already verified token."""
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Verify once
        result1 = verification.verify("test_token_123")
        first_verified_at = verification.verified_at

        # Try to verify again
        result2 = verification.verify("test_token_123")

        # Both should succeed, but verified_at shouldn't change
        self.assertTrue(result1)
        self.assertTrue(result2)
        self.assertEqual(verification.verified_at, first_verified_at)


class EmailVerificationQuerySetTest(TestCase):
    """Test custom QuerySet methods for EmailVerification."""

    def setUp(self):
        """Set up test data with various verification states."""
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="TestPass123!",
        )
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="TestPass123!",
        )

        # Active (not expired, not verified)
        self.active_verification = EmailVerification.objects.create(
            user=self.user1,
            token="active_token_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Expired (not verified)
        self.expired_verification = EmailVerification.objects.create(
            user=self.user2,
            token="expired_token_123",
            expires_at=timezone.now() - timedelta(hours=1),
        )

        # Verified
        self.verified_verification = EmailVerification.objects.create(
            user=self.user1,
            token="verified_token_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )
        self.verified_verification.mark_verified()

    def test_active_queryset_method(self):
        """Test QuerySet method to get active verifications."""
        active_verifications = EmailVerification.objects.active()

        self.assertIn(self.active_verification, active_verifications)
        self.assertNotIn(self.expired_verification, active_verifications)
        # Verified ones should still be included if not expired
        self.assertIn(self.verified_verification, active_verifications)

    def test_expired_queryset_method(self):
        """Test QuerySet method to get expired verifications."""
        expired_verifications = EmailVerification.objects.expired()

        self.assertNotIn(self.active_verification, expired_verifications)
        self.assertIn(self.expired_verification, expired_verifications)
        self.assertNotIn(self.verified_verification, expired_verifications)

    def test_verified_queryset_method(self):
        """Test QuerySet method to get verified verifications."""
        verified_verifications = EmailVerification.objects.verified()

        self.assertNotIn(self.active_verification, verified_verifications)
        self.assertNotIn(self.expired_verification, verified_verifications)
        self.assertIn(self.verified_verification, verified_verifications)

    def test_pending_queryset_method(self):
        """Test QuerySet method to get pending verifications."""
        pending_verifications = EmailVerification.objects.pending()

        # Should include active but not verified
        self.assertIn(self.active_verification, pending_verifications)
        self.assertNotIn(self.expired_verification, pending_verifications)
        self.assertNotIn(self.verified_verification, pending_verifications)

    def test_for_user_queryset_method(self):
        """Test QuerySet method to get verifications for specific user."""
        user1_verifications = EmailVerification.objects.for_user(self.user1)
        user2_verifications = EmailVerification.objects.for_user(self.user2)

        # user1 has active and verified
        self.assertEqual(user1_verifications.count(), 2)
        self.assertIn(self.active_verification, user1_verifications)
        self.assertIn(self.verified_verification, user1_verifications)

        # user2 has only expired
        self.assertEqual(user2_verifications.count(), 1)
        self.assertIn(self.expired_verification, user2_verifications)

    def test_cleanup_expired_method(self):
        """Test method to clean up old expired verifications."""
        # Create very old expired verification
        very_old_user = User.objects.create_user(
            username="very_old_user",
            email="very_old@example.com",
            password="TestPass123!",
        )
        very_old_verification = EmailVerification.objects.create(
            user=very_old_user,
            token="very_old_token",
            expires_at=timezone.now() - timedelta(days=31),  # Very old
        )

        initial_count = EmailVerification.objects.count()

        # Clean up expired verifications
        cleaned_count = EmailVerification.objects.cleanup_expired()

        # Should have cleaned up the very old one
        self.assertGreater(cleaned_count, 0)
        self.assertLess(EmailVerification.objects.count(), initial_count)

        # Very old verification should be deleted
        self.assertFalse(
            EmailVerification.objects.filter(id=very_old_verification.id).exists()
        )


class EmailVerificationCascadeTest(TestCase):
    """Test CASCADE behavior when user is deleted."""

    def test_user_deletion_cascades_to_verifications(self):
        """Test that deleting user deletes associated verifications."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Create multiple verifications for user
        verification1 = EmailVerification.objects.create(
            user=user,
            token="token1",
            expires_at=timezone.now() + timedelta(hours=24),
        )
        verification2 = EmailVerification.objects.create(
            user=user,
            token="token2",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Delete user
        user.delete()

        # Verifications should be deleted too
        self.assertFalse(EmailVerification.objects.filter(id=verification1.id).exists())
        self.assertFalse(EmailVerification.objects.filter(id=verification2.id).exists())


class EmailVerificationManagerTest(TestCase):
    """Test custom manager methods."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_create_for_user_manager_method(self):
        """Test manager method to create verification for user."""
        verification = EmailVerification.create_for_user(self.user)

        self.assertEqual(verification.user, self.user)
        self.assertIsNotNone(verification.token)
        self.assertGreater(len(verification.token), 16)
        self.assertIsNotNone(verification.expires_at)
        self.assertIsNone(verification.verified_at)

    def test_get_by_token_manager_method(self):
        """Test manager method to get verification by token."""
        verification = EmailVerification.objects.create(
            user=self.user,
            token="test_token_123",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Should find the verification
        found = EmailVerification.objects.get_by_token("test_token_123")
        self.assertEqual(found, verification)

        # Should return None for non-existent token
        not_found = EmailVerification.objects.get_by_token("nonexistent_token")
        self.assertIsNone(not_found)

    def test_invalidate_user_verifications_manager_method(self):
        """Test manager method to invalidate all user verifications."""
        # Create multiple verifications
        verification1 = EmailVerification.objects.create(
            user=self.user,
            token="token1",
            expires_at=timezone.now() + timedelta(hours=24),
        )
        verification2 = EmailVerification.objects.create(
            user=self.user,
            token="token2",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Invalidate all verifications for user
        EmailVerification.objects.invalidate_user_verifications(self.user)

        # Should set expires_at to past time for all user verifications
        verification1.refresh_from_db()
        verification2.refresh_from_db()

        self.assertTrue(verification1.is_expired())
        self.assertTrue(verification2.is_expired())


class EmailVerificationValidationTest(TransactionTestCase):
    """Test validation and constraint enforcement."""

    def test_cannot_create_verification_without_user(self):
        """Test that EmailVerification requires a user."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EmailVerification.objects.create(
                    token="test_token",
                    expires_at=timezone.now() + timedelta(hours=24),
                )

    def test_auto_generates_token_when_missing(self):
        """Test that EmailVerification auto-generates token when not provided."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Create verification without providing token - should auto-generate
        verification = EmailVerification.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=24),
            # No token provided - should be auto-generated
        )

        # Should have auto-generated a token
        self.assertIsNotNone(verification.token)
        self.assertGreater(len(verification.token), 16)  # Should be a reasonable length

    def test_auto_generates_expires_at_when_missing(self):
        """Test that EmailVerification auto-generates expires_at when not provided."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        before_creation = timezone.now()

        # Create verification without providing expires_at - should auto-generate
        verification = EmailVerification.objects.create(
            user=user,
            token="test_token",
            # No expires_at provided - should be auto-generated
        )

        # Should have auto-generated expires_at (24 hours from creation)
        self.assertIsNotNone(verification.expires_at)
        expected_expiry = before_creation + timedelta(hours=24)
        # Allow 1 minute tolerance
        self.assertAlmostEqual(
            verification.expires_at.timestamp(), expected_expiry.timestamp(), delta=60
        )

    def test_token_uniqueness_across_users(self):
        """Test that token uniqueness is enforced across all users."""
        user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="TestPass123!",
        )
        user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="TestPass123!",
        )

        token = "shared_token_123"

        # First verification should succeed
        EmailVerification.objects.create(
            user=user1,
            token=token,
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Second verification with same token should fail
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EmailVerification.objects.create(
                    user=user2,
                    token=token,  # Duplicate token
                    expires_at=timezone.now() + timedelta(hours=24),
                )
