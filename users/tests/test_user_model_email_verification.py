"""
Tests for User model email verification extensions.

Tests the new fields and functionality added to the User model for Issue #135:
- email_verified: BooleanField(default=False)
- email_verification_token: CharField(max_length=64, blank=True)
- email_verification_sent_at: DateTimeField(null=True, blank=True)
"""

import secrets
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

User = get_user_model()


class UserEmailVerificationFieldsTest(TestCase):
    """Test the new email verification fields on the User model."""

    def setUp(self):
        """Set up test data."""
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!",
        }

    def test_user_default_email_verification_fields(self):
        """Test that new email verification fields have correct default values."""
        user = User.objects.create_user(**self.user_data)

        # Check default values for new fields
        self.assertFalse(user.email_verified)
        self.assertEqual(user.email_verification_token, "")
        self.assertIsNone(user.email_verification_sent_at)

    def test_email_verified_field_type_and_default(self):
        """Test email_verified field properties."""
        user = User.objects.create_user(**self.user_data)

        # Field should be a BooleanField with default False
        field = User._meta.get_field("email_verified")
        self.assertEqual(field.__class__.__name__, "BooleanField")
        self.assertFalse(field.default)
        self.assertFalse(user.email_verified)

    def test_email_verification_token_field_properties(self):
        """Test email_verification_token field properties."""
        user = User.objects.create_user(**self.user_data)

        # Field should be a CharField with max_length=64, blank=True
        field = User._meta.get_field("email_verification_token")
        self.assertEqual(field.__class__.__name__, "CharField")
        self.assertEqual(field.max_length, 64)
        self.assertTrue(field.blank)
        self.assertEqual(user.email_verification_token, "")

    def test_email_verification_sent_at_field_properties(self):
        """Test email_verification_sent_at field properties."""
        user = User.objects.create_user(**self.user_data)

        # Field should be a DateTimeField with null=True, blank=True
        field = User._meta.get_field("email_verification_sent_at")
        self.assertEqual(field.__class__.__name__, "DateTimeField")
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        self.assertIsNone(user.email_verification_sent_at)

    def test_set_email_verified_true(self):
        """Test setting email_verified to True."""
        user = User.objects.create_user(**self.user_data)

        user.email_verified = True
        user.save()
        user.refresh_from_db()

        self.assertTrue(user.email_verified)

    def test_set_email_verification_token(self):
        """Test setting email_verification_token."""
        user = User.objects.create_user(**self.user_data)
        token = secrets.token_urlsafe(32)  # 43 chars base64url

        user.email_verification_token = token
        user.save()
        user.refresh_from_db()

        self.assertEqual(user.email_verification_token, token)

    def test_email_verification_token_max_length_validation(self):
        """Test that email_verification_token respects max_length constraint."""
        user = User.objects.create_user(**self.user_data)

        # Create a token longer than 64 characters
        long_token = "a" * 65
        user.email_verification_token = long_token

        # This should raise ValidationError during full_clean()
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_set_email_verification_sent_at(self):
        """Test setting email_verification_sent_at."""
        user = User.objects.create_user(**self.user_data)
        now = timezone.now()

        user.email_verification_sent_at = now
        user.save()
        user.refresh_from_db()

        self.assertEqual(user.email_verification_sent_at, now)

    def test_email_verification_fields_in_database(self):
        """Test that the new fields are properly saved to database."""
        token = secrets.token_urlsafe(32)
        sent_at = timezone.now()

        user = User.objects.create_user(**self.user_data)
        user.email_verified = True
        user.email_verification_token = token
        user.email_verification_sent_at = sent_at
        user.save()

        # Reload from database
        user_from_db = User.objects.get(id=user.id)

        self.assertTrue(user_from_db.email_verified)
        self.assertEqual(user_from_db.email_verification_token, token)
        self.assertEqual(user_from_db.email_verification_sent_at, sent_at)

    def test_multiple_users_different_verification_states(self):
        """Test that multiple users can have different verification states."""
        # Create verified user
        verified_user = User.objects.create_user(
            username="verified",
            email="verified@example.com",
            password="TestPass123!",
        )
        verified_user.email_verified = True
        verified_user.save()

        # Create unverified user with token
        unverified_user = User.objects.create_user(
            username="unverified",
            email="unverified@example.com",
            password="TestPass123!",
        )
        unverified_user.email_verification_token = secrets.token_urlsafe(32)
        unverified_user.email_verification_sent_at = timezone.now()
        unverified_user.save()

        # Verify states
        verified_user.refresh_from_db()
        unverified_user.refresh_from_db()

        self.assertTrue(verified_user.email_verified)
        self.assertEqual(verified_user.email_verification_token, "")
        self.assertIsNone(verified_user.email_verification_sent_at)

        self.assertFalse(unverified_user.email_verified)
        self.assertNotEqual(unverified_user.email_verification_token, "")
        self.assertIsNotNone(unverified_user.email_verification_sent_at)


