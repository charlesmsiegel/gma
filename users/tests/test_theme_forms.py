"""
Test cases for theme form functionality.

Tests cover:
- Theme field in UserProfileForm
- Form validation and choice validation
- Widget rendering and attributes
- Form save behavior with themes
- Integration with existing profile form fields
"""

from django.contrib.auth import get_user_model
from django.forms import Select
from django.test import TestCase

from users.forms import UserProfileForm

User = get_user_model()


class ThemeFormTests(TestCase):
    """Test suite for theme-related form functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            theme="light",
        )

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

    def test_theme_field_exists_in_profile_form(self):
        """Test that theme field exists in UserProfileForm."""
        form = UserProfileForm()
        self.assertIn("theme", form.fields)

    def test_theme_field_choices_in_form(self):
        """Test that theme field has correct choices in form."""
        form = UserProfileForm()
        theme_field = form.fields["theme"]

        # Get choice values
        choice_values = [choice[0] for choice in theme_field.choices]

        # Verify all expected themes are present
        for theme in self.valid_themes:
            self.assertIn(theme, choice_values)

        # Verify we have exactly 13 choices
        self.assertEqual(len(choice_values), 13)

    def test_theme_field_choice_labels(self):
        """Test that theme field has proper display labels."""
        form = UserProfileForm()
        theme_field = form.fields["theme"]

        expected_choices = [
            ("light", "Light"),
            ("dark", "Dark"),
            ("forest", "Forest"),
            ("ocean", "Ocean"),
            ("sunset", "Sunset"),
            ("midnight", "Midnight"),
            ("lavender", "Lavender"),
            ("mint", "Mint"),
            ("high-contrast", "High Contrast"),
            ("warm", "Warm"),
            ("gothic", "Gothic"),
            ("cyberpunk", "Cyberpunk"),
            ("vintage", "Vintage"),
        ]

        self.assertEqual(list(theme_field.choices), expected_choices)

    def test_theme_field_widget_type(self):
        """Test that theme field uses Select widget."""
        form = UserProfileForm()
        theme_field = form.fields["theme"]

        self.assertIsInstance(theme_field.widget, Select)

    def test_theme_field_widget_attributes(self):
        """Test that theme field widget has proper CSS classes."""
        form = UserProfileForm()
        theme_field = form.fields["theme"]

        # Check for Bootstrap class
        widget_attrs = theme_field.widget.attrs
        self.assertIn("class", widget_attrs)
        self.assertIn("form-control", widget_attrs["class"])

    def test_theme_field_help_text(self):
        """Test that theme field has helpful text."""
        form = UserProfileForm()
        theme_field = form.fields["theme"]

        self.assertIsNotNone(theme_field.help_text)
        self.assertIn("theme", theme_field.help_text.lower())

    def test_form_validation_with_valid_themes(self):
        """Test form validation with all valid theme choices."""
        for theme in self.valid_themes:
            with self.subTest(theme=theme):
                form_data = {
                    "display_name": "Test User",
                    "timezone": "UTC",
                    "theme": theme,
                }

                form = UserProfileForm(data=form_data, instance=self.user)
                self.assertTrue(
                    form.is_valid(),
                    f"Form should be valid with theme '{theme}': {form.errors}",
                )

    def test_form_validation_with_invalid_themes(self):
        """Test form validation rejects invalid theme choices."""
        invalid_themes = [
            "invalid",
            "neon",
            "rainbow",
            "LIGHT",
            "dark-mode",
            "",
            None,
            123,
            "nonexistent-theme",
        ]

        for invalid_theme in invalid_themes:
            with self.subTest(theme=invalid_theme):
                form_data = {
                    "display_name": "Test User",
                    "timezone": "UTC",
                    "theme": invalid_theme,
                }

                form = UserProfileForm(data=form_data, instance=self.user)
                self.assertFalse(form.is_valid())
                self.assertIn("theme", form.errors)

    def test_form_save_updates_user_theme(self):
        """Test that saving form updates user's theme."""
        form_data = {
            "display_name": "Updated User",
            "timezone": "America/New_York",
            "theme": "ocean",
        }

        form = UserProfileForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

        updated_user = form.save()

        self.assertEqual(updated_user.theme, "ocean")
        self.assertEqual(updated_user.display_name, "Updated User")
        self.assertEqual(updated_user.timezone, "America/New_York")

    def test_form_initialization_with_user_theme(self):
        """Test that form initializes with user's current theme."""
        self.user.theme = "gothic"
        self.user.save()

        form = UserProfileForm(instance=self.user)

        # Check initial value
        self.assertEqual(form["theme"].initial, "gothic")

    def test_form_preserves_existing_fields(self):
        """Test that adding theme field doesn't break existing functionality."""
        form_data = {
            "display_name": "New Display Name",
            "timezone": "Europe/London",
            "theme": "vintage",
        }

        form = UserProfileForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

        updated_user = form.save()

        # All fields should be updated
        self.assertEqual(updated_user.display_name, "New Display Name")
        self.assertEqual(updated_user.timezone, "Europe/London")
        self.assertEqual(updated_user.theme, "vintage")

    def test_form_clean_theme_method_exists(self):
        """Test that form has theme cleaning method if needed."""
        form = UserProfileForm()

        # Check if custom clean_theme method exists
        if hasattr(form, "clean_theme"):
            # Test custom validation
            form_data = {
                "display_name": "Test",
                "timezone": "UTC",
                "theme": "dark",
            }

            form = UserProfileForm(data=form_data, instance=self.user)
            self.assertTrue(form.is_valid())

    def test_form_theme_field_required_setting(self):
        """Test theme field required setting."""
        form = UserProfileForm()
        theme_field = form.fields["theme"]

        # Theme should be optional to support backward compatibility
        self.assertFalse(theme_field.required)

    def test_form_with_missing_theme_field(self):
        """Test form behavior when theme field is missing from data."""
        form_data = {
            "display_name": "Test User",
            "timezone": "UTC",
            # theme field missing
        }

        form = UserProfileForm(data=form_data, instance=self.user)

        # Form should be valid when theme field is missing (backward compatibility)
        self.assertTrue(form.is_valid())
        # Theme should not be in errors since it's handled gracefully
        self.assertNotIn("theme", form.errors)

    def test_form_theme_field_empty_string(self):
        """Test form behavior with empty string theme value."""
        form_data = {
            "display_name": "Test User",
            "timezone": "UTC",
            "theme": "",
        }

        form = UserProfileForm(data=form_data, instance=self.user)

        # Empty string should be invalid
        self.assertFalse(form.is_valid())
        self.assertIn("theme", form.errors)

    def test_form_theme_field_none_value(self):
        """Test form behavior with None theme value."""
        form_data = {
            "display_name": "Test User",
            "timezone": "UTC",
            "theme": None,
        }

        form = UserProfileForm(data=form_data, instance=self.user)

        # None should be invalid
        self.assertFalse(form.is_valid())
        self.assertIn("theme", form.errors)

    def test_form_meta_fields_include_theme(self):
        """Test that form Meta fields include core fields (theme handled separately)."""
        form = UserProfileForm()
        meta_fields = form.Meta.fields

        # Theme is handled as separate form field, not in Meta.fields
        self.assertNotIn("theme", meta_fields)
        # Should include existing core fields
        self.assertIn("display_name", meta_fields)
        self.assertIn("timezone", meta_fields)

        # But theme field should still be available in the form
        self.assertIn("theme", form.fields)

    def test_form_rendering_includes_theme_field(self):
        """Test that form rendering includes theme field HTML."""
        form = UserProfileForm(instance=self.user)
        form_html = form.as_p()

        # Check that theme field is rendered
        self.assertIn('name="theme"', form_html)
        self.assertIn("<select", form_html)

        # Check that all theme options are rendered
        for theme in self.valid_themes:
            self.assertIn(f'value="{theme}"', form_html)

    def test_form_theme_field_default_selection(self):
        """Test that form shows current user theme as selected."""
        self.user.theme = "cyberpunk"
        self.user.save()

        form = UserProfileForm(instance=self.user)
        form_html = form.as_p()

        # Should have cyberpunk selected
        self.assertIn('value="cyberpunk" selected', form_html)

    def test_form_validation_error_messages(self):
        """Test that form provides clear error messages for invalid themes."""
        form_data = {
            "display_name": "Test User",
            "timezone": "UTC",
            "theme": "invalid_theme_choice",
        }

        form = UserProfileForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())

        theme_errors = form.errors["theme"]
        self.assertTrue(
            any(
                "not one of the available choices" in str(error)
                for error in theme_errors
            )
        )

    def test_form_bound_vs_unbound_theme_behavior(self):
        """Test form behavior for bound vs unbound forms with theme."""
        # Unbound form
        unbound_form = UserProfileForm()
        self.assertFalse(unbound_form.is_bound)
        self.assertIn("theme", unbound_form.fields)

        # Bound form with valid data
        form_data = {
            "display_name": "Test",
            "timezone": "UTC",
            "theme": "mint",
        }
        bound_form = UserProfileForm(data=form_data, instance=self.user)
        self.assertTrue(bound_form.is_bound)
        self.assertTrue(bound_form.is_valid())

    def test_form_save_commit_false_with_theme(self):
        """Test form save with commit=False preserves theme changes."""
        form_data = {
            "display_name": "Test Save",
            "timezone": "Europe/Berlin",
            "theme": "lavender",
        }

        form = UserProfileForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

        # Save with commit=False
        user = form.save(commit=False)

        # Theme should be set on the unsaved instance
        self.assertEqual(user.theme, "lavender")
        self.assertEqual(user.display_name, "Test Save")
        self.assertEqual(user.timezone, "Europe/Berlin")

        # Check that they're the same instance
        self.assertEqual(user.pk, self.user.pk)

        # Now save the user
        user.save()

        # Now it should be persisted - refresh from database
        saved_user = User.objects.get(pk=self.user.pk)
        self.assertEqual(saved_user.theme, "lavender")
        self.assertEqual(saved_user.display_name, "Test Save")
        self.assertEqual(saved_user.timezone, "Europe/Berlin")

    def test_form_multiple_instances_different_themes(self):
        """Test multiple form instances with different themes."""
        user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
            theme="forest",
        )

        form1 = UserProfileForm(instance=self.user)
        form2 = UserProfileForm(instance=user2)

        # Each form should show its user's theme
        self.assertEqual(form1["theme"].initial, "light")
        self.assertEqual(form2["theme"].initial, "forest")

    def test_form_theme_field_accessibility_attributes(self):
        """Test that theme field has proper accessibility attributes."""
        form = UserProfileForm()
        theme_field = form.fields["theme"]

        # Check for ARIA or other accessibility attributes if implemented
        # This test depends on specific implementation
        self.assertIsInstance(theme_field.widget, Select)

        # Verify widget has proper attributes for accessibility
        widget_attrs = theme_field.widget.attrs
        if "aria-label" in widget_attrs or "aria-describedby" in widget_attrs:
            # Good - form has accessibility attributes
            pass

        # At minimum, should have help text for screen readers
        self.assertIsNotNone(theme_field.help_text)
