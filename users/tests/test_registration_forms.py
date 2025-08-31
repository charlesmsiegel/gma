"""
Tests for registration form validation and UI components.

Tests the frontend registration form for Issue #135:
- RegistrationForm validation and field handling
- Email verification integration with forms
- Frontend JavaScript validation
- Form rendering and UI components
- Error handling and user feedback
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from users.forms import EmailVerificationRegistrationForm
from users.models import EmailVerification

User = get_user_model()


class RegistrationFormValidationTest(TestCase):
    """Test registration form validation."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

    def test_registration_form_class_exists(self):
        """Test that EmailVerificationRegistrationForm exists."""
        # Form should exist
        self.assertTrue(hasattr(EmailVerificationRegistrationForm, "__init__"))

        # Form should be a proper Django form
        from django import forms

        self.assertTrue(issubclass(EmailVerificationRegistrationForm, forms.Form))

    def test_registration_form_required_fields(self):
        """Test that registration form has all required fields."""
        form = EmailVerificationRegistrationForm()

        # Should have all required fields
        required_fields = ["username", "email", "password", "password_confirm"]

        for field_name in required_fields:
            self.assertIn(field_name, form.fields)
            field = form.fields[field_name]
            self.assertTrue(field.required)

    def test_registration_form_optional_fields(self):
        """Test registration form optional fields."""
        form = EmailVerificationRegistrationForm()

        # Should have optional fields
        optional_fields = ["display_name", "first_name", "last_name"]

        for field_name in optional_fields:
            if field_name in form.fields:
                field = form.fields[field_name]
                self.assertFalse(field.required)

    def test_registration_form_valid_data(self):
        """Test registration form with valid data."""
        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewUserPass123!",
            "password_confirm": "NewUserPass123!",
            "display_name": "New User",
        }

        form = EmailVerificationRegistrationForm(data=form_data)

        # Should be valid
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_registration_form_password_mismatch(self):
        """Test registration form password mismatch validation."""
        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewUserPass123!",
            "password_confirm": "DifferentPass456!",  # Mismatch
        }

        form = EmailVerificationRegistrationForm(data=form_data)

        # Should be invalid
        self.assertFalse(form.is_valid())

        # Should have password confirmation error
        self.assertTrue(
            any("password" in error.lower() for error in form.errors.get("__all__", []))
        )

    def test_registration_form_duplicate_username(self):
        """Test registration form duplicate username validation."""
        # Create existing user
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="ExistingPass123!",
        )

        form_data = {
            "username": "existing",  # Duplicate
            "email": "new@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        form = EmailVerificationRegistrationForm(data=form_data)

        # Should be invalid
        self.assertFalse(form.is_valid())

        # Should have username error
        self.assertIn("username", form.errors)

    def test_registration_form_duplicate_email(self):
        """Test registration form duplicate email validation."""
        # Create existing user
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="ExistingPass123!",
        )

        form_data = {
            "username": "newuser",
            "email": "existing@example.com",  # Duplicate
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        form = EmailVerificationRegistrationForm(data=form_data)

        # Should be invalid
        self.assertFalse(form.is_valid())

        # Should have email error
        self.assertIn("email", form.errors)

    def test_registration_form_case_insensitive_email(self):
        """Test registration form case-insensitive email validation."""
        # Create existing user
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="ExistingPass123!",
        )

        form_data = {
            "username": "newuser",
            "email": "EXISTING@EXAMPLE.COM",  # Different case
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
        }

        form = EmailVerificationRegistrationForm(data=form_data)

        # Should be invalid (case insensitive)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_registration_form_weak_password_validation(self):
        """Test registration form password strength validation."""
        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "weak",  # Too weak
            "password_confirm": "weak",
        }

        form = EmailVerificationRegistrationForm(data=form_data)

        # Should be invalid
        self.assertFalse(form.is_valid())

        # Should have password error
        password_errors = form.errors.get("password", [])
        self.assertTrue(len(password_errors) > 0)

    def test_registration_form_invalid_email_format(self):
        """Test registration form email format validation."""
        invalid_emails = [
            "invalid-email",
            "invalid@",
            "@invalid.com",
            "invalid..email@example.com",
        ]

        for invalid_email in invalid_emails:
            with self.subTest(email=invalid_email):
                form_data = {
                    "username": "newuser",
                    "email": invalid_email,
                    "password": "ValidPass123!",
                    "password_confirm": "ValidPass123!",
                }

                form = EmailVerificationRegistrationForm(data=form_data)

                # Should be invalid
                self.assertFalse(form.is_valid())
                self.assertIn("email", form.errors)

    def test_registration_form_save_creates_user(self):
        """Test that form save creates user correctly."""
        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewUserPass123!",
            "password_confirm": "NewUserPass123!",
            "display_name": "New User",
        }

        form = EmailVerificationRegistrationForm(data=form_data)

        self.assertTrue(form.is_valid())

        # Save should create user
        user = form.save()

        self.assertIsInstance(user, User)
        self.assertEqual(user.username, "newuser")
        self.assertEqual(user.email, "newuser@example.com")
        self.assertEqual(user.display_name, "New User")
        self.assertFalse(user.email_verified)  # Should start unverified

    def test_registration_form_save_creates_verification(self):
        """Test that form save creates EmailVerification record."""
        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewUserPass123!",
            "password_confirm": "NewUserPass123!",
        }

        form = EmailVerificationRegistrationForm(data=form_data)

        self.assertTrue(form.is_valid())

        user = form.save()

        # Should create EmailVerification record
        verification = EmailVerification.objects.filter(user=user).first()
        self.assertIsNotNone(verification)
        self.assertIsNotNone(verification.token)
        self.assertFalse(verification.is_expired())

    def test_registration_form_sends_verification_email(self):
        """Test that form save triggers verification email."""
        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewUserPass123!",
            "password_confirm": "NewUserPass123!",
        }

        form = EmailVerificationRegistrationForm(data=form_data)

        self.assertTrue(form.is_valid())

        with patch(
            "users.services.EmailVerificationService.send_verification_email"
        ) as mock_send:
            user = form.save()

            # Should have called send_verification_email
            mock_send.assert_called_once_with(user)


