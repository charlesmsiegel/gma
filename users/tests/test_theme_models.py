"""
Test cases for user theme model functionality.

Tests cover:
- Theme field choices and validation
- Default theme values for new users
- Theme field database constraints
- Edge cases and invalid values
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()


class UserThemeModelTests(TestCase):
    """Test suite for User model theme field functionality."""

    def setUp(self):
        """Set up test data."""
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

    def test_theme_field_exists(self):
        """Test that theme field exists on User model."""
        user = User()
        self.assertTrue(hasattr(user, "theme"))

    def test_theme_field_choices(self):
        """Test that theme field has correct choices defined."""
        # Get theme field from model
        theme_field = User._meta.get_field("theme")

        # Extract choice values
        choice_values = [choice[0] for choice in theme_field.choices]

        # Verify all expected themes are present
        for theme in self.valid_themes:
            self.assertIn(theme, choice_values)

        # Verify we have exactly 13 choices
        self.assertEqual(len(choice_values), 13)

    def test_theme_field_default_value(self):
        """Test that theme field defaults to 'light' for new users."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Check default value
        self.assertEqual(user.theme, "light")

        # Verify it persists in database
        user.refresh_from_db()
        self.assertEqual(user.theme, "light")

    def test_theme_field_can_be_set_to_valid_values(self):
        """Test that theme field accepts all valid theme choices."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Test each valid theme
        for theme in self.valid_themes:
            user.theme = theme
            user.full_clean()  # This will raise ValidationError if invalid
            user.save()

            # Verify it persisted
            user.refresh_from_db()
            self.assertEqual(user.theme, theme)

    def test_theme_field_rejects_invalid_values(self):
        """Test that theme field rejects invalid theme choices."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        invalid_themes = [
            "invalid",
            "neon",
            "rainbow",
            "LIGHT",  # Case sensitive
            "dark-mode",
            "",
            None,
            123,
            "theme-that-does-not-exist",
        ]

        for invalid_theme in invalid_themes:
            with self.subTest(theme=invalid_theme):
                user.theme = invalid_theme
                with self.assertRaises(ValidationError):
                    user.full_clean()

    def test_theme_field_max_length(self):
        """Test theme field respects max_length constraint."""
        theme_field = User._meta.get_field("theme")
        self.assertEqual(theme_field.max_length, 20)

    def test_theme_field_null_and_blank_settings(self):
        """Test theme field null and blank constraints."""
        theme_field = User._meta.get_field("theme")

        # Theme should not allow null (has default)
        self.assertFalse(theme_field.null)

        # Theme should not allow blank (required field)
        self.assertFalse(theme_field.blank)

    def test_multiple_users_can_have_same_theme(self):
        """Test that multiple users can have the same theme value."""
        # Create multiple users with same theme
        user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )
        user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )

        # Both should default to light
        self.assertEqual(user1.theme, "light")
        self.assertEqual(user2.theme, "light")

        # Both can be set to same custom theme
        user1.theme = "dark"
        user2.theme = "dark"

        user1.save()
        user2.save()

        user1.refresh_from_db()
        user2.refresh_from_db()

        self.assertEqual(user1.theme, "dark")
        self.assertEqual(user2.theme, "dark")

    def test_theme_field_database_constraint(self):
        """Test theme field database-level constraints."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Try to bypass Django validation and set invalid value directly in DB
        # This should be caught by database constraints if properly configured
        with transaction.atomic():
            try:
                # Use raw SQL to try to set invalid theme
                from django.db import connection

                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE users_user SET theme = %s WHERE id = %s",
                        ["invalid_theme", user.id],
                    )

                # If we get here, the database allowed the invalid value
                # Refresh and check - Django validation should catch it
                user.refresh_from_db()
                with self.assertRaises(ValidationError):
                    user.full_clean()

            except (IntegrityError, ValidationError):
                # Expected - either DB constraint or Django validation caught it
                pass

    def test_user_str_representation_unaffected_by_theme(self):
        """Test that theme field doesn't affect user string representation."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        original_str = str(user)

        # Change theme
        user.theme = "dark"
        user.save()

        # String representation should be unchanged
        self.assertEqual(str(user), original_str)

    def test_theme_field_in_user_creation(self):
        """Test setting theme during user creation."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            theme="ocean",
        )

        self.assertEqual(user.theme, "ocean")

        # Verify it persists
        user.refresh_from_db()
        self.assertEqual(user.theme, "ocean")

    def test_theme_field_migration_compatibility(self):
        """Test that existing users get default theme value."""
        # Create user without explicitly setting theme
        user = User(username="testuser", email="test@example.com")
        user.set_password("testpass123")

        # Before saving, theme should have default
        self.assertEqual(user.theme, "light")

        user.save()

        # After saving, theme should still be default
        self.assertEqual(user.theme, "light")

    def test_theme_choices_display_names(self):
        """Test that theme choices have proper display names."""
        theme_field = User._meta.get_field("theme")

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

    def test_theme_field_help_text(self):
        """Test that theme field has appropriate help text."""
        theme_field = User._meta.get_field("theme")

        expected_help_text = "Choose your preferred theme for the interface"
        self.assertEqual(theme_field.help_text, expected_help_text)

    def test_bulk_create_users_with_themes(self):
        """Test bulk creation of users with different themes."""
        users_data = []
        for i, theme in enumerate(self.valid_themes):
            users_data.append(
                User(username=f"user{i}", email=f"user{i}@example.com", theme=theme)
            )

        # Set passwords after creation since bulk_create doesn't call save()
        for user in users_data:
            user.set_password("testpass123")

        User.objects.bulk_create(users_data)

        # Verify all themes were set correctly
        for i, theme in enumerate(self.valid_themes):
            user = User.objects.get(username=f"user{i}")
            self.assertEqual(user.theme, theme)

    def test_theme_field_ordering_unaffected(self):
        """Test that User model ordering is unaffected by theme field."""
        # Create users with different themes
        user_a = User.objects.create_user(
            username="a_user",
            email="a@example.com",
            password="testpass123",
            theme="dark",
        )
        user_z = User.objects.create_user(
            username="z_user",
            email="z@example.com",
            password="testpass123",
            theme="light",
        )

        # Verify ordering is still by username (as defined in Meta)
        users = list(User.objects.all())
        self.assertEqual(users[0], user_a)  # a_user comes first
        self.assertEqual(users[1], user_z)  # z_user comes second
