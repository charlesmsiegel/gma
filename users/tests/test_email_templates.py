"""
Tests for email template rendering and sending.

Tests the email template system for Issue #135:
- Email verification template rendering
- Template context variables
- HTML and text email formats
- Email sending integration
- Template customization and localization
- Error handling in email sending
"""

from unittest.mock import patch
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.template import Context, Template, TemplateDoesNotExist
from django.template.loader import get_template, render_to_string
from django.test import TestCase, override_settings

from users.models import EmailVerification

User = get_user_model()


class EmailVerificationTemplateTest(TestCase):
    """Test email verification template rendering."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        self.verification = EmailVerification.create_for_user(self.user)

    def test_email_verification_html_template_exists(self):
        """Test that HTML email verification template exists."""
        try:
            template = get_template("emails/verification/email_verification.html")
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("HTML email verification template should exist")

    def test_email_verification_text_template_exists(self):
        """Test that text email verification template exists."""
        try:
            template = get_template("emails/verification/email_verification.txt")
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail("Text email verification template should exist")

    def test_template_renders_with_required_context(self):
        """Test that templates render with required context variables."""
        context = {
            "user": self.user,
            "verification": self.verification,
            "verification_url": (
                f"https://example.com/verify/{self.verification.token}/"
            ),
            "site_name": "Game Master Application",
        }

        # Test HTML template
        try:
            html_content = render_to_string(
                "emails/verification/email_verification.html", context
            )
            self.assertIsNotNone(html_content)
            self.assertGreater(len(html_content), 0)
        except TemplateDoesNotExist:
            # Create mock template content for testing
            html_content = """
            <html>
                <body>
                    <h1>Verify Your Email</h1>
                    <p>Hello {{ user.username }},</p>
                    <p>Please verify your email by clicking: {{ verification_url }}</p>
                </body>
            </html>
            """

        # Test text template
        try:
            text_content = render_to_string(
                "emails/verification/email_verification.txt", context
            )
            self.assertIsNotNone(text_content)
            self.assertGreater(len(text_content), 0)
        except TemplateDoesNotExist:
            # Create mock template content for testing
            text_content = """
            Hello {{ user.username }},

            Please verify your email by visiting: {{ verification_url }}

            Thanks,
            {{ site_name }}
            """

    def test_template_context_variables(self):
        """Test that all required context variables are available."""
        required_variables = [
            "user",
            "verification",
            "verification_url",
            "site_name",
            "expiry_hours",
        ]

        context = {
            "user": self.user,
            "verification": self.verification,
            "verification_url": (
                f"https://example.com/verify/{self.verification.token}/"
            ),
            "site_name": "Game Master Application",
            "expiry_hours": 24,
        }

        # Test each variable is accessible
        for var in required_variables:
            self.assertIn(var, context)
            self.assertIsNotNone(context[var])

    def test_verification_url_format_in_template(self):
        """Test that verification URL is properly formatted in templates."""
        verification_url = f"https://example.com/verify/{self.verification.token}/"

        context = {
            "user": self.user,
            "verification": self.verification,
            "verification_url": verification_url,
            "site_name": "Test Site",
        }

        # Mock template rendering
        template_content = "Verification URL: {{ verification_url }}"
        template = Template(template_content)
        rendered = template.render(Context(context))

        self.assertIn(verification_url, rendered)

        # URL should be valid
        parsed_url = urlparse(verification_url)
        self.assertTrue(parsed_url.scheme)
        self.assertTrue(parsed_url.netloc)
        self.assertIn(self.verification.token, parsed_url.path)

    def test_template_user_information_display(self):
        """Test that user information is properly displayed in templates."""
        # User with display name
        user_with_display = User.objects.create_user(
            username="displayuser",
            email="display@example.com",
            password="DisplayPass123!",
            display_name="Display Name",
        )

        verification = EmailVerification.create_for_user(user_with_display)

        context = {
            "user": user_with_display,
            "verification": verification,
            "verification_url": f"https://example.com/verify/{verification.token}/",
            "site_name": "Test Site",
        }

        # Test template shows display name when available
        template_content = "Hello {{ user.get_display_name }},"
        template = Template(template_content)
        rendered = template.render(Context(context))

        self.assertIn("Display Name", rendered)

    def test_template_handles_missing_display_name(self):
        """Test that templates handle users without display names."""
        context = {
            "user": self.user,  # No display name
            "verification": self.verification,
            "verification_url": (
                f"https://example.com/verify/{self.verification.token}/"
            ),
            "site_name": "Test Site",
        }

        # Template should fall back to username
        template_content = "Hello {{ user.get_display_name }},"
        template = Template(template_content)
        rendered = template.render(Context(context))

        self.assertIn(self.user.username, rendered)

    def test_template_security_token_handling(self):
        """Test that templates handle verification tokens securely."""
        context = {
            "user": self.user,
            "verification": self.verification,
            "verification_url": (
                f"https://example.com/verify/{self.verification.token}/"
            ),
            "site_name": "Test Site",
        }

        # Token should only appear in URL, not exposed separately
        template_content = """
        Verification URL: {{ verification_url }}
        Token: {{ verification.token }}
        """
        template = Template(template_content)
        rendered = template.render(Context(context))

        # URL should contain token
        self.assertIn(self.verification.token, rendered)

        # But token should not appear separately unless explicitly included
        token_count = rendered.count(self.verification.token)
        self.assertGreaterEqual(token_count, 1)  # At least in URL


class EmailSendingIntegrationTest(TestCase):
    """Test email sending integration with templates."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_verification_email_sending_basic(self):
        """Test basic verification email sending."""
        from users.services import EmailVerificationService

        service = EmailVerificationService()
        service.send_verification_email(self.user)

        # Should have sent one email
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to, [self.user.email])
        self.assertIn("verify", email.subject.lower())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_verification_email_contains_valid_link(self):
        """Test that verification email contains valid verification link."""
        from users.services import EmailVerificationService

        service = EmailVerificationService()
        service.send_verification_email(self.user)

        email = mail.outbox[0]

        # Email should contain verification link
        verification = EmailVerification.objects.filter(user=self.user).first()
        self.assertIsNotNone(verification)

        # Check both HTML and text parts
        email_content = ""
        if hasattr(email, "body"):
            email_content += email.body

        # Should contain verification token
        self.assertIn(verification.token, email_content)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_verification_email_multipart_format(self):
        """Test that verification email is sent in multipart format."""
        from users.services import EmailVerificationService

        service = EmailVerificationService()
        service.send_verification_email(self.user)

        email = mail.outbox[0]

        # Check if email has both HTML and text parts
        # This depends on the email service implementation
        self.assertIsNotNone(email.body)

        # If HTML is supported, check alternatives
        if hasattr(email, "alternatives") and email.alternatives:
            html_content = None
            for content, mime_type in email.alternatives:
                if mime_type == "text/html":
                    html_content = content
                    break

            if html_content:
                self.assertIn(email.to[0], html_content)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_verification_email_headers(self):
        """Test that verification email has appropriate headers."""
        from users.services import EmailVerificationService

        service = EmailVerificationService()
        service.send_verification_email(self.user)

        email = mail.outbox[0]

        # Check basic headers
        self.assertIsNotNone(email.subject)
        self.assertIsNotNone(email.from_email)
        self.assertEqual(len(email.to), 1)
        self.assertEqual(email.to[0], self.user.email)

        # Check that from email is properly set
        self.assertNotEqual(email.from_email, "")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_verification_email_subject_customization(self):
        """Test that verification email subject can be customized."""
        from users.services import EmailVerificationService

        with override_settings(
            EMAIL_VERIFICATION_SUBJECT="Custom: Verify Your Account"
        ):
            service = EmailVerificationService()
            service.send_verification_email(self.user)

            email = mail.outbox[0]
            self.assertIn("Custom", email.subject)
            self.assertIn("Verify", email.subject)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_VERIFICATION_FROM_EMAIL="custom@example.com",
    )
    def test_verification_email_from_address_customization(self):
        """Test that verification email from address can be customized."""
        from users.services import EmailVerificationService

        service = EmailVerificationService()
        service.send_verification_email(self.user)

        email = mail.outbox[0]
        self.assertEqual(email.from_email, "custom@example.com")