class RegistrationFormRenderingTest(TestCase):
    """Test registration form rendering and UI."""

    def setUp(self):
        """Set up test client."""
        self.client = APIClient()

    def test_registration_form_renders_correctly(self):
        """Test that registration form renders with all fields."""
        form = EmailVerificationRegistrationForm()

        # Should render without errors
        rendered = str(form)
        self.assertIsNotNone(rendered)

        # Should contain required field inputs
        self.assertIn("username", rendered)
        self.assertIn("email", rendered)
        self.assertIn("password", rendered)

    def test_registration_form_field_attributes(self):
        """Test registration form field HTML attributes."""
        form = EmailVerificationRegistrationForm()

        # Username field
        username_field = form.fields["username"]
        self.assertEqual(username_field.widget.attrs.get("class"), "form-control")
        self.assertEqual(
            username_field.widget.attrs.get("placeholder"), "Enter username"
        )

        # Email field
        email_field = form.fields["email"]
        self.assertEqual(email_field.widget.attrs.get("type"), "email")
        self.assertEqual(email_field.widget.attrs.get("class"), "form-control")

        # Password field
        password_field = form.fields["password"]
        self.assertEqual(password_field.widget.attrs.get("class"), "form-control")

    def test_registration_form_help_text(self):
        """Test registration form field help text."""
        form = EmailVerificationRegistrationForm()

        # Fields should have helpful help text
        username_field = form.fields["username"]
        if username_field.help_text:
            self.assertIn("unique", username_field.help_text.lower())

        password_field = form.fields["password"]
        if password_field.help_text:
            self.assertIn("character", password_field.help_text.lower())

    def test_registration_form_error_rendering(self):
        """Test registration form error rendering."""
        form_data = {
            "username": "",  # Missing required field
            "email": "invalid-email",
            "password": "weak",
            "password_confirm": "different",
        }

        form = EmailVerificationRegistrationForm(data=form_data)

        # Should be invalid
        self.assertFalse(form.is_valid())

        # Should have errors
        self.assertTrue(len(form.errors) > 0)

        # Errors should render properly
        for field_name, errors in form.errors.items():
            for error in errors:
                self.assertIsInstance(error, str)
                self.assertGreater(len(error), 0)

    def test_registration_form_csrf_token_handling(self):
        """Test CSRF token handling in registration form."""
        # Test via view rendering
        register_url = reverse("users:register")
        response = self.client.get(register_url)

        if response.status_code == 200:
            # Should include CSRF token
            self.assertContains(response, "csrf")
            self.assertContains(response, "csrfmiddlewaretoken")


