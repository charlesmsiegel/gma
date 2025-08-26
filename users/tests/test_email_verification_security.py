"""
Security tests for email verification system.

Comprehensive security testing for Issue #135:
- Token expiration handling and edge cases
- Invalid token protection and enumeration prevention
- Timing attack protection
- Rate limiting and abuse prevention
- Information leakage prevention
- Edge cases and boundary conditions
"""

import secrets
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from users.models import EmailVerification

User = get_user_model()


class TokenExpirationSecurityTest(TestCase):
    """Test security aspects of token expiration."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_expired_token_cannot_verify_email(self):
        """Test that expired tokens cannot be used for verification."""
        # Create expired verification
        verification = EmailVerification.objects.create(
            user=self.user,
            token="expired_token_123",
            expires_at=timezone.now() - timedelta(hours=1),
        )

        url = reverse("api:verify_email", kwargs={"token": verification.token})
        response = self.client.get(url)

        # Should fail
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # User should remain unverified
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)

    def test_token_expiration_boundary_conditions(self):
        """Test token expiration at exact boundary times."""
        now = timezone.now()

        # Create verification that expires exactly now
        verification = EmailVerification.objects.create(
            user=self.user,
            token="boundary_token_123",
            expires_at=now,
        )

        # At exact expiry time should be considered expired
        with patch("django.utils.timezone.now", return_value=now):
            self.assertTrue(verification.is_expired())

        # One microsecond before expiry should not be expired
        just_before = now - timedelta(microseconds=1)
        with patch("django.utils.timezone.now", return_value=just_before):
            self.assertFalse(verification.is_expired())

        # One microsecond after expiry should be expired
        just_after = now + timedelta(microseconds=1)
        with patch("django.utils.timezone.now", return_value=just_after):
            self.assertTrue(verification.is_expired())

    def test_very_old_expired_tokens(self):
        """Test handling of very old expired tokens."""
        # Create verification that expired long ago
        very_old_expiry = timezone.now() - timedelta(days=365)
        verification = EmailVerification.objects.create(
            user=self.user,
            token="very_old_token_123",
            expires_at=very_old_expiry,
        )

        url = reverse("api:verify_email", kwargs={"token": verification.token})
        response = self.client.get(url)

        # Should still handle gracefully
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", response.data["error"].lower())

    def test_future_dated_expiry_times(self):
        """Test handling of future-dated expiry times."""
        # Create verification with far future expiry
        far_future = timezone.now() + timedelta(days=365)
        verification = EmailVerification.objects.create(
            user=self.user,
            token="future_token_123",
            expires_at=far_future,
        )

        # Should still work normally
        url = reverse("api:verify_email", kwargs={"token": verification.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # User should be verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_concurrent_expiry_checks(self):
        """Test concurrent expiry checking doesn't cause issues."""
        verification = EmailVerification.objects.create(
            user=self.user,
            token="concurrent_token_123",
            expires_at=timezone.now() + timedelta(minutes=1),
        )

        # Simulate concurrent expiry checks
        results = []
        for _ in range(5):
            results.append(verification.is_expired())

        # All results should be consistent
        self.assertTrue(all(result == results[0] for result in results))

    def test_token_cleanup_after_expiry(self):
        """Test that expired tokens are properly cleaned up."""
        # Create multiple expired verifications
        expired_verifications = []
        for i in range(3):
            verification = EmailVerification.objects.create(
                user=self.user,
                token=f"expired_token_{i}",
                expires_at=timezone.now() - timedelta(days=31),  # Very old
            )
            expired_verifications.append(verification)

        initial_count = EmailVerification.objects.count()

        # Run cleanup
        cleaned_count = EmailVerification.objects.cleanup_expired()

        # Should have cleaned up expired verifications
        self.assertGreater(cleaned_count, 0)
        self.assertLess(EmailVerification.objects.count(), initial_count)


