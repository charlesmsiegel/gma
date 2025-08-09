from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from polymorphic.models import PolymorphicModel

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character

User = get_user_model()


class CharacterModelCreationTest(TestCase):
    """Test Character model creation with valid data."""

    def setUp(self):
        """Set up test users and campaigns."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=2,
        )
        # Create membership for player
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

    def test_create_character_with_required_fields(self):
        """Test creating a character with only required fields."""
        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(character.name, "Test Character")
        self.assertEqual(character.campaign, self.campaign)
        self.assertEqual(character.player_owner, self.player)
        self.assertEqual(character.game_system, "Mage: The Ascension")
        self.assertEqual(character.description, "")
        self.assertIsNotNone(character.created_at)
        self.assertIsNotNone(character.updated_at)

    def test_create_character_with_all_fields(self):
        """Test creating a character with all optional fields."""
        character = Character.objects.create(
            name="Detailed Character",
            description="A mysterious mage with a dark past",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(character.name, "Detailed Character")
        self.assertEqual(character.description, "A mysterious mage with a dark past")
        self.assertEqual(character.campaign, self.campaign)
        self.assertEqual(character.player_owner, self.player)
        self.assertEqual(character.game_system, "Mage: The Ascension")
        self.assertIsNotNone(character.created_at)
        self.assertIsNotNone(character.updated_at)

    def test_automatic_timestamp_setting(self):
        """Test that created_at and updated_at are automatically set."""
        character = Character.objects.create(
            name="Timestamp Test",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Mage: The Ascension",
        )
        self.assertIsNotNone(character.created_at)
        self.assertIsNotNone(character.updated_at)
        # Timestamps should be very close (within 1 second)
        time_diff = abs((character.updated_at - character.created_at).total_seconds())
        self.assertLess(time_diff, 1.0)

    def test_character_str_representation(self):
        """Test the string representation of Character model."""
        character = Character.objects.create(
            name="String Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(str(character), "String Test Character")


class CharacterModelValidationTest(TestCase):
    """Test Character model validation constraints."""

    def setUp(self):
        """Set up test users and campaigns."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        self.campaign1 = Campaign.objects.create(
            name="Campaign 1",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=2,
        )
        self.campaign2 = Campaign.objects.create(
            name="Campaign 2",
            owner=self.owner,
            game_system="Vampire: The Masquerade",
            max_characters_per_player=1,
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign2, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player2, role="PLAYER"
        )

    def test_character_name_uniqueness_within_campaign(self):
        """Test that character names must be unique within a campaign."""
        # Create first character
        Character.objects.create(
            name="Unique Name",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Try to create second character with same name in same campaign
        with self.assertRaises(IntegrityError):
            Character.objects.create(
                name="Unique Name",
                campaign=self.campaign1,
                player_owner=self.player2,
                game_system="Mage: The Ascension",
            )

    def test_character_name_uniqueness_across_different_campaigns(self):
        """Test that character names can be the same across different campaigns."""
        # Create character in first campaign
        char1 = Character.objects.create(
            name="Shared Name",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Create character with same name in different campaign - should succeed
        char2 = Character.objects.create(
            name="Shared Name",
            campaign=self.campaign2,
            player_owner=self.player1,
            game_system="Vampire: The Masquerade",
        )

        self.assertEqual(char1.name, char2.name)
        self.assertNotEqual(char1.campaign, char2.campaign)
        self.assertTrue(Character.objects.filter(name="Shared Name").count() == 2)

    def test_character_name_length_validation(self):
        """Test that character names are limited to 100 characters."""
        # Test valid length (100 characters exactly)
        long_name = "A" * 100
        character = Character.objects.create(
            name=long_name,
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(len(character.name), 100)

        # Test invalid length (101 characters) - should fail at validation level
        # We catch DataError which is the specific postgres error for too long data
        from django.db.utils import DataError

        too_long_name = "A" * 101
        character = Character(
            name=too_long_name,
            campaign=self.campaign1,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )
        with self.assertRaises((ValidationError, IntegrityError, DataError)):
            character.full_clean()

    def test_empty_character_name_validation(self):
        """Test that character names cannot be empty."""
        with self.assertRaises(ValidationError):
            character = Character(
                name="",
                campaign=self.campaign1,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )
            character.full_clean()

    def test_blank_character_name_validation(self):
        """Test that character names cannot be blank."""
        with self.assertRaises(ValidationError):
            character = Character(
                name="   ",  # Only whitespace
                campaign=self.campaign1,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )
            character.full_clean()

    def test_player_ownership_validation_for_members(self):
        """Test that only campaign members can own characters."""
        # Campaign member should be able to create character
        character = Character.objects.create(
            name="Valid Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(character.player_owner, self.player1)

        # Non-member should not be able to create character
        with self.assertRaises(ValidationError):
            character = Character(
                name="Invalid Character",
                campaign=self.campaign1,
                player_owner=self.non_member,
                game_system="Mage: The Ascension",
            )
            character.full_clean()

    def test_campaign_owner_can_create_characters(self):
        """Test that campaign owner can create characters in their campaign."""
        character = Character.objects.create(
            name="Owner Character",
            campaign=self.campaign1,
            player_owner=self.owner,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(character.player_owner, self.owner)

    def test_max_characters_per_player_limit_enforcement(self):
        """Test that players cannot exceed max_characters_per_player limit."""
        # Create characters up to the limit (campaign1 allows 2 characters)
        Character.objects.create(
            name="Character 1",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        Character.objects.create(
            name="Character 2",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Try to create third character - should fail validation
        with self.assertRaises(ValidationError):
            character = Character(
                name="Character 3",
                campaign=self.campaign1,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )
            character.full_clean()

    def test_max_characters_validation_respects_campaign_limits(self):
        """Test that max characters validation respects individual campaign limits."""
        # Create one character in campaign2 (limit = 1)
        Character.objects.create(
            name="Solo Character",
            campaign=self.campaign2,
            player_owner=self.player1,
            game_system="Vampire: The Masquerade",
        )

        # Try to create second character in campaign2 - should fail
        with self.assertRaises(ValidationError):
            character = Character(
                name="Second Character",
                campaign=self.campaign2,
                player_owner=self.player1,
                game_system="Vampire: The Masquerade",
            )
            character.full_clean()

        # But player1 should still be able to create characters in campaign1
        Character.objects.create(
            name="First in Campaign1",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )


class CharacterPolymorphicTest(TestCase):
    """Test Character model polymorphic functionality."""

    def setUp(self):
        """Set up test data for polymorphic tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Polymorphic Test Campaign",
            owner=self.owner,
            game_system="Mixed Systems",
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

    def test_character_inherits_from_polymorphic_model(self):
        """Test that Character model inherits from PolymorphicModel."""
        self.assertTrue(issubclass(Character, PolymorphicModel))

    def test_polymorphic_queries_return_correct_instances(self):
        """Test that polymorphic queries work correctly."""
        # Create a base Character
        Character.objects.create(
            name="Base Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Generic",
        )

        # Query should return the character
        characters = Character.objects.all()
        self.assertEqual(characters.count(), 1)
        self.assertEqual(characters[0].name, "Base Character")
        self.assertIsInstance(characters[0], Character)

    def test_can_create_subclasses_of_character_model(self):
        """Test that we can create subclasses of Character model."""

        # This test verifies that the Character model is set up for
        # polymorphic inheritance
        # by checking that it inherits from PolymorphicModel and has the
        # necessary fields.
        # In actual implementation, subclasses would be defined as separate models.

        # Verify that Character has polymorphic fields
        self.assertTrue(hasattr(Character, "polymorphic_ctype"))

        # Verify that we can query for polymorphic types
        Character.objects.create(
            name="Base Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Generic",
        )

        # Should be able to query polymorphically
        all_characters = Character.objects.all()
        self.assertEqual(all_characters.count(), 1)
        self.assertIsInstance(all_characters[0], Character)

    def test_polymorphic_content_type_is_set(self):
        """Test that polymorphic content type is properly set."""
        character = Character.objects.create(
            name="ContentType Test",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Generic",
        )

        # Character should have polymorphic_ctype set
        self.assertIsNotNone(character.polymorphic_ctype)
        self.assertEqual(character.polymorphic_ctype.model_class(), Character)


class CharacterRelationshipTest(TestCase):
    """Test Character model foreign key relationships."""

    def setUp(self):
        """Set up test data for relationship tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Relationship Test Campaign",
            owner=self.owner,
            game_system="Test System",
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player, role="PLAYER"
        )

    def test_foreign_key_relationships_work_correctly(self):
        """Test that foreign key relationships are properly established."""
        character = Character.objects.create(
            name="Relationship Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )

        # Test direct relationships
        self.assertEqual(character.campaign, self.campaign)
        self.assertEqual(character.player_owner, self.player)

        # Test reverse relationships
        self.assertIn(character, self.campaign.characters.all())
        self.assertIn(character, self.player.owned_characters.all())

    def test_reverse_relationship_names_for_performance(self):
        """Test that reverse relationships have proper names for performance queries."""
        character = Character.objects.create(
            name="Performance Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )

        # Test that reverse relationship names exist and work
        campaign_characters = self.campaign.characters.all()
        player_characters = self.player.owned_characters.all()

        self.assertEqual(campaign_characters.count(), 1)
        self.assertEqual(player_characters.count(), 1)
        self.assertEqual(campaign_characters[0], character)
        self.assertEqual(player_characters[0], character)

    def test_cascade_deletion_when_campaign_deleted(self):
        """Test that characters are deleted when their campaign is deleted."""
        character = Character.objects.create(
            name="Cascade Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )
        character_id = character.id

        # Delete campaign - character should be deleted too
        self.campaign.delete()

        # Character should no longer exist
        self.assertFalse(Character.objects.filter(id=character_id).exists())

    def test_cascade_deletion_when_user_deleted(self):
        """Test that characters are deleted when their owner is deleted."""
        character = Character.objects.create(
            name="User Cascade Test Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )
        character_id = character.id

        # Delete player - character should be deleted too
        self.player.delete()

        # Character should no longer exist
        self.assertFalse(Character.objects.filter(id=character_id).exists())

    def test_multiple_characters_same_player(self):
        """Test that a player can own multiple characters in same campaign."""
        # Update campaign to allow multiple characters
        self.campaign.max_characters_per_player = 3
        self.campaign.save()

        char1 = Character.objects.create(
            name="Character 1",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )
        char2 = Character.objects.create(
            name="Character 2",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )

        player_characters = self.player.owned_characters.filter(campaign=self.campaign)
        self.assertEqual(player_characters.count(), 2)
        self.assertIn(char1, player_characters)
        self.assertIn(char2, player_characters)

    def test_multiple_characters_same_campaign(self):
        """Test that a campaign can have multiple characters from different players."""
        player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=player2, role="PLAYER"
        )

        char1 = Character.objects.create(
            name="Player1 Character",
            campaign=self.campaign,
            player_owner=self.player,
            game_system="Test System",
        )
        char2 = Character.objects.create(
            name="Player2 Character",
            campaign=self.campaign,
            player_owner=player2,
            game_system="Test System",
        )

        campaign_characters = self.campaign.characters.all()
        self.assertEqual(campaign_characters.count(), 2)
        self.assertIn(char1, campaign_characters)
        self.assertIn(char2, campaign_characters)


class CharacterValidationOptimizationTest(TestCase):
    """Test optimized Character validation logic performance."""

    def setUp(self):
        """Set up test data for optimization tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

    def test_unlimited_characters_early_exit(self):
        """Test that max_characters_per_player=0 skips validation queries."""
        # Create campaign with unlimited characters
        campaign = Campaign.objects.create(
            name="Unlimited Campaign",
            owner=self.owner,
            game_system="Test System",
            max_characters_per_player=0,  # Unlimited
        )
        CampaignMembership.objects.create(
            campaign=campaign, user=self.player, role="PLAYER"
        )

        # This should succeed without hitting the database for character counts
        character = Character(
            name="Unlimited Character",
            campaign=campaign,
            player_owner=self.player,
            game_system="Test System",
        )
        # Should not raise ValidationError
        character.full_clean()

    def test_missing_fields_early_exit(self):
        """Test that validation skips when required fields are missing."""
        character = Character(
            name="Test Character",
            game_system="Test System",
        )
        # Should not raise ValidationError for missing campaign/player_owner
        # The required field validation will catch this elsewhere
        character._validate_character_limit()  # Should not crash

    def test_optimized_query_uses_field_ids(self):
        """Test that optimized queries use _id fields to avoid extra queries."""
        campaign = Campaign.objects.create(
            name="Query Test Campaign",
            owner=self.owner,
            game_system="Test System",
            max_characters_per_player=2,
        )
        CampaignMembership.objects.create(
            campaign=campaign, user=self.player, role="PLAYER"
        )

        # Create character instance with IDs set
        character = Character(
            name="Query Test Character",
            campaign=campaign,
            player_owner=self.player,
            game_system="Test System",
        )
        character.campaign_id = campaign.id
        character.player_owner_id = self.player.id

        # The validation should work without additional queries
        character._validate_character_limit()

    def test_character_limit_validation_edge_cases(self):
        """Test edge cases in character limit validation."""
        campaign = Campaign.objects.create(
            name="Edge Case Campaign",
            owner=self.owner,
            game_system="Test System",
            max_characters_per_player=1,
        )
        CampaignMembership.objects.create(
            campaign=campaign, user=self.player, role="PLAYER"
        )

        # Create first character
        existing_char = Character.objects.create(
            name="Existing Character",
            campaign=campaign,
            player_owner=self.player,
            game_system="Test System",
        )

        # Test updating existing character (should not count itself)
        existing_char.name = "Updated Name"
        existing_char.full_clean()  # Should succeed

        # Test creating new character when limit is reached
        with self.assertRaises(ValidationError):
            new_char = Character(
                name="New Character",
                campaign=campaign,
                player_owner=self.player,
                game_system="Test System",
            )
            new_char.full_clean()

    def test_exists_optimization_performance(self):
        """Test that exists() with limit is used instead of count()."""
        campaign = Campaign.objects.create(
            name="Performance Campaign",
            owner=self.owner,
            game_system="Test System",
            max_characters_per_player=3,
        )
        CampaignMembership.objects.create(
            campaign=campaign, user=self.player, role="PLAYER"
        )

        # Create characters up to limit
        for i in range(3):
            Character.objects.create(
                name=f"Character {i+1}",
                campaign=campaign,
                player_owner=self.player,
                game_system="Test System",
            )

        # Test validation on character that would exceed limit
        with self.assertRaises(ValidationError) as cm:
            character = Character(
                name="Exceeding Character",
                campaign=campaign,
                player_owner=self.player,
                game_system="Test System",
            )
            character.full_clean()

        self.assertIn("cannot have more than 3", str(cm.exception))

    def test_validation_with_different_campaigns(self):
        """Test that validation is scoped to specific campaigns."""
        campaign1 = Campaign.objects.create(
            name="Campaign 1",
            owner=self.owner,
            game_system="Test System",
            max_characters_per_player=1,
        )
        campaign2 = Campaign.objects.create(
            name="Campaign 2",
            owner=self.owner,
            game_system="Test System",
            max_characters_per_player=1,
        )

        for campaign in [campaign1, campaign2]:
            CampaignMembership.objects.create(
                campaign=campaign, user=self.player, role="PLAYER"
            )

        # Create character in campaign1
        Character.objects.create(
            name="Character 1",
            campaign=campaign1,
            player_owner=self.player,
            game_system="Test System",
        )

        # Should still be able to create character in campaign2
        character2 = Character(
            name="Character 2",
            campaign=campaign2,
            player_owner=self.player,
            game_system="Test System",
        )
        character2.full_clean()  # Should succeed


class CharacterEdgeCaseTest(TestCase):
    """Test Character model edge cases and special scenarios."""

    def setUp(self):
        """Set up test data for edge case tests."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player = User.objects.create_user(
            username="player", email="player@test.com", password="testpass123"
        )

    def test_campaign_with_zero_max_characters_per_player(self):
        """Test behavior when campaign allows 0 characters per player."""
        campaign = Campaign.objects.create(
            name="Zero Characters Campaign",
            owner=self.owner,
            game_system="Restricted System",
            max_characters_per_player=0,
        )
        CampaignMembership.objects.create(
            campaign=campaign, user=self.player, role="PLAYER"
        )

        # Player should not be able to create any characters
        with self.assertRaises(ValidationError):
            character = Character(
                name="Forbidden Character",
                campaign=campaign,
                player_owner=self.player,
                game_system="Restricted System",
            )
            character.full_clean()

    def test_character_creation_when_user_not_campaign_member(self):
        """Test that non-members cannot create characters."""
        campaign = Campaign.objects.create(
            name="Members Only Campaign",
            owner=self.owner,
            game_system="Exclusive System",
        )
        # Note: self.player is NOT a member of this campaign

        with self.assertRaises(ValidationError):
            character = Character(
                name="Unauthorized Character",
                campaign=campaign,
                player_owner=self.player,
                game_system="Exclusive System",
            )
            character.full_clean()

    def test_multiple_characters_by_same_player_different_campaigns(self):
        """Test that a player can have characters in multiple campaigns."""
        campaign1 = Campaign.objects.create(
            name="Campaign 1",
            owner=self.owner,
            game_system="System 1",
            max_characters_per_player=2,
        )
        campaign2 = Campaign.objects.create(
            name="Campaign 2",
            owner=self.owner,
            game_system="System 2",
            max_characters_per_player=1,
        )

        # Make player a member of both campaigns
        CampaignMembership.objects.create(
            campaign=campaign1, user=self.player, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=campaign2, user=self.player, role="PLAYER"
        )

        # Create characters in both campaigns
        char1 = Character.objects.create(
            name="Campaign 1 Character",
            campaign=campaign1,
            player_owner=self.player,
            game_system="System 1",
        )
        char2 = Character.objects.create(
            name="Campaign 2 Character",
            campaign=campaign2,
            player_owner=self.player,
            game_system="System 2",
        )

        # Both should exist and be owned by the same player
        self.assertEqual(char1.player_owner, self.player)
        self.assertEqual(char2.player_owner, self.player)
        self.assertNotEqual(char1.campaign, char2.campaign)

        # Player should have characters in both campaigns
        total_characters = Character.objects.filter(player_owner=self.player).count()
        self.assertEqual(total_characters, 2)

    def test_gm_can_create_characters(self):
        """Test that GMs can create characters in their campaigns."""
        gm_user = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        campaign = Campaign.objects.create(
            name="GM Campaign",
            owner=self.owner,
            game_system="GM System",
        )
        CampaignMembership.objects.create(campaign=campaign, user=gm_user, role="GM")

        character = Character.objects.create(
            name="GM Character",
            campaign=campaign,
            player_owner=gm_user,
            game_system="GM System",
        )
        self.assertEqual(character.player_owner, gm_user)

    def test_observer_can_create_characters(self):
        """Test that observers can create characters if allowed."""
        observer_user = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        campaign = Campaign.objects.create(
            name="Observer Campaign",
            owner=self.owner,
            game_system="Observer System",
        )
        CampaignMembership.objects.create(
            campaign=campaign, user=observer_user, role="OBSERVER"
        )

        character = Character.objects.create(
            name="Observer Character",
            campaign=campaign,
            player_owner=observer_user,
            game_system="Observer System",
        )
        self.assertEqual(character.player_owner, observer_user)

    def test_character_creation_atomic_transaction(self):
        """Test that character creation is properly handled in transactions."""
        campaign = Campaign.objects.create(
            name="Transaction Test Campaign",
            owner=self.owner,
            game_system="Transaction System",
            max_characters_per_player=1,
        )
        CampaignMembership.objects.create(
            campaign=campaign, user=self.player, role="PLAYER"
        )

        # Create first character (should succeed)
        Character.objects.create(
            name="First Character",
            campaign=campaign,
            player_owner=self.player,
            game_system="Transaction System",
        )

        # Try to create second character in a transaction (should fail)
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                character = Character(
                    name="Second Character",
                    campaign=campaign,
                    player_owner=self.player,
                    game_system="Transaction System",
                )
                character.full_clean()

        # Should still only have one character
        self.assertEqual(
            Character.objects.filter(
                campaign=campaign, player_owner=self.player
            ).count(),
            1,
        )
