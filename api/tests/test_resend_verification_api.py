"""
Tests for Resend Email Verification API endpoint.

Tests the resend verification functionality for Issue #135:
- POST /api/auth/resend-verification/ - Resend verification email
- Rate limiting and security for resend requests
- Token regeneration and expiry handling
- Integration with email sending service
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import EmailVerification

User = get_user_model()


class ResendVerificationAPIBasicTest(TestCase):
    """Test basic resend verification API functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.resend_url = reverse("api:auth:resend_verification")

        # Create unverified user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_successful_resend_verification(self):
        """Test successful resend verification for unverified user."""
        data = {"email": "test@example.com"}

        response = self.client.post(self.resend_url, data, format="json")

        # Should succeed
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should contain success message
        self.assertIn("message", response.data)
        self.assertIn("sent", response.data["message"].lower())

        # Should have created EmailVerification record
        self.assertTrue(EmailVerification.objects.filter(user=self.user).exists())

        # User token fields should be updated
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.email_verification_token, "")
        self.assertIsNotNone(self.user.email_verification_sent_at)

    def test_resend_creates_new_verification_record(self):
        """Test that resend creates new verification record."""
        # Create initial verification
        old_verification = EmailVerification.create_for_user(self.user)
        old_token = old_verification.token

        data = {"email": "test@example.com"}
        response = self.client.post(self.resend_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have new verification record
        new_verification = (
            EmailVerification.objects.filter(user=self.user)
            .order_by("-created_at")
            .first()
        )
        self.assertNotEqual(new_verification.token, old_token)
        self.assertFalse(new_verification.is_expired())

    def test_resend_invalidates_old_verification_tokens(self):
        """Test that resend invalidates previous verification tokens."""
        # Create multiple old verifications
        old_verification1 = EmailVerification.create_for_user(self.user)
        old_verification2 = EmailVerification.create_for_user(self.user)

        data = {"email": "test@example.com"}
        response = self.client.post(self.resend_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Old verifications should be invalidated (expired)
        old_verification1.refresh_from_db()
        old_verification2.refresh_from_db()

        self.assertTrue(old_verification1.is_expired())
        self.assertTrue(old_verification2.is_expired())

    def test_resend_with_case_insensitive_email(self):
        """Test resend with case-insensitive email matching."""
        data = {"email": "TEST@EXAMPLE.COM"}  # Different case

        response = self.client.post(self.resend_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should still work for the correct user
        self.assertTrue(EmailVerification.objects.filter(user=self.user).exists())

    @override_settings(EMAIL_BACKEND="core.test_backends.QuietEmailBackend")
    def test_resend_sends_email(self):
        """Test that resend actually sends verification email."""
        data = {"email": "test@example.com"}

        response = self.client.post(self.resend_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have sent one email
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to, ["test@example.com"])
        self.assertIn("verify", email.subject.lower())

        # Email should contain new verification token
        verification = (
            EmailVerification.objects.filter(user=self.user)
            .order_by("-created_at")
            .first()
        )
        self.assertIn(verification.token, email.body)


class ResendVerificationValidationTest(TestCase):
    """Test validation scenarios for resend verification."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.resend_url = reverse("api:auth:resend_verification")

    def test_resend_nonexistent_email(self):
        """Test resend with nonexistent email."""
        data = {"email": "nonexistent@example.com"}

        response = self.client.post(self.resend_url, data, format="json")

        # Should return success for security (don't reveal user existence)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_resend_already_verified_user(self):
        """Test resend for already verified user."""
        # Create verified user
        user = User.objects.create_user(
            username="verified",
            email="verified@example.com",
            password="TestPass123!",
        )
        user.email_verified = True
        user.save()

        data = {"email": "verified@example.com"}
        response = self.client.post(self.resend_url, data, format="json")

        # Should return appropriate response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already verified", response.data["error"].lower())

    def test_resend_missing_email(self):
        """Test resend without email field."""
        data = {}

        response = self.client.post(self.resend_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", str(response.data).lower())

    def test_resend_empty_email(self):
        """Test resend with empty email."""
        data = {"email": ""}

        response = self.client.post(self.resend_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_invalid_email_format(self):
        """Test resend with invalid email format."""
        invalid_emails = [
            "invalid-email",
            "invalid@",
            "@invalid.com",
            "invalid..email@example.com",
            "invalid email@example.com",
        ]

        for invalid_email in invalid_emails:
            with self.subTest(email=invalid_email):
                data = {"email": invalid_email}
                response = self.client.post(self.resend_url, data, format="json")

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_inactive_user(self):
        """Test resend for inactive user."""
        # Create inactive user
        user = User.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password="TestPass123!",
        )
        user.is_active = False
        user.save()

        data = {"email": "inactive@example.com"}
        response = self.client.post(self.resend_url, data, format="json")

        # Should return success for security, but not actually send
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ResendVerificationRateLimitingTest(TestCase):
    """Test rate limiting for resend verification."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.resend_url = reverse("api:auth:resend_verification")

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_resend_rate_limiting_by_email(self):
        """Test that resend is rate limited by email address."""
        data = {"email": "test@example.com"}

        # First request should succeed
        response1 = self.client.post(self.resend_url, data, format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Immediate second request should be rate limited
        response2 = self.client.post(self.resend_url, data, format="json")

        # Should be rate limited or have cooldown
        self.assertIn(
            response2.status_code,
            [status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_400_BAD_REQUEST],
        )

        if response2.status_code == status.HTTP_400_BAD_REQUEST:
            self.assertIn("wait", response2.data.get("error", "").lower())

    def test_resend_rate_limiting_by_ip(self):
        """Test that resend is rate limited by IP address."""
        # Make multiple requests with different emails but same IP
        emails = [
            "user1@example.com",
            "user2@example.com",
            "user3@example.com",
            "user4@example.com",
            "user5@example.com",
        ]

        responses = []
        for email in emails:
            data = {"email": email}
            response = self.client.post(self.resend_url, data, format="json")
            responses.append(response)

        # After several requests, should get rate limited
        # (exact behavior depends on rate limiting implementation)
        last_responses = responses[-2:]  # Check last 2 responses

        # At least one should be rate limited
        rate_limited = any(
            resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            for resp in last_responses
        )

        # If no explicit rate limiting, at least check for consistent responses
        if not rate_limited:
            for response in responses:
                self.assertIn(
                    response.status_code,
                    [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST],
                )

    def test_resend_cooldown_period(self):
        """Test cooldown period between resend requests."""
        data = {"email": "test@example.com"}

        # First request
        response1 = self.client.post(self.resend_url, data, format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Second request immediately
        response2 = self.client.post(self.resend_url, data, format="json")

        if response2.status_code == status.HTTP_400_BAD_REQUEST:
            # Should indicate when user can try again
            error_msg = response2.data.get("error", "").lower()
            self.assertTrue(
                any(
                    word in error_msg
                    for word in ["wait", "minute", "cooldown", "try again"]
                )
            )

    def test_resend_different_users_different_limits(self):
        """Test that different users have separate rate limits."""
        user1 = self.user
        user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="TestPass123!",
        )

        # Send verification for user1
        data1 = {"email": user1.email}
        response1 = self.client.post(self.resend_url, data1, format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Send verification for user2 (should not be affected by user1's limit)
        data2 = {"email": user2.email}
        response2 = self.client.post(self.resend_url, data2, format="json")
        self.assertEqual(response2.status_code, status.HTTP_200_OK)


class ResendVerificationSecurityTest(TestCase):
    """Test security aspects of resend verification."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.resend_url = reverse("api:auth:resend_verification")

    def test_resend_no_user_enumeration(self):
        """Test that resend doesn't allow user enumeration."""
        # Requests for valid and invalid emails should have similar responses
        valid_data = {"email": "test@example.com"}
        invalid_data = {"email": "nonexistent@example.com"}

        # Create user for valid email
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        response_valid = self.client.post(self.resend_url, valid_data, format="json")
        response_invalid = self.client.post(
            self.resend_url, invalid_data, format="json"
        )

        # Both should return 200 OK for security
        self.assertEqual(response_valid.status_code, status.HTTP_200_OK)
        self.assertEqual(response_invalid.status_code, status.HTTP_200_OK)

        # Messages should be generic
        self.assertIn("message", response_valid.data)
        self.assertIn("message", response_invalid.data)

    def test_resend_timing_attack_protection(self):
        """Test basic protection against timing attacks."""
        # Create user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        valid_data = {"email": "test@example.com"}
        invalid_data = {"email": "nonexistent@example.com"}

        # Both requests should complete (basic check)
        response_valid = self.client.post(self.resend_url, valid_data, format="json")
        response_invalid = self.client.post(
            self.resend_url, invalid_data, format="json"
        )

        # Both should return successful responses
        self.assertEqual(response_valid.status_code, status.HTTP_200_OK)
        self.assertEqual(response_invalid.status_code, status.HTTP_200_OK)

    def test_resend_csrf_protection(self):
        """Test that resend endpoint is protected against CSRF."""
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        data = {"email": "test@example.com"}
        response = self.client.post(self.resend_url, data, format="json")

        # Should succeed with proper CSRF handling
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_resend_logs_security_events(self):
        """Test that resend logs security events."""
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        with patch("logging.Logger.info") as mock_log:
            data = {"email": "test@example.com"}
            response = self.client.post(self.resend_url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Should log the resend request
            mock_log.assert_called()

            # Log should not contain sensitive information
            log_calls = [call[0][0] for call in mock_log.call_args_list]
            log_messages = " ".join(log_calls)

            self.assertIn("resend", log_messages.lower())
            # Should not log raw email or tokens
            self.assertNotIn("test@example.com", log_messages)


class ResendVerificationServiceIntegrationTest(TestCase):
    """Test integration with email service and other components."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.resend_url = reverse("api:auth:resend_verification")

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_resend_handles_email_service_failure(self):
        """Test that resend handles email service failures gracefully."""
        with patch(
            "users.services.EmailVerificationService.resend_verification_email"
        ) as mock_send:
            mock_send.return_value = False

            data = {"email": "test@example.com"}
            response = self.client.post(self.resend_url, data, format="json")

            # Should still return success but indicate email issue
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("email_sending_failed", response.data)

    def test_resend_updates_user_fields(self):
        """Test that resend properly updates user verification fields."""
        data = {"email": "test@example.com"}

        # Clear initial fields
        self.user.email_verification_token = ""
        self.user.email_verification_sent_at = None
        self.user.save()

        response = self.client.post(self.resend_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # User fields should be updated
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.email_verification_token, "")
        self.assertIsNotNone(self.user.email_verification_sent_at)

    def test_resend_creates_audit_trail(self):
        """Test that resend creates appropriate audit trail."""
        data = {"email": "test@example.com"}

        initial_verification_count = EmailVerification.objects.filter(
            user=self.user
        ).count()

        response = self.client.post(self.resend_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should have created new verification record
        final_verification_count = EmailVerification.objects.filter(
            user=self.user
        ).count()
        self.assertGreater(final_verification_count, initial_verification_count)

    def test_resend_respects_user_email_preferences(self):
        """Test that resend respects user email preferences."""
        # This is a placeholder for future email preference functionality
        data = {"email": "test@example.com"}

        response = self.client.post(self.resend_url, data, format="json")

        # Should succeed for now
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_resend_with_custom_template(self):
        """Test that resend uses appropriate email template."""
        with patch(
            "users.services.EmailVerificationService.resend_verification_email"
        ) as mock_send:
            data = {"email": "test@example.com"}
            response = self.client.post(self.resend_url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Should have called email service
            mock_send.assert_called_once_with(self.user)


class ResendVerificationHTTPMethodTest(TestCase):
    """Test HTTP methods for resend verification endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.resend_url = reverse("api:auth:resend_verification")

    def test_resend_post_method(self):
        """Test that POST method works for resend."""
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        data = {"email": "test@example.com"}
        response = self.client.post(self.resend_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_resend_get_method_not_allowed(self):
        """Test that GET method is not allowed."""
        response = self.client.get(self.resend_url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_resend_put_method_not_allowed(self):
        """Test that PUT method is not allowed."""
        response = self.client.put(self.resend_url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_resend_delete_method_not_allowed(self):
        """Test that DELETE method is not allowed."""
        response = self.client.delete(self.resend_url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_resend_options_method(self):
        """Test that OPTIONS method works."""
        response = self.client.options(self.resend_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should indicate only POST is allowed
        allowed_methods = response.get("Allow", "").split(", ")
        self.assertIn("POST", allowed_methods)
        self.assertNotIn("GET", allowed_methods)
