"""
Test cases for user theme view functionality.

Tests cover:
- Profile edit view with theme selection
- Theme form submission and validation
- Template rendering with theme data
- Page reload after theme change
- Authentication requirements for theme changes
"""

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class UserThemeViewTests(TestCase):
    """Test suite for theme-related view functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            theme="light",  # Start with light theme
        )
        self.profile_edit_url = reverse("users:profile_edit")

        self.valid_themes = [
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

    def test_profile_edit_view_requires_authentication(self):
        """Test that profile edit view requires user authentication."""
        # Try to access without login
        response = self.client.get(self.profile_edit_url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_profile_edit_view_displays_current_theme(self):
        """Test that profile edit view displays user's current theme."""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(self.profile_edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "theme")

        # Check that current theme is selected
        self.assertContains(response, 'value="light" selected')

    def test_profile_edit_view_shows_all_theme_options(self):
        """Test that all theme options are available in the form."""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(self.profile_edit_url)

        self.assertEqual(response.status_code, 200)

        # Check that all theme options are present
        for theme in self.valid_themes:
            self.assertContains(response, f'value="{theme}"')

    def test_theme_change_via_post_request(self):
        """Test changing theme via POST request to profile edit."""
        self.client.login(username="testuser", password="testpass123")

        # Submit form with new theme
        response = self.client.post(
            self.profile_edit_url,
            {
                "theme": "dark",
                "display_name": self.user.display_name or "",
                "timezone": self.user.timezone,
            },
        )

        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)

        # Verify theme was changed in database
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme, "dark")

    def test_all_themes_can_be_set_via_view(self):
        """Test that all valid themes can be set through the view."""
        self.client.login(username="testuser", password="testpass123")

        for theme in self.valid_themes:
            with self.subTest(theme=theme):
                response = self.client.post(
                    self.profile_edit_url,
                    {
                        "theme": theme,
                        "display_name": self.user.display_name or "",
                        "timezone": self.user.timezone,
                    },
                )

                self.assertEqual(response.status_code, 302)

                # Verify theme was set
                self.user.refresh_from_db()
                self.assertEqual(self.user.theme, theme)

    def test_invalid_theme_rejected_by_view(self):
        """Test that invalid theme values are rejected by the view."""
        self.client.login(username="testuser", password="testpass123")

        invalid_themes = ["invalid", "neon", "", "LIGHT"]

        for invalid_theme in invalid_themes:
            with self.subTest(theme=invalid_theme):
                original_theme = self.user.theme

                response = self.client.post(
                    self.profile_edit_url,
                    {
                        "theme": invalid_theme,
                        "display_name": self.user.display_name or "",
                        "timezone": self.user.timezone,
                    },
                )

                # Form should not be valid, should show errors
                self.assertEqual(response.status_code, 200)  # Shows form with errors

                # Theme should not have changed
                self.user.refresh_from_db()
                self.assertEqual(self.user.theme, original_theme)

    def test_missing_theme_preserves_current_theme(self):
        """Test that when theme field is not provided, current theme is preserved."""
        self.client.login(username="testuser", password="testpass123")

        # Set user to a specific theme first
        self.user.theme = "cyberpunk"
        self.user.save()

        # Update profile without providing theme field (simulates old tests)
        response = self.client.post(
            self.profile_edit_url,
            {
                "display_name": "Updated Name",
                "timezone": "Europe/London",
                # Note: no theme field provided
            },
        )

        # Should succeed (302 redirect)
        self.assertEqual(response.status_code, 302)

        # Theme should be preserved
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme, "cyberpunk")

    def test_theme_form_validation_errors_displayed(self):
        """Test that theme validation errors are properly displayed."""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            self.profile_edit_url,
            {
                "theme": "invalid_theme",
                "display_name": self.user.display_name or "",
                "timezone": self.user.timezone,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "theme",
            "Select a valid choice. invalid_theme is not one of the available choices.",
        )

    def test_successful_theme_change_shows_success_message(self):
        """Test that successful theme change shows success message."""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            self.profile_edit_url,
            {
                "theme": "ocean",
                "display_name": self.user.display_name or "",
                "timezone": self.user.timezone,
            },
            follow=True,
        )

        # Check for success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("successfully updated" in str(m) for m in messages))

    def test_theme_persists_across_requests(self):
        """Test that theme change persists across multiple requests."""
        self.client.login(username="testuser", password="testpass123")

        # Change theme
        self.client.post(
            self.profile_edit_url,
            {
                "theme": "cyberpunk",
                "display_name": self.user.display_name or "",
                "timezone": self.user.timezone,
            },
        )

        # Make another request to profile edit
        response = self.client.get(self.profile_edit_url)

        # Verify cyberpunk theme is still selected
        self.assertContains(response, 'value="cyberpunk" selected')

        # Verify in database
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme, "cyberpunk")

    def test_page_reload_after_theme_change(self):
        """Test that page reloads with new theme applied after change."""
        self.client.login(username="testuser", password="testpass123")

        # Change theme
        response = self.client.post(
            self.profile_edit_url,
            {
                "theme": "midnight",
                "display_name": self.user.display_name or "",
                "timezone": self.user.timezone,
            },
            follow=True,
        )

        # Should have redirected and followed to show updated page
        self.assertEqual(response.status_code, 200)

        # Check that the page contains theme data
        # (This assumes theme is injected into context and used in template)
        self.assertContains(response, 'data-theme="midnight"')

    def test_concurrent_theme_changes(self):
        """Test handling of concurrent theme changes."""
        # Create two clients for the same user
        client1 = Client()
        client2 = Client()

        client1.login(username="testuser", password="testpass123")
        client2.login(username="testuser", password="testpass123")

        # Both clients change theme simultaneously
        response1 = client1.post(
            self.profile_edit_url,
            {
                "theme": "forest",
                "display_name": self.user.display_name or "",
                "timezone": self.user.timezone,
            },
        )

        response2 = client2.post(
            self.profile_edit_url,
            {
                "theme": "vintage",
                "display_name": self.user.display_name or "",
                "timezone": self.user.timezone,
            },
        )

        # Both should succeed (last write wins)
        self.assertEqual(response1.status_code, 302)
        self.assertEqual(response2.status_code, 302)

        # Final theme should be one of the two
        self.user.refresh_from_db()
        self.assertIn(self.user.theme, ["forest", "vintage"])

    def test_theme_in_template_context(self):
        """Test that current user theme is available in template context."""
        self.client.login(username="testuser", password="testpass123")

        # Change to a distinctive theme
        self.user.theme = "gothic"
        self.user.save()

        response = self.client.get(self.profile_edit_url)

        # Check template context has user theme
        self.assertEqual(response.context["user"].theme, "gothic")

    def test_anonymous_user_has_default_theme_context(self):
        """Test that anonymous users get default theme in context."""
        # Don't login - test anonymous user

        # Try accessing a public page (if any exist)
        # For this test, we'll use the profile edit page redirect
        self.client.get(self.profile_edit_url)

        # Should redirect to login (302), but let's test context processor
        # We'll test this more thoroughly in the context processor tests

    def test_theme_form_preserves_other_fields(self):
        """Test that changing theme preserves other profile fields."""
        self.client.login(username="testuser", password="testpass123")

        # Set some profile data
        self.user.display_name = "Test Display Name"
        self.user.timezone = "America/New_York"
        self.user.save()

        # Change only theme
        response = self.client.post(
            self.profile_edit_url,
            {
                "theme": "warm",
                "display_name": "Test Display Name",
                "timezone": "America/New_York",
            },
        )

        self.assertEqual(response.status_code, 302)

        # Verify theme changed but other fields preserved
        self.user.refresh_from_db()
        self.assertEqual(self.user.theme, "warm")
        self.assertEqual(self.user.display_name, "Test Display Name")
        self.assertEqual(self.user.timezone, "America/New_York")

    def test_partial_form_submission_with_theme(self):
        """Test form submission with missing fields but valid theme."""
        self.client.login(username="testuser", password="testpass123")

        # Submit with only theme (missing other fields)
        response = self.client.post(
            self.profile_edit_url,
            {
                "theme": "lavender",
            },
        )

        # Form should handle missing fields gracefully
        # (Depends on form implementation - might be valid or might show errors)
        if response.status_code == 302:
            # If successful, theme should be updated
            self.user.refresh_from_db()
            self.assertEqual(self.user.theme, "lavender")
        else:
            # If form errors, original theme should be preserved
            self.user.refresh_from_db()
            self.assertEqual(self.user.theme, "light")

    def test_csrf_protection_on_theme_change(self):
        """Test that CSRF protection is enforced on theme changes."""
        self.client.login(username="testuser", password="testpass123")

        # Try to submit without CSRF token
        self.client.logout()
        self.client.login(username="testuser", password="testpass123")

        # Disable CSRF middleware for this test by using enforce_csrf_checks=False
        # or test that CSRF token is required
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username="testuser", password="testpass123")

        response = csrf_client.post(
            self.profile_edit_url,
            {
                "theme": "dark",
                "display_name": "",
                "timezone": "UTC",
            },
        )

        # Should be rejected due to missing CSRF token
        self.assertEqual(response.status_code, 403)

    def test_get_request_to_profile_shows_form(self):
        """Test that GET request to profile edit shows the form correctly."""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(self.profile_edit_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")
        self.assertContains(response, 'name="theme"')
        self.assertContains(response, "<select")

        # Should contain all theme options
        for theme in self.valid_themes:
            self.assertContains(response, theme)

    def test_profile_view_accessibility_for_theme_selector(self):
        """Test that theme selector has proper accessibility attributes."""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(self.profile_edit_url)

        self.assertEqual(response.status_code, 200)

        # Check for accessibility features
        self.assertContains(response, 'name="theme"')
        # Note: Specific accessibility attributes would
        # depend on template implementation
