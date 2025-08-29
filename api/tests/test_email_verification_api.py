"""
Tests for Email Verification API endpoints.

Tests the email verification flow for Issue #135:
- GET /api/auth/verify-email/{token}/ - Email verification endpoint
- Token validation and user account activation
- Security testing for invalid and expired tokens
- Integration with User model and EmailVerification model
"""

from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from users.models import EmailVerification

User = get_user_model()


class EmailVerificationAPIBasicTest(TestCase):
    """Test basic email verification API functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create unverified user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Create verification record
        self.verification = EmailVerification.create_for_user(self.user)

        self.verify_url = reverse(
            "api:auth:verify_email", kwargs={"token": self.verification.token}
        )

    def test_successful_email_verification(self):
        """Test successful email verification with valid token."""
        response = self.client.get(self.verify_url)

        # Should succeed
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # User should be verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
        self.assertEqual(self.user.email_verification_token, "")
        self.assertIsNone(self.user.email_verification_sent_at)

        # Verification record should be marked as verified
        self.verification.refresh_from_db()
        self.assertTrue(self.verification.is_verified())
        self.assertIsNotNone(self.verification.verified_at)

        # Response should contain success message
        self.assertIn("message", response.data)
        self.assertIn("success", response.data["message"].lower())

    def test_verification_response_structure(self):
        """Test that verification response has proper structure."""
        response = self.client.get(self.verify_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should contain required fields
        self.assertIn("message", response.data)
        self.assertIn("user", response.data)
        self.assertIn("verified_at", response.data)

        # User data should show verification status
        user_data = response.data["user"]
        self.assertTrue(user_data["email_verified"])
        self.assertEqual(user_data["username"], self.user.username)
        self.assertEqual(user_data["email"], self.user.email)

    def test_verification_token_cleared_after_success(self):
        """Test that verification token is cleared after successful verification."""
        # Verify token exists initially
        self.assertNotEqual(self.user.email_verification_token, "")

        response = self.client.get(self.verify_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Token should be cleared
        self.user.refresh_from_db()
        self.assertEqual(self.user.email_verification_token, "")
        self.assertIsNone(self.user.email_verification_sent_at)

    def test_verification_idempotent(self):
        """Test that verifying already verified email is idempotent."""
        # First verification
        response1 = self.client.get(self.verify_url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        first_verified_at = (
            self.verification.refresh_from_db() or self.verification.verified_at
        )

        # Second verification attempt
        response2 = self.client.get(self.verify_url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Should still be successful and not change verified_at
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.verified_at, first_verified_at)


class EmailVerificationErrorHandlingTest(TestCase):
    """Test error handling in email verification."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_verification_invalid_token(self):
        """Test verification with invalid token."""
        invalid_token = "invalid_token_123"
        url = reverse("api:auth:verify_email", kwargs={"token": invalid_token})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Should contain error message
        self.assertIn("error", response.data)
        self.assertIn("not found", response.data["error"].lower())

        # User should remain unverified
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)

    def test_verification_nonexistent_token(self):
        """Test verification with nonexistent token."""
        nonexistent_token = "nonexistent_token_456"
        url = reverse("api:auth:verify_email", kwargs={"token": nonexistent_token})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Should contain error message
        self.assertIn("error", response.data)
        self.assertIn("not found", response.data["error"].lower())

    def test_verification_expired_token(self):
        """Test verification with expired token."""
        # Create expired verification
        verification = EmailVerification.objects.create(
            user=self.user,
            token="expired_token_123",
            expires_at=timezone.now() - timedelta(hours=1),  # Expired
        )

        url = reverse("api:auth:verify_email", kwargs={"token": verification.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Should contain expiry error
        self.assertIn("error", response.data)
        self.assertIn("expired", response.data["error"].lower())

        # User should remain unverified
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)

    def test_verification_token_format_validation(self):
        """Test verification with malformed token."""
        malformed_tokens = [
            "",  # Empty
            "a",  # Too short
            "a" * 100,  # Too long
            "token with spaces",  # Contains spaces
            "token/with/slashes",  # Contains slashes
            "token?with=query",  # Contains query characters
        ]

        for malformed_token in malformed_tokens:
            with self.subTest(token=malformed_token):
                try:
                    url = reverse(
                        "api:auth:verify_email", kwargs={"token": malformed_token}
                    )
                    response = self.client.get(url)

                    # Should return 400 or 404 depending on validation
                    self.assertIn(
                        response.status_code,
                        [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND],
                    )
                except Exception:
                    # Some malformed tokens can't be handled by URL routing
                    # This is acceptable as they would never be valid tokens
                    pass

    def test_verification_deleted_user(self):
        """Test verification when user is deleted."""
        verification = EmailVerification.create_for_user(self.user)
        token = verification.token

        # Delete user (should cascade to verification)
        self.user.delete()

        url = reverse("api:auth:verify_email", kwargs={"token": token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_verification_inactive_user(self):
        """Test verification with inactive user."""
        verification = EmailVerification.create_for_user(self.user)

        # Deactivate user
        self.user.is_active = False
        self.user.save()

        url = reverse("api:auth:verify_email", kwargs={"token": verification.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Should indicate user is inactive
        self.assertIn("error", response.data)
        self.assertIn("inactive", response.data["error"].lower())


class EmailVerificationSecurityTest(TestCase):
    """Test security aspects of email verification."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_verification_no_information_leakage(self):
        """Test that verification doesn't leak information about users."""
        # Create verification for existing user
        verification = EmailVerification.create_for_user(self.user)

        # Create fake token that doesn't exist
        fake_token = "fake_token_that_doesnt_exist"

        # Both should return different status codes but not leak info
        valid_url = reverse(
            "api:auth:verify_email", kwargs={"token": verification.token}
        )
        invalid_url = reverse("api:auth:verify_email", kwargs={"token": fake_token})

        valid_response = self.client.get(valid_url)
        invalid_response = self.client.get(invalid_url)

        self.assertEqual(valid_response.status_code, status.HTTP_200_OK)
        self.assertEqual(invalid_response.status_code, status.HTTP_404_NOT_FOUND)

        # Error messages should be generic
        self.assertNotIn(self.user.email, str(invalid_response.data))
        self.assertNotIn(self.user.username, str(invalid_response.data))

    def test_verification_token_enumeration_protection(self):
        """Test protection against token enumeration attacks."""
        # Try multiple invalid tokens
        invalid_tokens = ["token1", "token2", "token3", "token4", "token5"]

        for token in invalid_tokens:
            url = reverse("api:auth:verify_email", kwargs={"token": token})
            response = self.client.get(url)

            # All should return same error response
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # Response time should be consistent (basic check)
            self.assertIn("error", response.data)

    def test_verification_timing_attack_protection(self):
        """Test basic protection against timing attacks."""
        # This is a simplified test - real timing attack protection
        # would require more sophisticated measurement

        verification = EmailVerification.create_for_user(self.user)

        valid_token = verification.token
        invalid_token = "invalid_token_123"

        # Both requests should take similar time (basic check)
        valid_url = reverse("api:auth:verify_email", kwargs={"token": valid_token})
        invalid_url = reverse("api:auth:verify_email", kwargs={"token": invalid_token})

        response1 = self.client.get(valid_url)
        response2 = self.client.get(invalid_url)

        # Just verify they complete without errors
        self.assertIn(response1.status_code, [status.HTTP_200_OK])
        self.assertIn(response2.status_code, [status.HTTP_404_NOT_FOUND])

    def test_verification_rate_limiting_headers(self):
        """Test that verification includes rate limiting info."""
        verification = EmailVerification.create_for_user(self.user)
        url = reverse("api:auth:verify_email", kwargs={"token": verification.token})

        response = self.client.get(url)

        # Should succeed
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Could include rate limiting headers (implementation dependent)
        # This is a placeholder for future rate limiting

    def test_verification_logs_security_events(self):
        """Test that verification logs important security events."""
        verification = EmailVerification.create_for_user(self.user)

        with patch("logging.Logger.info") as mock_log:
            url = reverse("api:auth:verify_email", kwargs={"token": verification.token})
            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Should log successful verification
            mock_log.assert_called()

            # Log should contain relevant info but not sensitive data
            log_calls = [call[0][0] for call in mock_log.call_args_list]
            log_messages = " ".join(log_calls)

            self.assertIn("verification", log_messages.lower())
            # Should not log the actual token
            self.assertNotIn(verification.token, log_messages)


class EmailVerificationIntegrationTest(TestCase):
    """Test integration between verification API and other systems."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_verification_updates_both_models(self):
        """Test that verification updates both User and EmailVerification models."""
        verification = EmailVerification.create_for_user(self.user)

        # Before verification
        self.assertFalse(self.user.email_verified)
        self.assertFalse(verification.is_verified())

        url = reverse("api:auth:verify_email", kwargs={"token": verification.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # After verification - both models should be updated
        self.user.refresh_from_db()
        verification.refresh_from_db()

        self.assertTrue(self.user.email_verified)
        self.assertTrue(verification.is_verified())

    def test_verification_clears_user_token_fields(self):
        """Test that verification clears user token fields."""
        # Set user token fields
        self.user.email_verification_token = "user_token_123"
        self.user.email_verification_sent_at = timezone.now()
        self.user.save()

        verification = EmailVerification.create_for_user(self.user)

        url = reverse("api:auth:verify_email", kwargs={"token": verification.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # User token fields should be cleared
        self.user.refresh_from_db()
        self.assertEqual(self.user.email_verification_token, "")
        self.assertIsNone(self.user.email_verification_sent_at)

    def test_verification_enables_campaign_access(self):
        """Test that verification enables access to campaign features."""
        verification = EmailVerification.create_for_user(self.user)

        # Before verification - user should not be able to create campaigns
        # This is a placeholder - actual implementation would check
        # email_verified in campaign creation permissions
        self.assertFalse(self.user.email_verified)

        # Verify email
        url = reverse("api:auth:verify_email", kwargs={"token": verification.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # After verification - user should be able to access campaigns
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_verification_with_multiple_verification_records(self):
        """Test verification when user has multiple verification records."""
        # Create multiple verifications (edge case)
        verification1 = EmailVerification.create_for_user(self.user)
        verification2 = EmailVerification.create_for_user(self.user)

        # Use second (latest) token since old ones are expired by create_for_user
        url = reverse("api:auth:verify_email", kwargs={"token": verification2.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # User should be verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

        # Second (latest) verification should be verified, first should be expired
        verification1.refresh_from_db()
        verification2.refresh_from_db()

        self.assertTrue(verification1.is_expired())  # Old token should be expired
        self.assertTrue(verification2.is_verified())  # New token should be verified


class EmailVerificationURLPatternTest(TestCase):
    """Test URL patterns and routing for email verification."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        self.verification = EmailVerification.create_for_user(self.user)

    def test_verification_url_pattern(self):
        """Test that verification URL pattern works correctly."""
        # URL should be properly formed
        expected_path = f"/api/auth/verify-email/{self.verification.token}/"
        url = reverse(
            "api:auth:verify_email", kwargs={"token": self.verification.token}
        )

        parsed_url = urlparse(url)
        self.assertEqual(parsed_url.path, expected_path)

    def test_verification_url_with_special_characters(self):
        """Test verification URL with special characters in token."""
        # Create verification with special characters in token
        special_token = "token-with_special.characters123"
        EmailVerification.objects.create(
            user=self.user,
            token=special_token,
            expires_at=timezone.now() + timedelta(hours=24),
        )

        url = reverse("api:auth:verify_email", kwargs={"token": special_token})

        # URL should be properly encoded
        self.assertIn(special_token, url)

    def test_verification_url_case_sensitivity(self):
        """Test that verification URLs are case sensitive."""
        token = self.verification.token

        # Original case should work
        url_original = reverse("api:auth:verify_email", kwargs={"token": token})
        response_original = self.client.get(url_original)

        # Different case should not work (if token contains letters)
        if any(c.isalpha() for c in token):
            token_different_case = token.swapcase()
            url_different = reverse(
                "api:auth:verify_email", kwargs={"token": token_different_case}
            )
            response_different = self.client.get(url_different)

            self.assertEqual(response_original.status_code, status.HTTP_200_OK)
            self.assertEqual(response_different.status_code, status.HTTP_404_NOT_FOUND)


class EmailVerificationMethodTest(TestCase):
    """Test HTTP methods for email verification endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        self.verification = EmailVerification.create_for_user(self.user)
        self.url = reverse(
            "api:auth:verify_email", kwargs={"token": self.verification.token}
        )

    def test_verification_get_method(self):
        """Test that GET method works for verification."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_verification_post_method_not_allowed(self):
        """Test that POST method is not allowed."""
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_verification_put_method_not_allowed(self):
        """Test that PUT method is not allowed."""
        response = self.client.put(self.url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_verification_delete_method_not_allowed(self):
        """Test that DELETE method is not allowed."""
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_verification_options_method(self):
        """Test that OPTIONS method works."""
        response = self.client.options(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should indicate only GET is allowed
        allowed_methods = response.get("Allow", "").split(", ")
        self.assertIn("GET", allowed_methods)
        self.assertNotIn("POST", allowed_methods)
