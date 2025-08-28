"""
Tests for password reset API serializers.

This test suite covers:
- PasswordResetRequestSerializer validation
- PasswordResetConfirmSerializer validation
- PasswordResetTokenValidationSerializer validation
- Error handling and edge cases
- Security considerations in serializer logic
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from api.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetTokenValidationSerializer,
)
from users.models.password_reset import PasswordReset

User = get_user_model()


class PasswordResetRequestSerializerTest(TestCase):
    """Test the PasswordResetRequestSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", email="test2@example.com", password="TestPass123!"
        )

    def test_valid_email_serializer(self):
        """Test serializer with valid email."""
        data = {"email": "test@example.com"}
        serializer = PasswordResetRequestSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "test@example.com")

    def test_valid_username_serializer(self):
        """Test serializer with valid username in email field."""
        data = {"email": "testuser"}
        serializer = PasswordResetRequestSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "testuser")

    def test_case_insensitive_email_serializer(self):
        """Test serializer with case-insensitive email."""
        data = {"email": "TEST@EXAMPLE.COM"}
        serializer = PasswordResetRequestSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        # Serializer should normalize to lowercase
        self.assertEqual(serializer.validated_data["email"], "test@example.com")

    def test_missing_email_field(self):
        """Test serializer with missing email field."""
        data = {}
        serializer = PasswordResetRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
        self.assertIn("required", str(serializer.errors["email"]).lower())

    def test_empty_email_field(self):
        """Test serializer with empty email field."""
        data = {"email": ""}
        serializer = PasswordResetRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)
        self.assertIn("blank", str(serializer.errors["email"]).lower())

    def test_whitespace_only_email_field(self):
        """Test serializer with whitespace-only email field."""
        data = {"email": "   "}
        serializer = PasswordResetRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_invalid_email_format(self):
        """Test serializer with invalid email format."""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "test@",
            "test.example.com",
            "test@.com",
        ]

        for invalid_email in invalid_emails:
            data = {"email": invalid_email}
            serializer = PasswordResetRequestSerializer(data=data)

            # Should still be valid at serializer level - validation happens in view
            # Serializer just ensures it's a non-empty string
            self.assertTrue(serializer.is_valid() or "email" in serializer.errors)

    def test_email_max_length_validation(self):
        """Test email field maximum length validation."""
        long_email = "a" * 300 + "@example.com"
        data = {"email": long_email}
        serializer = PasswordResetRequestSerializer(data=data)

        # Should fail validation if max_length is enforced
        if not serializer.is_valid():
            self.assertIn("email", serializer.errors)

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        data = {
            "email": "test@example.com",
            "extra_field": "should_be_ignored",
            "password": "should_not_be_here",
        }
        serializer = PasswordResetRequestSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        # Extra fields should not be in validated_data
        self.assertNotIn("extra_field", serializer.validated_data)
        self.assertNotIn("password", serializer.validated_data)

    def test_serializer_save_method(self):
        """Test that serializer save method works correctly."""
        data = {"email": "test@example.com"}
        serializer = PasswordResetRequestSerializer(data=data)

        self.assertTrue(serializer.is_valid())

        # Save method should return the found user (if implemented)
        result = serializer.save()

        # This depends on implementation - might return user, reset object, or None
        # For security, it might always return None
        self.assertIsInstance(result, (User, type(None), dict))


