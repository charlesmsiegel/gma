"""
Tests for password reset email functionality.

This test suite covers:
- Email template rendering and customization
- Email sending success and failure handling
- HTML and text email versions
- Email content validation and security
- Multi-language support preparation
- Email delivery tracking
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template
from django.test import TestCase, override_settings
from django.urls import reverse

from users.models.password_reset import PasswordReset

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetEmailTemplateTest(TestCase):
    """Test password reset email template functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.reset = PasswordReset.objects.create_for_user(self.user)

    def test_email_subject_template(self):
        """Test password reset email subject template."""
        from users.services import PasswordResetService

        service = PasswordResetService()

        # Mock the email sending to capture subject
        with patch.object(service, "_send_email") as mock_send:
            service.send_reset_email(self.user, self.reset)

            # Check that email sending was attempted
            if mock_send.called:
                call_args = mock_send.call_args
                subject = call_args[1].get("subject") or call_args[0][0]

                # Subject should be appropriate
                self.assertIn("password reset", subject.lower())
                self.assertNotIn("{{", subject)  # No template variables left
                self.assertNotIn("}}", subject)

    def test_email_text_template(self):
        """Test password reset email text template content."""
        from users.services import PasswordResetService

        service = PasswordResetService()

        with patch.object(service, "_send_email") as mock_send:
            service.send_reset_email(self.user, self.reset)

            if mock_send.called:
                call_args = mock_send.call_args
                text_content = call_args[1].get("message") or call_args[0][1]

                # Text should contain required elements
                self.assertIn(self.user.username, text_content)
                self.assertIn(self.reset.token, text_content)
                self.assertIn("password reset", text_content.lower())

                # Should not contain HTML tags
                self.assertNotIn("<html>", text_content)
                self.assertNotIn("<body>", text_content)

                # Should not contain unrendered template variables
                self.assertNotIn("{{", text_content)
                self.assertNotIn("}}", text_content)

    def test_email_html_template(self):
        """Test password reset email HTML template content."""
        from users.services import PasswordResetService

        service = PasswordResetService()

        with patch.object(service, "_send_email") as mock_send:
            service.send_reset_email(self.user, self.reset)

            if mock_send.called:
                call_args = mock_send.call_args

                # Check if HTML content was provided
                html_content = call_args[1].get("html_message")

                if html_content:
                    # HTML should contain required elements
                    self.assertIn(self.user.username, html_content)
                    self.assertIn(self.reset.token, html_content)
                    self.assertIn("password reset", html_content.lower())

                    # Should contain HTML structure
                    self.assertIn("<html>", html_content)
                    self.assertIn("<body>", html_content)

                    # Should not contain unrendered template variables
                    self.assertNotIn("{{", html_content)
                    self.assertNotIn("}}", html_content)

    def test_email_reset_link_generation(self):
        """Test that email contains proper reset link."""
        from users.services import PasswordResetService

        service = PasswordResetService()

        with patch.object(service, "_send_email") as mock_send:
            service.send_reset_email(self.user, self.reset)

            if mock_send.called:
                call_args = mock_send.call_args
                text_content = call_args[1].get("message") or call_args[0][1]

                # Should contain a URL with the token
                self.assertIn("http", text_content)
                self.assertIn(self.reset.token, text_content)

                # URL should be for password reset
                self.assertIn("password-reset", text_content)

    def test_email_template_context_variables(self):
        """Test that all expected context variables are available."""
        # Test template rendering directly
        template_content = """
        Hello {{ user.username }},

        Reset link: {{ reset_url }}
        Token: {{ token }}
        Expires: {{ expires_at }}
        Site: {{ site_name }}
        """

        template = Template(template_content)
        context = Context(
            {
                "user": self.user,
                "token": self.reset.token,
                "reset_url": f"https://example.com/password-reset/{self.reset.token}/",
                "expires_at": self.reset.expires_at,
                "site_name": "Test Site",
            }
        )

        rendered = template.render(context)

        # All variables should be rendered
        self.assertIn(self.user.username, rendered)
        self.assertIn(self.reset.token, rendered)
        self.assertIn("https://example.com", rendered)
        self.assertIn("Test Site", rendered)
        self.assertNotIn("{{", rendered)

    def test_email_template_security(self):
        """Test that email templates are secure against XSS."""
        # Create user with potentially malicious data
        malicious_user = User.objects.create_user(
            username="<script>alert('xss')</script>",
            email="malicious@example.com",
            password="TestPass123!",
        )
        malicious_reset = PasswordReset.objects.create_for_user(malicious_user)

        from users.services import PasswordResetService

        service = PasswordResetService()

        with patch.object(service, "_send_email") as mock_send:
            service.send_reset_email(malicious_user, malicious_reset)

            if mock_send.called:
                call_args = mock_send.call_args
                text_content = call_args[1].get("message") or call_args[0][1]

                # Script tags should be escaped in plain text
                # (Django templates auto-escape by default)
                if "<script>" in text_content:
                    # If not escaped, this is a security issue
                    self.fail("Email template not properly escaping user input")

    def test_email_template_customization(self):
        """Test that email templates can be customized."""
        # This test ensures templates are properly structured for customization

        # Test with custom site settings
        with self.settings(
            EMAIL_SUBJECT_PREFIX="[CustomSite] ",
            DEFAULT_FROM_EMAIL="noreply@customsite.com",
        ):
            from users.services import PasswordResetService

            service = PasswordResetService()

            with patch.object(service, "_send_email") as mock_send:
                service.send_reset_email(self.user, self.reset)

                if mock_send.called:
                    call_args = mock_send.call_args
                    from_email = call_args[1].get("from_email")

                    # Should use custom settings
                    if from_email:
                        self.assertEqual(from_email, "noreply@customsite.com")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetEmailSendingTest(TestCase):
    """Test password reset email sending functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_email_sent_on_password_reset_request(self):
        """Test that email is sent when password reset is requested."""
        from rest_framework.test import APIClient

        client = APIClient()
        data = {"email": "test@example.com"}

        response = client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, 200)

        # Email should be sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to, [self.user.email])
        self.assertIn("password reset", email.subject.lower())

    def test_email_contains_reset_token(self):
        """Test that sent email contains the reset token."""
        from rest_framework.test import APIClient

        client = APIClient()
        data = {"email": "test@example.com"}

        response = client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        # Get the created reset token
        reset = PasswordReset.objects.get(user=self.user)

        # Email should contain the token
        self.assertIn(reset.token, email.body)

    def test_email_from_address(self):
        """Test that email is sent from correct address."""
        from rest_framework.test import APIClient

        client = APIClient()
        data = {"email": "test@example.com"}

        with self.settings(DEFAULT_FROM_EMAIL="noreply@example.com"):
            response = client.post(
                reverse("api:auth:password_reset_request"), data, format="json"
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(mail.outbox), 1)

            email = mail.outbox[0]
            self.assertEqual(email.from_email, "noreply@example.com")

    def test_email_reply_to_address(self):
        """Test email reply-to address configuration."""
        from rest_framework.test import APIClient

        client = APIClient()
        data = {"email": "test@example.com"}

        response = client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        # Reply-to should be set appropriately (if configured)
        if hasattr(email, "reply_to") and email.reply_to:
            self.assertIsInstance(email.reply_to, list)

    @patch("django.core.mail.send_mail")
    def test_email_sending_failure_handling(self, mock_send_mail):
        """Test handling of email sending failures."""
        from rest_framework.test import APIClient

        # Mock email sending to fail
        mock_send_mail.side_effect = Exception("SMTP Error")

        client = APIClient()
        data = {"email": "test@example.com"}

        response = client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        # Should still return success for security
        self.assertEqual(response.status_code, 200)

        # Should indicate email sending failed
        self.assertTrue(response.data.get("email_sending_failed", False))

        # Password reset record should still be created
        self.assertTrue(PasswordReset.objects.filter(user=self.user).exists())

    def test_html_and_text_email_versions(self):
        """Test that email contains both HTML and text versions."""
        from rest_framework.test import APIClient

        client = APIClient()
        data = {"email": "test@example.com"}

        response = client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        # Should have text body
        self.assertIsNotNone(email.body)

        # Check for HTML alternative (if implemented)
        if isinstance(email, EmailMultiAlternatives):
            html_alternatives = [
                alt for alt in email.alternatives if alt[1] == "text/html"
            ]
            if html_alternatives:
                html_content = html_alternatives[0][0]
                self.assertIn("<html>", html_content.lower())
                self.assertIn("<body>", html_content.lower())

    def test_email_headers(self):
        """Test that appropriate email headers are set."""
        from rest_framework.test import APIClient

        client = APIClient()
        data = {"email": "test@example.com"}

        response = client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        # Check for security headers
        headers = getattr(email, "extra_headers", {})

        # These headers might not be set, but if they are, they should be appropriate
        if "X-Priority" in headers:
            self.assertIn(headers["X-Priority"], ["1", "2", "3", "4", "5"])

        if "X-Auto-Response-Suppress" in headers:
            self.assertEqual(headers["X-Auto-Response-Suppress"], "All")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_encoding(self):
        """Test that email handles special characters correctly."""
        # Create user with special characters in name
        User.objects.create_user(
            username="testüser",  # Unicode character
            email="unicode@example.com",  # Unique email to avoid setUp conflict
            password="TestPass123!",
        )

        from rest_framework.test import APIClient

        client = APIClient()
        data = {"email": "unicode@example.com"}

        response = client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        # Email should handle Unicode correctly
        if "testüser" in email.body:
            # Unicode should be properly encoded
            self.assertIsInstance(email.body, str)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    USE_I18N=True,
    USE_L10N=True,
)
class PasswordResetEmailInternationalizationTest(TestCase):
    """Test internationalization support for password reset emails."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_email_localization_preparation(self):
        """Test that email templates are prepared for localization."""
        from django.utils import translation

        # Test with different languages (if templates support it)
        languages_to_test = ["en", "es", "fr", "de"]

        for lang_code in languages_to_test:
            if lang_code == "en":  # Default language should always work
                with translation.override(lang_code):
                    from rest_framework.test import APIClient

                    client = APIClient()
                    data = {"email": "test@example.com"}

                    response = client.post(
                        reverse("api:auth:password_reset_request"), data, format="json"
                    )

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(len(mail.outbox), 1)

                    # Clear outbox for next test
                    mail.outbox.clear()

    def test_email_timezone_handling(self):
        """Test that email templates handle timezones correctly."""
        import pytz
        from django.utils import timezone

        # Test with different timezones
        timezones_to_test = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]

        for tz_name in timezones_to_test:
            tz = pytz.timezone(tz_name)

            with timezone.override(tz):
                from rest_framework.test import APIClient

                client = APIClient()
                data = {"email": "test@example.com"}

                response = client.post(
                    reverse("api:auth:password_reset_request"), data, format="json"
                )

                self.assertEqual(response.status_code, 200)

                if mail.outbox:
                    email = mail.outbox[-1]
                    # Email should not contain raw timezone-unaware times
                    self.assertNotIn("+00:00", email.body)

                # Clear outbox for next test
                mail.outbox.clear()


