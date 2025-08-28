"""Test cases for Campaign safety integration and safety-related functionality."""

import json
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from campaigns.models import Campaign

User = get_user_model()


class CampaignSafetyFieldsTest(TestCase):
    """Test Campaign model safety-related fields."""

    def setUp(self):
        """Set up test fixtures."""
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="testpass123"
        )
        self.user = User.objects.create_user(
            username="player",
            email="player@example.com",
            password="testpass123"
        )

    def test_campaign_content_warnings_field_default(self):
        """Test that content_warnings field has empty list as default."""
        campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension"
        )
        
        self.assertEqual(campaign.content_warnings, [])

    def test_campaign_safety_tools_enabled_default(self):
        """Test that safety_tools_enabled field defaults to True."""
        campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension"
        )
        
        self.assertTrue(campaign.safety_tools_enabled)

    def test_campaign_content_warnings_accepts_list_of_strings(self):
        """Test that content_warnings field accepts list of strings."""
        warnings = [
            "Graphic violence",
            "Sexual content",
            "Mental health issues",
            "Animal harm"
        ]
        
        campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Vampire: The Masquerade",
            content_warnings=warnings
        )
        
        self.assertEqual(campaign.content_warnings, warnings)

    def test_campaign_content_warnings_accepts_complex_data(self):
        """Test that content_warnings field accepts complex JSON data."""
        complex_warnings = [
            {
                "category": "violence",
                "description": "Combat scenes with detailed injury descriptions",
                "severity": "moderate"
            },
            {
                "category": "mental_health",
                "description": "Characters dealing with trauma and PTSD",
                "severity": "high",
                "resources": ["https://example.com/mental-health-support"]
            }
        ]
        
        campaign = Campaign.objects.create(
            name="Complex Campaign",
            owner=self.owner,
            game_system="Call of Cthulhu",
            content_warnings=complex_warnings
        )
        
        self.assertEqual(campaign.content_warnings, complex_warnings)

    def test_campaign_safety_tools_enabled_boolean_values(self):
        """Test that safety_tools_enabled accepts boolean values."""
        # Test True (should be default)
        campaign_enabled = Campaign.objects.create(
            name="Safety Enabled Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            safety_tools_enabled=True
        )
        self.assertTrue(campaign_enabled.safety_tools_enabled)
        
        # Test False
        campaign_disabled = Campaign.objects.create(
            name="Safety Disabled Campaign",
            owner=self.owner,
            game_system="D&D 5e",
            safety_tools_enabled=False
        )
        self.assertFalse(campaign_disabled.safety_tools_enabled)

    def test_campaign_content_warnings_empty_list(self):
        """Test that content_warnings can be explicitly set to empty list."""
        campaign = Campaign.objects.create(
            name="No Warnings Campaign",
            owner=self.owner,
            game_system="Wholesome RPG",
            content_warnings=[]
        )
        
        self.assertEqual(campaign.content_warnings, [])

    def test_campaign_content_warnings_json_serialization(self):
        """Test that content_warnings can be JSON serialized/deserialized."""
        warnings = ["Violence", "Language", "Adult themes"]
        
        campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Generic System",
            content_warnings=warnings
        )
        
        # Test JSON serialization
        warnings_json = json.dumps(campaign.content_warnings)
        deserialized_warnings = json.loads(warnings_json)
        
        self.assertEqual(deserialized_warnings, warnings)

    def test_campaign_safety_fields_validation(self):
        """Test validation of safety-related fields."""
        campaign = Campaign(
            name="Validation Test Campaign",
            owner=self.owner,
            game_system="Test System",
            content_warnings=["Valid warning"],
            safety_tools_enabled=True
        )
        
        # Should pass validation
        try:
            campaign.full_clean()
        except ValidationError as e:
            self.fail(f"Campaign safety fields validation failed unexpectedly: {e}")

    def test_campaign_content_warnings_with_long_content(self):
        """Test content_warnings field with very long content."""
        long_warning = "x" * 1000  # Very long warning text
        long_warnings = [long_warning, "Another warning", long_warning]
        
        campaign = Campaign.objects.create(
            name="Long Content Campaign",
            owner=self.owner,
            game_system="Test System",
            content_warnings=long_warnings
        )
        
        self.assertEqual(campaign.content_warnings, long_warnings)

    def test_campaign_content_warnings_special_characters(self):
        """Test content_warnings field handles special characters."""
        warnings_with_special_chars = [
            "Violence & Gore",
            "Content with 'quotes' and \"double quotes\"",
            "Unicode content: émotions, 中文, русский",
            "HTML-like content: <script>alert('test')</script>",
            "JSON-like content: {\"key\": \"value\"}"
        ]
        
        campaign = Campaign.objects.create(
            name="Special Characters Campaign",
            owner=self.owner,
            game_system="International System",
            content_warnings=warnings_with_special_chars
        )
        
        self.assertEqual(campaign.content_warnings, warnings_with_special_chars)


