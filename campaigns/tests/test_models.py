from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from campaigns.models import Campaign, CampaignMembership

User = get_user_model()


class CampaignModelTest(TestCase):
    """Test the Campaign model."""

    def setUp(self):
        """Set up test users."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.user = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

    def test_create_campaign(self):
        """Test creating a campaign with required fields."""
        campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            description="A test campaign",
            game_system="Mage: The Ascension",
        )
        self.assertEqual(campaign.name, "Test Campaign")
        self.assertEqual(campaign.owner, self.owner)
        self.assertEqual(campaign.description, "A test campaign")
        self.assertEqual(campaign.game_system, "Mage: The Ascension")
        self.assertTrue(campaign.is_active)
        self.assertIsNotNone(campaign.created_at)
        self.assertIsNotNone(campaign.updated_at)

    def test_campaign_str(self):
        """Test the campaign string representation."""
        campaign = Campaign.objects.create(
            name="My Campaign", owner=self.owner, game_system="Vampire: The Masquerade"
        )
        self.assertEqual(str(campaign), "My Campaign")

    def test_campaign_owner_deletion_cascade(self):
        """Test that deleting owner deletes campaign (CASCADE)."""
        campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Custom System"
        )
        campaign_id = campaign.id
        self.owner.delete()
        # Campaign should be deleted along with the owner
        self.assertFalse(Campaign.objects.filter(id=campaign_id).exists())

    def test_campaign_unique_slug(self):
        """Test that campaign slugs are unique."""
        Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="World of Darkness",
            slug="test-campaign",
        )
        with self.assertRaises(IntegrityError):
            Campaign.objects.create(
                name="Another Campaign",
                owner=self.user,
                game_system="World of Darkness",
                slug="test-campaign",
            )

    def test_campaign_game_system_free_text(self):
        """Test that game_system accepts any free text."""
        campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="My Custom Game System"
        )
        self.assertEqual(campaign.game_system, "My Custom Game System")

    def test_campaign_game_system_can_be_blank(self):
        """Test that game_system can be blank (empty)."""
        campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system=""
        )
        self.assertEqual(campaign.game_system, "")

    def test_campaign_default_values(self):
        """Test default values for campaign fields."""
        campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )
        self.assertTrue(campaign.is_active)
        self.assertEqual(campaign.description, "")


class CampaignMembershipModelTest(TestCase):
    """Test the CampaignMembership model."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )

    def test_create_membership(self):
        """Test creating a campaign membership."""
        membership = CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        self.assertEqual(membership.campaign, self.campaign)
        self.assertEqual(membership.user, self.player)
        self.assertEqual(membership.role, "PLAYER")
        self.assertIsNotNone(membership.joined_at)

    def test_membership_role_choices(self):
        """Test that role is limited to valid choices."""
        membership = CampaignMembership(
            campaign=self.campaign, user=self.player, role="invalid"
        )
        with self.assertRaises(ValidationError):
            membership.full_clean()

    def test_membership_unique_constraint(self):
        """Test that a user can only have one membership per campaign."""
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        with self.assertRaises(IntegrityError):
            CampaignMembership.objects.create(
                campaign=self.campaign, user=self.player, role="GM"
            )

    def test_membership_str(self):
        """Test the membership string representation."""
        membership = CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        expected = f"{self.player.username} - {self.campaign.name} (PLAYER)"
        self.assertEqual(str(membership), expected)

    def test_multiple_gms(self):
        """Test that a campaign can have multiple GMs."""
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        gm2 = User.objects.create_user(
            username="gm2", email="gm2@test.com", password="testpass123"
        )
        CampaignMembership.objects.create(campaign=self.campaign, user=gm2, role="GM")

        gm_count = CampaignMembership.objects.filter(
            campaign=self.campaign, role="GM"
        ).count()
        self.assertEqual(gm_count, 2)

    def test_owner_role_handled_automatically(self):
        """Test that the campaign owner role is handled automatically."""
        # Owner should NOT have a membership - they're handled via Campaign.owner field
        self.assertFalse(
            CampaignMembership.objects.filter(
                campaign=self.campaign, user=self.owner
            ).exists()
        )
        # But they should still be recognized as owner through Campaign methods
        self.assertTrue(self.campaign.is_owner(self.owner))
        self.assertEqual(self.campaign.get_user_role(self.owner), "OWNER")

    def test_all_role_types(self):
        """Test creating memberships with all role types."""
        roles = ["GM", "PLAYER", "OBSERVER"]
        users = [self.gm, self.player, self.observer]

        for user, role in zip(users, roles):
            membership = CampaignMembership.objects.create(
                campaign=self.campaign, user=user, role=role
            )
            self.assertEqual(membership.role, role)

    def test_cascade_delete_campaign(self):
        """Test that deleting a campaign deletes its memberships."""
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        campaign_id = self.campaign.id
        self.campaign.delete()

        self.assertFalse(
            CampaignMembership.objects.filter(campaign_id=campaign_id).exists()
        )

    def test_cascade_delete_user(self):
        """Test that deleting a user deletes their memberships."""
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        user_id = self.player.id
        self.player.delete()

        self.assertFalse(CampaignMembership.objects.filter(user_id=user_id).exists())

    def test_owner_cannot_have_membership(self):
        """Test that owner cannot have a membership role."""
        # Owners should not be able to have membership roles
        with self.assertRaises(ValidationError):
            membership = CampaignMembership(
                campaign=self.campaign, user=self.owner, role="GM"
            )
            membership.clean()

    def test_membership_role_validation(self):
        """Test that membership roles are properly validated."""
        # Valid roles should work
        for role in ["GM", "PLAYER", "OBSERVER"]:
            user = User.objects.create_user(
                username=f"test_{role.lower()}",
                email=f"{role.lower()}@test.com",
                password="pass123",
            )
            membership = CampaignMembership(
                campaign=self.campaign, user=user, role=role
            )
            # Should not raise ValidationError
            membership.full_clean()  # This should pass without exception
            membership.save()  # Save to verify it works

            # Verify the membership was created correctly
            self.assertEqual(membership.role, role)
            self.assertEqual(membership.campaign, self.campaign)
            self.assertEqual(membership.user, user)

        # Test invalid role
        invalid_user = User.objects.create_user(
            username="invalid_test", email="invalid@test.com", password="pass123"
        )
        membership = CampaignMembership(
            campaign=self.campaign, user=invalid_user, role="INVALID_ROLE"
        )

        # Should raise ValidationError for invalid role
        with self.assertRaises(ValidationError):
            membership.full_clean()


