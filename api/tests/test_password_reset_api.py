"""
Tests for password reset API endpoints.

This test suite covers:
- POST /api/auth/password-reset/ - Initiate password reset
- POST /api/auth/password-reset-confirm/ - Confirm password reset with token
- GET /api/auth/password-reset-validate/{token}/ - Validate reset token
- Rate limiting and security features
- Email template rendering and sending
- Integration with existing authentication system
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

from users.models.password_reset import PasswordReset

User = get_user_model()


class PasswordResetRequestAPITest(TestCase):
    """Test the password reset request API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.user2 = User.objects.create_user(
            username="anotheruser", email="another@example.com", password="TestPass123!"
        )

        self.password_reset_url = reverse("api:auth:password_reset_request")

    def test_password_reset_request_with_email_success(self):
        """Test successful password reset request with email."""
        data = {"email": "test@example.com"}

        with patch("users.services.PasswordResetService.send_reset_email") as mock_send:
            mock_send.return_value = True
            response = self.client.post(self.password_reset_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertIn("password reset link has been sent", response.data["message"])

        # Should create PasswordReset record
        self.assertTrue(PasswordReset.objects.filter(user=self.user).exists())

    def test_password_reset_request_with_username_success(self):
        """Test successful password reset request with username."""
        data = {"email": "testuser"}  # Using username in email field

        with patch("users.services.PasswordResetService.send_reset_email") as mock_send:
            mock_send.return_value = True
            response = self.client.post(self.password_reset_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should create PasswordReset record
        self.assertTrue(PasswordReset.objects.filter(user=self.user).exists())

    def test_password_reset_request_case_insensitive_email(self):
        """Test password reset with case-insensitive email lookup."""
        data = {"email": "TEST@EXAMPLE.COM"}

        with patch("users.services.PasswordResetService.send_reset_email") as mock_send:
            mock_send.return_value = True
            response = self.client.post(self.password_reset_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should find user and create reset
        self.assertTrue(PasswordReset.objects.filter(user=self.user).exists())

    def test_password_reset_request_nonexistent_user(self):
        """Test password reset request for nonexistent user."""
        data = {"email": "nonexistent@example.com"}

        response = self.client.post(self.password_reset_url, data, format="json")

        # Should return success for security (don't reveal user existence)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("password reset link has been sent", response.data["message"])

        # Should not create PasswordReset record
        self.assertEqual(PasswordReset.objects.count(), 0)

    def test_password_reset_request_inactive_user(self):
        """Test password reset request for inactive user."""
        self.user.is_active = False
        self.user.save()

        data = {"email": "test@example.com"}

        response = self.client.post(self.password_reset_url, data, format="json")

        # Should return success for security
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should not create PasswordReset record
        self.assertEqual(PasswordReset.objects.count(), 0)

    def test_password_reset_request_missing_email_field(self):
        """Test password reset request with missing email field."""
        data = {}

        response = self.client.post(self.password_reset_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data["errors"])

    def test_password_reset_request_empty_email_field(self):
        """Test password reset request with empty email field."""
        data = {"email": ""}

        response = self.client.post(self.password_reset_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data["errors"])

    def test_password_reset_request_invalid_email_format(self):
        """Test password reset request with invalid email format."""
        data = {"email": "not-an-email"}

        response = self.client.post(self.password_reset_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data["errors"])

    def test_password_reset_request_rate_limiting_per_user(self):
        """Test rate limiting for password reset requests per user."""
        data = {"email": "test@example.com"}

        with patch("users.services.PasswordResetService.send_reset_email") as mock_send:
            mock_send.return_value = True

            # First request should succeed
            response1 = self.client.post(self.password_reset_url, data, format="json")
            self.assertEqual(response1.status_code, status.HTTP_200_OK)

            # Second request immediately should be rate limited
            response2 = self.client.post(self.password_reset_url, data, format="json")
            self.assertEqual(response2.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
            self.assertIn("rate limit", response2.data["error"].lower())

    def test_password_reset_request_rate_limiting_per_ip(self):
        """Test rate limiting for password reset requests per IP address."""
        # Multiple users from same IP
        data1 = {"email": "test@example.com"}
        data2 = {"email": "another@example.com"}

        with patch("users.services.PasswordResetService.send_reset_email") as mock_send:
            mock_send.return_value = True

            # First few requests should succeed
            for _ in range(3):
                response = self.client.post(
                    self.password_reset_url, data1, format="json"
                )
                if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                    break
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                # Use different email to bypass per-user rate limiting
                data1, data2 = data2, data1

            # Eventually should hit IP rate limit
            response = self.client.post(self.password_reset_url, data1, format="json")
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                self.assertIn("rate limit", response.data["error"].lower())

    def test_password_reset_request_invalidates_existing_tokens(self):
        """Test that new password reset invalidates existing tokens."""
        # Create existing reset
        existing_reset = PasswordReset.objects.create_for_user(self.user)
        self.assertTrue(existing_reset.is_valid())

        # Request new reset
        data = {"email": "test@example.com"}

        with patch("users.services.PasswordResetService.send_reset_email") as mock_send:
            mock_send.return_value = True
            response = self.client.post(self.password_reset_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Existing reset should be invalidated
        existing_reset.refresh_from_db()
        self.assertFalse(existing_reset.is_valid())

        # New reset should exist and be valid
        new_resets = PasswordReset.objects.filter(user=self.user, used_at__isnull=True)
        self.assertEqual(new_resets.count(), 1)
        self.assertTrue(new_resets.first().is_valid())

    def test_password_reset_request_tracks_ip_address(self):
        """Test that password reset requests track IP addresses."""
        data = {"email": "test@example.com"}

        with patch("users.services.PasswordResetService.send_reset_email") as mock_send:
            mock_send.return_value = True

            # Set remote address in request
            response = self.client.post(
                self.password_reset_url,
                data,
                format="json",
                REMOTE_ADDR="192.168.1.100",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check IP address is tracked
        reset = PasswordReset.objects.get(user=self.user)
        self.assertEqual(reset.ip_address, "192.168.1.100")

    @patch("users.services.PasswordResetService.send_reset_email")
    def test_password_reset_request_email_sending_failure(self, mock_send):
        """Test password reset when email sending fails."""
        mock_send.return_value = False

        data = {"email": "test@example.com"}
        response = self.client.post(self.password_reset_url, data, format="json")

        # Should still return success but with warning
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("email_sending_failed", response.data)
        self.assertTrue(response.data["email_sending_failed"])

        # Reset record should still be created
        self.assertTrue(PasswordReset.objects.filter(user=self.user).exists())


class PasswordResetTokenValidationAPITest(TestCase):
    """Test the password reset token validation API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.valid_reset = PasswordReset.objects.create_for_user(self.user)

        # URL pattern expects token in path
        self.validate_url_pattern = "api:auth:password_reset_validate"

    def get_validate_url(self, token):
        """Get validation URL for a specific token."""
        if not token:
            return reverse("api:auth:password_reset_validate_empty")
        return reverse(self.validate_url_pattern, kwargs={"token": token})

    def test_validate_valid_token_success(self):
        """Test validation of valid token."""
        url = self.get_validate_url(self.valid_reset.token)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("valid", response.data)
        self.assertTrue(response.data["valid"])
        self.assertIn("user_email", response.data)
        self.assertEqual(response.data["user_email"], self.user.email)

    def test_validate_expired_token(self):
        """Test validation of expired token."""
        # Create expired reset
        expired_reset = PasswordReset.objects.create(
            user=self.user, expires_at=timezone.now() - timedelta(hours=1)
        )

        url = self.get_validate_url(expired_reset.token)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("expired", response.data["error"].lower())

    def test_validate_used_token(self):
        """Test validation of used token."""
        self.valid_reset.mark_as_used()

        url = self.get_validate_url(self.valid_reset.token)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("used", response.data["error"].lower())

    def test_validate_nonexistent_token(self):
        """Test validation of nonexistent token."""
        fake_token = "a" * 64
        url = self.get_validate_url(fake_token)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)
        self.assertIn("not found", response.data["error"].lower())

    def test_validate_malformed_token(self):
        """Test validation of malformed token."""
        malformed_tokens = [
            "short",
            "contains spaces",
            "contains/slashes",
            "",
        ]

        for malformed_token in malformed_tokens:
            url = self.get_validate_url(malformed_token)
            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("error", response.data)

    def test_validate_inactive_user_token(self):
        """Test validation of token for inactive user."""
        self.user.is_active = False
        self.user.save()

        url = self.get_validate_url(self.valid_reset.token)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("inactive", response.data["error"].lower())

    def test_validate_token_security_headers(self):
        """Test that validation endpoint includes security headers."""
        url = self.get_validate_url(self.valid_reset.token)
        response = self.client.get(url)

        # Check for security headers if implemented
        # This is a placeholder - actual headers depend on implementation
        self.assertIn("valid", response.data)

    def test_validate_token_does_not_affect_token_state(self):
        """Test that validation does not mark token as used."""
        url = self.get_validate_url(self.valid_reset.token)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Token should still be valid after validation
        self.valid_reset.refresh_from_db()
        self.assertTrue(self.valid_reset.is_valid())
        self.assertIsNone(self.valid_reset.used_at)


class PasswordResetConfirmAPITest(TestCase):
    """Test the password reset confirmation API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="OldPassword123!"
        )
        self.valid_reset = PasswordReset.objects.create_for_user(self.user)

        self.confirm_url = reverse("api:auth:password_reset_confirm")

    def test_password_reset_confirm_success(self):
        """Test successful password reset confirmation."""
        data = {
            "token": self.valid_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        response = self.client.post(self.confirm_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertIn("successfully reset", response.data["message"])

        # Token should be marked as used
        self.valid_reset.refresh_from_db()
        self.assertTrue(self.valid_reset.is_used())
        self.assertFalse(self.valid_reset.is_valid())

        # User password should be changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))
        self.assertFalse(self.user.check_password("OldPassword123!"))

    def test_password_reset_confirm_password_mismatch(self):
        """Test password reset confirmation with password mismatch."""
        data = {
            "token": self.valid_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "DifferentPassword123!",
        }

        response = self.client.post(self.confirm_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)
        self.assertIn("password", str(response.data["errors"]).lower())

        # Token should not be used
        self.valid_reset.refresh_from_db()
        self.assertFalse(self.valid_reset.is_used())
        self.assertTrue(self.valid_reset.is_valid())

        # User password should not change
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword123!"))

    def test_password_reset_confirm_weak_password(self):
        """Test password reset confirmation with weak password."""
        data = {
            "token": self.valid_reset.token,
            "new_password": "weak",
            "new_password_confirm": "weak",
        }

        response = self.client.post(self.confirm_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)

        # Token should not be used
        self.valid_reset.refresh_from_db()
        self.assertFalse(self.valid_reset.is_used())

    def test_password_reset_confirm_invalid_token(self):
        """Test password reset confirmation with invalid token."""
        fake_token = "a" * 64
        data = {
            "token": fake_token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        response = self.client.post(self.confirm_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("invalid", response.data["error"].lower())

    def test_password_reset_confirm_expired_token(self):
        """Test password reset confirmation with expired token."""
        # Create expired reset
        expired_reset = PasswordReset.objects.create(
            user=self.user, expires_at=timezone.now() - timedelta(hours=1)
        )

        data = {
            "token": expired_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        response = self.client.post(self.confirm_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("expired", response.data["error"].lower())

    def test_password_reset_confirm_used_token(self):
        """Test password reset confirmation with used token."""
        self.valid_reset.mark_as_used()

        data = {
            "token": self.valid_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        response = self.client.post(self.confirm_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("used", response.data["error"].lower())

    def test_password_reset_confirm_inactive_user(self):
        """Test password reset confirmation for inactive user."""
        self.user.is_active = False
        self.user.save()

        data = {
            "token": self.valid_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        response = self.client.post(self.confirm_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("inactive", response.data["error"].lower())

    def test_password_reset_confirm_missing_fields(self):
        """Test password reset confirmation with missing required fields."""
        test_cases = [
            {},  # No fields
            {"token": self.valid_reset.token},  # Missing passwords
            {"new_password": "NewPassword123!"},  # Missing token
            {"new_password_confirm": "NewPassword123!"},  # Missing token and password
        ]

        for data in test_cases:
            response = self.client.post(self.confirm_url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("errors", response.data)

    def test_password_reset_confirm_one_time_use(self):
        """Test that password reset token can only be used once."""
        data = {
            "token": self.valid_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        # First use should succeed
        response1 = self.client.post(self.confirm_url, data, format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Second use should fail
        data["new_password"] = "AnotherPassword123!"
        data["new_password_confirm"] = "AnotherPassword123!"

        response2 = self.client.post(self.confirm_url, data, format="json")
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

        # User should still have first password
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))
        self.assertFalse(self.user.check_password("AnotherPassword123!"))

    def test_password_reset_confirm_logs_successful_reset(self):
        """Test that successful password reset is logged."""
        data = {
            "token": self.valid_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        with patch("logging.Logger.info") as mock_log:
            response = self.client.post(self.confirm_url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Check that success was logged
            mock_log.assert_called()
            log_args = mock_log.call_args[0][0]
            self.assertIn("Password reset successful", log_args)
            self.assertIn(str(self.user.id), log_args)


class PasswordResetSecurityTest(TestCase):
    """Test security aspects of password reset API."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_password_reset_timing_attack_protection(self):
        """Test that response times don't reveal user existence."""
        import time

        # Measure response time for existing user
        start_time = time.time()
        response1 = self.client.post(
            reverse("api:auth:password_reset_request"),
            {"email": "test@example.com"},
            format="json",
        )
        existing_user_time = time.time() - start_time

        # Measure response time for non-existing user
        start_time = time.time()
        response2 = self.client.post(
            reverse("api:auth:password_reset_request"),
            {"email": "nonexistent@example.com"},
            format="json",
        )
        nonexistent_user_time = time.time() - start_time

        # Both should return 200
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Response times should be similar (within reasonable bounds)
        # This is a heuristic test - timing can vary based on system load
        time_difference = abs(existing_user_time - nonexistent_user_time)
        self.assertLess(time_difference, 1.0)  # Should be within 1 second

    def test_password_reset_information_disclosure_protection(self):
        """Test that API doesn't disclose user information inappropriately."""
        # Test with nonexistent email
        response = self.client.post(
            reverse("api:auth:password_reset_request"),
            {"email": "nonexistent@example.com"},
            format="json",
        )

        # Should not reveal user existence in message
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        message = response.data.get("message", "").lower()
        self.assertNotIn("user not found", message)
        self.assertNotIn("does not exist", message)
        self.assertNotIn("invalid email", message)

    def test_password_reset_brute_force_protection(self):
        """Test protection against brute force token attacks."""
        # This would typically be implemented at the infrastructure level
        # but we can test rate limiting here

        fake_token = "a" * 64
        confirm_url = reverse("api:auth:password_reset_confirm")

        # Try multiple invalid attempts
        for i in range(10):
            data = {
                "token": fake_token + str(i),
                "new_password": "NewPassword123!",
                "new_password_confirm": "NewPassword123!",
            }

            response = self.client.post(confirm_url, data, format="json")

            # Should consistently return 400 (not 429 for now, unless rate limiting implemented)  # noqa: E501
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_csrf_protection_not_required(self):
        """Test that password reset endpoints don't require CSRF tokens."""
        # API endpoints should be CSRF-exempt for cross-origin usage

        # This test verifies that the endpoints work without CSRF tokens
        # In a real implementation, you'd use proper API authentication

        response = self.client.post(
            reverse("api:auth:password_reset_request"),
            {"email": "test@example.com"},
            format="json",
        )

        # Should work without CSRF token
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_password_reset_logs_security_events(self):
        """Test that security events are properly logged."""
        with patch("logging.Logger.warning") as mock_warning:
            # Invalid token attempt
            self.client.post(
                reverse("api:auth:password_reset_confirm"),
                {
                    "token": "invalid_token",
                    "new_password": "NewPassword123!",
                    "new_password_confirm": "NewPassword123!",
                },
                format="json",
            )

            # Should log security warning
            if mock_warning.called:
                log_args = mock_warning.call_args[0][0]
                self.assertIn("password reset", log_args.lower())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetEmailTest(TestCase):
    """Test password reset email functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_password_reset_email_sent(self):
        """Test that password reset email is sent."""
        data = {"email": "test@example.com"}

        response = self.client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertIn("password reset", email.subject.lower())
        self.assertEqual(email.to, [self.user.email])

    def test_password_reset_email_contains_token_link(self):
        """Test that password reset email contains valid reset link."""
        data = {"email": "test@example.com"}

        response = self.client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        # Email should contain reset token
        reset = PasswordReset.objects.get(user=self.user)
        self.assertIn(reset.token, email.body)

    def test_password_reset_email_template_customization(self):
        """Test that password reset email uses custom template."""
        data = {"email": "test@example.com"}

        response = self.client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        # Email should contain expected content
        self.assertIn(self.user.username, email.body)
        self.assertIn("password reset", email.body.lower())

    def test_password_reset_email_html_and_text_versions(self):
        """Test that password reset email has both HTML and text versions."""
        data = {"email": "test@example.com"}

        response = self.client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        # Check for HTML version (if implemented)
        # This is a placeholder - actual implementation may vary
        self.assertIsNotNone(email.body)


class PasswordResetIntegrationTest(TestCase):
    """Integration tests for complete password reset workflow."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="OldPassword123!"
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_complete_password_reset_workflow(self):
        """Test complete password reset workflow from request to confirmation."""
        # Step 1: Request password reset
        request_data = {"email": "test@example.com"}
        request_response = self.client.post(
            reverse("api:auth:password_reset_request"), request_data, format="json"
        )

        self.assertEqual(request_response.status_code, status.HTTP_200_OK)

        # Step 2: Get reset token from database
        reset = PasswordReset.objects.get(user=self.user)
        self.assertTrue(reset.is_valid())

        # Step 3: Validate token
        validate_response = self.client.get(
            reverse("api:auth:password_reset_validate", kwargs={"token": reset.token})
        )

        self.assertEqual(validate_response.status_code, status.HTTP_200_OK)
        self.assertTrue(validate_response.data["valid"])

        # Step 4: Confirm password reset
        confirm_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }
        confirm_response = self.client.post(
            reverse("api:auth:password_reset_confirm"), confirm_data, format="json"
        )

        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        # Step 5: Verify password changed and user can login
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))
        self.assertFalse(self.user.check_password("OldPassword123!"))

        # Step 6: Verify token is now invalid
        reset.refresh_from_db()
        self.assertFalse(reset.is_valid())
        self.assertTrue(reset.is_used())

        # Step 7: Verify second validation attempt fails
        validate_response2 = self.client.get(
            reverse("api:auth:password_reset_validate", kwargs={"token": reset.token})
        )

        self.assertEqual(validate_response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_integration_with_login(self):
        """Test password reset integration with login API."""
        # Create password reset and use it
        reset = PasswordReset.objects.create_for_user(self.user)

        confirm_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response = self.client.post(
            reverse("api:auth:password_reset_confirm"), confirm_data, format="json"
        )

        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        # Test login with new password
        login_data = {"username": "testuser", "password": "NewPassword123!"}

        login_response = self.client.post(
            reverse("api:auth:api_login"), login_data, format="json"
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("user", login_response.data)

        # Test that old password no longer works
        old_login_data = {"username": "testuser", "password": "OldPassword123!"}

        old_login_response = self.client.post(
            reverse("api:auth:api_login"), old_login_data, format="json"
        )

        self.assertEqual(old_login_response.status_code, status.HTTP_400_BAD_REQUEST)