class CampaignSafetyAgreementModelTest(TestCase):
    """Test the CampaignSafetyAgreement model."""

    def setUp(self):
        """Set up test fixtures."""
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player",
            email="player@example.com",
            password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            content_warnings=["Violence", "Mature themes"],
            safety_tools_enabled=True
        )

    def test_campaign_safety_agreement_creation(self):
        """Test creating a CampaignSafetyAgreement."""
        # Import here to avoid circular imports during test discovery
        from campaigns.models import CampaignSafetyAgreement
        
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player
        )
        
        self.assertEqual(agreement.campaign, self.campaign)
        self.assertEqual(agreement.participant, self.player)
        self.assertFalse(agreement.agreed_to_terms)  # Default should be False
        self.assertEqual(agreement.acknowledged_warnings, [])  # Default should be empty list
        self.assertIsNotNone(agreement.created_at)
        self.assertIsNotNone(agreement.updated_at)

    def test_campaign_safety_agreement_string_representation(self):
        """Test string representation of CampaignSafetyAgreement."""
        from campaigns.models import CampaignSafetyAgreement
        
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player
        )
        
        expected_str = f"Safety agreement: {self.player.username} in {self.campaign.name}"
        self.assertEqual(str(agreement), expected_str)

    def test_campaign_safety_agreement_agreed_to_terms_field(self):
        """Test agreed_to_terms field behavior."""
        from campaigns.models import CampaignSafetyAgreement
        
        # Test default value (False)
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player
        )
        self.assertFalse(agreement.agreed_to_terms)
        
        # Test setting to True
        agreement.agreed_to_terms = True
        agreement.save()
        agreement.refresh_from_db()
        self.assertTrue(agreement.agreed_to_terms)

    def test_campaign_safety_agreement_acknowledged_warnings_field(self):
        """Test acknowledged_warnings field accepts list of strings."""
        from campaigns.models import CampaignSafetyAgreement
        
        acknowledged = ["Violence", "Mature themes"]
        
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player,
            acknowledged_warnings=acknowledged
        )
        
        self.assertEqual(agreement.acknowledged_warnings, acknowledged)

    def test_campaign_safety_agreement_acknowledged_warnings_complex_data(self):
        """Test acknowledged_warnings field with complex JSON data."""
        from campaigns.models import CampaignSafetyAgreement
        
        complex_acknowledgments = [
            {
                "warning": "Violence",
                "acknowledged_at": "2024-01-01T12:00:00Z",
                "comfort_level": "acceptable"
            },
            {
                "warning": "Mature themes",
                "acknowledged_at": "2024-01-01T12:01:00Z",
                "comfort_level": "needs_discussion"
            }
        ]
        
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player,
            acknowledged_warnings=complex_acknowledgments
        )
        
        self.assertEqual(agreement.acknowledged_warnings, complex_acknowledgments)

    def test_campaign_safety_agreement_unique_constraint(self):
        """Test that campaign+participant combination is unique."""
        from campaigns.models import CampaignSafetyAgreement
        
        # Create first agreement
        CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player
        )
        
        # Try to create second agreement for same campaign+participant
        with self.assertRaises(IntegrityError):
            CampaignSafetyAgreement.objects.create(
                campaign=self.campaign,
                participant=self.player
            )

    def test_campaign_safety_agreement_cascade_deletion(self):
        """Test cascade behavior when campaign or participant is deleted."""
        from campaigns.models import CampaignSafetyAgreement
        
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player
        )
        agreement_id = agreement.id
        
        # Delete campaign - agreement should be deleted
        self.campaign.delete()
        
        with self.assertRaises(CampaignSafetyAgreement.DoesNotExist):
            CampaignSafetyAgreement.objects.get(id=agreement_id)

    def test_campaign_safety_agreement_participant_deletion(self):
        """Test behavior when participant is deleted."""
        from campaigns.models import CampaignSafetyAgreement
        
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player
        )
        agreement_id = agreement.id
        
        # Delete participant - agreement should be deleted
        self.player.delete()
        
        with self.assertRaises(CampaignSafetyAgreement.DoesNotExist):
            CampaignSafetyAgreement.objects.get(id=agreement_id)

    def test_campaign_safety_agreement_foreign_key_relationships(self):
        """Test foreign key relationships work correctly."""
        from campaigns.models import CampaignSafetyAgreement
        
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence"]
        )
        
        # Test forward relationships
        self.assertEqual(agreement.campaign, self.campaign)
        self.assertEqual(agreement.participant, self.player)
        
        # Test reverse relationships if they exist
        campaign_agreements = self.campaign.safety_agreements.all()
        self.assertIn(agreement, campaign_agreements)
        
        participant_agreements = self.player.safety_agreements.all()
        self.assertIn(agreement, participant_agreements)

    def test_campaign_safety_agreement_multiple_participants(self):
        """Test multiple participants can have agreements for same campaign."""
        from campaigns.models import CampaignSafetyAgreement
        
        # Create additional participants
        player2 = User.objects.create_user(
            username="player2",
            email="player2@example.com",
            password="testpass123"
        )
        player3 = User.objects.create_user(
            username="player3",
            email="player3@example.com",
            password="testpass123"
        )
        
        # Create agreements for all participants
        agreement1 = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player,
            agreed_to_terms=True
        )
        agreement2 = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=player2,
            agreed_to_terms=False
        )
        agreement3 = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=player3,
            agreed_to_terms=True
        )
        
        # Verify all agreements exist and are different
        all_agreements = CampaignSafetyAgreement.objects.filter(campaign=self.campaign)
        self.assertEqual(all_agreements.count(), 3)
        self.assertIn(agreement1, all_agreements)
        self.assertIn(agreement2, all_agreements)
        self.assertIn(agreement3, all_agreements)

    def test_campaign_safety_agreement_json_serialization(self):
        """Test JSON serialization of acknowledged_warnings field."""
        from campaigns.models import CampaignSafetyAgreement
        
        warnings = ["Violence", "Language", "Mature themes"]
        
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=self.campaign,
            participant=self.player,
            acknowledged_warnings=warnings
        )
        
        # Test JSON serialization
        warnings_json = json.dumps(agreement.acknowledged_warnings)
        deserialized_warnings = json.loads(warnings_json)
        
        self.assertEqual(deserialized_warnings, warnings)

    def test_campaign_safety_agreement_validation(self):
        """Test field validation for CampaignSafetyAgreement."""
        from campaigns.models import CampaignSafetyAgreement
        
        agreement = CampaignSafetyAgreement(
            campaign=self.campaign,
            participant=self.player,
            agreed_to_terms=True,
            acknowledged_warnings=["Valid warning"]
        )
        
        # Should pass validation
        try:
            agreement.full_clean()
        except ValidationError as e:
            self.fail(f"CampaignSafetyAgreement validation failed unexpectedly: {e}")


