"""Test cases for Campaign Safety API endpoints."""

import json
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class CampaignSafetyAPITest(TestCase):
    """Test the campaign safety API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create test users
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="TestPass123!"
        )
        self.gm = User.objects.create_user(
            username="gm",
            email="gm@example.com",
            password="TestPass123!"
        )
        self.player = User.objects.create_user(
            username="player",
            email="player@example.com",
            password="TestPass123!"
        )
        self.outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="TestPass123!"
        )
        
        # Create test campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            content_warnings=["Violence", "Supernatural themes", "Mental health issues"],
            safety_tools_enabled=True
        )
        
        # Add campaign memberships
        CampaignMembership.objects.create(
            campaign=self.campaign,
            user=self.gm,
            role='GM'
        )
        CampaignMembership.objects.create(
            campaign=self.campaign,
            user=self.player,
            role='PLAYER'
        )
        
        # API endpoints
        self.campaign_safety_url = lambda campaign_id: reverse(
            "api:campaign_safety", kwargs={"campaign_id": campaign_id}
        )
        self.campaign_safety_agreement_url = lambda campaign_id: reverse(
            "api:campaign_safety_agreement", kwargs={"campaign_id": campaign_id}
        )

    def test_get_campaign_safety_info_as_owner(self):
        """Test getting campaign safety information as owner."""
        self.client.force_authenticate(user=self.owner)
        
        response = self.client.get(self.campaign_safety_url(self.campaign.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['content_warnings'], 
            ["Violence", "Supernatural themes", "Mental health issues"]
        )
        self.assertTrue(response.data['safety_tools_enabled'])

    def test_get_campaign_safety_info_as_member(self):
        """Test getting campaign safety information as campaign member."""
        self.client.force_authenticate(user=self.player)
        
        response = self.client.get(self.campaign_safety_url(self.campaign.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['content_warnings'],
            ["Violence", "Supernatural themes", "Mental health issues"]
        )
        self.assertTrue(response.data['safety_tools_enabled'])

    def test_get_campaign_safety_info_as_outsider_denied(self):
        """Test that outsiders cannot access campaign safety info."""
        self.client.force_authenticate(user=self.outsider)
        
        response = self.client.get(self.campaign_safety_url(self.campaign.id))
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_campaign_safety_settings_as_owner(self):
        """Test updating campaign safety settings as owner."""
        self.client.force_authenticate(user=self.owner)
        
        updated_data = {
            "content_warnings": ["Updated violence", "New warning", "Psychological horror"],
            "safety_tools_enabled": False
        }
        
        response = self.client.put(
            self.campaign_safety_url(self.campaign.id),
            updated_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content_warnings'], updated_data['content_warnings'])
        self.assertFalse(response.data['safety_tools_enabled'])
        
        # Verify database was updated
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.content_warnings, updated_data['content_warnings'])
        self.assertFalse(self.campaign.safety_tools_enabled)

    def test_update_campaign_safety_settings_as_gm(self):
        """Test updating campaign safety settings as GM (should be allowed)."""
        self.client.force_authenticate(user=self.gm)
        
        updated_data = {
            "content_warnings": ["GM updated warnings"],
            "safety_tools_enabled": True
        }
        
        response = self.client.put(
            self.campaign_safety_url(self.campaign.id),
            updated_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content_warnings'], updated_data['content_warnings'])

    def test_update_campaign_safety_settings_as_player_denied(self):
        """Test that players cannot update campaign safety settings."""
        self.client.force_authenticate(user=self.player)
        
        updated_data = {
            "content_warnings": ["Player trying to update"],
            "safety_tools_enabled": False
        }
        
        response = self.client.put(
            self.campaign_safety_url(self.campaign.id),
            updated_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_complex_content_warnings_structure(self):
        """Test handling complex JSON structures in content warnings."""
        self.client.force_authenticate(user=self.owner)
        
        complex_warnings = [
            {
                "category": "violence",
                "description": "Combat scenes with injury details",
                "severity": "moderate",
                "resources": ["https://example.com/violence-support"]
            },
            {
                "category": "mental_health",
                "description": "Characters dealing with trauma",
                "severity": "high",
                "contact_gm": True
            }
        ]
        
        updated_data = {
            "content_warnings": complex_warnings,
            "safety_tools_enabled": True
        }
        
        response = self.client.put(
            self.campaign_safety_url(self.campaign.id),
            updated_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content_warnings'], complex_warnings)

    def test_empty_content_warnings(self):
        """Test setting empty content warnings list."""
        self.client.force_authenticate(user=self.owner)
        
        updated_data = {
            "content_warnings": [],
            "safety_tools_enabled": True
        }
        
        response = self.client.put(
            self.campaign_safety_url(self.campaign.id),
            updated_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content_warnings'], [])

    def test_nonexistent_campaign_404(self):
        """Test accessing safety info for nonexistent campaign returns 404."""
        self.client.force_authenticate(user=self.owner)
        
        response = self.client.get(self.campaign_safety_url(99999))
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CampaignSafetyAgreementAPITest(TestCase):
    """Test the campaign safety agreement API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create test users
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="TestPass123!"
        )
        self.player1 = User.objects.create_user(
            username="player1",
            email="player1@example.com",
            password="TestPass123!"
        )
        self.player2 = User.objects.create_user(
            username="player2",
            email="player2@example.com",
            password="TestPass123!"
        )
        
        # Create test campaign
        self.campaign = Campaign.objects.create(
            name="Safety Agreement Campaign",
            owner=self.owner,
            game_system="World of Darkness",
            content_warnings=["Violence", "Supernatural horror", "Mental illness"],
            safety_tools_enabled=True
        )
        
        # Add campaign memberships
        CampaignMembership.objects.create(
            campaign=self.campaign,
            user=self.player1,
            role='PLAYER'
        )
        CampaignMembership.objects.create(
            campaign=self.campaign,
            user=self.player2,
            role='PLAYER'
        )
        
        # API endpoints
        self.safety_agreement_url = lambda campaign_id: reverse(
            "api:campaign_safety_agreement", kwargs={"campaign_id": campaign_id}
        )

    def test_create_safety_agreement(self):
        """Test creating a new safety agreement."""
        self.client.force_authenticate(user=self.player1)
        
        agreement_data = {
            "agreed_to_terms": True,
            "acknowledged_warnings": ["Violence", "Supernatural horror"]
        }
        
        response = self.client.post(
            self.safety_agreement_url(self.campaign.id),
            agreement_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['agreed_to_terms'])
        self.assertEqual(
            response.data['acknowledged_warnings'],
            ["Violence", "Supernatural horror"]
        )
        self.assertEqual(response.data['participant'], self.player1.id)
        self.assertEqual(response.data['campaign'], self.campaign.id)

    def test_get_own_safety_agreement(self):
        """Test getting own safety agreement."""
        from campaigns.models import CampaignSafetyAgreement
        
        # Create existing agreement
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player1,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence"]
        )
        
        self.client.force_authenticate(user=self.player1)
        
        response = self.client.get(self.safety_agreement_url(self.campaign.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['agreed_to_terms'])
        self.assertEqual(response.data['acknowledged_warnings'], ["Violence"])

    def test_update_existing_safety_agreement(self):
        """Test updating an existing safety agreement."""
        from campaigns.models import CampaignSafetyAgreement
        
        # Create existing agreement
        CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player1,
            agreed_to_terms=False,
            acknowledged_warnings=["Violence"]
        )
        
        self.client.force_authenticate(user=self.player1)
        
        updated_data = {
            "agreed_to_terms": True,
            "acknowledged_warnings": ["Violence", "Supernatural horror", "Mental illness"]
        }
        
        response = self.client.put(
            self.safety_agreement_url(self.campaign.id),
            updated_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['agreed_to_terms'])
        self.assertEqual(
            response.data['acknowledged_warnings'],
            ["Violence", "Supernatural horror", "Mental illness"]
        )

    def test_complex_acknowledged_warnings(self):
        """Test safety agreement with complex acknowledged warnings structure."""
        self.client.force_authenticate(user=self.player1)
        
        complex_acknowledgments = [
            {
                "warning": "Violence",
                "comfort_level": "acceptable",
                "notes": "Fine with combat violence"
            },
            {
                "warning": "Mental illness",
                "comfort_level": "needs_discussion",
                "notes": "Please discuss before including"
            }
        ]
        
        agreement_data = {
            "agreed_to_terms": True,
            "acknowledged_warnings": complex_acknowledgments
        }
        
        response = self.client.post(
            self.safety_agreement_url(self.campaign.id),
            agreement_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['acknowledged_warnings'], complex_acknowledgments)

    def test_non_member_cannot_create_agreement(self):
        """Test that non-campaign members cannot create safety agreements."""
        outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="TestPass123!"
        )
        
        self.client.force_authenticate(user=outsider)
        
        agreement_data = {
            "agreed_to_terms": True,
            "acknowledged_warnings": ["Violence"]
        }
        
        response = self.client.post(
            self.safety_agreement_url(self.campaign.id),
            agreement_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_can_view_all_agreements(self):
        """Test that campaign owner can view all safety agreements."""
        from campaigns.models import CampaignSafetyAgreement
        
        # Create agreements for players
        CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player1,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence"]
        )
        CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player2,
            agreed_to_terms=False,
            acknowledged_warnings=[]
        )
        
        self.client.force_authenticate(user=self.owner)
        
        # Use different endpoint for viewing all agreements
        response = self.client.get(
            reverse("api:campaign_safety_agreements", kwargs={"campaign_id": self.campaign.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['agreements']), 2)

    def test_delete_safety_agreement(self):
        """Test deleting a safety agreement."""
        from campaigns.models import CampaignSafetyAgreement
        
        # Create agreement to delete
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player1,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence"]
        )
        
        self.client.force_authenticate(user=self.player1)
        
        response = self.client.delete(self.safety_agreement_url(self.campaign.id))
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify agreement was deleted
        with self.assertRaises(CampaignSafetyAgreement.DoesNotExist):
            CampaignSafetyAgreement.objects.get(id=agreement.id)

    def test_agreement_validation_errors(self):
        """Test validation errors in safety agreement creation."""
        self.client.force_authenticate(user=self.player1)
        
        # Test invalid data types
        invalid_data = {
            "agreed_to_terms": "not_a_boolean",
            "acknowledged_warnings": "not_a_list"
        }
        
        response = self.client.post(
            self.safety_agreement_url(self.campaign.id),
            invalid_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CampaignSafetyOverviewAPITest(TestCase):
    """Test campaign safety overview and management endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create test users
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="TestPass123!"
        )
        self.gm = User.objects.create_user(
            username="gm",
            email="gm@example.com",
            password="TestPass123!"
        )
        self.player1 = User.objects.create_user(
            username="player1",
            email="player1@example.com",
            password="TestPass123!"
        )
        self.player2 = User.objects.create_user(
            username="player2",
            email="player2@example.com",
            password="TestPass123!"
        )
        
        # Create test campaign
        self.campaign = Campaign.objects.create(
            name="Overview Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            content_warnings=["Violence", "Supernatural themes"],
            safety_tools_enabled=True
        )
        
        # Add memberships
        CampaignMembership.objects.create(
            campaign=self.campaign,
            user=self.gm,
            role='GM'
        )
        CampaignMembership.objects.create(
            campaign=self.campaign,
            user=self.player1,
            role='PLAYER'
        )
        CampaignMembership.objects.create(
            campaign=self.campaign,
            user=self.player2,
            role='PLAYER'
        )

    def test_safety_overview_as_owner(self):
        """Test getting safety overview as campaign owner."""
        from users.models.safety import UserSafetyPreferences
        from campaigns.models import CampaignSafetyAgreement
        
        # Create user safety preferences
        UserSafetyPreferences.objects.create(
            user=self.player1,
            lines=["Sexual content"],
            veils=["Violence"],
            privacy_level='gm_only'
        )
        UserSafetyPreferences.objects.create(
            user=self.player2,
            lines=["Animal harm"],
            veils=["Death"],
            privacy_level='campaign_members'
        )
        
        # Create safety agreements
        CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player1,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence"]
        )
        
        self.client.force_authenticate(user=self.owner)
        
        response = self.client.get(
            reverse("api:campaign_safety_overview", kwargs={"campaign_id": self.campaign.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('participants', response.data)
        self.assertIn('safety_summary', response.data)
        self.assertIn('agreements_status', response.data)

    def test_safety_overview_as_gm(self):
        """Test getting safety overview as GM."""
        self.client.force_authenticate(user=self.gm)
        
        response = self.client.get(
            reverse("api:campaign_safety_overview", kwargs={"campaign_id": self.campaign.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('participants', response.data)

    def test_safety_overview_as_player_limited_access(self):
        """Test that players get limited safety overview access."""
        self.client.force_authenticate(user=self.player1)
        
        response = self.client.get(
            reverse("api:campaign_safety_overview", kwargs={"campaign_id": self.campaign.id})
        )
        
        # Players might get limited data or be denied
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
        
        if response.status_code == status.HTTP_200_OK:
            # Limited data - no other players' private info
            self.assertNotIn('private_preferences', response.data)

    def test_safety_compatibility_check(self):
        """Test safety compatibility checking between campaign and users."""
        from users.models.safety import UserSafetyPreferences
        
        # Create user preferences that conflict with campaign warnings
        UserSafetyPreferences.objects.create(
            user=self.player1,
            lines=["Violence"],  # Conflicts with campaign warning
            veils=["Supernatural themes"],  # Also in campaign warnings
            privacy_level='gm_only'
        )
        
        self.client.force_authenticate(user=self.owner)
        
        response = self.client.post(
            reverse("api:campaign_safety_check", kwargs={"campaign_id": self.campaign.id}),
            {"user_id": self.player1.id},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('compatibility_result', response.data)
        self.assertIn('conflicts', response.data['compatibility_result'])

    def test_bulk_safety_agreement_status(self):
        """Test getting bulk safety agreement status for all participants."""
        from campaigns.models import CampaignSafetyAgreement
        
        # Create partial agreements
        CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player1,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence"]
        )
        # player2 has no agreement yet
        
        self.client.force_authenticate(user=self.owner)
        
        response = self.client.get(
            reverse("api:campaign_safety_agreements_status", kwargs={"campaign_id": self.campaign.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('agreements_status', response.data)
        self.assertEqual(len(response.data['agreements_status']), 3)  # 2 players + GM
        
        # Find player1's status
        player1_status = next(
            (status for status in response.data['agreements_status'] 
             if status['user_id'] == self.player1.id),
            None
        )
        self.assertIsNotNone(player1_status)
        self.assertTrue(player1_status['has_agreement'])
        self.assertTrue(player1_status['agreed_to_terms'])


class CampaignSafetyAPISecurityTest(TestCase):
    """Test security aspects of campaign safety API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="TestPass123!"
        )
        self.malicious_user = User.objects.create_user(
            username="malicious",
            email="malicious@example.com",
            password="TestPass123!"
        )
        
        self.campaign = Campaign.objects.create(
            name="Security Test Campaign",
            owner=self.owner,
            game_system="Test System",
            content_warnings=["Test warning"],
            safety_tools_enabled=True
        )

    def test_unauthorized_safety_settings_modification(self):
        """Test that unauthorized users cannot modify safety settings."""
        self.client.force_authenticate(user=self.malicious_user)
        
        malicious_data = {
            "content_warnings": ["Malicious content"],
            "safety_tools_enabled": False
        }
        
        response = self.client.put(
            reverse("api:campaign_safety", kwargs={"campaign_id": self.campaign.id}),
            malicious_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verify original settings unchanged
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.content_warnings, ["Test warning"])
        self.assertTrue(self.campaign.safety_tools_enabled)

    def test_campaign_id_tampering(self):
        """Test that users cannot access other campaigns by ID tampering."""
        # Create second campaign
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.malicious_user,
            game_system="Other System",
            content_warnings=["Other warning"],
            safety_tools_enabled=False
        )
        
        # Try to access first campaign as malicious user
        self.client.force_authenticate(user=self.malicious_user)
        
        response = self.client.get(
            reverse("api:campaign_safety", kwargs={"campaign_id": self.campaign.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_safety_agreement_cross_campaign_protection(self):
        """Test that safety agreements are properly isolated between campaigns."""
        from campaigns.models import CampaignSafetyAgreement
        
        # Create second campaign with malicious user as member
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.malicious_user,
            game_system="Other System"
        )
        
        # Create legitimate agreement in first campaign
        CampaignMembership.objects.create(
            campaign=self.campaign,
            user=self.owner,
            role='PLAYER'  # Owner as player for this test
        )
        
        CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.owner,
            agreed_to_terms=True,
            acknowledged_warnings=["Test warning"]
        )
        
        # Try to access agreement via other campaign
        self.client.force_authenticate(user=self.malicious_user)
        
        response = self.client.get(
            reverse("api:campaign_safety_agreement", kwargs={"campaign_id": other_campaign.id})
        )
        
        # Should not find any agreement
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_privacy_level_information_leakage(self):
        """Test that private safety preferences don't leak through campaign API."""
        from users.models.safety import UserSafetyPreferences
        
        # Add malicious user to campaign
        CampaignMembership.objects.create(
            campaign=self.campaign,
            user=self.malicious_user,
            role='PLAYER'
        )
        
        # Create private preferences for owner
        UserSafetyPreferences.objects.create(
            user=self.owner,
            lines=["Secret private line"],
            veils=["Secret private veil"],
            privacy_level='private'
        )
        
        # Try to access campaign overview as malicious user
        self.client.force_authenticate(user=self.malicious_user)
        
        response = self.client.get(
            reverse("api:campaign_safety_overview", kwargs={"campaign_id": self.campaign.id})
        )
        
        # Should not contain private preferences
        response_text = str(response.data)
        self.assertNotIn("Secret private line", response_text)
        self.assertNotIn("Secret private veil", response_text)