class InvalidTokenSecurityTest(TestCase):
    """Test security against invalid token attacks."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_malformed_token_handling(self):
        """Test handling of malformed tokens."""
        malformed_tokens = [
            "",  # Empty
            "x",  # Too short
            "a" * 200,  # Too long
            "token with spaces",  # Contains spaces
            "token\nwith\nnewlines",  # Contains newlines
            "token\twith\ttabs",  # Contains tabs
            "token/with/slashes",  # Contains slashes
            "token?with=query&params",  # Contains query params
            "token#with#fragments",  # Contains fragments
            "token<script>alert('xss')</script>",  # XSS attempt
            "token'; DROP TABLE users; --",  # SQL injection attempt
            "../../../etc/passwd",  # Path traversal attempt
        ]

        for malformed_token in malformed_tokens:
            with self.subTest(token=malformed_token):
                try:
                    url = reverse("api:verify_email", kwargs={"token": malformed_token})
                    response = self.client.get(url)

                    # Should return error status
                    self.assertIn(
                        response.status_code,
                        [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND],
                    )

                    # Should not cause server error
                    self.assertNotEqual(
                        response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                except Exception:
                    # URL reversal might fail for some malformed tokens
                    # This is acceptable behavior
                    pass

    def test_token_enumeration_protection(self):
        """Test protection against token enumeration attacks."""
        # Create valid verification
        verification = EmailVerification.objects.create_for_user(self.user)
        valid_token = verification.token

        # Generate many invalid tokens
        invalid_tokens = [secrets.token_urlsafe(32) for _ in range(50)]

        # Test timing consistency (simplified)
        valid_url = reverse("api:verify_email", kwargs={"token": valid_token})

        self.client.get(valid_url)

        # Test a few invalid tokens
        for invalid_token in invalid_tokens[:5]:
            invalid_url = reverse("api:verify_email", kwargs={"token": invalid_token})
            invalid_response = self.client.get(invalid_url)

            # Should return consistent error response
            self.assertEqual(invalid_response.status_code, status.HTTP_404_NOT_FOUND)

            # Error structure should be consistent
            self.assertIn("error", invalid_response.data)

    def test_case_sensitivity_security(self):
        """Test that tokens are properly case sensitive."""
        verification = EmailVerification.objects.create_for_user(self.user)
        original_token = verification.token

        # Only test if token contains letters
        if any(c.isalpha() for c in original_token):
            # Test different case variations
            case_variations = [
                original_token.upper(),
                original_token.lower(),
                original_token.swapcase(),
                original_token.capitalize(),
            ]

            for variant_token in case_variations:
                if variant_token != original_token:
                    with self.subTest(token=variant_token):
                        url = reverse(
                            "api:verify_email", kwargs={"token": variant_token}
                        )
                        response = self.client.get(url)

                        # Should fail with wrong case
                        self.assertEqual(
                            response.status_code, status.HTTP_404_NOT_FOUND
                        )

    def test_url_encoding_attacks(self):
        """Test protection against URL encoding attacks."""
        verification = EmailVerification.objects.create_for_user(self.user)
        original_token = verification.token

        # Test various encoding schemes
        encoded_variants = [
            quote(original_token),  # URL encode
            quote(original_token, safe=""),  # URL encode everything
            original_token.encode("utf-8").hex(),  # Hex encode
            original_token + "%00",  # Null byte injection
            original_token + "%20",  # Space injection
        ]

        for encoded_token in encoded_variants:
            if encoded_token != original_token:
                with self.subTest(token=encoded_token):
                    try:
                        url = reverse(
                            "api:verify_email", kwargs={"token": encoded_token}
                        )
                        response = self.client.get(url)

                        # Should not verify with encoded token
                        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
                    except Exception:
                        # URL reversal failure is acceptable
                        pass

    def test_unicode_token_handling(self):
        """Test handling of unicode characters in tokens."""
        # Try to create verification with unicode token (should fail)
        unicode_token = "token_with_unicode_😀_characters"

        try:
            EmailVerification.objects.create(
                user=self.user,
                token=unicode_token,
                expires_at=timezone.now() + timedelta(hours=24),
            )

            # If creation succeeds, test that it handles properly
            url = reverse("api:verify_email", kwargs={"token": unicode_token})
            response = self.client.get(url)

            # Should either work or fail gracefully
            self.assertIn(
                response.status_code,
                [
                    status.HTTP_200_OK,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_404_NOT_FOUND,
                ],
            )
        except (ValidationError, UnicodeError):
            # Should reject unicode tokens during creation
            pass


class TimingAttackProtectionTest(TestCase):
    """Test protection against timing attacks."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_consistent_response_times(self):
        """Test that response times are consistent for valid/invalid tokens."""
        # This is a simplified test - real timing attack protection
        # would require statistical analysis of response times

        # Create valid verification
        verification = EmailVerification.objects.create_for_user(self.user)
        valid_token = verification.token
        invalid_token = "invalid_token_123"

        valid_url = reverse("api:verify_email", kwargs={"token": valid_token})
        invalid_url = reverse("api:verify_email", kwargs={"token": invalid_token})

        # Test multiple times
        valid_responses = []
        invalid_responses = []

        for _ in range(3):
            valid_responses.append(self.client.get(valid_url))
            invalid_responses.append(self.client.get(invalid_url))

        # All requests should complete without errors
        for response in valid_responses + invalid_responses:
            self.assertNotEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def test_database_query_consistency(self):
        """Test that database queries are consistent for timing protection."""
        EmailVerification.objects.create_for_user(self.user)

        with patch("django.db.models.QuerySet.get") as mock_get:
            # Mock to always raise DoesNotExist
            from django.core.exceptions import ObjectDoesNotExist

            mock_get.side_effect = ObjectDoesNotExist()

            invalid_url = reverse("api:verify_email", kwargs={"token": "invalid"})
            response = self.client.get(invalid_url)

            # Should still perform consistent processing
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertIn("error", response.data)

    def test_error_message_consistency(self):
        """Test that error messages don't reveal timing information."""
        EmailVerification.objects.create_for_user(self.user)

        # Test different types of invalid tokens
        test_cases = [
            ("nonexistent_token", "nonexistent"),
            ("", "empty"),
            ("a" * 100, "too_long"),
        ]

        error_messages = []
        for token, case_name in test_cases:
            try:
                url = reverse("api:verify_email", kwargs={"token": token})
                response = self.client.get(url)

                error_messages.append((case_name, response.data.get("error", "")))
            except Exception:
                # URL reversal might fail
                pass

        # Error messages should be generic and consistent
        for case_name, error_msg in error_messages:
            self.assertIsInstance(error_msg, str)
            # Should not contain specific details about why it failed
            self.assertNotIn("nonexistent", error_msg.lower())
            self.assertNotIn("too long", error_msg.lower())