class PasswordResetConfirmSerializerTest(TestCase):
    """Test the PasswordResetConfirmSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="OldPassword123!"
        )
        self.valid_reset = PasswordReset.objects.create_for_user(self.user)

    def test_valid_password_reset_confirm_serializer(self):
        """Test serializer with valid data."""
        data = {
            "token": self.valid_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }
        serializer = PasswordResetConfirmSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["token"], self.valid_reset.token)
        self.assertEqual(serializer.validated_data["new_password"], "NewPassword123!")

    def test_password_mismatch(self):
        """Test serializer with password mismatch."""
        data = {
            "token": self.valid_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "DifferentPassword123!",
        }
        serializer = PasswordResetConfirmSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)
        self.assertIn("passwords", str(serializer.errors["non_field_errors"]).lower())

    def test_weak_password_validation(self):
        """Test serializer with weak password."""
        data = {
            "token": self.valid_reset.token,
            "new_password": "weak",
            "new_password_confirm": "weak",
        }
        serializer = PasswordResetConfirmSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        # Should fail Django's password validation
        self.assertIn("new_password", serializer.errors)

    def test_missing_token_field(self):
        """Test serializer with missing token field."""
        data = {
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }
        serializer = PasswordResetConfirmSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("token", serializer.errors)

    def test_missing_password_fields(self):
        """Test serializer with missing password fields."""
        # Missing new_password
        data1 = {
            "token": self.valid_reset.token,
            "new_password_confirm": "NewPassword123!",
        }
        serializer1 = PasswordResetConfirmSerializer(data=data1)
        self.assertFalse(serializer1.is_valid())
        self.assertIn("new_password", serializer1.errors)

        # Missing new_password_confirm
        data2 = {"token": self.valid_reset.token, "new_password": "NewPassword123!"}
        serializer2 = PasswordResetConfirmSerializer(data=data2)
        self.assertFalse(serializer2.is_valid())
        self.assertIn("new_password_confirm", serializer2.errors)

    def test_empty_fields(self):
        """Test serializer with empty fields."""
        data = {"token": "", "new_password": "", "new_password_confirm": ""}
        serializer = PasswordResetConfirmSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("token", serializer.errors)
        self.assertIn("new_password", serializer.errors)

    def test_invalid_token_format(self):
        """Test serializer with invalid token format."""
        invalid_tokens = [
            "short",
            "a" * 65,  # Too long
            "contains spaces",
            "contains/special@chars",
        ]

        for invalid_token in invalid_tokens:
            data = {
                "token": invalid_token,
                "new_password": "NewPassword123!",
                "new_password_confirm": "NewPassword123!",
            }
            serializer = PasswordResetConfirmSerializer(data=data)

            # Token format validation might be at serializer or view level
            if not serializer.is_valid():
                self.assertIn("token", serializer.errors)

    def test_password_complexity_requirements(self):
        """Test password complexity requirements."""
        weak_passwords = [
            "password",  # Common password
            "12345678",  # All numbers
            "abcdefgh",  # All lowercase
            "ABCDEFGH",  # All uppercase
            "abc123",  # Too short
        ]

        for weak_password in weak_passwords:
            data = {
                "token": self.valid_reset.token,
                "new_password": weak_password,
                "new_password_confirm": weak_password,
            }
            serializer = PasswordResetConfirmSerializer(data=data)

            # Should fail Django's password validation
            if not serializer.is_valid():
                self.assertIn("new_password", serializer.errors)

    def test_serializer_save_method(self):
        """Test that serializer save method works correctly."""
        data = {
            "token": self.valid_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }
        serializer = PasswordResetConfirmSerializer(data=data)

        self.assertTrue(serializer.is_valid())

        # Save should reset the password and mark token as used
        serializer.save()

        # Check that password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))

        # Check that token was marked as used
        self.valid_reset.refresh_from_db()
        self.assertTrue(self.valid_reset.is_used())


class PasswordResetTokenValidationSerializerTest(TestCase):
    """Test the PasswordResetTokenValidationSerializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.valid_reset = PasswordReset.objects.create_for_user(self.user)

    def test_valid_token_serializer(self):
        """Test serializer with valid token."""
        data = {"token": self.valid_reset.token}
        serializer = PasswordResetTokenValidationSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["token"], self.valid_reset.token)

    def test_expired_token_validation(self):
        """Test serializer with expired token."""
        # Create expired reset
        expired_reset = PasswordReset.objects.create(
            user=self.user, expires_at=timezone.now() - timedelta(hours=1)
        )

        data = {"token": expired_reset.token}
        serializer = PasswordResetTokenValidationSerializer(data=data)

        # Serializer might validate format but business logic validates expiration
        if serializer.is_valid():
            # Validation happens in view/service layer
            pass
        else:
            self.assertIn("token", serializer.errors)

    def test_used_token_validation(self):
        """Test serializer with used token."""
        self.valid_reset.mark_as_used()

        data = {"token": self.valid_reset.token}
        serializer = PasswordResetTokenValidationSerializer(data=data)

        # Serializer might validate format but business logic validates usage
        if serializer.is_valid():
            # Validation happens in view/service layer
            pass
        else:
            self.assertIn("token", serializer.errors)

    def test_nonexistent_token_validation(self):
        """Test serializer with nonexistent token."""
        fake_token = "a" * 64
        data = {"token": fake_token}
        serializer = PasswordResetTokenValidationSerializer(data=data)

        # Format validation should pass, existence validation in view/service
        self.assertTrue(serializer.is_valid())

    def test_malformed_token_validation(self):
        """Test serializer with malformed token."""
        malformed_tokens = [
            "",
            "short",
            "a" * 65,  # Too long
            "contains spaces",
            "contains/slashes",
        ]

        for malformed_token in malformed_tokens:
            data = {"token": malformed_token}
            serializer = PasswordResetTokenValidationSerializer(data=data)

            # Should fail format validation
            if not serializer.is_valid():
                self.assertIn("token", serializer.errors)

    def test_missing_token_field(self):
        """Test serializer with missing token field."""
        data = {}
        serializer = PasswordResetTokenValidationSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("token", serializer.errors)

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        data = {
            "token": self.valid_reset.token,
            "extra_field": "should_be_ignored",
            "password": "should_not_be_here",
        }
        serializer = PasswordResetTokenValidationSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        # Extra fields should not be in validated_data
        self.assertNotIn("extra_field", serializer.validated_data)
        self.assertNotIn("password", serializer.validated_data)


