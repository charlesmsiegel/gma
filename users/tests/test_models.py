from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone


class CustomUserModelTest(TestCase):
    """Test cases for the custom User model."""

    def setUp(self):
        """Set up test fixtures."""
        self.User = get_user_model()

    def test_custom_user_model_exists(self):
        """Test that custom User model is properly defined."""
        # Verify the User model has the expected fields
        user_field_names = [field.name for field in self.User._meta.fields]

        # Check required Django User fields exist
        required_fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
        ]
        for field in required_fields:
            self.assertIn(
                field,
                user_field_names,
                f"Required field '{field}' not found in User model",
            )

        # Check custom fields exist
        custom_fields = ["display_name", "timezone", "created_at", "updated_at"]
        for field in custom_fields:
            self.assertIn(
                field,
                user_field_names,
                f"Custom field '{field}' not found in User model",
            )

    def test_user_creation_with_required_fields(self):
        """Test creating a user with required fields only."""
        user = self.User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpass123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_user_creation_with_custom_fields(self):
        """Test creating a user with custom fields."""
        user = self.User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            display_name="Test User",
            timezone="America/New_York",
        )

        self.assertEqual(user.display_name, "Test User")
        self.assertEqual(user.timezone, "America/New_York")
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)

    def test_display_name_field_properties(self):
        """Test display_name field properties."""
        # Test max length constraint
        user = self.User(
            username="testuser",
            email="test@example.com",
            display_name="x" * 100,  # Exactly 100 characters
        )
        user.set_password("testpass123")
        # Should not raise ValidationError
        user.full_clean()

        # Test exceeding max length
        user.display_name = "x" * 101  # 101 characters
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_timezone_field_default(self):
        """Test timezone field has correct default value."""
        user = self.User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.assertEqual(user.timezone, "UTC")

    def test_timezone_field_properties(self):
        """Test timezone field properties."""
        # Test max length constraint
        user = self.User(
            username="testuser",
            email="test@example.com",
            timezone="x" * 50,  # Exactly 50 characters
        )
        user.set_password("testpass123")
        # Should raise ValidationError due to invalid timezone
        with self.assertRaises(ValidationError):
            user.full_clean()

        # Test exceeding max length
        user.timezone = "x" * 51  # 51 characters
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_timezone_validation(self):
        """Test timezone field validates against valid timezone names."""
        # Test valid timezone
        user = self.User(
            username="testuser",
            email="test@example.com",
            timezone="America/New_York",
        )
        user.set_password("testpass123")
        # Should not raise ValidationError
        user.full_clean()

        # Test another valid timezone
        user.timezone = "Europe/London"
        user.full_clean()  # Should pass

        # Test invalid timezone
        user.timezone = "Invalid/Timezone"
        with self.assertRaises(ValidationError):
            user.full_clean()

        # Test empty timezone (should fail since field is not blank)
        user.timezone = ""
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_created_at_auto_now_add(self):
        """Test that created_at is automatically set on creation."""
        before_creation = timezone.now()
        user = self.User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        after_creation = timezone.now()

        self.assertIsNotNone(user.created_at)
        self.assertGreaterEqual(user.created_at, before_creation)
        self.assertLessEqual(user.created_at, after_creation)

        # Test that created_at doesn't change on update
        original_created_at = user.created_at
        user.display_name = "Updated Name"
        user.save()
        user.refresh_from_db()

        self.assertEqual(user.created_at, original_created_at)

    def test_updated_at_auto_now(self):
        """Test that updated_at is automatically updated on save."""
        user = self.User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        original_updated_at = user.updated_at

        # Wait a moment to ensure timestamp difference
        import time

        time.sleep(0.001)

        # Update the user
        before_update = timezone.now()
        user.display_name = "Updated Name"
        user.save()
        after_update = timezone.now()
        user.refresh_from_db()

        self.assertNotEqual(user.updated_at, original_updated_at)
        self.assertGreaterEqual(user.updated_at, before_update)
        self.assertLessEqual(user.updated_at, after_update)

    def test_superuser_creation(self):
        """Test creating a superuser."""
        admin_user = self.User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )

        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)

    def test_username_unique_constraint(self):
        """Test that username must be unique."""
        self.User.objects.create_user(
            username="testuser", email="test1@example.com", password="testpass123"
        )

        with self.assertRaises(IntegrityError):
            self.User.objects.create_user(
                username="testuser",  # Same username
                email="test2@example.com",
                password="testpass123",
            )

    def test_user_str_representation(self):
        """Test User model string representation."""
        user = self.User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Default Django behavior should return username
        self.assertEqual(str(user), "testuser")

    def test_user_model_inheritance(self):
        """Test that User model properly inherits from AbstractUser."""
        from django.contrib.auth.models import AbstractUser

        self.assertTrue(issubclass(self.User, AbstractUser))

    def test_user_authentication(self):
        """Test that custom User model works with Django auth system."""
        from django.contrib.auth import authenticate

        user = self.User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Test authentication
        authenticated_user = authenticate(username="testuser", password="testpass123")
        self.assertIsNotNone(authenticated_user)
        self.assertEqual(authenticated_user, user)

        # Test failed authentication
        failed_auth = authenticate(username="testuser", password="wrongpass")
        self.assertIsNone(failed_auth)

    def test_get_display_name_with_display_name_set(self):
        """Test get_display_name returns display_name when set."""
        user = self.User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            display_name="Test User Display",
        )

        self.assertEqual(user.get_display_name(), "Test User Display")

    def test_get_display_name_fallback_to_username(self):
        """Test get_display_name falls back to username when display_name is empty."""
        user = self.User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            display_name="",  # Empty display name
        )

        self.assertEqual(user.get_display_name(), "testuser")

    def test_get_display_name_fallback_to_username_when_none(self):
        """Test get_display_name falls back to username when display_name is None."""
        user = self.User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        # Explicitly set display_name to None (should be empty by default)
        user.display_name = None
        user.save()

        self.assertEqual(user.get_display_name(), "testuser")