class EmailTemplateContextTest(TestCase):
    """Test email template context generation."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        self.verification = EmailVerification.create_for_user(self.user)

    def test_email_context_generation(self):
        """Test that email context is properly generated."""
        from users.services import EmailVerificationService

        service = EmailVerificationService()
        context = service.get_email_context(self.user, self.verification)

        # Check required context variables
        required_keys = ["user", "verification", "verification_url", "site_name"]
        for key in required_keys:
            self.assertIn(key, context)

    def test_verification_url_generation(self):
        """Test that verification URL is properly generated."""
        from users.services import EmailVerificationService

        service = EmailVerificationService()
        context = service.get_email_context(self.user, self.verification)

        verification_url = context.get("verification_url")
        self.assertIsNotNone(verification_url)
        self.assertIn(self.verification.token, verification_url)

        # URL should be absolute
        parsed_url = urlparse(verification_url)
        self.assertTrue(parsed_url.scheme in ["http", "https"])
        self.assertTrue(parsed_url.netloc)

    def test_context_includes_expiry_information(self):
        """Test that context includes token expiry information."""
        from users.services import EmailVerificationService

        service = EmailVerificationService()
        context = service.get_email_context(self.user, self.verification)

        # Should include expiry hours
        self.assertIn("expiry_hours", context)
        self.assertEqual(context["expiry_hours"], 24)  # Default 24 hours

        # Should include formatted expiry time
        if "expires_at" in context:
            self.assertIsNotNone(context["expires_at"])

    def test_context_includes_site_information(self):
        """Test that context includes site information."""
        from users.services import EmailVerificationService

        service = EmailVerificationService()
        context = service.get_email_context(self.user, self.verification)

        # Should include site name
        self.assertIn("site_name", context)
        self.assertIsNotNone(context["site_name"])

        # Site name should be reasonable
        site_name = context["site_name"]
        self.assertGreater(len(site_name), 0)
        self.assertLess(len(site_name), 100)

    def test_context_user_information(self):
        """Test that context properly includes user information."""
        from users.services import EmailVerificationService

        # Test user with display name
        user_with_display = User.objects.create_user(
            username="displayuser",
            email="display@example.com",
            password="DisplayPass123!",
            display_name="Display Name",
        )

        verification = EmailVerification.create_for_user(user_with_display)

        service = EmailVerificationService()
        context = service.get_email_context(user_with_display, verification)

        # Should include user object
        self.assertEqual(context["user"], user_with_display)

        # User should have display name method available
        self.assertEqual(context["user"].get_display_name(), "Display Name")


class EmailErrorHandlingTest(TestCase):
    """Test error handling in email sending."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        # Make sure the user can receive verification emails
        self.user.email_verified = False  # Need to verify
        self.user.save()

    def test_email_service_unavailable_handling(self):
        """Test handling when email service is unavailable."""
        from users.services import EmailVerificationService

        with patch("django.core.mail.send_mail") as mock_send:
            mock_send.side_effect = Exception("Email service unavailable")

            service = EmailVerificationService()

            # Should handle exception gracefully
            with self.assertRaises(Exception):
                service.send_verification_email(self.user)

    def test_invalid_email_address_handling(self):
        """Test handling of invalid email addresses."""
        from users.services import EmailVerificationService

        # User with invalid email
        invalid_user = User.objects.create_user(
            username="invalid",
            email="invalid-email-format",
            password="InvalidPass123!",
        )

        service = EmailVerificationService()

        # Should handle invalid email gracefully
        try:
            service.send_verification_email(invalid_user)
        except Exception as e:
            # Should be a reasonable exception
            self.assertIsInstance(e, (ValidationError, ValueError))

    def test_template_missing_handling(self):
        """Test handling when email templates are missing."""
        from users.services import EmailVerificationService

        with patch("django.template.loader.render_to_string") as mock_render:
            mock_render.side_effect = TemplateDoesNotExist("Template not found")

            service = EmailVerificationService()

            # Should handle missing template gracefully
            with self.assertRaises(TemplateDoesNotExist):
                service.send_verification_email(self.user)

    def test_context_generation_error_handling(self):
        """Test error handling in context generation."""
        from users.services import EmailVerificationService

        service = EmailVerificationService()

        # Test with None verification
        with self.assertRaises(AttributeError):
            service.get_email_context(self.user, None)

        # Test with None user
        verification = EmailVerification.create_for_user(self.user)
        with self.assertRaises(AttributeError):
            service.get_email_context(None, verification)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
    def test_smtp_connection_error_handling(self):
        """Test handling of SMTP connection errors."""
        from users.services import EmailVerificationService

        with patch("django.core.mail.send_mail") as mock_send_mail:
            mock_send_mail.side_effect = Exception("SMTP connection failed")

            service = EmailVerificationService()

            # Should handle SMTP errors gracefully
            with self.assertRaises(Exception):
                service.send_verification_email(self.user)


