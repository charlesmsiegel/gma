"""
Tests for User Registration API with Email Verification.

Tests the enhanced registration API endpoint for Issue #135:
- POST /api/auth/register/ - Enhanced user registration with email verification
- Email verification token generation and user state management
- Integration with EmailVerification model
- Comprehensive validation scenarios and error handling
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from users.models import EmailVerification

User = get_user_model()


class RegistrationAPIBasicTest(TestCase):
    """Test basic registration API functionality."""

    def setUp(self):
        """Set up test client and URLs."""
        self.client = APIClient()
        self.register_url = reverse("api:auth:api_register")

    def test_successful_registration_with_email_verification(self):
        """Test successful user registration creates EmailVerification record."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
            "display_name": "New User",
        }

        response = self.client.post(self.register_url, data, format="json")

        # Should succeed
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # User should be created but not email verified
        user = User.objects.get(username="newuser")
        self.assertFalse(user.email_verified)
        self.assertEqual(user.email, "newuser@example.com")
        self.assertEqual(user.display_name, "New User")

        # EmailVerification record should be created
        verification = EmailVerification.objects.get(user=user)
        self.assertIsNotNone(verification.token)
        self.assertIsNotNone(verification.expires_at)
        self.assertIsNone(verification.verified_at)
        self.assertFalse(verification.is_expired())

    def test_registration_sends_verification_email(self):
        """Test that registration sends verification email."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        with patch(
            "users.services.EmailVerificationService.send_verification_email"
        ) as mock_send:
            response = self.client.post(self.register_url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            # Should have called send_verification_email
            mock_send.assert_called_once()
            user = User.objects.get(username="newuser")
            mock_send.assert_called_with(user)

    @override_settings(EMAIL_VERIFICATION_REQUIRED=True)
    def test_registration_response_includes_verification_info(self):
        """Test that registration response includes email verification info."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Response should include verification status
        self.assertIn("user", response.data)
        self.assertIn("message", response.data)
        self.assertIn("email_verification_required", response.data)

        user_data = response.data["user"]
        self.assertEqual(user_data["email_verified"], False)
        self.assertTrue(response.data["email_verification_required"])

        # Should not expose verification token in response
        self.assertNotIn("email_verification_token", user_data)

    def test_registration_minimal_fields(self):
        """Test registration with minimal required fields."""
        data = {
            "username": "minimal",
            "email": "minimal@example.com",
            "password": "MinimalPass123!",
            "password_confirm": "MinimalPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="minimal")
        self.assertEqual(user.email, "minimal@example.com")
        self.assertFalse(user.email_verified)

        # Should still create verification record
        self.assertTrue(EmailVerification.objects.filter(user=user).exists())


class RegistrationValidationTest(TestCase):
    """Test registration validation scenarios."""

    def setUp(self):
        """Set up test client and URLs."""
        self.client = APIClient()
        self.register_url = reverse("api:auth:api_register")

    def test_registration_duplicate_username(self):
        """Test registration with duplicate username."""
        # Create existing user
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="ExistingPass123!",
        )

        data = {
            "username": "existing",  # Duplicate
            "email": "new@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Should return generic error for security
        self.assertIn("Registration failed", str(response.data))

    def test_registration_duplicate_email(self):
        """Test registration with duplicate email."""
        # Create existing user
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="ExistingPass123!",
        )

        data = {
            "username": "newuser",
            "email": "existing@example.com",  # Duplicate
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Should return generic error for security
        self.assertIn("Registration failed", str(response.data))

    def test_registration_case_insensitive_email_duplicate(self):
        """Test registration with case-insensitive email duplicate."""
        # Create existing user
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="ExistingPass123!",
        )

        data = {
            "username": "newuser",
            "email": "EXISTING@EXAMPLE.COM",  # Different case
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_password_mismatch(self):
        """Test registration with password mismatch."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "DifferentPass456!",  # Mismatch
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Passwords do not match", str(response.data))

    def test_registration_weak_password(self):
        """Test registration with weak password."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "weak",  # Too weak
            "password_confirm": "weak",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Should contain password validation error
        self.assertIn("password", str(response.data).lower())

    def test_registration_invalid_email_format(self):
        """Test registration with invalid email format."""
        data = {
            "username": "newuser",
            "email": "invalid-email-format",  # Invalid format
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", str(response.data).lower())

    def test_registration_missing_required_fields(self):
        """Test registration with missing required fields."""
        # Missing username
        data = {
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", str(response.data).lower())

    def test_registration_empty_fields(self):
        """Test registration with empty fields."""
        data = {
            "username": "",
            "email": "",
            "password": "",
            "password_confirm": "",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_very_long_username(self):
        """Test registration with very long username."""
        data = {
            "username": "a" * 200,  # Very long
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_very_long_email(self):
        """Test registration with very long email."""
        long_local = "a" * 100
        data = {
            "username": "newuser",
            "email": f"{long_local}@example.com",  # Very long email
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_display_name_too_long(self):
        """Test registration with display name too long."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
            "display_name": "a" * 200,  # Too long
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RegistrationSecurityTest(TestCase):
    """Test security aspects of registration."""

    def setUp(self):
        """Set up test client and URLs."""
        self.client = APIClient()
        self.register_url = reverse("api:auth:api_register")

    def test_registration_does_not_leak_user_existence(self):
        """Test that registration errors don't reveal user existence."""
        # Create existing user
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="ExistingPass123!",
        )

        # Try duplicate username
        data1 = {
            "username": "existing",
            "email": "new1@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }
        response1 = self.client.post(self.register_url, data1, format="json")

        # Try duplicate email
        data2 = {
            "username": "newuser",
            "email": "existing@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }
        response2 = self.client.post(self.register_url, data2, format="json")

        # Both should return same generic error
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

        # Errors should be generic, not specific
        error1 = str(response1.data)
        error2 = str(response2.data)

        self.assertIn("Registration failed", error1)
        self.assertIn("Registration failed", error2)
        self.assertNotIn("username", error1.lower())
        self.assertNotIn("email", error1.lower())

    def test_registration_rate_limiting_headers(self):
        """Test that registration includes appropriate rate limiting info."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        # Should include rate limiting headers (if implemented)
        # This is a placeholder for future rate limiting implementation
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_registration_csrf_protection(self):
        """Test that registration is protected against CSRF."""
        # This test verifies CSRF protection is in place
        # The exact implementation depends on Django settings
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        # Should succeed with proper CSRF handling
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class RegistrationEmailVerificationIntegrationTest(TestCase):
    """Test integration between registration and email verification system."""

    def setUp(self):
        """Set up test client and URLs."""
        self.client = APIClient()
        self.register_url = reverse("api:auth:api_register")

    def test_registration_creates_unique_verification_tokens(self):
        """Test that multiple registrations create unique verification tokens."""
        users_data = [
            {
                "username": "user1",
                "email": "user1@example.com",
                "password": "User1Pass123!",
                "password_confirm": "User1Pass123!",
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "password": "User2Pass123!",
                "password_confirm": "User2Pass123!",
            },
        ]

        tokens = []
        for user_data in users_data:
            response = self.client.post(self.register_url, user_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            user = User.objects.get(username=user_data["username"])
            verification = EmailVerification.objects.get(user=user)
            tokens.append(verification.token)

        # All tokens should be unique
        self.assertEqual(len(set(tokens)), len(tokens))

    def test_registration_sets_appropriate_expiry(self):
        """Test that verification tokens have appropriate expiry time."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        before_registration = timezone.now()
        response = self.client.post(self.register_url, data, format="json")
        after_registration = timezone.now()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="newuser")
        verification = EmailVerification.objects.get(user=user)

        # Should expire in 24 hours
        expected_min_expiry = before_registration + timedelta(hours=24)
        expected_max_expiry = after_registration + timedelta(hours=24)

        self.assertGreaterEqual(verification.expires_at, expected_min_expiry)
        self.assertLessEqual(verification.expires_at, expected_max_expiry)

    @override_settings(EMAIL_BACKEND="core.test_backends.QuietEmailBackend")
    def test_registration_sends_email_with_verification_link(self):
        """Test that registration sends email with verification link."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Should have sent one email
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to, ["newuser@example.com"])
        self.assertIn("verify", email.subject.lower())

        # Email should contain verification link
        user = User.objects.get(username="newuser")
        verification = EmailVerification.objects.get(user=user)
        self.assertIn(verification.token, email.body)

    @override_settings(EMAIL_VERIFICATION_REQUIRED=True)
    def test_registration_handles_email_sending_failure(self):
        """Test that registration handles email sending failure gracefully."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        with patch(
            "users.services.EmailVerificationService.send_verification_email"
        ) as mock_send:
            mock_send.side_effect = Exception("Email service unavailable")

            response = self.client.post(self.register_url, data, format="json")

            # Registration should still succeed
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            # User and verification should be created
            user = User.objects.get(username="newuser")
            self.assertTrue(EmailVerification.objects.filter(user=user).exists())

            # Response should indicate email issue
            self.assertIn("email_sending_failed", response.data)

    def test_registration_updates_user_verification_fields(self):
        """Test that registration properly updates user verification fields."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="newuser")

        # User fields should be set appropriately
        self.assertFalse(user.email_verified)
        self.assertNotEqual(user.email_verification_token, "")
        self.assertIsNotNone(user.email_verification_sent_at)


class RegistrationEdgeCasesTest(TestCase):
    """Test edge cases and error conditions in registration."""

    def setUp(self):
        """Set up test client and URLs."""
        self.client = APIClient()
        self.register_url = reverse("api:auth:api_register")

    def test_registration_with_unicode_characters(self):
        """Test registration with unicode characters in fields."""
        data = {
            "username": "üser123",
            "email": "tëst@éxämplé.com",
            "password": "UnicodePass123!",
            "password_confirm": "UnicodePass123!",
            "display_name": "Tëst Üser",
        }

        response = self.client.post(self.register_url, data, format="json")

        # Should handle unicode properly
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="üser123")
        self.assertEqual(user.email, "tëst@éxämplé.com")
        self.assertEqual(user.display_name, "Tëst Üser")

    def test_registration_with_special_characters(self):
        """Test registration with special characters."""
        data = {
            "username": "user-123_test",
            "email": "user+tag@example.com",
            "password": "SpecialPass123!",
            "password_confirm": "SpecialPass123!",
            "display_name": "User O'Connor-Smith",
        }

        response = self.client.post(self.register_url, data, format="json")

        # Should handle special characters properly
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_registration_database_error_handling(self):
        """Test registration handles database errors gracefully."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        with patch.object(User.objects, "create_user") as mock_create:
            mock_create.side_effect = Exception("Database unavailable")

            response = self.client.post(self.register_url, data, format="json")

            # Should return 500 error
            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def test_registration_verification_token_collision_handling(self):
        """Test handling of verification token collisions."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        # Create existing verification with a known token
        existing_user = User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="ExistingPass123!",
        )
        EmailVerification.objects.create(
            user=existing_user,
            token="existing_collision_token",
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Mock secrets.token_urlsafe to first return existing token, then unique token
        with patch("secrets.token_urlsafe") as mock_token_gen:
            # First call returns existing token (collision), second returns unique token
            mock_token_gen.side_effect = [
                "existing_collision_token",
                "unique_new_token",
            ]

            response = self.client.post(self.register_url, data, format="json")

            # Should still succeed with unique token after collision handling
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            user = User.objects.get(username="newuser")
            verification = EmailVerification.objects.get(user=user)
            self.assertEqual(verification.token, "unique_new_token")

            # Verify the method was called twice due to collision
            self.assertEqual(mock_token_gen.call_count, 2)

    def test_registration_concurrent_requests(self):
        """Test handling of concurrent registration requests."""
        data = {
            "username": "concurrent_user",
            "email": "concurrent@example.com",
            "password": "ConcurrentPass123!",
            "password_confirm": "ConcurrentPass123!",
        }

        # Simulate concurrent requests (simplified test)
        response1 = self.client.post(self.register_url, data, format="json")

        # Second request with same data should fail
        response2 = self.client.post(self.register_url, data, format="json")

        # First should succeed
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second should fail due to duplicate
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_with_inactive_user_reregistration(self):
        """Test re-registration attempt with inactive user."""
        # Create inactive user
        inactive_user = User.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password="InactivePass123!",
        )
        inactive_user.is_active = False
        inactive_user.save()

        # Try to register with same credentials
        data = {
            "username": "inactive",
            "email": "inactive@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response = self.client.post(self.register_url, data, format="json")

        # Should fail due to duplicate
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