class UserEmailVerificationMethodsTest(TestCase):
    """Test custom methods for email verification functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_generate_email_verification_token_method(self):
        """Test method to generate email verification token."""
        # This method should exist on the User model
        self.assertTrue(hasattr(self.user, "generate_email_verification_token"))

        # Generate token
        token = self.user.generate_email_verification_token()

        # Token should be a non-empty string
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)
        self.assertLessEqual(len(token), 64)

        # Token should be set on the user
        self.assertEqual(self.user.email_verification_token, token)
        self.assertIsNotNone(self.user.email_verification_sent_at)

    def test_generate_email_verification_token_uniqueness(self):
        """Test that generated tokens are unique."""
        token1 = self.user.generate_email_verification_token()

        # Create another user
        user2 = User.objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="TestPass123!",
        )
        token2 = user2.generate_email_verification_token()

        # Tokens should be different
        self.assertNotEqual(token1, token2)

    def test_clear_email_verification_token_method(self):
        """Test method to clear email verification token."""
        # First generate a token
        self.user.generate_email_verification_token()
        self.assertNotEqual(self.user.email_verification_token, "")

        # This method should exist
        self.assertTrue(hasattr(self.user, "clear_email_verification_token"))

        # Clear the token
        self.user.clear_email_verification_token()

        self.assertEqual(self.user.email_verification_token, "")
        self.assertIsNone(self.user.email_verification_sent_at)

    def test_mark_email_verified_method(self):
        """Test method to mark email as verified."""
        # Start with unverified user with token
        self.user.generate_email_verification_token()
        self.assertFalse(self.user.email_verified)

        # This method should exist
        self.assertTrue(hasattr(self.user, "mark_email_verified"))

        # Mark as verified
        self.user.mark_email_verified()

        # Should be verified and token cleared
        self.assertTrue(self.user.email_verified)
        self.assertEqual(self.user.email_verification_token, "")
        self.assertIsNone(self.user.email_verification_sent_at)

    def test_is_email_verification_token_expired_method(self):
        """Test method to check if verification token is expired."""
        # This method should exist
        self.assertTrue(hasattr(self.user, "is_email_verification_token_expired"))

        # No token should not be expired
        self.assertFalse(self.user.is_email_verification_token_expired())

        # Fresh token should not be expired
        self.user.generate_email_verification_token()
        self.assertFalse(self.user.is_email_verification_token_expired())

        # Old token should be expired
        # Calculate future time before mock context to avoid MagicMock issues
        future_time = timezone.now() + timedelta(hours=25)
        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = future_time

            self.assertTrue(self.user.is_email_verification_token_expired())

    def test_get_email_verification_expiry_method(self):
        """Test method to get verification token expiry time."""
        # This method should exist
        self.assertTrue(hasattr(self.user, "get_email_verification_expiry"))

        # No sent_at should return None
        self.assertIsNone(self.user.get_email_verification_expiry())

        # With sent_at should return expiry time
        self.user.generate_email_verification_token()
        expiry = self.user.get_email_verification_expiry()

        self.assertIsNotNone(expiry)
        self.assertIsInstance(expiry, timezone.datetime)
        # Should be 24 hours from sent_at
        expected_expiry = self.user.email_verification_sent_at + timedelta(hours=24)
        self.assertEqual(expiry, expected_expiry)


class UserEmailVerificationSecurityTest(TestCase):
    """Test security aspects of email verification fields."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_email_verification_token_not_in_serialization(self):
        """Test that verification token is not exposed in serialization."""
        # Generate token
        self.user.generate_email_verification_token()

        # Token should not appear in str representation
        user_str = str(self.user)
        self.assertNotIn(self.user.email_verification_token, user_str)

    def test_token_length_and_randomness(self):
        """Test that generated tokens have appropriate length and randomness."""
        tokens = set()

        # Generate multiple tokens for different users
        for i in range(10):
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="TestPass123!",
            )
            token = user.generate_email_verification_token()
            tokens.add(token)

            # Each token should be reasonable length
            self.assertGreaterEqual(len(token), 32)
            self.assertLessEqual(len(token), 64)

        # All tokens should be unique
        self.assertEqual(len(tokens), 10)

    def test_verification_token_cleared_after_verification(self):
        """Test that token is cleared after successful verification."""
        # Generate token
        token = self.user.generate_email_verification_token()
        self.assertEqual(self.user.email_verification_token, token)

        # Verify email
        self.user.mark_email_verified()

        # Token should be cleared
        self.assertEqual(self.user.email_verification_token, "")
        self.assertIsNone(self.user.email_verification_sent_at)

    def test_cannot_verify_with_expired_token(self):
        """Test that expired tokens cannot be used for verification."""
        # Generate token
        self.user.generate_email_verification_token()

        # Mock time to make token expired
        # Calculate future time before mock context to avoid MagicMock issues
        future_time = timezone.now() + timedelta(hours=25)
        with patch("django.utils.timezone.now") as mock_now:
            mock_now.return_value = future_time

            # Token should be expired
            self.assertTrue(self.user.is_email_verification_token_expired())

            # Verification should fail with expired token
            with self.assertRaises(ValidationError) as cm:
                self.user.verify_email_with_token(self.user.email_verification_token)

            self.assertIn("expired", str(cm.exception).lower())

    def test_cannot_verify_with_invalid_token(self):
        """Test that invalid tokens cannot be used for verification."""
        # Generate valid token (not used in this test)
        self.user.generate_email_verification_token()

        # Try with invalid token
        invalid_token = "invalid_token_123"

        with self.assertRaises(ValidationError) as cm:
            self.user.verify_email_with_token(invalid_token)

        self.assertIn("invalid", str(cm.exception).lower())

    def test_token_reset_on_email_change(self):
        """Test that verification token is reset when email changes."""
        # Generate token
        self.user.generate_email_verification_token()
        original_token = self.user.email_verification_token

        # Change email
        self.user.email = "newemail@example.com"
        self.user.save()

        # Should trigger token reset and email_verified = False
        self.assertNotEqual(self.user.email_verification_token, original_token)
        self.assertFalse(self.user.email_verified)


