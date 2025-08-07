"""
Tests for authentication views.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()


class RegisterViewTest(TestCase):
    """Test user registration view."""

    def test_get_register_view(self):
        """Test GET request to registration view displays form."""
        response = self.client.get(reverse("users:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Register")
        self.assertContains(response, "username")
        self.assertContains(response, "email")
        self.assertContains(response, "password1")
        self.assertContains(response, "password2")

    def test_register_user_success(self):
        """Test successful user registration."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password1": "TestPass123!",
            "password2": "TestPass123!",
        }
        response = self.client.post(reverse("users:register"), data)

        # Should redirect after successful registration
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:login"))

        # User should be created
        self.assertTrue(User.objects.filter(username="testuser").exists())
        user = User.objects.get(username="testuser")
        self.assertEqual(user.email, "test@example.com")

    def test_register_user_with_display_name(self):
        """Test registration with optional display_name field."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password1": "TestPass123!",
            "password2": "TestPass123!",
            "display_name": "Test User",
        }
        response = self.client.post(reverse("users:register"), data)

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="testuser")
        self.assertEqual(user.display_name, "Test User")

    def test_register_user_password_mismatch(self):
        """Test registration fails with password mismatch."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password1": "TestPass123!",
            "password2": "DifferentPass456!",
        }
        response = self.client.post(reverse("users:register"), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "password")
        self.assertFalse(User.objects.filter(username="testuser").exists())

    def test_register_user_weak_password(self):
        """Test registration fails with weak password."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password1": "123",
            "password2": "123",
        }
        response = self.client.post(reverse("users:register"), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "password")
        self.assertFalse(User.objects.filter(username="testuser").exists())

    def test_register_duplicate_username(self):
        """Test registration fails with duplicate username."""
        User.objects.create_user("testuser", "existing@example.com", "TestPass123!")

        data = {
            "username": "testuser",
            "email": "new@example.com",
            "password1": "TestPass123!",
            "password2": "TestPass123!",
        }
        response = self.client.post(reverse("users:register"), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "username")
        self.assertEqual(User.objects.filter(username="testuser").count(), 1)


class LoginViewTest(TestCase):
    """Test user login view."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_get_login_view(self):
        """Test GET request to login view displays form."""
        response = self.client.get(reverse("users:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Login")
        self.assertContains(response, "username")
        self.assertContains(response, "password")

    def test_login_success(self):
        """Test successful login."""
        data = {
            "username": "testuser",
            "password": "TestPass123!",
        }
        response = self.client.post(reverse("users:login"), data)

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("core:index"))

        # User should be logged in
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_with_email(self):
        """Test login with email instead of username."""
        data = {
            "username": "test@example.com",
            "password": "TestPass123!",
        }
        response = self.client.post(reverse("users:login"), data)

        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        data = {
            "username": "testuser",
            "password": "WrongPassword",
        }
        response = self.client.post(reverse("users:login"), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Please enter a correct username/email and password"
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_inactive_user(self):
        """Test login with inactive user."""
        self.user.is_active = False
        self.user.save()

        data = {
            "username": "testuser",
            "password": "TestPass123!",
        }
        response = self.client.post(reverse("users:login"), data)

        self.assertEqual(response.status_code, 200)
        # Inactive users show as invalid credentials for security
        self.assertContains(
            response, "Please enter a correct username/email and password"
        )

    def test_login_redirect_to_next(self):
        """Test login redirects to next parameter."""
        next_url = reverse("campaigns:list")
        data = {
            "username": "testuser",
            "password": "TestPass123!",
        }
        response = self.client.post(reverse("users:login") + f"?next={next_url}", data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, next_url)


class LogoutViewTest(TestCase):
    """Test user logout view."""

    def setUp(self):
        """Create and login test user."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.client.login(username="testuser", password="TestPass123!")

    def test_logout_post(self):
        """Test POST logout logs user out and redirects."""
        response = self.client.post(reverse("users:logout"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("core:index"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_get_redirects(self):
        """Test GET logout redirects to confirmation."""
        response = self.client.get(reverse("users:logout"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Are you sure you want to log out?")


class PasswordChangeViewTest(TestCase):
    """Test password change view."""

    def setUp(self):
        """Create and login test user."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.client.login(username="testuser", password="TestPass123!")

    def test_get_password_change_view(self):
        """Test GET request to password change view."""
        response = self.client.get(reverse("users:password_change"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Change Password")
        self.assertContains(response, "old_password")
        self.assertContains(response, "new_password1")
        self.assertContains(response, "new_password2")

    def test_password_change_success(self):
        """Test successful password change."""
        data = {
            "old_password": "TestPass123!",
            "new_password1": "NewTestPass456!",
            "new_password2": "NewTestPass456!",
        }
        response = self.client.post(reverse("users:password_change"), data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:password_change_done"))

        # User should still be logged in with new password
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewTestPass456!"))

    def test_password_change_wrong_old_password(self):
        """Test password change fails with wrong old password."""
        data = {
            "old_password": "WrongPassword",
            "new_password1": "NewTestPass456!",
            "new_password2": "NewTestPass456!",
        }
        response = self.client.post(reverse("users:password_change"), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "old password is incorrect")

    def test_password_change_requires_login(self):
        """Test password change requires authentication."""
        self.client.logout()
        response = self.client.get(reverse("users:password_change"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("users:login") + f'?next={reverse("users:password_change")}',
        )


class PasswordResetViewTest(TestCase):
    """Test password reset views."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_get_password_reset_view(self):
        """Test GET request to password reset view."""
        response = self.client.get(reverse("users:password_reset"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Password Reset")
        self.assertContains(response, "email")

    def test_password_reset_success(self):
        """Test successful password reset request."""
        data = {"email": "test@example.com"}
        response = self.client.post(reverse("users:password_reset"), data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:password_reset_done"))

        # Email should be sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Password reset", mail.outbox[0].subject)

    def test_password_reset_invalid_email(self):
        """Test password reset with non-existent email."""
        data = {"email": "nonexistent@example.com"}
        response = self.client.post(reverse("users:password_reset"), data)

        # Should still redirect (security - don't reveal valid emails)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:password_reset_done"))

        # No email should be sent
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_confirm_get(self):
        """Test GET request to password reset confirm view."""
        # Generate valid reset token
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        url = reverse(
            "users:password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter New Password")

    def test_password_reset_confirm_success(self):
        """Test successful password reset confirmation."""
        # Generate valid reset token
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        url = reverse(
            "users:password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}
        )

        data = {
            "new_password1": "NewResetPass789!",
            "new_password2": "NewResetPass789!",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:password_reset_complete"))

        # Password should be changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewResetPass789!"))

    def test_password_reset_confirm_invalid_token(self):
        """Test password reset confirm with invalid token."""
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))

        url = reverse(
            "users:password_reset_confirm",
            kwargs={"uidb64": uidb64, "token": "invalid-token"},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "invalid")


class AuthenticationIntegrationTest(TestCase):
    """Test authentication workflow integration."""

    def test_register_then_login_workflow(self):
        """Test complete register -> login workflow."""
        # Register user
        register_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password1": "TestPass123!",
            "password2": "TestPass123!",
        }
        response = self.client.post(reverse("users:register"), register_data)
        self.assertEqual(response.status_code, 302)

        # User should exist
        self.assertTrue(User.objects.filter(username="newuser").exists())

        # Login with new credentials
        login_data = {
            "username": "newuser",
            "password": "TestPass123!",
        }
        response = self.client.post(reverse("users:login"), login_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_change_password_then_login_workflow(self):
        """Test password change -> logout -> login workflow."""
        # Create and login user
        User.objects.create_user(
            username="testuser", email="test@example.com", password="OldPass123!"
        )
        self.client.login(username="testuser", password="OldPass123!")

        # Change password
        change_data = {
            "old_password": "OldPass123!",
            "new_password1": "NewPass456!",
            "new_password2": "NewPass456!",
        }
        response = self.client.post(reverse("users:password_change"), change_data)
        self.assertEqual(response.status_code, 302)

        # Logout
        response = self.client.post(reverse("users:logout"))
        self.assertEqual(response.status_code, 302)

        # Login with new password
        login_data = {
            "username": "testuser",
            "password": "NewPass456!",
        }
        response = self.client.post(reverse("users:login"), login_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)