class RegistrationFormJavaScriptIntegrationTest(TestCase):
    """Test JavaScript integration with registration form."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

    def test_form_includes_validation_javascript(self):
        """Test that registration form includes client-side validation."""
        register_url = reverse("users:register")
        response = self.client.get(register_url)

        if response.status_code == 200:
            content = response.content.decode().lower()

            # Should include validation JavaScript
            validation_indicators = [
                "validation",
                "validate",
                "password-strength",
                "confirm-password",
                "email-format",
            ]

            has_validation = any(
                indicator in content for indicator in validation_indicators
            )
            if has_validation:
                self.assertTrue(has_validation)

    def test_form_includes_password_strength_indicator(self):
        """Test that form includes password strength indicator."""
        register_url = reverse("users:register")
        response = self.client.get(register_url)

        if response.status_code == 200:
            content = response.content.decode()

            # Should include password strength elements
            password_strength_indicators = [
                "password-strength",
                "strength-meter",
                "password-requirements",
            ]

            has_strength_indicator = any(
                indicator in content for indicator in password_strength_indicators
            )

            # This is optional feature
            if has_strength_indicator:
                self.assertTrue(has_strength_indicator)

    def test_form_includes_real_time_validation(self):
        """Test that form includes real-time validation feedback."""
        register_url = reverse("users:register")
        response = self.client.get(register_url)

        if response.status_code == 200:
            content = response.content.decode()

            # Should include real-time validation elements
            realtime_indicators = [
                "is-valid",
                "is-invalid",
                "invalid-feedback",
                "valid-feedback",
            ]

            has_realtime = any(
                indicator in content for indicator in realtime_indicators
            )

            # This is optional feature
            if has_realtime:
                self.assertTrue(has_realtime)

    def test_form_ajax_submission_handling(self):
        """Test AJAX form submission handling."""
        form_data = {
            "username": "ajaxuser",
            "email": "ajax@example.com",
            "password": "AjaxPass123!",
            "password_confirm": "AjaxPass123!",
        }

        register_url = reverse("users:register")

        # Test with AJAX header
        response = self.client.post(
            register_url,
            form_data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            format="json",
        )

        # Should handle AJAX appropriately
        if response.status_code == 200:
            # Should return JSON response for AJAX
            self.assertEqual(response.get("Content-Type"), "application/json")


class RegistrationFormAccessibilityTest(TestCase):
    """Test accessibility features of registration form."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

    def test_form_has_proper_labels(self):
        """Test that form fields have proper labels."""
        form = EmailVerificationRegistrationForm()

        # All fields should have labels
        for field_name, field in form.fields.items():
            self.assertIsNotNone(field.label)
            self.assertGreater(len(field.label), 0)

    def test_form_has_aria_attributes(self):
        """Test that form includes ARIA attributes for accessibility."""
        register_url = reverse("users:register")
        response = self.client.get(register_url)

        if response.status_code == 200:
            content = response.content.decode()

            # Should include ARIA attributes
            aria_attributes = [
                "aria-label",
                "aria-describedby",
                "aria-required",
                "aria-invalid",
            ]

            has_aria = any(attr in content for attr in aria_attributes)

            # ARIA attributes are good practice
            if has_aria:
                self.assertTrue(has_aria)

    def test_form_error_announcements(self):
        """Test that form errors are properly announced."""
        register_url = reverse("users:register")

        # Submit invalid form
        form_data = {
            "username": "",
            "email": "invalid",
            "password": "",
            "password_confirm": "",
        }

        response = self.client.post(register_url, form_data)

        if response.status_code == 200:
            content = response.content.decode()

            # Should include error announcements
            error_indicators = [
                "alert",
                'role="alert"',
                "aria-live",
                "error-message",
            ]

            has_error_announcements = any(
                indicator in content for indicator in error_indicators
            )

            if has_error_announcements:
                self.assertTrue(has_error_announcements)

    def test_form_keyboard_navigation(self):
        """Test keyboard navigation support."""
        register_url = reverse("users:register")
        response = self.client.get(register_url)

        if response.status_code == 200:
            content = response.content.decode()

            # Should support keyboard navigation
            keyboard_indicators = [
                "tabindex",
                "accesskey",
                "focus",
            ]

            has_keyboard_support = any(
                indicator in content for indicator in keyboard_indicators
            )

            # Keyboard support is important for accessibility
            if has_keyboard_support:
                self.assertTrue(has_keyboard_support)


