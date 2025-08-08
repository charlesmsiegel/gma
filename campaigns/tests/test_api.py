"""
Tests for campaign API endpoints.

This module tests the REST API endpoints for campaign creation and management,
following DRF standards and testing both authenticated and unauthenticated access.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class CampaignCreateAPITest(TestCase):
    """Test the campaign creation API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.create_url = reverse("api:campaigns:list_create")

    def test_create_campaign_requires_authentication(self):
        """Test that unauthenticated users get 403 error (DRF default)."""
        campaign_data = {
            "name": "Test Campaign",
            "description": "A test campaign",
            "game_system": "Mage: The Ascension",
        }

        response = self.client.post(self.create_url, campaign_data, format="json")

        # DRF returns 403 for IsAuthenticated permission denied
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_can_create_campaign(self):
        """Test that authenticated users can create campaigns via API."""
        self.client.force_authenticate(user=self.user)

        campaign_data = {
            "name": "API Test Campaign",
            "description": "A campaign created via API",
            "game_system": "Vampire: The Masquerade",
        }

        response = self.client.post(self.create_url, campaign_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify response data
        self.assertEqual(response.data["name"], "API Test Campaign")
        self.assertEqual(response.data["description"], "A campaign created via API")
        self.assertEqual(response.data["game_system"], "Vampire: The Masquerade")
        self.assertEqual(response.data["owner"]["id"], self.user.id)
        self.assertEqual(response.data["owner"]["username"], self.user.username)
        self.assertIn("slug", response.data)
        self.assertIn("created_at", response.data)
        self.assertIn("updated_at", response.data)
        self.assertTrue(response.data["is_active"])

    def test_create_campaign_with_minimal_data(self):
        """Test creating campaign with only required fields."""
        self.client.force_authenticate(user=self.user)

        campaign_data = {"name": "Minimal Campaign"}

        response = self.client.post(self.create_url, campaign_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Minimal Campaign")
        self.assertEqual(response.data["description"], "")
        self.assertEqual(response.data["game_system"], "")

        # Verify in database
        campaign = Campaign.objects.get(name="Minimal Campaign")
        self.assertEqual(campaign.owner, self.user)

    def test_create_campaign_invalid_data_returns_400(self):
        """Test that invalid data returns validation errors."""
        self.client.force_authenticate(user=self.user)

        # Missing required name field
        campaign_data = {
            "description": "Missing name field",
            "game_system": "Some System",
        }

        response = self.client.post(self.create_url, campaign_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

        # Verify no campaign was created
        self.assertEqual(Campaign.objects.count(), 0)

    def test_create_campaign_empty_name_returns_400(self):
        """Test that empty name field returns validation error."""
        self.client.force_authenticate(user=self.user)

        campaign_data = {"name": "", "description": "Test description"}  # Empty name

        response = self.client.post(self.create_url, campaign_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_create_campaign_name_too_long_returns_400(self):
        """Test that name exceeding max length returns validation error."""
        self.client.force_authenticate(user=self.user)

        campaign_data = {
            "name": "A" * 201,  # Exceeds 200 char limit
            "description": "Test with too long name",
        }

        response = self.client.post(self.create_url, campaign_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_create_campaign_owner_automatically_assigned(self):
        """Test that creator is automatically assigned as owner."""
        self.client.force_authenticate(user=self.user)

        campaign_data = {
            "name": "Owner Assignment Test",
            "description": "Testing automatic owner assignment",
        }

        response = self.client.post(self.create_url, campaign_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check database
        campaign = Campaign.objects.get(name="Owner Assignment Test")
        self.assertEqual(campaign.owner, self.user)

        # Check response data
        self.assertEqual(response.data["owner"]["id"], self.user.id)

    def test_create_campaign_generates_unique_slug(self):
        """Test that campaign creation generates unique slug."""
        self.client.force_authenticate(user=self.user)

        # Create first campaign
        campaign_data1 = {
            "name": "Duplicate Name Test",
            "description": "First campaign",
        }

        response1 = self.client.post(self.create_url, campaign_data1, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Create second campaign with same name
        campaign_data2 = {
            "name": "Duplicate Name Test",
            "description": "Second campaign",
        }

        response2 = self.client.post(self.create_url, campaign_data2, format="json")
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Verify both have unique slugs
        self.assertNotEqual(response1.data["slug"], response2.data["slug"])

        # Verify both exist in database
        campaigns = Campaign.objects.filter(name="Duplicate Name Test")
        self.assertEqual(campaigns.count(), 2)

    def test_api_response_structure_follows_drf_standards(self):
        """Test that API response follows DRF standards."""
        self.client.force_authenticate(user=self.user)

        campaign_data = {
            "name": "DRF Standards Test",
            "description": "Testing DRF response structure",
            "game_system": "Test System",
        }

        response = self.client.post(self.create_url, campaign_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check required response fields
        required_fields = [
            "id",
            "name",
            "slug",
            "description",
            "game_system",
            "is_active",
            "created_at",
            "updated_at",
            "owner",
        ]

        for field in required_fields:
            self.assertIn(field, response.data)

        # Check owner is nested object with required fields
        owner_fields = ["id", "username"]
        for field in owner_fields:
            self.assertIn(field, response.data["owner"])


class CampaignListAPITest(TestCase):
    """Test the campaign list API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="TestPass123!"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="TestPass123!"
        )

        # Create campaigns owned by different users
        self.campaign1 = Campaign.objects.create(
            name="User 1 Campaign",
            description="Campaign owned by user1",
            game_system="Mage",
            owner=self.user1,
        )
        self.campaign2 = Campaign.objects.create(
            name="User 2 Campaign",
            description="Campaign owned by user2",
            game_system="Vampire",
            owner=self.user2,
        )

        self.list_url = reverse("api:campaigns:list_create")

    def test_list_campaigns_requires_authentication(self):
        """Test that unauthenticated users get 403 error (DRF default)."""
        response = self.client.get(self.list_url)

        # DRF returns 403 for IsAuthenticated permission denied
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_can_list_campaigns(self):
        """Test that authenticated users can list campaigns."""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 2)  # Direct list, not paginated

    def test_campaign_list_includes_owned_campaigns(self):
        """Test that user can see campaigns they own."""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Find user1's campaign in results
        campaign_names = [c["name"] for c in response.data]
        self.assertIn("User 1 Campaign", campaign_names)

    def test_campaign_list_response_structure(self):
        """Test that list response has correct structure."""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check campaign data structure
        if response.data:
            campaign = response.data[0]
            required_fields = [
                "id",
                "name",
                "slug",
                "description",
                "game_system",
                "is_active",
                "created_at",
                "updated_at",
                "owner",
            ]
            for field in required_fields:
                self.assertIn(field, campaign)


class CampaignDetailAPITest(TestCase):
    """Test the campaign detail API endpoint."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="TestPass123!"
        )
        self.member = User.objects.create_user(
            username="member", email="member@example.com", password="TestPass123!"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@example.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Detail Test Campaign",
            description="Campaign for testing detail endpoint",
            game_system="World of Darkness",
            owner=self.owner,
            is_public=True,  # Make campaign public for API tests
        )

        # Add member to campaign
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.member, role="PLAYER"
        )

        self.detail_url = reverse(
            "api:campaigns:detail", kwargs={"pk": self.campaign.pk}
        )

    def test_campaign_detail_allows_unauthenticated_for_public_campaigns(self):
        """Test that unauthenticated users can view public campaign details."""
        response = self.client.get(self.detail_url)

        # Public campaigns are accessible to unauthenticated users
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Detail Test Campaign")

    def test_owner_can_view_campaign_detail(self):
        """Test that campaign owner can view detail."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Detail Test Campaign")
        self.assertEqual(response.data["owner"]["id"], self.owner.id)

    def test_member_can_view_campaign_detail(self):
        """Test that campaign member can view detail."""
        self.client.force_authenticate(user=self.member)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Detail Test Campaign")

    def test_non_member_can_view_public_campaign_detail(self):
        """Test that non-members can view public campaign details."""
        self.client.force_authenticate(user=self.non_member)

        response = self.client.get(self.detail_url)

        # Assuming campaigns are publicly viewable by default
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Detail Test Campaign")

    def test_nonexistent_campaign_returns_404(self):
        """Test that nonexistent campaign returns 404."""
        self.client.force_authenticate(user=self.owner)

        nonexistent_url = reverse("api:campaigns:detail", kwargs={"pk": 99999})
        response = self.client.get(nonexistent_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_campaign_detail_response_structure(self):
        """Test that detail response has correct structure."""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check all required fields are present
        required_fields = [
            "id",
            "name",
            "slug",
            "description",
            "game_system",
            "is_active",
            "created_at",
            "updated_at",
            "owner",
        ]

        for field in required_fields:
            self.assertIn(field, response.data)

        # Check owner nested structure
        self.assertIn("id", response.data["owner"])
        self.assertIn("username", response.data["owner"])


class CampaignSerializerTest(TestCase):
    """Test campaign serializer directly."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )

    def test_campaign_serializer_valid_data(self):
        """Test serializer with valid data."""
        from api.serializers import CampaignSerializer

        data = {
            "name": "Serializer Test Campaign",
            "description": "Testing the serializer",
            "game_system": "Test System",
        }

        serializer = CampaignSerializer(data=data)

        self.assertTrue(serializer.is_valid())

    def test_campaign_serializer_required_fields(self):
        """Test serializer validation of required fields."""
        from api.serializers import CampaignSerializer

        # Missing required name field
        data = {"description": "Missing name", "game_system": "Test System"}

        serializer = CampaignSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_campaign_serializer_save_with_owner(self):
        """Test that serializer save method sets owner correctly."""
        from api.serializers import CampaignSerializer

        data = {
            "name": "Owner Test Campaign",
            "description": "Testing owner assignment in serializer",
            "game_system": "Test System",
        }

        serializer = CampaignSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        campaign = serializer.save(owner=self.user)

        self.assertEqual(campaign.owner, self.user)
        self.assertEqual(campaign.name, "Owner Test Campaign")
        self.assertIsNotNone(campaign.slug)

    def test_campaign_serializer_read_fields(self):
        """Test that read-only fields are properly handled."""
        from api.serializers import CampaignSerializer

        campaign = Campaign.objects.create(
            name="Read Test Campaign",
            description="Testing read fields",
            owner=self.user,
        )

        serializer = CampaignSerializer(campaign)

        # Check that read-only fields are included
        read_only_fields = ["id", "slug", "created_at", "updated_at", "owner"]
        for field in read_only_fields:
            self.assertIn(field, serializer.data)

        # Check owner is properly serialized
        self.assertEqual(serializer.data["owner"]["id"], self.user.id)
        self.assertEqual(serializer.data["owner"]["username"], self.user.username)
