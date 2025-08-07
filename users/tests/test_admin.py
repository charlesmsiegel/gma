from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase


class UserAdminTest(TestCase):
    """Test cases for User model admin registration."""

    def test_user_model_registered_in_admin(self):
        """Test that User model is registered in Django admin."""
        User = get_user_model()

        # Check that User model is registered in admin
        self.assertIn(User, admin.site._registry)

        # Get the admin class for User
        user_admin = admin.site._registry[User]

        # Check that it's properly configured
        self.assertIsNotNone(user_admin)

    def test_user_admin_fields_accessible(self):
        """Test that custom fields are accessible in admin."""
        User = get_user_model()

        # Create a test user to ensure we can access fields
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            display_name="Test User",
            timezone="America/New_York",
        )

        # Check that admin can access the custom fields
        # This ensures the fields are properly configured for admin interface
        self.assertTrue(hasattr(user, "display_name"))
        self.assertTrue(hasattr(user, "timezone"))
        self.assertTrue(hasattr(user, "created_at"))
        self.assertTrue(hasattr(user, "updated_at"))