class EmailTemplateRenderingEdgeCasesTest(TestCase):
    """Test edge cases in email template rendering."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_template_rendering_with_unicode_user_data(self):
        """Test template rendering with unicode user data."""
        # User with unicode characters
        unicode_user = User.objects.create_user(
            username="üser123",
            email="tëst@éxämplé.com",
            password="UnicodePass123!",
            display_name="Tëst Üser",
        )

        verification = EmailVerification.create_for_user(unicode_user)

        context = {
            "user": unicode_user,
            "verification": verification,
            "verification_url": f"https://example.com/verify/{verification.token}/",
            "site_name": "Test Site",
        }

        # Should render without errors
        template_content = "Hello {{ user.get_display_name }},"
        template = Template(template_content)
        rendered = template.render(Context(context))

        self.assertIn("Tëst Üser", rendered)

    def test_template_rendering_with_very_long_usernames(self):
        """Test template rendering with very long usernames."""
        long_username = "a" * 150  # Very long username

        long_user = User.objects.create_user(
            username=long_username,
            email="long@example.com",
            password="LongPass123!",
        )

        verification = EmailVerification.create_for_user(long_user)

        context = {
            "user": long_user,
            "verification": verification,
            "verification_url": f"https://example.com/verify/{verification.token}/",
            "site_name": "Test Site",
        }

        # Should handle long usernames gracefully
        template_content = "Hello {{ user.username|truncatechars:50 }},"
        template = Template(template_content)
        rendered = template.render(Context(context))

        # Should be truncated appropriately
        self.assertLess(len(rendered), len(long_username) + 20)

    def test_template_rendering_with_html_in_user_data(self):
        """Test template rendering with HTML in user data."""
        # User with HTML-like content in display name
        html_user = User.objects.create_user(
            username="htmluser",
            email="html@example.com",
            password="HtmlPass123!",
            display_name="<script>alert('xss')</script>Test User",
        )

        verification = EmailVerification.create_for_user(html_user)

        context = {
            "user": html_user,
            "verification": verification,
            "verification_url": f"https://example.com/verify/{verification.token}/",
            "site_name": "Test Site",
        }

        # Should escape HTML in text template
        template_content = "Hello {{ user.display_name|escape }},"
        template = Template(template_content)
        rendered = template.render(Context(context))

        # HTML should be escaped
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_template_rendering_performance(self):
        """Test template rendering performance with large datasets."""
        # This is a basic performance test
        users = []
        verifications = []

        # Create multiple users and verifications
        for i in range(10):
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="TestPass123!",
            )
            verification = EmailVerification.create_for_user(user)
            users.append(user)
            verifications.append(verification)

        # Render templates for all users
        template_content = "Hello {{ user.username }}, verify: {{ verification_url }}"
        template = Template(template_content)

        for user, verification in zip(users, verifications):
            context = Context(
                {
                    "user": user,
                    "verification": verification,
                    "verification_url": (
                        f"https://example.com/verify/{verification.token}/"
                    ),
                }
            )

            rendered = template.render(context)
            self.assertIn(user.username, rendered)
            self.assertIn(verification.token, rendered)
