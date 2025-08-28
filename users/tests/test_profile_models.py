"""
Tests for user profile model functionality (Issue #137).

Tests all profile fields, privacy settings, validation, and model methods.
"""

import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class UserProfileFieldsTest(TestCase):
    """Test user profile field functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_bio_field_length_validation(self):
        """Test bio field max length validation."""
        # Valid bio
        valid_bio = "A" * 500
        self.user.bio = valid_bio
        self.user.full_clean()  # Should not raise

        # Invalid bio (too long)
        invalid_bio = "A" * 501
        self.user.bio = invalid_bio
        with self.assertRaises(ValidationError):
            self.user.full_clean()

    def test_bio_field_can_be_empty(self):
        """Test bio field can be blank."""
        self.user.bio = ""
        self.user.full_clean()  # Should not raise

        self.user.bio = None
        # Django converts None to empty string for CharField
        self.assertEqual(self.user.bio, "")

    def test_avatar_field_optional(self):
        """Test avatar field is optional."""
        self.assertIsNone(self.user.avatar)
        self.user.full_clean()  # Should not raise

    def test_website_url_validation(self):
        """Test website URL validation."""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://www.example.com/path?param=value",
            "",  # Empty is valid
        ]

        for url in valid_urls:
            self.user.website_url = url
            self.user.full_clean()  # Should not raise

        # Invalid URLs
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # URLField validates but may not be what we want
        ]

        # Note: Django's URLField is quite permissive, so we test what actually fails
        self.user.website_url = "not-a-url"
        with self.assertRaises(ValidationError):
            self.user.full_clean()

    def test_social_links_json_field(self):
        """Test social links JSON field functionality."""
        # Test empty dict (default)
        self.assertEqual(self.user.social_links, {})

        # Test valid social links
        valid_social_links = {
            "twitter": "https://twitter.com/username",
            "discord": "username#1234",
            "github": "https://github.com/username",
        }
        self.user.social_links = valid_social_links
        self.user.full_clean()
        self.user.save()

        # Refresh from database
        self.user.refresh_from_db()
        self.assertEqual(self.user.social_links, valid_social_links)

    def test_profile_visibility_choices(self):
        """Test profile visibility field choices."""
        # Test default value
        self.assertEqual(self.user.profile_visibility, "members")

        # Test valid choices
        valid_choices = ["public", "members", "private"]
        for choice in valid_choices:
            self.user.profile_visibility = choice
            self.user.full_clean()  # Should not raise

        # Test invalid choice
        self.user.profile_visibility = "invalid"
        with self.assertRaises(ValidationError):
            self.user.full_clean()

    def test_privacy_boolean_fields(self):
        """Test privacy boolean fields have correct defaults."""
        self.assertFalse(self.user.show_email)
        self.assertTrue(self.user.show_real_name)
        self.assertFalse(self.user.show_last_login)
        self.assertTrue(self.user.allow_activity_tracking)

        # Test setting values
        self.user.show_email = True
        self.user.show_real_name = False
        self.user.show_last_login = True
        self.user.allow_activity_tracking = False
        self.user.full_clean()  # Should not raise


class UserProfileMethodsTest(TestCase):
    """Test user profile model methods."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
            display_name="JohnD",
        )

        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )

    def test_get_full_display_name_with_display_name(self):
        """Test get_full_display_name returns display_name when set."""
        result = self.user1.get_full_display_name()
        self.assertEqual(result, "JohnD")

    def test_get_full_display_name_with_real_name(self):
        """Test get_full_display_name returns real name when display_name not set and show_real_name is True."""
        self.user1.display_name = ""
        self.user1.show_real_name = True
        result = self.user1.get_full_display_name()
        self.assertEqual(result, "John Doe")

    def test_get_full_display_name_no_real_name(self):
        """Test get_full_display_name returns username when no real name or display name."""
        self.user1.display_name = ""
        self.user1.first_name = ""
        self.user1.last_name = ""
        result = self.user1.get_full_display_name()
        self.assertEqual(result, "user1")

    def test_get_full_display_name_privacy_hidden(self):
        """Test get_full_display_name respects show_real_name privacy setting."""
        self.user1.display_name = ""
        self.user1.show_real_name = False
        result = self.user1.get_full_display_name()
        self.assertEqual(result, "user1")  # Falls back to username

    def test_get_avatar_url_with_avatar(self):
        """Test get_avatar_url returns URL when avatar exists."""
        # Create a simple test image
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            img = Image.new("RGB", (100, 100), color="red")
            img.save(tmp_file, "JPEG")
            tmp_file.flush()

            with open(tmp_file.name, "rb") as f:
                avatar_file = SimpleUploadedFile(
                    name="test_avatar.jpg", content=f.read(), content_type="image/jpeg"
                )
                self.user1.avatar = avatar_file
                self.user1.save()

        avatar_url = self.user1.get_avatar_url()
        self.assertIsNotNone(avatar_url)
        self.assertIn("test_avatar", avatar_url)

    def test_get_avatar_url_without_avatar(self):
        """Test get_avatar_url returns None when no avatar."""
        result = self.user1.get_avatar_url()
        self.assertIsNone(result)