class CampaignSafetyIntegrationTest(TestCase):
    """Integration tests for Campaign safety features with other models."""

    def setUp(self):
        """Set up test fixtures."""
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm",
            email="gm@example.com",
            password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player",
            email="player@example.com",
            password="testpass123"
        )

    def test_campaign_safety_with_membership_system(self):
        """Test safety features integration with campaign membership."""
        from campaigns.models import CampaignSafetyAgreement, CampaignMembership
        
        campaign = Campaign.objects.create(
            name="Safety Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            content_warnings=["Violence", "Supernatural horror"],
            safety_tools_enabled=True
        )
        
        # Add members to campaign
        gm_membership = CampaignMembership.objects.create(
            campaign=campaign,
            user=self.gm,
            role='GM'
        )
        player_membership = CampaignMembership.objects.create(
            campaign=campaign,
            user=self.player,
            role='PLAYER'
        )
        
        # Create safety agreements
        gm_agreement = CampaignSafetyAgreement.objects.create(
            campaign=campaign,
            participant=self.gm,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence", "Supernatural horror"]
        )
        player_agreement = CampaignSafetyAgreement.objects.create(
            campaign=campaign,
            participant=self.player,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence"]
        )
        
        # Verify relationships
        self.assertEqual(gm_membership.campaign, campaign)
        self.assertEqual(gm_agreement.campaign, campaign)
        self.assertEqual(gm_agreement.participant, self.gm)

    def test_campaign_safety_with_user_safety_preferences(self):
        """Test campaign safety integration with user safety preferences."""
        from campaigns.models import CampaignSafetyAgreement
        from users.models.safety import UserSafetyPreferences
        
        # Create user safety preferences
        user_prefs = UserSafetyPreferences.objects.create(
            user=self.player,
            lines=["Sexual content", "Animal harm"],
            veils=["Graphic violence", "Mental health issues"],
            privacy_level='gm_only'
        )
        
        # Create campaign with content warnings
        campaign = Campaign.objects.create(
            name="Integrated Safety Campaign",
            owner=self.owner,
            game_system="World of Darkness",
            content_warnings=["Violence", "Mental health issues", "Supernatural themes"],
            safety_tools_enabled=True
        )
        
        # Create safety agreement
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=campaign,
            participant=self.player,
            agreed_to_terms=True,
            acknowledged_warnings=["Violence", "Mental health issues"]
        )
        
        # Verify both models exist and are accessible
        self.assertEqual(user_prefs.user, self.player)
        self.assertEqual(agreement.participant, self.player)
        self.assertIn("Mental health issues", user_prefs.veils)
        self.assertIn("Mental health issues", agreement.acknowledged_warnings)

    def test_multiple_campaigns_safety_agreements(self):
        """Test that users can have safety agreements with multiple campaigns."""
        from campaigns.models import CampaignSafetyAgreement
        
        # Create multiple campaigns
        campaign1 = Campaign.objects.create(
            name="Horror Campaign",
            owner=self.owner,
            game_system="Call of Cthulhu",
            content_warnings=["Cosmic horror", "Mental illness"],
            safety_tools_enabled=True
        )
        campaign2 = Campaign.objects.create(
            name="Action Campaign",
            owner=self.gm,
            game_system="D&D 5e",
            content_warnings=["Combat violence"],
            safety_tools_enabled=True
        )
        
        # Create safety agreements for same user with different campaigns
        agreement1 = CampaignSafetyAgreement.objects.create(
            campaign=campaign1,
            participant=self.player,
            agreed_to_terms=True,
            acknowledged_warnings=["Cosmic horror"]
        )
        agreement2 = CampaignSafetyAgreement.objects.create(
            campaign=campaign2,
            participant=self.player,
            agreed_to_terms=True,
            acknowledged_warnings=["Combat violence"]
        )
        
        # Verify distinct agreements
        self.assertNotEqual(agreement1.campaign, agreement2.campaign)
        self.assertEqual(agreement1.participant, agreement2.participant)
        self.assertNotEqual(agreement1.acknowledged_warnings, agreement2.acknowledged_warnings)

    def test_campaign_safety_disabled_scenarios(self):
        """Test behavior when safety tools are disabled."""
        campaign = Campaign.objects.create(
            name="No Safety Tools Campaign",
            owner=self.owner,
            game_system="Light RPG",
            content_warnings=[],
            safety_tools_enabled=False
        )
        
        self.assertFalse(campaign.safety_tools_enabled)
        self.assertEqual(campaign.content_warnings, [])
        
        # Safety agreement could still exist even if tools are disabled
        # (for audit/compliance purposes)
        from campaigns.models import CampaignSafetyAgreement
        
        agreement = CampaignSafetyAgreement.objects.create(
            campaign=campaign,
            participant=self.player,
            agreed_to_terms=True
        )
        
        self.assertEqual(agreement.campaign, campaign)
        self.assertFalse(agreement.campaign.safety_tools_enabled)