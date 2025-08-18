"""Basic tests for Character FSM status field functionality."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django_fsm import TransitionNotAllowed

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character

User = get_user_model()


class CharacterFSMBasicTest(TestCase):
    """Basic tests for Character FSM status functionality."""

    def setUp(self):
        """Set up test data."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="TestPass123!"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="TestPass123!"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="TestPass123!"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Test System",
            max_characters_per_player=10,  # Allow multiple characters for testing
        )

        # Add GM to campaign
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )

        # Add player to campaign
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )

    def test_character_starts_with_draft_status(self):
        """Test that new characters start with DRAFT status."""
        self.assertEqual(self.character.status, "DRAFT")

    def test_status_field_choices(self):
        """Test that status field has correct choices."""
        expected_choices = [
            ("DRAFT", "Draft"),
            ("SUBMITTED", "Submitted"),
            ("ACTIVE", "Active"),
            ("INACTIVE", "Inactive"),
            ("RETIRED", "Retired"),
            ("DECEASED", "Deceased"),
        ]
        status_field = Character._meta.get_field("status")
        self.assertEqual(status_field.choices, expected_choices)

    def test_basic_transition_flow(self):
        """Test basic transition flow: DRAFT -> SUBMITTED -> ACTIVE."""
        # Character starts as DRAFT
        self.assertEqual(self.character.status, "DRAFT")

        # Player can submit for approval
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.assertEqual(self.character.status, "SUBMITTED")

        # GM can approve
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "ACTIVE")

    def test_permission_restrictions(self):
        """Test that permission restrictions work correctly."""
        # Only character owner can submit from DRAFT
        with self.assertRaises(PermissionError):
            self.character.submit_for_approval(user=self.gm)

        # Submit as owner
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)

        # Only GM/owner can approve from SUBMITTED
        with self.assertRaises(PermissionError):
            self.character.approve(user=self.player)

    def test_invalid_transitions_blocked(self):
        """Test that invalid transitions are blocked."""
        # Cannot approve from DRAFT (must go through SUBMITTED)
        with self.assertRaises(TransitionNotAllowed):
            self.character.approve(user=self.gm)

        # Cannot retire from DRAFT (must be ACTIVE)
        with self.assertRaises(TransitionNotAllowed):
            self.character.retire(user=self.player)

    def test_rejection_flow(self):
        """Test character rejection flow."""
        # Submit character
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.assertEqual(self.character.status, "SUBMITTED")

        # GM can reject back to DRAFT
        self.character.reject(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "DRAFT")

    def test_active_state_transitions(self):
        """Test transitions from ACTIVE state."""
        # Get to ACTIVE state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "ACTIVE")

        # Test deactivate
        self.character.deactivate(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "INACTIVE")

        # Test reactivate
        self.character.activate(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "ACTIVE")

        # Test retirement by owner
        self.character.retire(user=self.player)
        self.character.save(audit_user=self.player)
        self.assertEqual(self.character.status, "RETIRED")

    def test_death_transition(self):
        """Test marking character as deceased."""
        # Get to ACTIVE state
        self.character.submit_for_approval(user=self.player)
        self.character.save(audit_user=self.player)
        self.character.approve(user=self.gm)
        self.character.save(audit_user=self.gm)

        # GM can mark as deceased
        self.character.mark_deceased(user=self.gm)
        self.character.save(audit_user=self.gm)
        self.assertEqual(self.character.status, "DECEASED")

        # Player cannot mark as deceased
        character2 = Character.objects.create(
            name="Test Character 2",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )
        character2.submit_for_approval(user=self.player)
        character2.save(audit_user=self.player)
        character2.approve(user=self.gm)
        character2.save(audit_user=self.gm)

        with self.assertRaises(PermissionError):
            character2.mark_deceased(user=self.player)

    def test_campaign_owner_permissions(self):
        """Test that campaign owners have GM-level permissions."""
        # Create character for owner
        owner_character = Character.objects.create(
            name="Owner Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="Test System",
        )

        # Owner can do GM-level transitions
        owner_character.submit_for_approval(user=self.owner)
        owner_character.save(audit_user=self.owner)
        owner_character.approve(user=self.owner)  # Owner acts as GM
        owner_character.save(audit_user=self.owner)
        self.assertEqual(owner_character.status, "ACTIVE")

    def test_filtering_by_status(self):
        """Test filtering characters by status."""
        # Create characters in different states
        Character.objects.create(
            name="Draft Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )

        char2 = Character.objects.create(
            name="Active Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )
        char2.submit_for_approval(user=self.player)
        char2.save(audit_user=self.player)
        char2.approve(user=self.gm)
        char2.save(audit_user=self.gm)

        # Refresh char2 from database to ensure status is updated
        char2.refresh_from_db()
        self.assertEqual(char2.status, "ACTIVE")

        # Test filtering
        draft_chars = Character.objects.filter(status="DRAFT")
        active_chars = Character.objects.filter(status="ACTIVE")

        # Should have char1 and self.character in DRAFT status
        self.assertEqual(draft_chars.count(), 2)
        # Should have char2 in ACTIVE status
        self.assertEqual(active_chars.count(), 1)
        self.assertEqual(active_chars.first().name, "Active Character")
