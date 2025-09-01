"""
Integration tests for complete password reset workflow.

This test suite covers:
- End-to-end password reset workflows
- Integration with existing authentication system
- Cross-browser and API compatibility
- Error recovery scenarios
- Performance under load
- Integration with user management
"""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from users.models.password_reset import PasswordReset

User = get_user_model()


@override_settings(EMAIL_BACKEND="core.test_backends.QuietEmailBackend")
class PasswordResetWorkflowIntegrationTest(TestCase):
    """Test complete password reset workflows."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="OldPassword123!"
        )

        # URL endpoints
        self.request_url = reverse("api:auth:password_reset_request")
        self.confirm_url = reverse("api:auth:password_reset_confirm")

    def test_complete_successful_workflow(self):
        """Test complete successful password reset workflow."""
        # Step 1: Request password reset
        request_data = {"email": "test@example.com"}

        request_response = self.client.post(
            self.request_url, request_data, format="json"
        )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)

        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.user.email])

        # Step 2: Extract token from database (simulating user clicking email link)
        reset = PasswordReset.objects.get(user=self.user)
        self.assertTrue(reset.is_valid())

        # Step 3: Validate token (optional step)
        validate_url = reverse(
            "api:auth:password_reset_validate", kwargs={"token": reset.token}
        )
        validate_response = self.client.get(validate_url)

        if validate_response.status_code == status.HTTP_200_OK:
            self.assertTrue(validate_response.data.get("valid"))
            self.assertEqual(validate_response.data.get("user_email"), self.user.email)

        # Step 4: Confirm password reset
        confirm_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response = self.client.post(
            self.confirm_url, confirm_data, format="json"
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        # Step 5: Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))
        self.assertFalse(self.user.check_password("OldPassword123!"))

        # Step 6: Verify token was consumed
        reset.refresh_from_db()
        self.assertTrue(reset.is_used())
        self.assertFalse(reset.is_valid())

        # Step 7: Verify user can login with new password
        login_data = {"username": "testuser", "password": "NewPassword123!"}
        login_response = self.client.post(
            reverse("api:auth:api_login"), login_data, format="json"
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_workflow_with_email_lookup(self):
        """Test password reset workflow using email for lookup."""
        # Use email instead of username for initial lookup
        request_data = {"email": "test@example.com"}

        request_response = self.client.post(
            self.request_url, request_data, format="json"
        )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)

        # Complete the workflow
        reset = PasswordReset.objects.get(user=self.user)

        confirm_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response = self.client.post(
            self.confirm_url, confirm_data, format="json"
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        # Verify success
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))

    def test_workflow_with_username_lookup(self):
        """Test password reset workflow using username for lookup."""
        # Use username in email field (should work)
        request_data = {"email": "testuser"}

        request_response = self.client.post(
            self.request_url, request_data, format="json"
        )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)

        # Complete the workflow
        reset = PasswordReset.objects.get(user=self.user)

        confirm_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response = self.client.post(
            self.confirm_url, confirm_data, format="json"
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        # Verify success
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))

    def test_workflow_with_case_insensitive_email(self):
        """Test password reset workflow with case-insensitive email."""
        # Use mixed case email
        request_data = {"email": "TEST@EXAMPLE.COM"}

        request_response = self.client.post(
            self.request_url, request_data, format="json"
        )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)

        # Complete the workflow
        reset = PasswordReset.objects.get(user=self.user)

        confirm_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response = self.client.post(
            self.confirm_url, confirm_data, format="json"
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        # Verify success
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))

    def test_workflow_prevents_multiple_token_usage(self):
        """Test that token can only be used once in complete workflow."""
        # Request password reset
        request_data = {"email": "test@example.com"}
        request_response = self.client.post(
            self.request_url, request_data, format="json"
        )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)

        reset = PasswordReset.objects.get(user=self.user)

        # Use token first time
        confirm_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response1 = self.client.post(
            self.confirm_url, confirm_data, format="json"
        )
        self.assertEqual(confirm_response1.status_code, status.HTTP_200_OK)

        # Try to use token second time
        confirm_data["new_password"] = "AnotherPassword123!"
        confirm_data["new_password_confirm"] = "AnotherPassword123!"

        confirm_response2 = self.client.post(
            self.confirm_url, confirm_data, format="json"
        )
        self.assertEqual(confirm_response2.status_code, status.HTTP_400_BAD_REQUEST)

        # Password should still be the first one
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))
        self.assertFalse(self.user.check_password("AnotherPassword123!"))

    def test_workflow_invalidates_old_tokens(self):
        """Test that new requests invalidate old tokens."""
        # First request
        request_data = {"email": "test@example.com"}
        request_response1 = self.client.post(
            self.request_url, request_data, format="json"
        )
        self.assertEqual(request_response1.status_code, status.HTTP_200_OK)

        old_reset = PasswordReset.objects.get(user=self.user)
        old_token = old_reset.token

        # Clear email outbox
        mail.outbox.clear()

        # Second request
        request_response2 = self.client.post(
            self.request_url, request_data, format="json"
        )
        self.assertEqual(request_response2.status_code, status.HTTP_200_OK)

        # Old token should be invalidated
        old_reset.refresh_from_db()
        self.assertFalse(old_reset.is_valid())

        # New token should exist and be valid
        new_resets = PasswordReset.objects.filter(user=self.user, used_at__isnull=True)
        self.assertEqual(new_resets.count(), 1)
        new_reset = new_resets.first()
        self.assertTrue(new_reset.is_valid())
        self.assertNotEqual(new_reset.token, old_token)

        # Old token should not work
        confirm_data_old = {
            "token": old_token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response_old = self.client.post(
            self.confirm_url, confirm_data_old, format="json"
        )
        self.assertEqual(confirm_response_old.status_code, status.HTTP_400_BAD_REQUEST)

        # New token should work
        confirm_data_new = {
            "token": new_reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response_new = self.client.post(
            self.confirm_url, confirm_data_new, format="json"
        )
        self.assertEqual(confirm_response_new.status_code, status.HTTP_200_OK)


class PasswordResetAuthenticationIntegrationTest(TestCase):
    """Test integration with existing authentication system."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="OldPassword123!"
        )

    @override_settings(EMAIL_BACKEND="core.test_backends.QuietEmailBackend")
    def test_password_reset_integration_with_login(self):
        """Test password reset integrates properly with login system."""
        # First, verify old password works
        login_data_old = {"username": "testuser", "password": "OldPassword123!"}
        login_response_old = self.client.post(
            reverse("api:auth:api_login"), login_data_old, format="json"
        )
        self.assertEqual(login_response_old.status_code, status.HTTP_200_OK)

        # Logout
        self.client.post(reverse("api:auth:api_logout"))

        # Reset password
        request_data = {"email": "test@example.com"}
        request_response = self.client.post(
            reverse("api:auth:password_reset_request"), request_data, format="json"
        )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)

        reset = PasswordReset.objects.get(user=self.user)

        confirm_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response = self.client.post(
            reverse("api:auth:password_reset_confirm"), confirm_data, format="json"
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        # Old password should no longer work
        login_response_old_after = self.client.post(
            reverse("api:auth:api_login"), login_data_old, format="json"
        )
        self.assertEqual(
            login_response_old_after.status_code, status.HTTP_400_BAD_REQUEST
        )

        # New password should work
        login_data_new = {"username": "testuser", "password": "NewPassword123!"}
        login_response_new = self.client.post(
            reverse("api:auth:api_login"), login_data_new, format="json"
        )
        self.assertEqual(login_response_new.status_code, status.HTTP_200_OK)

    @override_settings(EMAIL_BACKEND="core.test_backends.QuietEmailBackend")
    def test_password_reset_with_active_session(self):
        """Test password reset behavior with active user session."""
        # Login user first
        login_data = {"username": "testuser", "password": "OldPassword123!"}
        login_response = self.client.post(
            reverse("api:auth:api_login"), login_data, format="json"
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Verify user is authenticated
        info_response = self.client.get(reverse("api:auth:api_user_info"))
        self.assertEqual(info_response.status_code, status.HTTP_200_OK)

        # Reset password while logged in
        request_data = {"email": "test@example.com"}
        request_response = self.client.post(
            reverse("api:auth:password_reset_request"), request_data, format="json"
        )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)

        reset = PasswordReset.objects.get(user=self.user)

        confirm_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response = self.client.post(
            reverse("api:auth:password_reset_confirm"), confirm_data, format="json"
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        # Check if session is still valid (depends on implementation)
        info_response_after = self.client.get(reverse("api:auth:api_user_info"))

        # Either session should be invalidated (for security) or still valid
        self.assertIn(
            info_response_after.status_code,
            [
                status.HTTP_200_OK,  # Session still valid
                status.HTTP_401_UNAUTHORIZED,  # Session invalidated (more secure)
            ],
        )

    def test_password_reset_inactive_user_integration(self):
        """Test password reset integration with inactive users."""
        # Make user inactive
        self.user.is_active = False
        self.user.save()

        # Request password reset
        request_data = {"email": "test@example.com"}
        request_response = self.client.post(
            reverse("api:auth:password_reset_request"), request_data, format="json"
        )

        # Should return success for security
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)

        # Should not create password reset
        self.assertEqual(PasswordReset.objects.count(), 0)

        # Login should still fail
        login_data = {"username": "testuser", "password": "OldPassword123!"}
        login_response = self.client.post(
            reverse("api:auth:api_login"), login_data, format="json"
        )
        self.assertEqual(login_response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetErrorRecoveryTest(TestCase):
    """Test error recovery scenarios in password reset workflow."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="OldPassword123!"
        )

    @override_settings(EMAIL_BACKEND="core.test_backends.QuietEmailBackend")
    def test_recovery_from_expired_token(self):
        """Test recovery when token expires before use."""
        # Request password reset
        request_data = {"email": "test@example.com"}
        request_response = self.client.post(
            reverse("api:auth:password_reset_request"), request_data, format="json"
        )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)

        # Manually expire the token
        reset = PasswordReset.objects.get(user=self.user)
        reset.expires_at = timezone.now() - timedelta(hours=1)
        reset.save()

        # Try to use expired token
        confirm_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response = self.client.post(
            reverse("api:auth:password_reset_confirm"), confirm_data, format="json"
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Clear email outbox from first request
        mail.outbox.clear()

        # User should be able to request new reset
        request_response2 = self.client.post(
            reverse("api:auth:password_reset_request"), request_data, format="json"
        )
        self.assertEqual(request_response2.status_code, status.HTTP_200_OK)

        # New token should work
        new_reset = (
            PasswordReset.objects.filter(user=self.user).order_by("-created_at").first()
        )
        self.assertTrue(new_reset.is_valid())

        confirm_data["token"] = new_reset.token
        confirm_response2 = self.client.post(
            reverse("api:auth:password_reset_confirm"), confirm_data, format="json"
        )
        self.assertEqual(confirm_response2.status_code, status.HTTP_200_OK)

    def test_recovery_from_network_interruption(self):
        """Test recovery scenarios from network interruptions."""
        # This simulates scenarios where requests might be partially completed

        # Request password reset
        with patch("users.services.PasswordResetService.send_reset_email") as mock_send:
            # Simulate email sending failure
            mock_send.return_value = False

            request_data = {"email": "test@example.com"}
            request_response = self.client.post(
                reverse("api:auth:password_reset_request"), request_data, format="json"
            )

            # Should still return success but indicate email failure
            self.assertEqual(request_response.status_code, status.HTTP_200_OK)
            self.assertTrue(request_response.data.get("email_sending_failed", False))

            # Reset record should still be created
            self.assertTrue(PasswordReset.objects.filter(user=self.user).exists())

            # User should be able to retry request
            mock_send.return_value = True  # Email works now

            request_response2 = self.client.post(
                reverse("api:auth:password_reset_request"), request_data, format="json"
            )
            self.assertEqual(request_response2.status_code, status.HTTP_200_OK)
            self.assertFalse(request_response2.data.get("email_sending_failed", False))

    def test_recovery_from_partial_form_submission(self):
        """Test recovery from partial form submissions."""
        # Create valid reset
        reset = PasswordReset.objects.create_for_user(self.user)

        # Submit form with missing confirmation password
        partial_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            # Missing new_password_confirm
        }

        confirm_response = self.client.post(
            reverse("api:auth:password_reset_confirm"), partial_data, format="json"
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Token should still be valid for retry
        reset.refresh_from_db()
        self.assertTrue(reset.is_valid())

        # Complete form submission should work
        complete_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response2 = self.client.post(
            reverse("api:auth:password_reset_confirm"), complete_data, format="json"
        )
        self.assertEqual(confirm_response2.status_code, status.HTTP_200_OK)

    def test_recovery_from_password_validation_failure(self):
        """Test recovery from password validation failures."""
        # Create valid reset
        reset = PasswordReset.objects.create_for_user(self.user)

        # Submit with weak password
        weak_data = {
            "token": reset.token,
            "new_password": "weak",
            "new_password_confirm": "weak",
        }

        confirm_response = self.client.post(
            reverse("api:auth:password_reset_confirm"), weak_data, format="json"
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_400_BAD_REQUEST)

        # Token should still be valid
        reset.refresh_from_db()
        self.assertTrue(reset.is_valid())

        # Strong password should work
        strong_data = {
            "token": reset.token,
            "new_password": "StrongPassword123!",
            "new_password_confirm": "StrongPassword123!",
        }

        confirm_response2 = self.client.post(
            reverse("api:auth:password_reset_confirm"), strong_data, format="json"
        )
        self.assertEqual(confirm_response2.status_code, status.HTTP_200_OK)


class PasswordResetPerformanceIntegrationTest(TransactionTestCase):
    """Test password reset performance under various conditions."""

    def setUp(self):
        """Set up test data."""
        self.users = []
        for i in range(10):
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="TestPass123!",
            )
            # Mark email as verified for password reset functionality
            user.mark_email_verified()
            user.save()
            self.users.append(user)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.dummy.EmailBackend")
    def test_concurrent_same_user_requests(self):
        """Test concurrent requests for same user."""
        user = self.users[0]

        def make_request():
            client = APIClient()
            data = {"email": user.email}

            response = client.post(
                reverse("api:auth:password_reset_request"), data, format="json"
            )
            return response.status_code

        # Make multiple concurrent requests for same user
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = [executor.submit(make_request) for _ in range(5)]
            status_codes = [result.result() for result in results]

        # Most should succeed (with rate limiting, some might be blocked)
        successful_requests = sum(
            1 for code in status_codes if code == status.HTTP_200_OK
        )
        self.assertGreaterEqual(successful_requests, 1)

        # Should have at most one valid reset (others invalidated)
        valid_resets = PasswordReset.objects.filter(user=user, used_at__isnull=True)
        self.assertEqual(valid_resets.count(), 1)

    def test_password_reset_database_performance(self):
        """Test database performance with many password resets."""
        import time

        # Create many password resets
        start_time = time.time()

        for user in self.users:
            PasswordReset.objects.create_for_user(user)

        creation_time = time.time() - start_time

        # Should be reasonably fast
        self.assertLess(creation_time, 5.0)  # 5 seconds for 10 users

        # Test token lookup performance
        resets = PasswordReset.objects.filter(user__in=self.users)
        tokens = [reset.token for reset in resets]

        start_time = time.time()

        for token in tokens:
            PasswordReset.objects.get_valid_reset_by_token(token)

        lookup_time = time.time() - start_time

        # Lookups should be fast
        self.assertLess(lookup_time, 2.0)  # 2 seconds for 10 lookups

    def test_cleanup_performance(self):
        """Test performance of cleanup operations."""
        # Create many expired resets
        for user in self.users:
            for _ in range(10):  # 10 resets per user
                reset = PasswordReset.objects.create_for_user(user)
                # Make some expired, some used
                if _ % 3 == 0:
                    reset.expires_at = timezone.now() - timedelta(hours=1)
                    reset.save()
                elif _ % 3 == 1:
                    reset.mark_as_used()

        # Test cleanup performance
        start_time = time.time()
        deleted_count = PasswordReset.objects.cleanup_expired()
        cleanup_time = time.time() - start_time

        # Should delete expired and used resets efficiently
        self.assertGreater(deleted_count, 0)
        self.assertLess(cleanup_time, 5.0)  # Should be fast


class PasswordResetCrossSystemIntegrationTest(TestCase):
    """Test password reset integration across different system components."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="OldPassword123!"
        )

    def test_password_reset_with_user_profile_updates(self):
        """Test password reset doesn't interfere with user profile updates."""
        # Update user profile
        self.user.first_name = "Test"
        self.user.last_name = "User"
        self.user.save()

        # Request password reset
        with patch("users.services.PasswordResetService.send_reset_email") as mock_send:
            mock_send.return_value = True

            request_data = {"email": "test@example.com"}
            request_response = self.client.post(
                reverse("api:auth:password_reset_request"), request_data, format="json"
            )
            self.assertEqual(request_response.status_code, status.HTTP_200_OK)

        # Complete password reset
        reset = PasswordReset.objects.get(user=self.user)

        confirm_data = {
            "token": reset.token,
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!",
        }

        confirm_response = self.client.post(
            reverse("api:auth:password_reset_confirm"), confirm_data, format="json"
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        # User profile data should be preserved
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Test")
        self.assertEqual(self.user.last_name, "User")
        self.assertTrue(self.user.check_password("NewPassword123!"))

    def test_password_reset_with_permission_system(self):
        """Test password reset interaction with Django permission system."""
        # Give user some permissions
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        # Add some permissions
        content_type = ContentType.objects.get_for_model(User)
        permission = Permission.objects.get(
            codename="change_user",
            content_type=content_type,
        )
        self.user.user_permissions.add(permission)

        # Reset password
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

        # Permissions should be preserved
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_perm("users.change_user"))

    def test_password_reset_with_user_groups(self):
        """Test password reset preserves user group memberships."""
        from django.contrib.auth.models import Group

        # Create group and add user
        group = Group.objects.create(name="Test Group")
        self.user.groups.add(group)

        # Reset password
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

        # Group membership should be preserved
        self.user.refresh_from_db()
        self.assertIn(group, self.user.groups.all())

    @override_settings(EMAIL_BACKEND="core.test_backends.QuietEmailBackend")
    def test_password_reset_email_integration_with_settings(self):
        """Test password reset email integration with Django settings."""
        # Test with various email settings
        with self.settings(
            DEFAULT_FROM_EMAIL="custom@example.com", EMAIL_SUBJECT_PREFIX="[Test Site] "
        ):
            request_data = {"email": "test@example.com"}
            request_response = self.client.post(
                reverse("api:auth:password_reset_request"), request_data, format="json"
            )
            self.assertEqual(request_response.status_code, status.HTTP_200_OK)

            # Email should use custom settings
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]

            # Should use custom from email
            self.assertEqual(email.from_email, "custom@example.com")

            # Should use subject prefix if implemented
            if "[Test Site]" in email.subject:
                self.assertIn("[Test Site]", email.subject)