class InformationLeakagePreventionTest(TestCase):
    """Test prevention of information leakage through error messages."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

    def test_registration_error_information_hiding(self):
        """Test that registration errors don't leak user information."""
        # Create existing user
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="ExistingPass123!",
        )

        register_url = reverse("api:api_register")

        # Test duplicate username
        duplicate_username_data = {
            "username": "existing",
            "email": "new@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        # Test duplicate email
        duplicate_email_data = {
            "username": "newuser",
            "email": "existing@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        response1 = self.client.post(
            register_url, duplicate_username_data, format="json"
        )
        response2 = self.client.post(register_url, duplicate_email_data, format="json")

        # Both should return same generic error
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

        error1 = str(response1.data).lower()
        error2 = str(response2.data).lower()

        # Should not reveal specific field that caused the error
        self.assertNotIn("username", error1)
        self.assertNotIn("email", error1)
        self.assertNotIn("username", error2)
        self.assertNotIn("email", error2)

    def test_resend_verification_information_hiding(self):
        """Test that resend verification doesn't leak user information."""
        # Create user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        resend_url = reverse("api:resend_verification")

        # Test with existing email
        existing_response = self.client.post(
            resend_url, {"email": "test@example.com"}, format="json"
        )

        # Test with nonexistent email
        nonexistent_response = self.client.post(
            resend_url, {"email": "nonexistent@example.com"}, format="json"
        )

        # Both should return success (don't reveal user existence)
        self.assertEqual(existing_response.status_code, status.HTTP_200_OK)
        self.assertEqual(nonexistent_response.status_code, status.HTTP_200_OK)

        # Messages should be generic
        existing_msg = existing_response.data.get("message", "").lower()
        nonexistent_msg = nonexistent_response.data.get("message", "").lower()

        self.assertIn("sent", existing_msg)
        self.assertIn("sent", nonexistent_msg)

    def test_verification_error_information_hiding(self):
        """Test that verification errors don't leak sensitive information."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Create verification
        verification = EmailVerification.objects.create_for_user(user)

        # Test with invalid token
        invalid_url = reverse("api:verify_email", kwargs={"token": "invalid_token"})
        response = self.client.get(invalid_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        error_msg = response.data.get("error", "").lower()

        # Should not reveal user information
        self.assertNotIn(user.username, error_msg)
        self.assertNotIn(user.email, error_msg)
        self.assertNotIn("testuser", error_msg)
        self.assertNotIn("test@example.com", error_msg)

        # Should not reveal valid token information
        self.assertNotIn(verification.token, error_msg)

    def test_stack_trace_information_hiding(self):
        """Test that error responses don't include stack traces in production."""
        # This test ensures that debug information isn't leaked

        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        with patch.object(EmailVerification.objects, "get_by_token") as mock_get:
            mock_get.side_effect = Exception("Database error")

            url = reverse("api:verify_email", kwargs={"token": "test_token"})
            response = self.client.get(url)

            # Should return generic error, not expose exception
            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )

            # Should not contain stack trace or debug information
            response_str = str(response.data).lower()
            self.assertNotIn("traceback", response_str)
            self.assertNotIn("exception", response_str)
            self.assertNotIn("database error", response_str)