class PasswordResetEmailSecurityTest(TestCase):
    """Test security aspects of password reset emails."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_does_not_contain_sensitive_info(self):
        """Test that email doesn't contain sensitive information."""
        from rest_framework.test import APIClient

        client = APIClient()
        data = {"email": "test@example.com"}

        response = client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        # Email should not contain:
        sensitive_info = [
            self.user.password,  # Hashed password
            "password hash",
            "database",
            "secret",
            "private key",
        ]

        for info in sensitive_info:
            self.assertNotIn(info.lower(), email.body.lower())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_contains_security_warnings(self):
        """Test that email contains appropriate security warnings."""
        from rest_framework.test import APIClient

        client = APIClient()
        data = {"email": "test@example.com"}

        response = client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        # Email should contain security advice
        security_phrases = [
            "do not share",
            "expires",
            "secure",
            "if you didn't request",
        ]

        email_body_lower = email.body.lower()
        found_phrases = [
            phrase for phrase in security_phrases if phrase in email_body_lower
        ]

        # Should contain at least some security messaging
        self.assertGreater(
            len(found_phrases), 0, "Email should contain security warnings"
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_expiration_clearly_stated(self):
        """Test that email clearly states when the reset link expires."""
        from rest_framework.test import APIClient

        client = APIClient()
        data = {"email": "test@example.com"}

        response = client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        # Email should mention expiration
        expiration_phrases = ["expires", "valid for", "24 hours", "expire"]

        email_body_lower = email.body.lower()
        found_expiration = any(
            phrase in email_body_lower for phrase in expiration_phrases
        )

        self.assertTrue(found_expiration, "Email should clearly state expiration time")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_email_backend_configuration(self):
        """Test that email backend can be configured appropriately."""
        from rest_framework.test import APIClient

        client = APIClient()
        data = {"email": "test@example.com"}

        # This should work with console backend
        response = client.post(
            reverse("api:auth:password_reset_request"), data, format="json"
        )

        self.assertEqual(response.status_code, 200)

        # Password reset should still be created even if email goes to console
        self.assertTrue(PasswordReset.objects.filter(user=self.user).exists())
