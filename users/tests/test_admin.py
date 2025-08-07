from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
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
        # Create test users for this specific test
        user1 = self.User.objects.create_user(
            username="testuser1", email="test1@example.com", is_active=False
        )
        user2 = self.User.objects.create_user(
            username="testuser2", email="test2@example.com", is_active=False
        )

        # Create queryset
        queryset = self.User.objects.filter(id__in=[user1.id, user2.id])

        # Execute bulk action
        superuser = self.User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        request = self._get_request(superuser)
        self.user_admin.activate_users(request, queryset)

        # Check users are activated
        user1.refresh_from_db()
        user2.refresh_from_db()
        self.assertTrue(user1.is_active)
        self.assertTrue(user2.is_active)

    def test_deactivate_users_bulk_action(self):
        """Test deactivate_users bulk action functionality."""
        # Create test users for this specific test
        user1 = self.User.objects.create_user(
            username="testuser3", email="test3@example.com", is_active=True
        )
        user2 = self.User.objects.create_user(
            username="testuser4", email="test4@example.com", is_active=True
        )

        # Create queryset
        queryset = self.User.objects.filter(id__in=[user1.id, user2.id])

        # Execute bulk action
        superuser = self.User.objects.create_superuser(
            username="admin2", email="admin2@example.com", password="adminpass"
        )
        request = self._get_request(superuser)
        self.user_admin.deactivate_users(request, queryset)

        # Check users are deactivated
        user1.refresh_from_db()
        user2.refresh_from_db()
        self.assertFalse(user1.is_active)
        self.assertFalse(user2.is_active)

    def test_deactivate_users_protects_superusers(self):
        """Test that deactivate_users protects superusers from being deactivated."""
        # Create superuser for this test
        superuser = self.User.objects.create_superuser(
            username="admin3", email="admin3@example.com", password="adminpass"
        )

        # Try to deactivate superuser
        queryset = self.User.objects.filter(id=superuser.id)
        request = self._get_request(superuser)
        self.user_admin.deactivate_users(request, queryset)

        # Check superuser is still active
        superuser.refresh_from_db()
        self.assertTrue(superuser.is_active)

    def test_has_delete_permission_protects_users(self):
        """Test that delete permission is restricted to prevent accidental deletions."""
        superuser = self.User.objects.create_superuser(
            username="admin4", email="admin4@example.com", password="adminpass"
        )
        request = self._get_request(superuser)

        # Test that delete permission returns False to prevent bulk deletions
        has_delete_perm = self.user_admin.has_delete_permission(request)
        self.assertFalse(has_delete_perm)

    def test_readonly_fields_include_timestamps(self):
        """Test that readonly fields include timestamp fields."""
        readonly_fields = self.user_admin.readonly_fields
        self.assertIn("created_at", readonly_fields)
        self.assertIn("updated_at", readonly_fields)

    def test_list_per_page_configuration(self):
        """Test that list_per_page is configured for better pagination."""
        self.assertEqual(self.user_admin.list_per_page, 50)

    def test_date_hierarchy_configuration(self):
        """Test that date_hierarchy is configured for date-based navigation."""
        self.assertEqual(self.user_admin.date_hierarchy, "created_at")

    def test_pagination_with_large_dataset(self):
        """Test pagination behavior with a larger dataset."""
        # Create more users than the page size
        users = []
        for i in range(75):  # More than list_per_page (50)
            user = self.User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="testpass123",
            )
            users.append(user)

        # Verify we have more users than one page can display
        self.assertGreater(self.User.objects.count(), self.user_admin.list_per_page)

        # Test that pagination configuration is accessible
        self.assertTrue(hasattr(self.user_admin, "list_per_page"))
        self.assertIsInstance(self.user_admin.list_per_page, int)
        self.assertGreater(self.user_admin.list_per_page, 0)

    def test_deactivate_users_optimized_query(self):
        """Test that deactivate_users uses optimized query logic."""
        # Create mix of regular users and superusers
        regular_user1 = self.User.objects.create_user(
            username="regular1", email="regular1@example.com", is_active=True
        )
        regular_user2 = self.User.objects.create_user(
            username="regular2", email="regular2@example.com", is_active=True
        )
        superuser1 = self.User.objects.create_superuser(
            username="super1", email="super1@example.com", password="superpass"
        )
        superuser2 = self.User.objects.create_superuser(
            username="super2", email="super2@example.com", password="superpass"
        )

        # Create queryset with all users
        queryset = self.User.objects.filter(
            id__in=[regular_user1.id, regular_user2.id, superuser1.id, superuser2.id]
        )

        # Execute bulk action
        admin_user = self.User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        request = self._get_request(admin_user)

        # Capture the behavior - this tests the optimized query logic
        self.user_admin.deactivate_users(request, queryset)

        # Verify results: regular users deactivated, superusers protected
        regular_user1.refresh_from_db()
        regular_user2.refresh_from_db()
        superuser1.refresh_from_db()
        superuser2.refresh_from_db()

        self.assertFalse(regular_user1.is_active)
        self.assertFalse(regular_user2.is_active)
        self.assertTrue(superuser1.is_active)  # Protected
        self.assertTrue(superuser2.is_active)  # Protected

    def test_admin_configuration_completeness(self):
        """Test that all admin configuration attributes are properly set."""
        # Test all the configuration attributes
        self.assertTrue(hasattr(self.user_admin, "list_display"))
        self.assertTrue(hasattr(self.user_admin, "list_filter"))
        self.assertTrue(hasattr(self.user_admin, "search_fields"))
        self.assertTrue(hasattr(self.user_admin, "ordering"))
        self.assertTrue(hasattr(self.user_admin, "actions"))
        self.assertTrue(hasattr(self.user_admin, "list_per_page"))
        self.assertTrue(hasattr(self.user_admin, "date_hierarchy"))
        self.assertTrue(hasattr(self.user_admin, "readonly_fields"))

        # Test that they are properly configured
        self.assertIsInstance(self.user_admin.list_display, tuple)
        self.assertIsInstance(self.user_admin.list_filter, tuple)
        self.assertIsInstance(self.user_admin.search_fields, tuple)
        self.assertIsInstance(self.user_admin.ordering, tuple)
        self.assertIsInstance(self.user_admin.actions, list)
        self.assertIsInstance(self.user_admin.list_per_page, int)
        self.assertIsInstance(self.user_admin.date_hierarchy, str)
        self.assertIsInstance(self.user_admin.readonly_fields, tuple)

    def test_date_hierarchy_field_exists_in_model(self):
        """Test that the date_hierarchy field actually exists in the model."""
        # Verify the field used for date_hierarchy exists in the User model
        self.assertTrue(hasattr(self.User, self.user_admin.date_hierarchy))

        # Create a user and verify the field has a value
        user = self.User.objects.create_user(
            username="datetest", email="datetest@example.com", password="testpass123"
        )

        # Get the field value
        field_value = getattr(user, self.user_admin.date_hierarchy)
        self.assertIsNotNone(field_value)

        # Verify it's a datetime field
        self.assertTrue(hasattr(field_value, "year"))  # Should be a datetime object