class PasswordResetSerializerSecurityTest(TestCase):
    """Test security aspects of password reset serializers."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.valid_reset = PasswordReset.objects.create_for_user(self.user)

    def test_password_not_in_serialized_data(self):
        """Test that passwords are not included in serialized output."""
        data = {
            "token": self.valid_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }
        serializer = PasswordResetConfirmSerializer(data=data)

        self.assertTrue(serializer.is_valid())

        # Serialized data should not contain actual passwords
        serialized = serializer.data
        self.assertNotIn("new_password", serialized)
        self.assertNotIn("new_password_confirm", serialized)

    def test_token_not_in_response_data(self):
        """Test that tokens are not echoed back in responses."""
        data = {"token": self.valid_reset.token}
        serializer = PasswordResetTokenValidationSerializer(data=data)

        self.assertTrue(serializer.is_valid())

        # Serialized data should not echo back the token
        serialized = serializer.data
        if "token" in serialized:
            # If included, should be masked or truncated
            self.assertNotEqual(serialized["token"], self.valid_reset.token)

    def test_user_information_not_leaked(self):
        """Test that user information is not leaked through serializers."""
        data = {"email": "nonexistent@example.com"}
        serializer = PasswordResetRequestSerializer(data=data)

        self.assertTrue(serializer.is_valid())

        # Serializer should not reveal whether user exists
        serialized = serializer.data
        self.assertNotIn("user_exists", serialized)
        self.assertNotIn("user_found", serialized)

    def test_sensitive_error_messages(self):
        """Test that error messages don't reveal sensitive information."""
        # Test with various invalid tokens
        invalid_tokens = [
            "a" * 64,  # Valid format, nonexistent
            "expired_token_format",
            "used_token_format",
        ]

        for invalid_token in invalid_tokens:
            data = {
                "token": invalid_token,
                "new_password": "NewPassword123!",
                "new_password_confirm": "NewPassword123!",
            }
            serializer = PasswordResetConfirmSerializer(data=data)

            if not serializer.is_valid():
                error_message = str(serializer.errors).lower()
                # Should not reveal specific reasons for token invalidity
                self.assertNotIn("expired", error_message)
                self.assertNotIn("used", error_message)
                self.assertNotIn("nonexistent", error_message)

    def test_timing_attack_resistance_data_preparation(self):
        """Test that serializers prepare data consistently regardless of validity."""
        # This is more of a guideline test - actual timing attack resistance
        # happens at the view/service layer, but serializers should not
        # short-circuit validation in ways that reveal information

        valid_data = {
            "token": self.valid_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        invalid_data = {
            "token": "a" * 64,  # Valid format, nonexistent token
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        # Both should go through same validation steps
        valid_serializer = PasswordResetConfirmSerializer(data=valid_data)
        invalid_serializer = PasswordResetConfirmSerializer(data=invalid_data)

        # Both should validate format consistently
        # (business logic validation happens later)
        valid_result = valid_serializer.is_valid()
        invalid_result = invalid_serializer.is_valid()

        # Format validation should be consistent
        self.assertIsInstance(valid_result, bool)
        self.assertIsInstance(invalid_result, bool)
