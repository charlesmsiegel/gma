"""Test cases for Content Validation API endpoints."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class ContentValidationAPITest(TestCase):
    """Test the content validation API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        # Create test users
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="TestPass123!"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@example.com", password="TestPass123!"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@example.com", password="TestPass123!"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@example.com", password="TestPass123!"
        )

        # Create test campaign
        self.campaign = Campaign.objects.create(
            name="Validation Campaign",
            owner=self.owner,
            game_system="World of Darkness",
            content_warnings=["Violence", "Supernatural themes", "Mental health"],
            safety_tools_enabled=True,
        )

        # Add campaign memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )

        # Create user safety preferences
        from users.models.safety import UserSafetyPreferences

        UserSafetyPreferences.objects.create(
            user=self.player1,
            lines=["Sexual content", "Graphic torture"],
            veils=["Violence", "Character death"],
            privacy_level="gm_only",
            consent_required=True,
        )
        UserSafetyPreferences.objects.create(
            user=self.player2,
            lines=["Animal harm"],
            veils=["Mental health issues", "Substance abuse"],
            privacy_level="campaign_members",
            consent_required=False,
        )

        # API endpoints
        self.validate_content_url = reverse("api:validate_content")
        self.validate_for_user_url = reverse("api:validate_content_for_user")
        self.validate_for_campaign_url = reverse("api:validate_content_for_campaign")
        self.pre_scene_check_url = reverse("api:pre_scene_safety_check")

    def test_validate_content_against_single_user(self):
        """Test validating content against a single user's preferences."""
        self.client.force_authenticate(user=self.gm)

        content_data = {
            "content": "This scene contains graphic torture and violence.",
            "user_id": self.player1.id,
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            self.validate_for_user_url, content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_safe"])  # Lines violated
        self.assertIn("Graphic torture", response.data["lines_violated"])
        self.assertIn("Violence", response.data["veils_triggered"])

    def test_validate_safe_content(self):
        """Test validating content that doesn't trigger any safety concerns."""
        self.client.force_authenticate(user=self.gm)

        content_data = {
            "content": "The characters have a pleasant conversation at the tavern.",
            "user_id": self.player1.id,
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            self.validate_for_user_url, content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_safe"])
        self.assertEqual(response.data["lines_violated"], [])
        self.assertEqual(response.data["veils_triggered"], [])

    def test_validate_content_for_entire_campaign(self):
        """Test validating content against all campaign participants."""
        self.client.force_authenticate(user=self.gm)

        content_data = {
            "content": (
                "This scene involves violence against animals and mental "
                "health issues."
            ),
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            self.validate_for_campaign_url, content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_safe"])  # Due to player2's animal harm line

        # Check individual user results
        self.assertIn("user_results", response.data)
        user_results = response.data["user_results"]

        # Player1 should have mental health as veil (not in their lines)
        player1_result = next(
            (result for result in user_results if result["user_id"] == self.player1.id),
            None,
        )
        self.assertIsNotNone(player1_result)

        # Player2 should have animal harm as line violation
        player2_result = next(
            (result for result in user_results if result["user_id"] == self.player2.id),
            None,
        )
        self.assertIsNotNone(player2_result)
        self.assertIn("Animal harm", player2_result["lines_violated"])

    def test_validate_content_with_privacy_restrictions(self):
        """Test content validation respecting privacy levels."""
        # Player trying to validate content against another player with private prefs
        from users.models.safety import UserSafetyPreferences

        # Update player2's preferences to private
        prefs = UserSafetyPreferences.objects.get(user=self.player2)
        prefs.privacy_level = "private"
        prefs.save()

        self.client.force_authenticate(user=self.player1)

        content_data = {
            "content": "Test content",
            "user_id": self.player2.id,
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            self.validate_for_user_url, content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("privacy_restricted", response.data)

    def test_validate_content_as_non_campaign_member(self):
        """Test that non-campaign members cannot validate content."""
        outsider = User.objects.create_user(
            username="outsider", email="outsider@example.com", password="TestPass123!"
        )

        self.client.force_authenticate(user=outsider)

        content_data = {
            "content": "Test content",
            "user_id": self.player1.id,
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            self.validate_for_user_url, content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pre_scene_safety_check(self):
        """Test pre-scene safety check workflow."""
        from campaigns.models import CampaignSafetyAgreement

        # Create safety agreements
        CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player1,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence", "Supernatural themes"],
        )
        CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player2,
            agreed_to_terms=False,  # Not agreed yet
            acknowledged_warnings=["Violence"],
        )

        self.client.force_authenticate(user=self.gm)

        check_data = {
            "campaign_id": self.campaign.id,
            "planned_content_summary": "Combat scene with supernatural elements",
            "participants": [self.player1.id, self.player2.id],
        }

        response = self.client.post(self.pre_scene_check_url, check_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("check_results", response.data)
        self.assertIn("recommendations", response.data)
        self.assertIn("safety_warnings", response.data)

    def test_content_validation_with_consent_required(self):
        """Test content validation when user requires explicit consent."""
        self.client.force_authenticate(user=self.gm)

        content_data = {
            # Triggers veils for player1
            "content": "Scene with character death and violence",
            "user_id": self.player1.id,
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            self.validate_for_user_url, content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            response.data["consent_required"]
        )  # player1 has consent_required=True
        self.assertIn("Character death", response.data["veils_triggered"])

    def test_validate_empty_content(self):
        """Test validation of empty or None content."""
        self.client.force_authenticate(user=self.gm)

        # Test empty content
        content_data = {
            "content": "",
            "user_id": self.player1.id,
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            self.validate_for_user_url, content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_safe"])

    def test_validate_very_long_content(self):
        """Test validation of very long content."""
        self.client.force_authenticate(user=self.gm)

        # Create long content with safety-triggering words
        long_content = "Safe content " * 1000 + "with graphic torture at the end"

        content_data = {
            "content": long_content,
            "user_id": self.player1.id,
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            self.validate_for_user_url, content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_safe"])
        self.assertIn("Graphic torture", response.data["lines_violated"])

    def test_validate_content_special_characters(self):
        """Test content validation with special characters and encoding."""
        self.client.force_authenticate(user=self.gm)

        special_content = """
        Content with émotions, 中文 characters, русский text,
        and special symbols: ♠♥♦♣ ™® ¿¡
        Also includes "quotes" and 'apostrophes' and <html> tags.
        This contains graphic torture for testing.
        """

        content_data = {
            "content": special_content,
            "user_id": self.player1.id,
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            self.validate_for_user_url, content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_safe"])  # Should detect "graphic torture"

    def test_batch_content_validation(self):
        """Test validating multiple content pieces at once."""
        self.client.force_authenticate(user=self.gm)

        batch_data = {
            "campaign_id": self.campaign.id,
            "content_items": [
                {"id": "scene1", "content": "Safe tavern conversation"},
                {"id": "scene2", "content": "Combat with violence and torture"},
                {"id": "scene3", "content": "Animal harm scenario"},
            ],
        }

        response = self.client.post(
            reverse("api:validate_content_batch"), batch_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 3)

        # Check individual results
        results_by_id = {result["id"]: result for result in response.data["results"]}

        self.assertTrue(results_by_id["scene1"]["is_safe"])
        self.assertFalse(results_by_id["scene2"]["is_safe"])  # Violence + torture
        self.assertFalse(results_by_id["scene3"]["is_safe"])  # Animal harm


class ContentValidationAPIErrorHandlingTest(TestCase):
    """Test error handling in content validation API."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="TestPass123!"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
            game_system="Test System",
            safety_tools_enabled=True,
        )

        self.validate_for_user_url = reverse("api:validate_content_for_user")

    def test_missing_required_fields(self):
        """Test validation with missing required fields."""
        self.client.force_authenticate(user=self.user)

        # Missing content field
        incomplete_data = {"user_id": self.user.id, "campaign_id": self.campaign.id}

        response = self.client.post(
            self.validate_for_user_url, incomplete_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    def test_invalid_user_id(self):
        """Test validation with invalid user ID."""
        self.client.force_authenticate(user=self.user)

        content_data = {
            "content": "Test content",
            "user_id": 99999,  # Non-existent user
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            self.validate_for_user_url, content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_campaign_id(self):
        """Test validation with invalid campaign ID."""
        self.client.force_authenticate(user=self.user)

        content_data = {
            "content": "Test content",
            "user_id": self.user.id,
            "campaign_id": 99999,  # Non-existent campaign
        }

        response = self.client.post(
            self.validate_for_user_url, content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_malformed_json_request(self):
        """Test handling of malformed JSON requests."""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.validate_for_user_url,
            '{"content": "test", "user_id":}',  # Malformed JSON
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_data_types(self):
        """Test handling of invalid data types."""
        self.client.force_authenticate(user=self.user)

        invalid_data = {
            "content": ["not_a_string"],  # Should be string
            "user_id": "not_an_integer",  # Should be integer
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            self.validate_for_user_url, invalid_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ContentValidationAPIPerformanceTest(TestCase):
    """Test performance aspects of content validation API."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Performance Test Campaign",
            owner=self.owner,
            game_system="Test System",
            safety_tools_enabled=True,
        )

        # Create many users with safety preferences
        self.users = []
        for i in range(20):  # Create 20 test users
            user = User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="TestPass123!",
            )
            self.users.append(user)

            # Add to campaign
            CampaignMembership.objects.create(
                campaign=self.campaign, user=user, role="PLAYER"
            )

            # Create safety preferences
            from users.models.safety import UserSafetyPreferences

            UserSafetyPreferences.objects.create(
                user=user,
                lines=[f"Line {i}", f"Another line {i}"],
                veils=[f"Veil {i}", f"Another veil {i}"],
                privacy_level="campaign_members",
            )

    def test_validate_content_for_large_campaign(self):
        """Test content validation performance with many participants."""
        self.client.force_authenticate(user=self.owner)

        content_data = {
            "content": (
                "This is a test scene with some content that might trigger "
                "safety concerns."
            ),
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            reverse("api:validate_content_for_campaign"), content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user_results", response.data)

        # Should return results for all users (20 created users + 1 owner)
        self.assertEqual(len(response.data["user_results"]), 21)

    def test_batch_validation_performance(self):
        """Test batch validation performance."""
        self.client.force_authenticate(user=self.owner)

        # Create batch of content to validate
        content_items = []
        for i in range(50):  # 50 content items
            content_items.append(
                {
                    "id": f"content{i}",
                    "content": f"Test content item {i} with various safety concerns",
                }
            )

        batch_data = {"campaign_id": self.campaign.id, "content_items": content_items}

        response = self.client.post(
            reverse("api:validate_content_batch"), batch_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 50)


class ContentValidationAPISecurityTest(TestCase):
    """Test security aspects of content validation API."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

        self.legitimate_user = User.objects.create_user(
            username="legitimate",
            email="legitimate@example.com",
            password="TestPass123!",
        )
        self.malicious_user = User.objects.create_user(
            username="malicious", email="malicious@example.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Security Test Campaign",
            owner=self.legitimate_user,
            game_system="Test System",
            safety_tools_enabled=True,
        )

        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.legitimate_user, role="GM"
        )

    def test_cross_campaign_validation_attempt(self):
        """Test that users cannot validate content for campaigns they're not in."""
        self.client.force_authenticate(user=self.malicious_user)

        # Try to validate content for legitimate user's campaign
        content_data = {
            "content": "Malicious validation attempt",
            "user_id": self.legitimate_user.id,
            "campaign_id": self.campaign.id,  # Campaign malicious user is not in
        }

        response = self.client.post(
            reverse("api:validate_content_for_user"), content_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_injection_attempt_in_content(self):
        """Test that potential injection attempts in content are handled safely."""
        self.client.force_authenticate(user=self.legitimate_user)

        injection_attempts = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "{{7*7}}",  # Template injection
            "${7*7}",  # Expression injection
            "%%USER%%",  # Variable injection
        ]

        for injection_attempt in injection_attempts:
            with self.subTest(injection=injection_attempt):
                content_data = {
                    "content": injection_attempt,
                    "user_id": self.legitimate_user.id,
                    "campaign_id": self.campaign.id,
                }

                response = self.client.post(
                    reverse("api:validate_content_for_user"),
                    content_data,
                    format="json",
                )

                # Should succeed (content treated as data, not code)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_rate_limiting_validation_requests(self):
        """Test rate limiting on validation requests."""
        self.client.force_authenticate(user=self.legitimate_user)

        content_data = {
            "content": "Rate limit test content",
            "user_id": self.legitimate_user.id,
            "campaign_id": self.campaign.id,
        }

        # Make many rapid requests
        for i in range(20):
            response = self.client.post(
                reverse("api:validate_content_for_user"), content_data, format="json"
            )

            # All should succeed (no rate limiting implemented yet)
            # But this test documents expected behavior
            self.assertIn(
                response.status_code,
                [status.HTTP_200_OK, status.HTTP_429_TOO_MANY_REQUESTS],
            )

    def test_large_content_size_limits(self):
        """Test handling of extremely large content."""
        self.client.force_authenticate(user=self.legitimate_user)

        # Create very large content (1MB+)
        large_content = "A" * (1024 * 1024 + 1)  # 1MB + 1 byte

        content_data = {
            "content": large_content,
            "user_id": self.legitimate_user.id,
            "campaign_id": self.campaign.id,
        }

        response = self.client.post(
            reverse("api:validate_content_for_user"), content_data, format="json"
        )

        # Should either succeed or be rejected due to size limits
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE],
        )
