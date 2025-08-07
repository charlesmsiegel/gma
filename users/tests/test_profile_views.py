"""
Tests for user profile management views.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UserProfileViewTest(TestCase):
    """Test user profile display view."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            display_name="Test User",
            timezone="America/New_York",
        )

    def test_profile_view_requires_login(self):
        """Test profile view requires authentication."""
        response = self.client.get(reverse("users:profile"))

        self.assertEqual(response.status_code, 302)
        expected_url = reverse("users:login") + f'?next={reverse("users:profile")}'
        self.assertRedirects(response, expected_url)

    def test_profile_view_authenticated_user(self):
        """Test profile view shows user data when authenticated."""
        self.client.login(username="testuser", password="TestPass123!")
        response = self.client.get(reverse("users:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test User")  # display_name
        self.assertContains(response, "testuser")  # username
        self.assertContains(response, "test@example.com")  # email
        self.assertContains(response, "America/New_York")  # timezone

    def test_profile_view_user_without_display_name(self):
        """Test profile view for user without display_name shows username."""
        User.objects.create_user(
            username="nodisplayname",
            email="nodisplay@example.com",
            password="TestPass123!",
            # No display_name set
        )
        self.client.login(username="nodisplayname", password="TestPass123!")
        response = self.client.get(reverse("users:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "nodisplayname"
        )  # Should show username as fallback

    def test_profile_view_contains_edit_link(self):
        """Test profile view contains link to edit profile."""
        self.client.login(username="testuser", password="TestPass123!")
        response = self.client.get(reverse("users:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("users:profile_edit"))


class UserProfileEditViewTest(TestCase):
    """Test user profile edit view."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            display_name="Test User",
            timezone="America/New_York",
        )

    def test_profile_edit_view_requires_login(self):
        """Test profile edit view requires authentication."""
        response = self.client.get(reverse("users:profile_edit"))

        self.assertEqual(response.status_code, 302)
        expected_url = reverse("users:login") + f'?next={reverse("users:profile_edit")}'
        self.assertRedirects(response, expected_url)

    def test_get_profile_edit_view(self):
        """Test GET request to profile edit view displays form."""
        self.client.login(username="testuser", password="TestPass123!")
        response = self.client.get(reverse("users:profile_edit"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Profile")
        self.assertContains(response, "display_name")
        self.assertContains(response, "timezone")
        # Form should be pre-filled with current values
        self.assertContains(response, "Test User")
        self.assertContains(response, "America/New_York")

    def test_profile_edit_success(self):
        """Test successful profile edit."""
        self.client.login(username="testuser", password="TestPass123!")
        data = {
            "display_name": "Updated Display Name",
            "timezone": "Europe/London",
        }
        response = self.client.post(reverse("users:profile_edit"), data)

        # Should redirect to profile view after successful update
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("users:profile"))

        # User data should be updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "Updated Display Name")
        self.assertEqual(self.user.timezone, "Europe/London")

    def test_profile_edit_success_message(self):
        """Test success message appears after profile update."""
        self.client.login(username="testuser", password="TestPass123!")
        data = {
            "display_name": "Updated Display Name",
            "timezone": "Europe/London",
        }
        response = self.client.post(reverse("users:profile_edit"), data, follow=True)

        # Check for success message
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Your profile has been updated successfully."
        )

    def test_profile_edit_empty_display_name(self):
        """Test profile edit with empty display_name (should be allowed)."""
        self.client.login(username="testuser", password="TestPass123!")
        data = {
            "display_name": "",  # Empty display name
            "timezone": "Europe/London",
        }
        response = self.client.post(reverse("users:profile_edit"), data)

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        # Empty display_name is stored as None for unique constraint
        self.assertIsNone(self.user.display_name)
        self.assertEqual(self.user.timezone, "Europe/London")

    def test_profile_edit_invalid_timezone(self):
        """Test profile edit fails with invalid timezone."""
        self.client.login(username="testuser", password="TestPass123!")
        data = {
            "display_name": "Test User",
            "timezone": "Invalid/Timezone",
        }
        response = self.client.post(reverse("users:profile_edit"), data)

        self.assertEqual(response.status_code, 200)  # Form redisplayed with errors
        self.assertContains(response, "not one of the available choices")
        # User data should not be changed
        self.user.refresh_from_db()
        self.assertEqual(self.user.timezone, "America/New_York")

    def test_profile_edit_empty_timezone(self):
        """Test profile edit fails with empty timezone."""
        self.client.login(username="testuser", password="TestPass123!")
        data = {
            "display_name": "Test User",
            "timezone": "",
        }
        response = self.client.post(reverse("users:profile_edit"), data)

        self.assertEqual(response.status_code, 200)  # Form redisplayed with errors
        self.assertContains(response, "This field is required")
        # User data should not be changed
        self.user.refresh_from_db()
        self.assertEqual(self.user.timezone, "America/New_York")

    def test_profile_edit_display_name_uniqueness_validation(self):
        """Test display_name uniqueness validation."""
        # Create another user with a display_name
        User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="TestPass123!",
            display_name="Existing Display Name",
        )

        self.client.login(username="testuser", password="TestPass123!")
        data = {
            "display_name": "Existing Display Name",  # Same as other user
            "timezone": "America/New_York",
        }
        response = self.client.post(reverse("users:profile_edit"), data)

        self.assertEqual(response.status_code, 200)  # Form redisplayed with errors
        self.assertContains(response, "A user with this display name already exists")
        # User data should not be changed
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "Test User")

    def test_profile_edit_display_name_uniqueness_case_insensitive(self):
        """Test display_name uniqueness validation is case-insensitive."""
        # Create another user with a display_name
        User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="TestPass123!",
            display_name="Existing Display Name",
        )

        self.client.login(username="testuser", password="TestPass123!")
        data = {
            "display_name": "existing display name",  # Different case
            "timezone": "America/New_York",
        }
        response = self.client.post(reverse("users:profile_edit"), data)

        self.assertEqual(response.status_code, 200)  # Form redisplayed with errors
        self.assertContains(response, "A user with this display name already exists")

    def test_profile_edit_display_name_uniqueness_allows_own_name(self):
        """Test user can keep their own display_name (uniqueness excludes self)."""
        self.client.login(username="testuser", password="TestPass123!")
        data = {
            "display_name": "Test User",  # Same as current display_name
            "timezone": "Europe/London",  # Change timezone only
        }
        response = self.client.post(reverse("users:profile_edit"), data)

        self.assertEqual(response.status_code, 302)  # Should succeed
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "Test User")
        self.assertEqual(self.user.timezone, "Europe/London")

    def test_profile_edit_form_contains_timezone_choices(self):
        """Test profile edit form contains common timezone choices."""
        self.client.login(username="testuser", password="TestPass123!")
        response = self.client.get(reverse("users:profile_edit"))

        # Should contain common timezones as options
        self.assertContains(response, "UTC")
        self.assertContains(response, "America/New_York")
        self.assertContains(response, "America/Los_Angeles")
        self.assertContains(response, "Europe/London")
        self.assertContains(response, "Asia/Tokyo")


class UserProfileFormValidationTest(TestCase):
    """Test UserProfileForm validation in isolation."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

    def test_valid_timezone_choices(self):
        """Test valid timezone identifiers are accepted."""
        self.client.login(username="testuser", password="TestPass123!")

        valid_timezones = [
            "UTC",
            "America/New_York",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Paris",
            "Asia/Tokyo",
            "Australia/Sydney",
        ]

        for timezone in valid_timezones:
            data = {
                "display_name": f"User in {timezone}",
                "timezone": timezone,
            }
            response = self.client.post(reverse("users:profile_edit"), data)
            self.assertEqual(
                response.status_code, 302, f"Failed for timezone: {timezone}"
            )

    def test_invalid_timezone_rejected(self):
        """Test invalid timezone identifiers are rejected."""
        self.client.login(username="testuser", password="TestPass123!")

        invalid_timezones = [
            "Invalid/Timezone",
            "NotReal/Zone",
            "America/FakeCity",
            "Europe/NonExistent",
            "Random String",
        ]

        for timezone in invalid_timezones:
            data = {
                "display_name": "Test User",
                "timezone": timezone,
            }
            response = self.client.post(reverse("users:profile_edit"), data)
            self.assertEqual(
                response.status_code, 200, f"Should fail for timezone: {timezone}"
            )
            self.assertContains(response, "not one of the available choices")

    def test_display_name_max_length_validation(self):
        """Test display_name respects max_length constraint."""
        self.client.login(username="testuser", password="TestPass123!")

        # Test exactly 100 characters (should pass)
        long_name_100 = "A" * 100
        data = {
            "display_name": long_name_100,
            "timezone": "UTC",
        }
        response = self.client.post(reverse("users:profile_edit"), data)
        self.assertEqual(response.status_code, 302)  # Should succeed

        # Test 101 characters (should fail)
        long_name_101 = "A" * 101
        data = {
            "display_name": long_name_101,
            "timezone": "UTC",
        }
        response = self.client.post(reverse("users:profile_edit"), data)
        self.assertEqual(response.status_code, 200)  # Should fail
        self.assertContains(response, "Ensure this value has at most 100 characters")


class ProfileIntegrationTest(TestCase):
    """Test profile functionality integration."""

    def test_profile_workflow(self):
        """Test complete profile view -> edit -> view workflow."""
        # Create and login user
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            display_name="Initial Name",
            timezone="UTC",
        )
        self.client.login(username="testuser", password="TestPass123!")

        # View initial profile
        response = self.client.get(reverse("users:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Initial Name")
        self.assertContains(response, "UTC")

        # Edit profile
        edit_data = {
            "display_name": "Updated Name",
            "timezone": "America/New_York",
        }
        response = self.client.post(reverse("users:profile_edit"), edit_data)
        self.assertEqual(response.status_code, 302)

        # View updated profile
        response = self.client.get(reverse("users:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Updated Name")
        self.assertContains(response, "America/New_York")
        # Should not contain old values
        self.assertNotContains(response, "Initial Name")
        self.assertNotContains(response, "UTC")