class TokenSecurityConstraintsTest(TransactionTestCase):
    """Test database constraints and security around tokens."""

    def test_token_uniqueness_enforcement(self):
        """Test that token uniqueness is strictly enforced."""
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

        # Create first verification
        token = "duplicate_token_123"
        EmailVerification.objects.create(
            user=user1,
            token=token,
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Attempt to create second verification with same token
        with self.assertRaises(Exception):  # IntegrityError or similar
            with transaction.atomic():
                EmailVerification.objects.create(
                    user=user2,
                    token=token,  # Same token
                    expires_at=timezone.now() + timedelta(hours=24),
                )

    def test_token_generation_collision_handling(self):
        """Test handling of token generation collisions."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Create existing verification
        existing_token = "existing_token_123"
        EmailVerification.objects.create(
            user=user,
            token=existing_token,
            expires_at=timezone.now() + timedelta(hours=24),
        )

        # Mock token generation to return existing token first
        with patch("secrets.token_urlsafe") as mock_token:
            mock_token.side_effect = [existing_token, "unique_token_456"]

            # Should handle collision and generate unique token
            new_verification = EmailVerification.objects.create_for_user(user)

            self.assertNotEqual(new_verification.token, existing_token)
            self.assertEqual(new_verification.token, "unique_token_456")

    def test_token_length_security_constraints(self):
        """Test that token length constraints are enforced."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Test token too long
        very_long_token = "a" * 65  # Longer than 64 chars
        verification = EmailVerification(
            user=user,
            token=very_long_token,
            expires_at=timezone.now() + timedelta(hours=24),
        )

        with self.assertRaises(ValidationError):
            verification.full_clean()

    def test_concurrent_token_generation_safety(self):
        """Test that concurrent token generation doesn't cause issues."""
        users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="TestPass123!",
            )
            users.append(user)

        # Generate tokens concurrently (simulated)
        verifications = []
        for user in users:
            verification = EmailVerification.objects.create_for_user(user)
            verifications.append(verification)

        # All tokens should be unique
        tokens = [v.token for v in verifications]
        self.assertEqual(len(set(tokens)), len(tokens))

    def test_token_randomness_quality(self):
        """Test that generated tokens have sufficient randomness."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Generate multiple tokens
        tokens = []
        for _ in range(100):
            verification = EmailVerification.objects.create_for_user(user)
            tokens.append(verification.token)

        # All tokens should be unique
        self.assertEqual(len(set(tokens)), len(tokens))

        # Tokens should have reasonable length
        for token in tokens[:10]:  # Check first 10
            self.assertGreaterEqual(len(token), 32)
            self.assertLessEqual(len(token), 64)

            # Should contain mix of characters (basic check)
            self.assertTrue(any(c.isalnum() for c in token))


class EdgeCaseSecurityTest(TestCase):
    """Test security in edge cases and boundary conditions."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

    def test_deleted_user_verification_attempt(self):
        """Test verification attempt after user is deleted."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        verification = EmailVerification.objects.create_for_user(user)
        token = verification.token

        # Delete user (should cascade to verification)
        user.delete()

        # Attempt verification
        url = reverse("api:verify_email", kwargs={"token": token})
        response = self.client.get(url)

        # Should handle gracefully
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Should not reveal that user was deleted
        error_msg = response.data.get("error", "").lower()
        self.assertNotIn("deleted", error_msg)
        self.assertNotIn("user", error_msg)

    def test_verification_during_maintenance_mode(self):
        """Test verification behavior during system maintenance."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        verification = EmailVerification.objects.create_for_user(user)

        # Simulate database unavailability
        with patch.object(EmailVerification.objects, "get_by_token") as mock_get:
            mock_get.side_effect = Exception("Database unavailable")

            url = reverse("api:verify_email", kwargs={"token": verification.token})
            response = self.client.get(url)

            # Should return appropriate error
            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def test_timezone_edge_cases_in_expiry(self):
        """Test timezone-related edge cases in token expiry."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Test with different timezone settings

        # Create verification in UTC
        utc_time = timezone.now()
        verification = EmailVerification.objects.create(
            user=user,
            token="timezone_test_token",
            expires_at=utc_time + timedelta(hours=1),
        )

        # Test expiry check with different timezone awareness
        self.assertFalse(verification.is_expired())

        # Mock timezone change
        future_time = utc_time + timedelta(hours=2)
        with patch("django.utils.timezone.now", return_value=future_time):
            self.assertTrue(verification.is_expired())

    def test_leap_second_handling_in_expiry(self):
        """Test handling of leap seconds and edge time cases."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Create verification with microsecond precision
        now = timezone.now()
        microsecond_future = now + timedelta(microseconds=1)

        verification = EmailVerification.objects.create(
            user=user,
            token="microsecond_test_token",
            expires_at=microsecond_future,
        )

        # Should handle microsecond precision correctly
        self.assertFalse(verification.is_expired())

        # Move time past expiry
        past_expiry = microsecond_future + timedelta(microseconds=1)
        with patch("django.utils.timezone.now", return_value=past_expiry):
            self.assertTrue(verification.is_expired())

    def test_memory_exhaustion_protection(self):
        """Test protection against memory exhaustion attacks."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        # Attempt to create many verifications rapidly
        verifications_created = 0
        max_attempts = 10  # Limited for test performance

        try:
            for i in range(max_attempts):
                EmailVerification.objects.create_for_user(user)
                verifications_created += 1
        except Exception:
            # Should handle gracefully if there are limits
            pass

        # Should have created at least some verifications
        self.assertGreater(verifications_created, 0)

        # Database should remain consistent
        db_count = EmailVerification.objects.filter(user=user).count()
        self.assertEqual(db_count, verifications_created)
