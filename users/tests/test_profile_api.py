"""
Tests for user profile API endpoints (Issue #137).

Tests API security, serialization, validation, and privacy controls.
"""

import json
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class ProfileAPITest(APITestCase):
    """Test profile API endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
            display_name="JohnD",
            bio="Original bio",
        )

        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )

        self.profile_url = reverse("api:auth:profile")

    def test_get_profile_authenticated(self):
        """Test getting own profile when authenticated."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check profile data is returned
        self.assertEqual(data["username"], "testuser")
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["first_name"], "John")
        self.assertEqual(data["last_name"], "Doe")
        self.assertEqual(data["display_name"], "JohnD")
        self.assertEqual(data["bio"], "Original bio")
        self.assertEqual(data["full_display_name"], "JohnD")

        # Check privacy settings are included
        self.assertIn("profile_visibility", data)
        self.assertIn("show_email", data)
        self.assertIn("show_real_name", data)
        self.assertIn("show_last_login", data)
        self.assertIn("allow_activity_tracking", data)

    def test_get_profile_unauthenticated(self):
        """Test getting profile when not authenticated."""
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_authenticated(self):
        """Test updating own profile when authenticated."""
        self.client.force_authenticate(user=self.user)

        update_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "display_name": "JaneS",
            "bio": "Updated bio",
            "website_url": "https://example.com",
            "social_links": {"twitter": "https://twitter.com/janes"},
            "profile_visibility": "public",
            "show_email": True,
        }

        response = self.client.put(
            self.profile_url,
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify changes were saved
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Jane")
        self.assertEqual(self.user.last_name, "Smith")
        self.assertEqual(self.user.display_name, "JaneS")
        self.assertEqual(self.user.bio, "Updated bio")
        self.assertEqual(self.user.website_url, "https://example.com")
        self.assertEqual(
            self.user.social_links, {"twitter": "https://twitter.com/janes"}
        )
        self.assertEqual(self.user.profile_visibility, "public")
        self.assertTrue(self.user.show_email)

    def test_update_profile_partial(self):
        """Test partial profile update."""
        self.client.force_authenticate(user=self.user)

        # Only update bio
        update_data = {"bio": "Just bio update"}

        response = self.client.put(
            self.profile_url,
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify only bio changed
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, "Just bio update")
        self.assertEqual(self.user.first_name, "John")  # Unchanged
        self.assertEqual(self.user.display_name, "JohnD")  # Unchanged

    def test_update_profile_validation_errors(self):
        """Test profile update with validation errors."""
        self.client.force_authenticate(user=self.user)

        # Try to set display name that's already taken
        self.other_user.display_name = "TakenName"
        self.other_user.save()

        update_data = {"display_name": "TakenName"}

        response = self.client.put(
            self.profile_url,
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("display_name", response.json())

    def test_update_profile_bio_too_long(self):
        """Test profile update with bio too long."""
        self.client.force_authenticate(user=self.user)

        update_data = {"bio": "A" * 501}  # Over 500 character limit

        response = self.client.put(
            self.profile_url,
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("bio", response.json())

    def test_update_profile_invalid_url(self):
        """Test profile update with invalid website URL."""
        self.client.force_authenticate(user=self.user)

        update_data = {"website_url": "not-a-valid-url"}

        response = self.client.put(
            self.profile_url,
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("website_url", response.json())


class PublicProfileAPITest(APITestCase):
    """Test public profile API endpoints."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
            bio="Public bio",
            profile_visibility="public",
            show_email=True,
            show_real_name=True,
            show_last_login=True,
        )

        self.campaign_member = User.objects.create_user(
            username="member", email="member@example.com", password="testpass123"
        )

        self.stranger = User.objects.create_user(
            username="stranger", email="stranger@example.com", password="testpass123"
        )

        # Create campaign with membership
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Test System"
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.campaign_member, role="PLAYER"
        )

        self.public_profile_url = reverse(
            "api:auth:public-profile", kwargs={"user_id": self.owner.id}
        )
        self.public_profile_username_url = reverse(
            "api:auth:public-profile-username", kwargs={"username": self.owner.username}
        )

    def test_public_profile_by_id_public_visibility(self):
        """Test accessing public profile by user ID."""
        self.client.force_authenticate(user=self.stranger)

        response = self.client.get(self.public_profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check public data is returned
        self.assertTrue(data["profile_visible"])
        self.assertEqual(data["username"], "owner")
        self.assertEqual(data["bio"], "Public bio")
        self.assertEqual(data["email"], "owner@example.com")  # show_email=True
        self.assertEqual(data["first_name"], "John")  # show_real_name=True
        self.assertEqual(data["last_name"], "Doe")

    def test_public_profile_by_username_public_visibility(self):
        """Test accessing public profile by username."""
        self.client.force_authenticate(user=self.stranger)

        response = self.client.get(self.public_profile_username_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check public data is returned
        self.assertTrue(data["profile_visible"])
        self.assertEqual(data["username"], "owner")
        self.assertEqual(data["bio"], "Public bio")

    def test_public_profile_members_only_visibility_campaign_member(self):
        """Test campaign member can view members-only profile."""
        self.owner.profile_visibility = "members"
        self.owner.save()

        self.client.force_authenticate(user=self.campaign_member)

        response = self.client.get(self.public_profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["profile_visible"])

    def test_public_profile_members_only_visibility_stranger(self):
        """Test stranger cannot view members-only profile."""
        self.owner.profile_visibility = "members"
        self.owner.save()

        self.client.force_authenticate(user=self.stranger)

        response = self.client.get(self.public_profile_url)

        # Should return 404 to hide existence
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_profile_private_visibility(self):
        """Test private profile is not accessible."""
        self.owner.profile_visibility = "private"
        self.owner.save()

        self.client.force_authenticate(user=self.stranger)

        response = self.client.get(self.public_profile_url)

        # Should return 404 to hide existence
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_profile_privacy_settings_respected(self):
        """Test privacy settings are respected in public profile."""
        self.owner.show_email = False
        self.owner.show_real_name = False
        self.owner.show_last_login = False
        self.owner.save()

        self.client.force_authenticate(user=self.stranger)

        response = self.client.get(self.public_profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check private data is hidden
        self.assertIsNone(data.get("email"))
        self.assertIsNone(data.get("first_name"))
        self.assertIsNone(data.get("last_name"))
        self.assertIsNone(data.get("last_login"))

    def test_public_profile_unauthenticated_public_visibility(self):
        """Test unauthenticated users can view public profiles."""
        response = self.client.get(self.public_profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["profile_visible"])

    def test_public_profile_unauthenticated_members_only(self):
        """Test unauthenticated users cannot view members-only profiles."""
        self.owner.profile_visibility = "members"
        self.owner.save()

        response = self.client.get(self.public_profile_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_profile_nonexistent_user(self):
        """Test accessing nonexistent user profile."""
        nonexistent_url = reverse("api:auth:public-profile", kwargs={"user_id": 99999})

        response = self.client.get(nonexistent_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_profile_nonexistent_username(self):
        """Test accessing nonexistent username profile."""
        nonexistent_url = reverse(
            "api:auth:public-profile-username", kwargs={"username": "nonexistent"}
        )

        response = self.client.get(nonexistent_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PrivacySettingsAPITest(APITestCase):
    """Test privacy settings API endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.privacy_url = reverse("api:auth:privacy-settings")

    def test_get_privacy_settings_authenticated(self):
        """Test getting privacy settings when authenticated."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.privacy_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check privacy settings are returned
        self.assertEqual(data["profile_visibility"], "members")  # Default
        self.assertFalse(data["show_email"])  # Default
        self.assertTrue(data["show_real_name"])  # Default
        self.assertFalse(data["show_last_login"])  # Default
        self.assertTrue(data["allow_activity_tracking"])  # Default

    def test_get_privacy_settings_unauthenticated(self):
        """Test getting privacy settings when not authenticated."""
        response = self.client.get(self.privacy_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_privacy_settings_authenticated(self):
        """Test updating privacy settings when authenticated."""
        self.client.force_authenticate(user=self.user)

        update_data = {
            "profile_visibility": "private",
            "show_email": True,
            "show_real_name": False,
            "show_last_login": True,
            "allow_activity_tracking": False,
        }

        response = self.client.put(
            self.privacy_url,
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify changes were saved
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile_visibility, "private")
        self.assertTrue(self.user.show_email)
        self.assertFalse(self.user.show_real_name)
        self.assertTrue(self.user.show_last_login)
        self.assertFalse(self.user.allow_activity_tracking)

    def test_update_privacy_settings_partial(self):
        """Test partial privacy settings update."""
        self.client.force_authenticate(user=self.user)

        # Set initial state
        self.user.profile_visibility = "public"
        self.user.show_email = True
        self.user.save()

        # Update only one setting
        update_data = {"profile_visibility": "private"}

        response = self.client.put(
            self.privacy_url,
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify only specified setting changed
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile_visibility, "private")
        self.assertTrue(self.user.show_email)  # Unchanged

    def test_update_privacy_settings_invalid_choice(self):
        """Test updating privacy settings with invalid choice."""
        self.client.force_authenticate(user=self.user)

        update_data = {"profile_visibility": "invalid_choice"}

        response = self.client.put(
            self.privacy_url,
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("profile_visibility", response.json())

    def test_update_privacy_settings_unauthenticated(self):
        """Test updating privacy settings when not authenticated."""
        update_data = {"profile_visibility": "private"}

        response = self.client.put(
            self.privacy_url,
            data=json.dumps(update_data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileSerializerTest(APITestCase):
    """Test profile API serializer functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def create_test_image(self):
        """Helper to create test image for avatar testing."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            img = Image.new("RGB", (100, 100), color="red")
            img.save(tmp_file, "JPEG")
            tmp_file.flush()

            with open(tmp_file.name, "rb") as f:
                return SimpleUploadedFile(
                    name="test_avatar.jpg", content=f.read(), content_type="image/jpeg"
                )

    def test_avatar_upload_via_api(self):
        """Test uploading avatar via API."""
        self.client.force_authenticate(user=self.user)

        avatar_file = self.create_test_image()

        # Use multipart form data for file upload
        response = self.client.put(
            reverse("api:auth:profile"),
            data={"avatar": avatar_file, "bio": "Updated with avatar"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check avatar was saved
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar)
        self.assertIsNotNone(self.user.get_avatar_url())
        self.assertEqual(self.user.bio, "Updated with avatar")

    def test_social_links_serialization(self):
        """Test social links JSON serialization."""
        self.client.force_authenticate(user=self.user)

        social_links = {
            "twitter": "https://twitter.com/user",
            "discord": "user#1234",
            "github": "https://github.com/user",
        }

        response = self.client.put(
            reverse("api:auth:profile"),
            data=json.dumps({"social_links": social_links}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check social links were saved correctly
        self.user.refresh_from_db()
        self.assertEqual(self.user.social_links, social_links)

        # Check they're returned correctly
        response_data = response.json()
        self.assertEqual(response_data["social_links"], social_links)