class UserEmailVerificationQuerySetTest(TestCase):
    """Test custom QuerySet methods for email verification."""

    def setUp(self):
        """Set up test data with various verification states."""
        # Verified user
        self.verified_user = User.objects.create_user(
            username="verified",
            email="verified@example.com",
            password="TestPass123!",
        )
        self.verified_user.email_verified = True
        self.verified_user.save()

        # Unverified user with recent token
        self.unverified_recent = User.objects.create_user(
            username="unverified_recent",
            email="unverified_recent@example.com",
            password="TestPass123!",
        )
        self.unverified_recent.generate_email_verification_token()

        # Unverified user with expired token
        self.unverified_expired = User.objects.create_user(
            username="unverified_expired",
            email="unverified_expired@example.com",
            password="TestPass123!",
        )
        # Set an old timestamp
        old_time = timezone.now() - timedelta(hours=25)
        self.unverified_expired.email_verification_token = secrets.token_urlsafe(32)
        self.unverified_expired.email_verification_sent_at = old_time
        self.unverified_expired.save()

    def test_verified_users_queryset(self):
        """Test QuerySet method to get verified users."""
        verified_users = User.objects.email_verified()

        self.assertIn(self.verified_user, verified_users)
        self.assertNotIn(self.unverified_recent, verified_users)
        self.assertNotIn(self.unverified_expired, verified_users)

    def test_unverified_users_queryset(self):
        """Test QuerySet method to get unverified users."""
        unverified_users = User.objects.email_unverified()

        self.assertNotIn(self.verified_user, unverified_users)
        self.assertIn(self.unverified_recent, unverified_users)
        self.assertIn(self.unverified_expired, unverified_users)

    def test_pending_verification_queryset(self):
        """Test QuerySet method to get users with pending verification."""
        pending_users = User.objects.pending_email_verification()

        # Should include users with tokens that haven't expired
        self.assertNotIn(self.verified_user, pending_users)
        self.assertIn(self.unverified_recent, pending_users)
        # Expired tokens should not be pending
        self.assertNotIn(self.unverified_expired, pending_users)

    def test_expired_verification_queryset(self):
        """Test QuerySet method to get users with expired verification tokens."""
        expired_users = User.objects.expired_email_verification()

        self.assertNotIn(self.verified_user, expired_users)
        self.assertNotIn(self.unverified_recent, expired_users)
        self.assertIn(self.unverified_expired, expired_users)


