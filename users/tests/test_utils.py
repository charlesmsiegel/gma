"""Tests for users utility functions."""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from users.utils import authenticate_by_email_or_username

User = get_user_model()


class AuthenticationUtilsTest(TestCase):
    """Test authentication utility functions."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_authenticate_by_username(self):
        """Test authentication using username."""
        request = self.factory.get("/")
        user = authenticate_by_email_or_username(request, "testuser", "testpass123")
        self.assertEqual(user, self.user)

    def test_authenticate_by_email(self):
        """Test authentication using email address."""
        request = self.factory.get("/")
        user = authenticate_by_email_or_username(
            request, "test@example.com", "testpass123"
        )
        self.assertEqual(user, self.user)

    def test_authenticate_by_email_case_insensitive(self):
        """Test authentication using email with different case."""
        request = self.factory.get("/")
        user = authenticate_by_email_or_username(
            request, "TEST@EXAMPLE.COM", "testpass123"
        )
        self.assertEqual(user, self.user)

    def test_authenticate_invalid_credentials(self):
        """Test authentication with invalid credentials returns None."""
        request = self.factory.get("/")
        user = authenticate_by_email_or_username(request, "testuser", "wrongpass")
        self.assertIsNone(user)

    def test_authenticate_nonexistent_email(self):
        """Test authentication with non-existent email falls back to username auth."""
        request = self.factory.get("/")
        user = authenticate_by_email_or_username(
            request, "nonexistent@example.com", "testpass123"
        )
        self.assertIsNone(user)

    def test_authenticate_empty_credentials(self):
        """Test authentication with empty credentials returns None."""
        request = self.factory.get("/")
        user = authenticate_by_email_or_username(request, "", "testpass123")
        self.assertIsNone(user)

        user = authenticate_by_email_or_username(request, "testuser", "")
        self.assertIsNone(user)

        user = authenticate_by_email_or_username(request, None, "testpass123")
        self.assertIsNone(user)

    def test_authenticate_without_request(self):
        """Test authentication works without request object (API context)."""
        user = authenticate_by_email_or_username(
            None, "test@example.com", "testpass123"
        )
        self.assertEqual(user, self.user)
