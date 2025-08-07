"""
Tests for authentication API endpoints.

These tests verify that the API authentication endpoints properly handle:
- Login with username
- Login with email (this should work but currently may not)
- Registration
- Profile management
- CSRF token handling
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class AuthenticationAPITest(TestCase):
    """Test authentication API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

        # Endpoints
        self.login_url = reverse("api:api_login")
        self.register_url = reverse("api:api_register")
        self.logout_url = reverse("api:api_logout")
        self.user_info_url = reverse("api:api_user_info")
        self.csrf_url = reverse("api:api_csrf_token")

    def test_login_with_username_success(self):
        """Test successful login with username."""
        data = {"username": "testuser", "password": "TestPass123!"}
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "Login successful")

    def test_login_with_email_should_work(self):
        """Test login with email - this should work but currently may not."""
        data = {
            "username": "test@example.com",  # Using email in username field
            "password": "TestPass123!",
        }
        response = self.client.post(self.login_url, data, format="json")

        # This test demonstrates the bug - it should succeed but may fail
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            # If it fails, this confirms the email authentication bypass bug
            self.assertIn("Invalid credentials", str(response.data))
            # Mark this as expected failure until we fix it
            self.fail(
                "Email authentication bypass confirmed - "
                "API does not handle email login"
            )
        else:
            # If it succeeds, the bug has been fixed
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["message"], "Login successful")

    def test_login_with_email_case_insensitive(self):
        """Test login with email should be case-insensitive."""
        data = {
            "username": "TEST@EXAMPLE.COM",  # Different case
            "password": "TestPass123!",
        }
        response = self.client.post(self.login_url, data, format="json")

        # This should work after the fix is implemented
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            self.fail(
                "Email authentication bypass - case-insensitive email login not working"
            )
        else:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_with_nonexistent_email(self):
        """Test login with non-existent email should fail gracefully."""
        data = {"username": "nonexistent@example.com", "password": "TestPass123!"}
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid credentials", str(response.data))

    def test_login_invalid_password(self):
        """Test login with invalid password."""
        data = {"username": "testuser", "password": "WrongPassword"}
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid credentials", str(response.data))

    def test_login_inactive_user(self):
        """Test login with inactive user should fail."""
        self.user.is_active = False
        self.user.save()

        data = {"username": "testuser", "password": "TestPass123!"}
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # API returns generic "Invalid credentials" for security
        # (matches Django form behavior)
        self.assertIn("Invalid credentials", str(response.data))

    def test_register_success(self):
        """Test successful user registration."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }
        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_password_mismatch(self):
        """Test registration with password mismatch."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "NewPass123!",
            "password_confirm": "DifferentPass456!",
        }
        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_register_duplicate_email(self):
        """Test registration with duplicate email."""
        data = {
            "username": "newuser",
            "email": "test@example.com",  # Same as existing user
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }
        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_csrf_token_endpoint(self):
        """Test CSRF token endpoint returns valid token."""
        response = self.client.get(self.csrf_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrfToken", response.data)
        self.assertIsNotNone(response.data["csrfToken"])

    def test_user_info_authenticated(self):
        """Test user info endpoint when authenticated."""
        # Login first
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.user_info_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["username"], "testuser")
        self.assertEqual(response.data["user"]["email"], "test@example.com")

    def test_user_info_unauthenticated(self):
        """Test user info endpoint when not authenticated."""
        response = self.client.get(self.user_info_url)

        # DRF returns 403 for permission denied when using IsAuthenticated
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logout_success(self):
        """Test successful logout."""
        # Login first
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)


class AuthenticationSerializerTest(TestCase):
    """Test authentication serializers directly."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_login_serializer_username(self):
        """Test login serializer with username."""
        from api.serializers import LoginSerializer

        data = {"username": "testuser", "password": "TestPass123!"}
        serializer = LoginSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_login_serializer_email(self):
        """Test login serializer with email - this exposes the bug."""
        from api.serializers import LoginSerializer

        data = {"username": "test@example.com", "password": "TestPass123!"}
        serializer = LoginSerializer(data=data, context={"request": None})

        # This will fail because authenticate() doesn't handle email lookup
        is_valid = serializer.is_valid()

        if not is_valid:
            # This confirms the bug exists
            self.assertIn("Invalid credentials", str(serializer.errors))
            self.fail(f"Email authentication bypass in serializer: {serializer.errors}")
        else:
            # If this passes, the bug has been fixed
            self.assertTrue(is_valid)

    def test_login_serializer_case_insensitive_email(self):
        """Test login serializer with case-insensitive email."""
        from api.serializers import LoginSerializer

        data = {"username": "TEST@EXAMPLE.COM", "password": "TestPass123!"}
        serializer = LoginSerializer(data=data, context={"request": None})

        # This should work after implementing the fix
        if not serializer.is_valid():
            self.fail(
                f"Case-insensitive email authentication failed: {serializer.errors}"
            )
        else:
            self.assertTrue(serializer.is_valid())


class EmailAuthenticationIntegrationTest(TestCase):
    """Integration tests comparing Django form auth vs API auth."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_django_form_email_authentication_works(self):
        """Verify that Django form-based authentication works with email."""
        from users.forms import EmailAuthenticationForm

        # This should work because EmailAuthenticationForm handles email lookup
        form_data = {"username": "test@example.com", "password": "TestPass123!"}
        form = EmailAuthenticationForm(data=form_data)

        self.assertTrue(
            form.is_valid(), f"Django form should handle email login: {form.errors}"
        )
        authenticated_user = form.get_user()
        self.assertEqual(authenticated_user.username, "testuser")

    def test_api_serializer_email_authentication_comparison(self):
        """Compare API serializer behavior to Django form behavior."""
        from api.serializers import LoginSerializer
        from users.forms import EmailAuthenticationForm

        # Test data
        test_data = {"username": "test@example.com", "password": "TestPass123!"}

        # Django form should work
        form = EmailAuthenticationForm(data=test_data)
        form_valid = form.is_valid()

        # API serializer currently doesn't work the same way
        serializer = LoginSerializer(data=test_data, context={"request": None})
        serializer_valid = serializer.is_valid()

        # Assert that both should behave the same way
        self.assertTrue(form_valid, "Django form should handle email authentication")

        if not serializer_valid:
            self.fail(
                f"API serializer should match Django form behavior for email "
                f"authentication. Form valid: {form_valid}, "
                f"Serializer valid: {serializer_valid}. "
                f"Serializer errors: {serializer.errors}"
            )