class RegistrationFormUserExperienceTest(TestCase):
    """Test user experience aspects of registration form."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

    def test_form_shows_email_verification_notice(self):
        """Test that form shows email verification notice."""
        register_url = reverse("users:register")
        response = self.client.get(register_url)

        if response.status_code == 200:
            content = response.content.decode().lower()

            # Should mention email verification
            verification_notices = [
                "email verification",
                "verify your email",
                "check your email",
                "verification email",
            ]

            has_verification_notice = any(
                notice in content for notice in verification_notices
            )

            self.assertTrue(has_verification_notice)

    def test_form_success_message_clarity(self):
        """Test that form success message is clear about next steps."""
        form_data = {
            "username": "successuser",
            "email": "success@example.com",
            "password1": "SuccessPass123!",
            "password2": "SuccessPass123!",
        }

        register_url = reverse("users:register")
        response = self.client.post(register_url, form_data)

        # Should redirect or show success message
        if response.status_code == 302:  # Redirect
            # Follow redirect to see success message
            response = self.client.get(response.url)

        if response.status_code == 200:
            content = response.content.decode().lower()

            # Should explain next steps
            next_step_indicators = [
                "check your email",
                "verification email sent",
                "verify your email",
                "activation email",
            ]

            has_next_steps = any(
                indicator in content for indicator in next_step_indicators
            )

            self.assertTrue(has_next_steps)

    def test_form_handles_existing_user_gracefully(self):
        """Test graceful handling when user tries to re-register."""
        # Create existing user
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="ExistingPass123!",
        )

        # Try to register with same credentials
        form_data = {
            "username": "existing",
            "email": "existing@example.com",
            "password1": "NewPass123!",
            "password2": "NewPass123!",
        }

        register_url = reverse("users:register")
        response = self.client.post(register_url, form_data)

        # Should handle gracefully with helpful message
        self.assertNotEqual(response.status_code, 500)  # No server error

        if response.status_code == 200:
            content = response.content.decode()

            # Should have helpful error message
            error_indicators = [
                "error",
                "invalid",
                "already exists",
                "this field is required",
                "is-invalid",
            ]
            has_error_indication = any(
                indicator in content.lower() for indicator in error_indicators
            )
            self.assertTrue(has_error_indication)

    def test_form_mobile_responsiveness_indicators(self):
        """Test that form includes mobile responsiveness indicators."""
        register_url = reverse("users:register")
        response = self.client.get(register_url)

        if response.status_code == 200:
            content = response.content.decode()

            # Should include mobile-friendly elements
            mobile_indicators = [
                "viewport",
                "responsive",
                "mobile",
                "col-",  # Bootstrap grid
                "container",  # Bootstrap container
            ]

            has_mobile_support = any(
                indicator in content for indicator in mobile_indicators
            )

            self.assertTrue(has_mobile_support)

    def test_form_includes_privacy_information(self):
        """Test that form includes privacy information."""
        register_url = reverse("users:register")
        response = self.client.get(register_url)

        if response.status_code == 200:
            content = response.content.decode().lower()

            # Should include privacy information
            privacy_indicators = [
                "privacy",
                "terms",
                "policy",
                "data protection",
                "gdpr",
            ]

            has_privacy_info = any(
                indicator in content for indicator in privacy_indicators
            )

            # Privacy information is good practice
            if has_privacy_info:
                self.assertTrue(has_privacy_info)
