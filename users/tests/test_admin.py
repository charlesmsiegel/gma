from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import transaction
from django.test import RequestFactory, TestCase

from users.admin import UserAdmin


class UserAdminTest(TestCase):
    """Test cases for User model admin registration."""

    def setUp(self):
        """Set up test data."""
        self.User = get_user_model()
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.user_admin = UserAdmin(self.User, self.site)

        # Create test users with explicit transaction handling
        with transaction.atomic():
            self.regular_user = self.User.objects.create_user(
                username="regularuser",
                email="regular@example.com",
                password="testpass123",
                display_name="Regular User",
                timezone="America/New_York",
            )

            self.staff_user = self.User.objects.create_user(
                username="staffuser",
                email="staff@example.com",
                password="testpass123",
                is_staff=True,
                display_name="Staff User",
            )

            self.superuser = self.User.objects.create_superuser(
                username="superuser",
                email="super@example.com",
                password="testpass123",
                display_name="Super User",
            )

    def tearDown(self):
        """Clean up test data."""
        # Ensure all database connections are properly closed
        with transaction.atomic():
            self.User.objects.all().delete()

    def _get_request(self, user=None):
        """Create a mock request with user."""
        request = self.factory.get("/")
        request.user = user or AnonymousUser()
        # Add messages framework
        setattr(request, "session", "session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)
        return request

    def test_user_model_registered_in_admin(self):
        """Test that User model is registered in Django admin."""
        # Check that User model is registered in admin
        self.assertIn(self.User, admin.site._registry)

        # Get the admin class for User
        user_admin = admin.site._registry[self.User]

        # Check that it's properly configured
        self.assertIsNotNone(user_admin)

    def test_user_admin_fields_accessible(self):
        """Test that custom fields are accessible in admin."""
        # Create a test user to ensure we can access fields
        user = self.User.objects.create_user(
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

    def test_admin_list_display_fields(self):
        """Test that admin list display contains required fields."""
        expected_fields = [
            "username",
            "display_name",
            "email",
            "is_active",
            "created_at",
        ]

        for field in expected_fields:
            self.assertIn(field, self.user_admin.list_display)

    def test_admin_search_fields(self):
        """Test that admin search fields are properly configured."""
        expected_search_fields = ["username", "display_name", "email"]

        for field in expected_search_fields:
            self.assertIn(field, self.user_admin.search_fields)

    def test_admin_list_filters(self):
        """Test that admin list filters include required fields."""
        expected_filters = ["is_active", "is_staff", "created_at"]

        for filter_field in expected_filters:
            self.assertIn(filter_field, self.user_admin.list_filter)

    def test_activate_users_bulk_action_exists(self):
        """Test that activate_users bulk action exists."""
        self.assertIn("activate_users", self.user_admin.actions)

    def test_deactivate_users_bulk_action_exists(self):
        """Test that deactivate_users bulk action exists."""
        self.assertIn("deactivate_users", self.user_admin.actions)

    def test_activate_users_bulk_action(self):
        """Test activate_users bulk action functionality."""
        # Deactivate users first
        with transaction.atomic():
            self.regular_user.is_active = False
            self.regular_user.save()
            self.staff_user.is_active = False
            self.staff_user.save()

        # Create queryset
        queryset = self.User.objects.filter(
            id__in=[self.regular_user.id, self.staff_user.id]
        )

        # Execute bulk action
        request = self._get_request(self.superuser)
        with transaction.atomic():
            self.user_admin.activate_users(request, queryset)

        # Check users are activated
        self.regular_user.refresh_from_db()
        self.staff_user.refresh_from_db()
        self.assertTrue(self.regular_user.is_active)
        self.assertTrue(self.staff_user.is_active)

    def test_deactivate_users_bulk_action(self):
        """Test deactivate_users bulk action functionality."""
        # Ensure users are active first
        with transaction.atomic():
            self.regular_user.is_active = True
            self.regular_user.save()
            self.staff_user.is_active = True
            self.staff_user.save()

        # Create queryset
        queryset = self.User.objects.filter(
            id__in=[self.regular_user.id, self.staff_user.id]
        )

        # Execute bulk action
        request = self._get_request(self.superuser)
        with transaction.atomic():
            self.user_admin.deactivate_users(request, queryset)

        # Check users are deactivated
        self.regular_user.refresh_from_db()
        self.staff_user.refresh_from_db()
        self.assertFalse(self.regular_user.is_active)
        self.assertFalse(self.staff_user.is_active)

    def test_deactivate_users_protects_superusers(self):
        """Test that deactivate_users protects superusers from being deactivated."""
        # Ensure superuser is active
        with transaction.atomic():
            self.superuser.is_active = True
            self.superuser.save()

        # Try to deactivate superuser
        queryset = self.User.objects.filter(id=self.superuser.id)
        request = self._get_request(self.superuser)
        with transaction.atomic():
            self.user_admin.deactivate_users(request, queryset)

        # Check superuser is still active
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)

    def test_has_delete_permission_protects_users(self):
        """Test that delete permission is restricted to prevent accidental deletions."""
        request = self._get_request(self.superuser)

        # Test that delete permission returns False to prevent bulk deletions
        has_delete_perm = self.user_admin.has_delete_permission(request)
        self.assertFalse(has_delete_perm)

    def test_readonly_fields_include_timestamps(self):
        """Test that readonly fields include timestamp fields."""
        readonly_fields = self.user_admin.readonly_fields
        self.assertIn("created_at", readonly_fields)
        self.assertIn("updated_at", readonly_fields)