class CampaignQueryMethodsTest(TestCase):
    """Test Campaign model query methods."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign", owner=self.owner, game_system="Mage: The Ascension"
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

    def test_is_owner(self):
        """Test the is_owner method."""
        self.assertTrue(self.campaign.is_owner(self.owner))
        self.assertFalse(self.campaign.is_owner(self.gm))
        self.assertFalse(self.campaign.is_owner(self.player))
        self.assertFalse(self.campaign.is_owner(self.non_member))

    def test_is_gm(self):
        """Test the is_gm method."""
        self.assertTrue(self.campaign.is_gm(self.gm))
        self.assertFalse(
            self.campaign.is_gm(self.owner)
        )  # Owner is not automatically GM
        self.assertFalse(self.campaign.is_gm(self.player))
        self.assertFalse(self.campaign.is_gm(self.observer))
        self.assertFalse(self.campaign.is_gm(self.non_member))

    def test_is_player(self):
        """Test the is_player method."""
        self.assertTrue(self.campaign.is_player(self.player))
        self.assertFalse(self.campaign.is_player(self.owner))
        self.assertFalse(self.campaign.is_player(self.gm))
        self.assertFalse(self.campaign.is_player(self.observer))
        self.assertFalse(self.campaign.is_player(self.non_member))

    def test_is_observer(self):
        """Test the is_observer method."""
        self.assertTrue(self.campaign.is_observer(self.observer))
        self.assertFalse(self.campaign.is_observer(self.owner))
        self.assertFalse(self.campaign.is_observer(self.gm))
        self.assertFalse(self.campaign.is_observer(self.player))
        self.assertFalse(self.campaign.is_observer(self.non_member))

    def test_is_member(self):
        """Test the is_member method (any role)."""
        self.assertTrue(
            self.campaign.is_member(self.owner)
        )  # Owner has automatic OWNER membership
        self.assertTrue(self.campaign.is_member(self.gm))
        self.assertTrue(self.campaign.is_member(self.player))
        self.assertTrue(self.campaign.is_member(self.observer))
        self.assertFalse(self.campaign.is_member(self.non_member))

    def test_get_user_role(self):
        """Test the get_user_role method."""
        self.assertEqual(self.campaign.get_user_role(self.owner), "OWNER")
        self.assertEqual(self.campaign.get_user_role(self.gm), "GM")
        self.assertEqual(self.campaign.get_user_role(self.player), "PLAYER")
        self.assertEqual(self.campaign.get_user_role(self.observer), "OBSERVER")
        self.assertIsNone(self.campaign.get_user_role(self.non_member))

    def test_owner_membership_permissions(self):
        """Test that owner has all necessary permissions through OWNER role."""
        self.assertTrue(self.campaign.is_owner(self.owner))
        self.assertTrue(self.campaign.is_member(self.owner))
        # get_user_role should return 'OWNER' as it's the highest permission
        self.assertEqual(self.campaign.get_user_role(self.owner), "OWNER")

    def test_membership_deletion_removes_permissions(self):
        """Test that deleting membership removes permissions."""
        membership = CampaignMembership.objects.get(
            campaign=self.campaign, user=self.player
        )
        membership.delete()

        self.assertFalse(self.campaign.is_player(self.player))
        self.assertFalse(self.campaign.is_member(self.player))
        self.assertIsNone(self.campaign.get_user_role(self.player))