class UserEmailVerificationConstraintsTest(TransactionTestCase):
    """Test database constraints and edge cases for email verification."""

    def test_email_verification_token_can_be_empty_string(self):
        """Test that email_verification_token can be empty string."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Default should be empty string
        self.assertEqual(user.email_verification_token, "")

        # Should be able to set to empty string explicitly
        user.email_verification_token = ""
        user.save()
        self.assertEqual(user.email_verification_token, "")

    def test_email_verification_sent_at_can_be_null(self):
        """Test that email_verification_sent_at can be NULL."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Default should be None
        self.assertIsNone(user.email_verification_sent_at)

        # Should be able to set to None explicitly
        user.email_verification_sent_at = None
        user.save()
        self.assertIsNone(user.email_verification_sent_at)

    def test_concurrent_token_generation_safety(self):
        """Test that concurrent token generation doesn't cause issues."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Simulate concurrent token generation
        def generate_token():
            user.generate_email_verification_token()
            return user.email_verification_token

        # This should not raise any database errors
        token1 = generate_token()
        token2 = generate_token()

        # Latest token should win
        self.assertEqual(user.email_verification_token, token2)
        self.assertNotEqual(token1, token2)

    def test_email_verification_with_unicode_email(self):
        """Test email verification works with unicode email addresses."""
        user = User.objects.create_user(
            username="unicode_user",
            email="tëst@éxämplé.com",
            password="TestPass123!",
        )

        # Should be able to generate token
        token = user.generate_email_verification_token()
        self.assertIsNotNone(token)

        # Should be able to verify
        user.mark_email_verified()
        self.assertTrue(user.email_verified)

    def test_very_long_token_rejection(self):
        """Test that tokens longer than 64 chars are rejected."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Try to set a token that's too long
        very_long_token = "a" * 65
        user.email_verification_token = very_long_token

        # Should raise ValidationError during full_clean()
        with self.assertRaises(ValidationError) as cm:
            user.full_clean()

        # Should mention the email_verification_token field
        self.assertIn("email_verification_token", str(cm.exception))
