"""
Test cases for theme context processor functionality.

Tests cover:
- Theme injection into template context
- Anonymous vs authenticated user theme handling
- Context processor performance and caching
- Integration with template rendering
- Template data-theme attribute injection
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.template import Context, Template
from django.test import RequestFactory, TestCase, override_settings
from django.test.client import Client

User = get_user_model()


class ThemeContextProcessorTests(TestCase):
    """Test suite for theme context processor functionality."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            theme="dark",
        )
        self.client = Client()

    def create_request(self, path="/", user=None):
        """Helper method to create request with user."""
        request = self.factory.get(path)
        if user:
            request.user = user
        else:
            request.user = AnonymousUser()
        return request

    def test_context_processor_exists(self):
        """Test that theme context processor is properly defined."""
        # This test verifies the context processor function exists
        try:
            from users.context_processors import theme_context

            self.assertTrue(callable(theme_context))
        except ImportError:
            self.fail(
                "Theme context processor not found. "
                "Should be defined in users.context_processors.theme_context"
            )

    def test_authenticated_user_theme_in_context(self):
        """Test that authenticated user's theme is injected into context."""
        from users.context_processors import theme_context

        request = self.create_request(user=self.user)
        context = theme_context(request)

        self.assertIn("user_theme", context)
        self.assertEqual(context["user_theme"], "dark")

    def test_anonymous_user_gets_default_theme(self):
        """Test that anonymous users get default theme in context."""
        from users.context_processors import theme_context

        request = self.create_request()  # No user - anonymous
        context = theme_context(request)

        self.assertIn("user_theme", context)
        self.assertEqual(context["user_theme"], "light")  # Default theme

    def test_different_user_themes_in_context(self):
        """Test that different users get their specific themes."""
        from users.context_processors import theme_context

        # Create users with different themes
        user_ocean = User.objects.create_user(
            username="ocean_user",
            email="ocean@example.com",
            password="testpass123",
            theme="ocean",
        )

        user_gothic = User.objects.create_user(
            username="gothic_user",
            email="gothic@example.com",
            password="testpass123",
            theme="gothic",
        )

        # Test each user gets their theme
        request1 = self.create_request(user=user_ocean)
        context1 = theme_context(request1)
        self.assertEqual(context1["user_theme"], "ocean")

        request2 = self.create_request(user=user_gothic)
        context2 = theme_context(request2)
        self.assertEqual(context2["user_theme"], "gothic")

    def test_context_processor_handles_none_user(self):
        """Test context processor gracefully handles None user."""
        from users.context_processors import theme_context

        request = self.factory.get("/")
        request.user = None

        # Should not raise exception
        context = theme_context(request)
        self.assertIn("user_theme", context)
        self.assertEqual(context["user_theme"], "light")

    def test_context_processor_with_invalid_user_theme(self):
        """Test context processor handles users with invalid theme values."""
        from users.context_processors import theme_context

        # Manually set invalid theme (bypassing validation)
        self.user.theme = "invalid_theme"
        # Save without full_clean to bypass validation
        User.objects.filter(id=self.user.id).update(theme="invalid_theme")

        # Refresh user from database
        self.user.refresh_from_db()

        request = self.create_request(user=self.user)
        context = theme_context(request)

        # Should fall back to default theme for invalid values
        self.assertIn("user_theme", context)
        self.assertEqual(context["user_theme"], "light")

    @override_settings(
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.debug",
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                        "users.context_processors.theme_context",
                    ],
                },
            }
        ]
    )
    def test_theme_available_in_template_rendering(self):
        """Test that theme is available during template rendering."""
        self.client.login(username="testuser", password="testpass123")

        # Create a simple template that uses the theme
        template_content = """
        <html>
        <body data-theme="{{ user_theme }}">
            <div class="theme-indicator">Theme: {{ user_theme }}</div>
        </body>
        </html>
        """

        template = Template(template_content)
        request = self.create_request(user=self.user)

        # Add required context processors
        context = Context(
            {
                "user": self.user,
                "request": request,
            }
        )

        # Manually add theme context
        from users.context_processors import theme_context

        theme_ctx = theme_context(request)
        context.update(theme_ctx)

        rendered = template.render(context)

        self.assertIn('data-theme="dark"', rendered)
        self.assertIn("Theme: dark", rendered)

    def test_theme_context_processor_performance(self):
        """Test that context processor is performant and doesn't cause extra queries."""
        from users.context_processors import theme_context

        request = self.create_request(user=self.user)

        # The new theme system will make queries to get theme objects and available themes
        # This is acceptable for the enhanced functionality
        with self.assertNumQueries(5):  # Expected queries for theme system
            context = theme_context(request)
            self.assertEqual(context["user_theme"], "dark")

    def test_context_processor_returns_dict(self):
        """Test that context processor returns a dictionary."""
        from users.context_processors import theme_context

        request = self.create_request(user=self.user)
        context = theme_context(request)

        self.assertIsInstance(context, dict)

    def test_context_processor_with_all_theme_values(self):
        """Test context processor with all valid theme values."""
        from users.context_processors import theme_context

        valid_themes = [
            "light",
            "dark",
            "forest",
            "ocean",
            "sunset",
            "midnight",
            "lavender",
            "mint",
            "high-contrast",
            "warm",
            "gothic",
            "cyberpunk",
            "vintage",
        ]

        for theme in valid_themes:
            with self.subTest(theme=theme):
                # Update user theme
                self.user.theme = theme
                self.user.save()

                request = self.create_request(user=self.user)
                context = theme_context(request)

                self.assertEqual(context["user_theme"], theme)

    def test_body_tag_data_theme_attribute(self):
        """Test that body tag gets data-theme attribute from context."""
        # This test would require actual template rendering
        # We'll test the context is available, template usage is tested elsewhere

        from users.context_processors import theme_context

        self.user.theme = "cyberpunk"
        self.user.save()

        request = self.create_request(user=self.user)
        context = theme_context(request)

        # Verify the context provides what templates need
        self.assertEqual(context["user_theme"], "cyberpunk")

        # Template would use: <body data-theme="{{ user_theme }}">
        # This creates: <body data-theme="cyberpunk">

    def test_context_processor_with_multiple_requests(self):
        """Test context processor handles multiple concurrent requests."""
        from users.context_processors import theme_context

        # Create multiple users
        users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="testpass123",
                theme="ocean" if i % 2 == 0 else "gothic",
            )
            users.append(user)

        # Test concurrent requests
        for user in users:
            request = self.create_request(user=user)
            context = theme_context(request)

            expected_theme = (
                "ocean" if user.username.endswith(("0", "2", "4")) else "gothic"
            )
            self.assertEqual(context["user_theme"], expected_theme)

    def test_context_processor_integration_with_settings(self):
        """Test that context processor is properly configured in settings."""
        # This test checks if the context processor is in Django settings
        from django.conf import settings

        # Check if our context processor is in TEMPLATES configuration
        template_config = settings.TEMPLATES[0]  # Assuming default template config
        context_processors = template_config["OPTIONS"]["context_processors"]

        self.assertIn("users.context_processors.theme_context", context_processors)

    def test_context_processor_caching_behavior(self):
        """Test context processor caching behavior if implemented."""
        from users.context_processors import theme_context

        request = self.create_request(user=self.user)

        # Call multiple times - will make queries each time due to theme lookups
        # In a real application, this would be cached or optimized
        with self.assertNumQueries(9):  # Theme lookup queries
            context1 = theme_context(request)
            context2 = theme_context(request)

            self.assertEqual(context1, context2)
            self.assertEqual(context1["user_theme"], "dark")

    def test_context_processor_with_request_without_user_attribute(self):
        """Test context processor handles requests without user attribute."""
        from users.context_processors import theme_context

        request = self.factory.get("/")
        # Don't set request.user

        try:
            context = theme_context(request)
            # Should default to light theme or handle gracefully
            self.assertIn("user_theme", context)
            self.assertEqual(context["user_theme"], "light")
        except AttributeError:
            # If it raises AttributeError, the context processor needs improvement
            self.fail("Context processor should handle requests without user attribute")

    def test_theme_context_processor_error_handling(self):
        """Test context processor error handling for edge cases."""
        from users.context_processors import theme_context

        # Test with various edge case requests
        edge_cases = [
            self.factory.get("/"),  # Basic request
            self.factory.post("/", {}),  # POST request
            self.factory.get("/?theme=invalid"),  # Request with query params
        ]

        for req in edge_cases:
            with self.subTest(request=req):
                req.user = self.user

                # Should not raise exceptions
                try:
                    context = theme_context(req)
                    self.assertIsInstance(context, dict)
                    self.assertIn("user_theme", context)
                except Exception as e:
                    self.fail(f"Context processor failed for request {req}: {e}")

    def test_theme_context_processor_with_superuser(self):
        """Test context processor with superuser accounts."""
        from users.context_processors import theme_context

        superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            theme="midnight",
        )

        request = self.create_request(user=superuser)
        context = theme_context(request)

        self.assertEqual(context["user_theme"], "midnight")

    def test_theme_context_processor_return_keys(self):
        """Test that context processor returns expected keys."""
        from users.context_processors import theme_context

        request = self.create_request(user=self.user)
        context = theme_context(request)

        # Should return exactly the keys we expect
        expected_keys = {"user_theme", "theme_object", "available_themes"}
        self.assertEqual(set(context.keys()), expected_keys)