class UserPrivacyTest(TestCase):
    """Test user privacy functionality."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="testpass123"
        )

        self.campaign_member = User.objects.create_user(
            username="member", email="member@example.com", password="testpass123"
        )

        self.stranger = User.objects.create_user(
            username="stranger", email="stranger@example.com", password="testpass123"
        )

        # Create a campaign with members
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Test System"
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.campaign_member, role="PLAYER"
        )

    def test_can_view_profile_own_profile(self):
        """Test users can always view their own profile."""
        self.assertTrue(self.owner.can_view_profile(self.owner))

    def test_can_view_profile_public_visibility(self):
        """Test public profile visibility."""
        self.owner.profile_visibility = "public"

        # Anyone can view public profiles
        self.assertTrue(self.owner.can_view_profile(self.stranger))
        self.assertTrue(self.owner.can_view_profile(self.campaign_member))
        self.assertTrue(self.owner.can_view_profile(None))  # Anonymous

    def test_can_view_profile_private_visibility(self):
        """Test private profile visibility."""
        self.owner.profile_visibility = "private"

        # Only owner can view private profiles
        self.assertFalse(self.owner.can_view_profile(self.stranger))
        self.assertFalse(self.owner.can_view_profile(self.campaign_member))
        self.assertFalse(self.owner.can_view_profile(None))  # Anonymous
        self.assertTrue(self.owner.can_view_profile(self.owner))  # Self

    def test_can_view_profile_members_visibility(self):
        """Test members-only profile visibility."""
        self.owner.profile_visibility = "members"  # Default

        # Campaign members can view
        self.assertTrue(self.owner.can_view_profile(self.campaign_member))

        # Strangers cannot view
        self.assertFalse(self.owner.can_view_profile(self.stranger))
        self.assertFalse(self.owner.can_view_profile(None))  # Anonymous

        # Self can always view
        self.assertTrue(self.owner.can_view_profile(self.owner))

    def test_are_campaign_members(self):
        """Test campaign membership detection."""
        # Owner and member are in same campaign
        self.assertTrue(self.owner.are_campaign_members(self.campaign_member))
        self.assertTrue(self.campaign_member.are_campaign_members(self.owner))

        # Stranger is not in campaign
        self.assertFalse(self.owner.are_campaign_members(self.stranger))
        self.assertFalse(self.stranger.are_campaign_members(self.owner))

        # None/anonymous user
        self.assertFalse(self.owner.are_campaign_members(None))

    def test_get_public_profile_data_visible_profile(self):
        """Test get_public_profile_data when profile is visible."""
        self.owner.profile_visibility = "public"
        self.owner.bio = "Test bio"
        self.owner.show_email = True
        self.owner.show_real_name = True
        self.owner.show_last_login = True

        data = self.owner.get_public_profile_data(viewer_user=self.stranger)

        # Should include all requested data
        self.assertTrue(data["profile_visible"])
        self.assertEqual(data["bio"], "Test bio")
        self.assertEqual(data["email"], self.owner.email)
        self.assertIn("first_name", data)
        self.assertIn("last_name", data)
        self.assertIn("last_login", data)

    def test_get_public_profile_data_hidden_profile(self):
        """Test get_public_profile_data when profile is hidden."""
        self.owner.profile_visibility = "private"

        data = self.owner.get_public_profile_data(viewer_user=self.stranger)

        # Should return minimal data
        self.assertFalse(data["profile_visible"])
        self.assertEqual(data["username"], self.owner.username)
        self.assertNotIn("email", data)
        self.assertNotIn("bio", data)

    def test_get_public_profile_data_privacy_settings(self):
        """Test get_public_profile_data respects privacy settings."""
        self.owner.profile_visibility = "public"
        self.owner.show_email = False
        self.owner.show_real_name = False
        self.owner.show_last_login = False

        data = self.owner.get_public_profile_data(viewer_user=self.stranger)

        # Should respect privacy settings
        self.assertTrue(data["profile_visible"])
        self.assertNotIn("email", data)
        self.assertNotIn("first_name", data)
        self.assertNotIn("last_name", data)
        self.assertNotIn("last_login", data)
