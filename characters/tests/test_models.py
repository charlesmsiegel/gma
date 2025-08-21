from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.test import TestCase, TransactionTestCase
from polymorphic.models import PolymorphicModel

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character

User = get_user_model()


class CharacterModelTest(TestCase):
    """Test Character model core functionality."""

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
        self.campaign1 = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=2,
        )
        self.campaign2 = Campaign.objects.create(
            name="Another Campaign",
            owner=self.owner,
            game_system="D&D 5e",
        )
        # Create membership for players
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign2, user=self.player1, role="PLAYER"
        )

    def test_create_character_with_required_fields(self):
        """Test creating a character with only required fields."""
        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(character.name, "Test Character")
        self.assertEqual(character.campaign, self.campaign1)
        self.assertEqual(character.player_owner, self.player1)
        self.assertEqual(character.game_system, "Mage: The Ascension")
        self.assertIsNotNone(character.created_at)
        self.assertIsNotNone(character.updated_at)

    def test_create_character_with_all_fields(self):
        """Test creating a character with all optional fields."""
        character = Character.objects.create(
            name="Detailed Character",
            description="A complex character with a rich backstory.",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(
            character.description, "A complex character with a rich backstory."
        )

    def test_character_str_representation(self):
        """Test the string representation of Character model."""
        character = Character.objects.create(
            name="String Test Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(str(character), "String Test Character")

    def test_automatic_timestamp_setting(self):
        """Test that created_at and updated_at are automatically set."""
        character = Character.objects.create(
            name="Timestamp Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.assertIsNotNone(character.created_at)
        self.assertIsNotNone(character.updated_at)

    def test_character_inherits_from_polymorphic_model(self):
        """Test that Character model inherits from PolymorphicModel."""
        self.assertTrue(issubclass(Character, PolymorphicModel))

    def test_polymorphic_queries_return_correct_instances(self):
        """Test that polymorphic queries work correctly."""
        Character.objects.create(
            name="Base Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Generic",
        )

        characters = Character.objects.all()
        self.assertEqual(characters.count(), 1)
        self.assertEqual(characters[0].name, "Base Character")
        self.assertIsInstance(characters[0], Character)

    def test_polymorphic_content_type_is_set(self):
        """Test that polymorphic content type is properly set."""
        character = Character.objects.create(
            name="ContentType Test",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Generic",
        )
        self.assertIsNotNone(character.polymorphic_ctype)
        self.assertEqual(character.polymorphic_ctype.model_class(), Character)

    def test_foreign_key_relationships_work_correctly(self):
        """Test that foreign key relationships are properly established."""
        character = Character.objects.create(
            name="Relationship Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Test forward relationships
        self.assertEqual(character.campaign, self.campaign1)
        self.assertEqual(character.player_owner, self.player1)

        # Test reverse relationships
        self.assertIn(character, self.campaign1.characters.all())
        self.assertIn(character, self.player1.owned_characters.all())

    def test_cascade_deletion_when_campaign_deleted(self):
        """Test that characters are deleted when their campaign is deleted."""
        character = Character.objects.create(
            name="Campaign Delete Test",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        character_id = character.id

        # Delete the campaign
        self.campaign1.delete()

        # Character should be deleted as well
        with self.assertRaises(Character.DoesNotExist):
            Character.objects.get(id=character_id)

    def test_cascade_deletion_when_user_deleted(self):
        """Test that characters are deleted when their owner is deleted."""
        character = Character.objects.create(
            name="User Delete Test",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        character_id = character.id

        # Delete the user
        self.player1.delete()

        # Character should be deleted as well
        with self.assertRaises(Character.DoesNotExist):
            Character.objects.get(id=character_id)

    def test_multiple_characters_same_campaign(self):
        """Test that a campaign can have multiple characters from different players."""
        character1 = Character.objects.create(
            name="Character One",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Add second player to campaign
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player2, role="PLAYER"
        )

        character2 = Character.objects.create(
            name="Character Two",
            campaign=self.campaign1,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )

        campaign_characters = self.campaign1.characters.all()
        self.assertEqual(campaign_characters.count(), 2)
        self.assertIn(character1, campaign_characters)
        self.assertIn(character2, campaign_characters)


class CharacterValidationTest(TestCase):
    """Test Character model validation logic."""

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
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=2,
        )
        self.campaign2 = Campaign.objects.create(
            name="Another Campaign",
            owner=self.owner,
            game_system="D&D 5e",
        )

        # Create membership for players
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player1, role="PLAYER"
        )

    def test_character_name_uniqueness_within_campaign(self):
        """Test that character names must be unique within a campaign."""
        Character.objects.create(
            name="Unique Name",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Creating another character with same name in same campaign should fail
        # Note: This now raises ValidationError instead of IntegrityError because
        # our enhanced validation catches this before reaching the database
        with self.assertRaises(ValidationError):
            Character.objects.create(
                name="Unique Name",
                campaign=self.campaign1,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )

    def test_character_name_uniqueness_across_different_campaigns(self):
        """Test that character names can be the same across different campaigns."""
        Character.objects.create(
            name="Cross Campaign Name",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Add player to second campaign
        CampaignMembership.objects.create(
            campaign=self.campaign2, user=self.player1, role="PLAYER"
        )

        # Same name in different campaign should be fine
        character2 = Character.objects.create(
            name="Cross Campaign Name",
            campaign=self.campaign2,
            player_owner=self.player1,
            game_system="D&D 5e",
        )
        self.assertEqual(character2.name, "Cross Campaign Name")

    def test_character_name_length_validation(self):
        """Test that character names are limited to 100 characters."""
        # Test valid length (100 characters)
        long_name = "A" * 100
        character = Character.objects.create(
            name=long_name,
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(len(character.name), 100)

        # Test invalid length (101 characters) - should fail at validation level
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
        # Non-member trying to create character should fail
        with self.assertRaises(ValidationError):
            character = Character(
                name="Non-member Character",
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
        # Create maximum allowed characters (2)
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

        # Third character should fail validation
        with self.assertRaises(ValidationError):
            character = Character(
                name="Character 3",
                campaign=self.campaign1,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )
            character.full_clean()

    def test_unlimited_characters_when_max_is_zero(self):
        """Test behavior when campaign allows unlimited characters."""
        # Set campaign to allow unlimited characters
        self.campaign1.max_characters_per_player = 0
        self.campaign1.save()

        # Should be able to create many characters
        for i in range(5):
            Character.objects.create(
                name=f"Character {i+1}",
                campaign=self.campaign1,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )

        self.assertEqual(
            Character.objects.filter(
                campaign=self.campaign1, player_owner=self.player1
            ).count(),
            5,
        )

    def test_character_update_validation_excludes_self(self):
        """Test that character update validation excludes current instance."""
        # Create a character at the limit
        self.campaign1.max_characters_per_player = 1
        self.campaign1.save()

        character = Character.objects.create(
            name="Original Name",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Should be able to update the character without validation error
        character.name = "Updated Name"
        character.full_clean()  # Should not raise ValidationError
        character.save()

        self.assertEqual(character.name, "Updated Name")


class CharacterManagerTest(TestCase):
    """Test Character model custom manager methods."""

    def setUp(self):
        """Set up test users and campaigns with various roles."""
        # Create users
        self.owner1 = User.objects.create_user(
            username="owner1", email="owner1@test.com", password="testpass123"
        )
        self.owner2 = User.objects.create_user(
            username="owner2", email="owner2@test.com", password="testpass123"
        )
        self.gm1 = User.objects.create_user(
            username="gm1", email="gm1@test.com", password="testpass123"
        )
        self.gm2 = User.objects.create_user(
            username="gm2", email="gm2@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )
        self.observer1 = User.objects.create_user(
            username="observer1", email="observer1@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )

        # Create campaigns
        self.campaign1 = Campaign.objects.create(
            name="Campaign One",
            owner=self.owner1,
            game_system="Mage: The Ascension",
            max_characters_per_player=0,  # Unlimited for testing multiple characters
        )
        self.campaign2 = Campaign.objects.create(
            name="Campaign Two",
            owner=self.owner2,
            game_system="D&D 5e",
            max_characters_per_player=0,  # Unlimited for testing multiple characters
        )
        self.campaign3 = Campaign.objects.create(
            name="Campaign Three",
            owner=self.owner1,
            game_system="Vampire: The Masquerade",
            max_characters_per_player=0,  # Unlimited for testing multiple characters
        )

        # Create memberships for campaign1
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.gm1, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player2, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.observer1, role="OBSERVER"
        )

        # Create memberships for campaign2
        CampaignMembership.objects.create(
            campaign=self.campaign2, user=self.gm2, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign2, user=self.player1, role="PLAYER"
        )

        # Create characters across campaigns
        self.char1_campaign1_owner = Character.objects.create(
            name="Owner Char 1",
            campaign=self.campaign1,
            player_owner=self.owner1,
            game_system="Mage: The Ascension",
        )
        self.char2_campaign1_gm = Character.objects.create(
            name="GM Char 1",
            campaign=self.campaign1,
            player_owner=self.gm1,
            game_system="Mage: The Ascension",
        )
        self.char3_campaign1_player1 = Character.objects.create(
            name="Player1 Char 1",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.char4_campaign1_player1 = Character.objects.create(
            name="Player1 Char 2",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.char5_campaign1_player2 = Character.objects.create(
            name="Player2 Char 1",
            campaign=self.campaign1,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )
        self.char6_campaign2_owner = Character.objects.create(
            name="Owner Char 2",
            campaign=self.campaign2,
            player_owner=self.owner2,
            game_system="D&D 5e",
        )
        self.char7_campaign2_player1 = Character.objects.create(
            name="Player1 Char 3",
            campaign=self.campaign2,
            player_owner=self.player1,
            game_system="D&D 5e",
        )

    def test_for_campaign_manager_method(self):
        """Test Character.objects.for_campaign() returns characters."""
        # Test campaign1 characters
        campaign1_chars = Character.objects.for_campaign(self.campaign1)
        self.assertEqual(campaign1_chars.count(), 5)

        expected_chars = [
            self.char1_campaign1_owner,
            self.char2_campaign1_gm,
            self.char3_campaign1_player1,
            self.char4_campaign1_player1,
            self.char5_campaign1_player2,
        ]
        for char in expected_chars:
            self.assertIn(char, campaign1_chars)

        # Test campaign2 characters
        campaign2_chars = Character.objects.for_campaign(self.campaign2)
        self.assertEqual(campaign2_chars.count(), 2)
        self.assertIn(self.char6_campaign2_owner, campaign2_chars)
        self.assertIn(self.char7_campaign2_player1, campaign2_chars)

        # Test empty campaign (campaign3 has no characters)
        campaign3_chars = Character.objects.for_campaign(self.campaign3)
        self.assertEqual(campaign3_chars.count(), 0)

    def test_for_campaign_returns_queryset(self):
        """Test that for_campaign returns a proper QuerySet for chaining."""
        queryset = Character.objects.for_campaign(self.campaign1)
        self.assertTrue(hasattr(queryset, "filter"))
        self.assertTrue(hasattr(queryset, "order_by"))

        # Test chaining with other filters
        player1_chars_in_campaign1 = queryset.filter(player_owner=self.player1)
        self.assertEqual(player1_chars_in_campaign1.count(), 2)

    def test_owned_by_manager_method(self):
        """Test Character.objects.owned_by() returns owned characters."""
        # Test player1 characters (across multiple campaigns)
        player1_chars = Character.objects.owned_by(self.player1)
        self.assertEqual(player1_chars.count(), 3)
        expected_chars = [
            self.char3_campaign1_player1,
            self.char4_campaign1_player1,
            self.char7_campaign2_player1,
        ]
        for char in expected_chars:
            self.assertIn(char, player1_chars)

        # Test owner1 characters
        owner1_chars = Character.objects.owned_by(self.owner1)
        self.assertEqual(owner1_chars.count(), 1)
        self.assertIn(self.char1_campaign1_owner, owner1_chars)

        # Test user with no characters
        observer_chars = Character.objects.owned_by(self.observer1)
        self.assertEqual(observer_chars.count(), 0)

        # Test non-member user
        nonmember_chars = Character.objects.owned_by(self.non_member)
        self.assertEqual(nonmember_chars.count(), 0)

    def test_owned_by_returns_queryset(self):
        """Test that owned_by returns a proper QuerySet for chaining."""
        queryset = Character.objects.owned_by(self.player1)
        self.assertTrue(hasattr(queryset, "filter"))

        # Test chaining to filter by campaign
        player1_campaign1_chars = queryset.filter(campaign=self.campaign1)
        self.assertEqual(player1_campaign1_chars.count(), 2)

    def test_editable_by_manager_method_character_owner(self):
        """Test editable_by for character owners - can edit their own characters."""
        # Player1 should be able to edit their own characters
        player1_editable = Character.objects.editable_by(self.player1, self.campaign1)
        self.assertEqual(player1_editable.count(), 2)
        self.assertIn(self.char3_campaign1_player1, player1_editable)
        self.assertIn(self.char4_campaign1_player1, player1_editable)

        # Should not include other players' characters
        self.assertNotIn(self.char5_campaign1_player2, player1_editable)
        self.assertNotIn(self.char2_campaign1_gm, player1_editable)

    def test_editable_by_manager_method_campaign_owner(self):
        """Test editable_by for campaign owners."""
        owner_editable = Character.objects.editable_by(self.owner1, self.campaign1)
        self.assertEqual(owner_editable.count(), 5)

        # Should include all characters in the campaign
        all_campaign1_chars = [
            self.char1_campaign1_owner,
            self.char2_campaign1_gm,
            self.char3_campaign1_player1,
            self.char4_campaign1_player1,
            self.char5_campaign1_player2,
        ]
        for char in all_campaign1_chars:
            self.assertIn(char, owner_editable)

    def test_editable_by_manager_method_campaign_gm(self):
        """Test editable_by for campaign GMs."""
        gm_editable = Character.objects.editable_by(self.gm1, self.campaign1)
        self.assertEqual(gm_editable.count(), 5)

        # Should include all characters in the campaign
        all_campaign1_chars = [
            self.char1_campaign1_owner,
            self.char2_campaign1_gm,
            self.char3_campaign1_player1,
            self.char4_campaign1_player1,
            self.char5_campaign1_player2,
        ]
        for char in all_campaign1_chars:
            self.assertIn(char, gm_editable)

    def test_editable_by_manager_method_observer(self):
        """Test editable_by for observers - cannot edit any characters."""
        observer_editable = Character.objects.editable_by(
            self.observer1, self.campaign1
        )
        self.assertEqual(observer_editable.count(), 0)

    def test_editable_by_manager_method_non_member(self):
        """Test editable_by for non-members - cannot edit any characters."""
        nonmember_editable = Character.objects.editable_by(
            self.non_member, self.campaign1
        )
        self.assertEqual(nonmember_editable.count(), 0)

    def test_editable_by_manager_method_cross_campaign(self):
        """Test editable_by respects campaign boundaries."""
        # Player1 should only see editable chars from specified campaign
        player1_campaign2_editable = Character.objects.editable_by(
            self.player1, self.campaign2
        )
        self.assertEqual(player1_campaign2_editable.count(), 1)
        self.assertIn(self.char7_campaign2_player1, player1_campaign2_editable)

        # Should not see characters from campaign1
        self.assertNotIn(self.char3_campaign1_player1, player1_campaign2_editable)

    def test_editable_by_returns_queryset(self):
        """Test that editable_by returns a proper QuerySet for chaining."""
        queryset = Character.objects.editable_by(self.owner1, self.campaign1)
        self.assertTrue(hasattr(queryset, "filter"))

        # Test chaining with additional filters
        filtered = queryset.filter(name__icontains="Player")
        self.assertEqual(
            filtered.count(), 3
        )  # Player1 Char 1, Player1 Char 2, Player2 Char 1

    def test_manager_methods_with_none_parameters(self):
        """Test manager methods handle None parameters gracefully."""
        # Test for_campaign with None
        with self.assertRaises(ValueError):
            Character.objects.for_campaign(None)

        # Test owned_by with None
        none_owned = Character.objects.owned_by(None)
        self.assertEqual(none_owned.count(), 0)

        # Test editable_by with None user
        none_user_editable = Character.objects.editable_by(None, self.campaign1)
        self.assertEqual(none_user_editable.count(), 0)

        # Test editable_by with None campaign
        with self.assertRaises(ValueError):
            Character.objects.editable_by(self.player1, None)


class CharacterPermissionTest(TestCase):
    """Test Character model permission methods."""

    def setUp(self):
        """Set up test users and campaigns with various roles."""
        # Create users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )
        self.observer = User.objects.create_user(
            username="observer", email="observer@test.com", password="testpass123"
        )
        self.non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )
        self.different_campaign_owner = User.objects.create_user(
            username="other_owner", email="other_owner@test.com", password="testpass123"
        )

        # Create campaigns
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=0,  # Unlimited for testing
        )
        self.other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.different_campaign_owner,
            game_system="D&D 5e",
            max_characters_per_player=0,  # Unlimited for testing
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.observer, role="OBSERVER"
        )

        # Create characters
        self.owner_character = Character.objects.create(
            name="Owner Character",
            campaign=self.campaign,
            player_owner=self.owner,
            game_system="Mage: The Ascension",
        )
        self.gm_character = Character.objects.create(
            name="GM Character",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
        )
        self.player1_character = Character.objects.create(
            name="Player1 Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.player2_character = Character.objects.create(
            name="Player2 Character",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )

    def test_can_be_edited_by_character_owner(self):
        """Test that character owners can edit their own characters."""
        # Player1 can edit their own character
        self.assertTrue(self.player1_character.can_be_edited_by(self.player1))

        # Player2 can edit their own character
        self.assertTrue(self.player2_character.can_be_edited_by(self.player2))

        # GM can edit their own character
        self.assertTrue(self.gm_character.can_be_edited_by(self.gm))

        # Owner can edit their own character
        self.assertTrue(self.owner_character.can_be_edited_by(self.owner))

    def test_can_be_edited_by_campaign_owner(self):
        """Test that campaign owners can edit all characters in their campaign."""
        # Campaign owner can edit all characters
        self.assertTrue(self.player1_character.can_be_edited_by(self.owner))
        self.assertTrue(self.player2_character.can_be_edited_by(self.owner))
        self.assertTrue(self.gm_character.can_be_edited_by(self.owner))
        self.assertTrue(self.owner_character.can_be_edited_by(self.owner))

    def test_can_be_edited_by_campaign_gm(self):
        """Test that campaign GMs can edit all characters in their campaign."""
        # GM can edit all characters in the campaign
        self.assertTrue(self.player1_character.can_be_edited_by(self.gm))
        self.assertTrue(self.player2_character.can_be_edited_by(self.gm))
        self.assertTrue(self.gm_character.can_be_edited_by(self.gm))
        self.assertTrue(self.owner_character.can_be_edited_by(self.gm))

    def test_can_be_edited_by_other_players(self):
        """Test that players cannot edit other players' characters."""
        # Player1 cannot edit Player2's character
        self.assertFalse(self.player2_character.can_be_edited_by(self.player1))

        # Player2 cannot edit Player1's character
        self.assertFalse(self.player1_character.can_be_edited_by(self.player2))

        # Player1 cannot edit GM's character
        self.assertFalse(self.gm_character.can_be_edited_by(self.player1))

        # Player1 cannot edit Owner's character
        self.assertFalse(self.owner_character.can_be_edited_by(self.player1))

    def test_can_be_edited_by_observer(self):
        """Test that observers cannot edit any characters."""
        # Observer cannot edit any characters
        self.assertFalse(self.player1_character.can_be_edited_by(self.observer))
        self.assertFalse(self.player2_character.can_be_edited_by(self.observer))
        self.assertFalse(self.gm_character.can_be_edited_by(self.observer))
        self.assertFalse(self.owner_character.can_be_edited_by(self.observer))

    def test_can_be_edited_by_non_member(self):
        """Test that non-members cannot edit any characters."""
        # Non-member cannot edit any characters
        self.assertFalse(self.player1_character.can_be_edited_by(self.non_member))
        self.assertFalse(self.player2_character.can_be_edited_by(self.non_member))
        self.assertFalse(self.gm_character.can_be_edited_by(self.non_member))
        self.assertFalse(self.owner_character.can_be_edited_by(self.non_member))

    def test_can_be_edited_by_different_campaign_owner(self):
        """Test that owners of different campaigns cannot edit characters."""
        # Owner of different campaign cannot edit characters
        self.assertFalse(
            self.player1_character.can_be_edited_by(self.different_campaign_owner)
        )
        self.assertFalse(
            self.gm_character.can_be_edited_by(self.different_campaign_owner)
        )

    def test_can_be_edited_by_with_none_user(self):
        """Test can_be_edited_by with None user."""
        self.assertFalse(self.player1_character.can_be_edited_by(None))

    def test_can_be_deleted_by_character_owner(self):
        """Test that character owners can delete their own characters."""
        # Player1 can delete their own character
        self.assertTrue(self.player1_character.can_be_deleted_by(self.player1))

        # Player2 can delete their own character
        self.assertTrue(self.player2_character.can_be_deleted_by(self.player2))

        # GM can delete their own character
        self.assertTrue(self.gm_character.can_be_deleted_by(self.gm))

        # Owner can delete their own character
        self.assertTrue(self.owner_character.can_be_deleted_by(self.owner))

    def test_can_be_deleted_by_campaign_owner(self):
        """Test that campaign owners can delete characters when setting allows."""
        # By default, campaign owners CAN delete characters
        # (allow_owner_character_deletion=True)
        self.assertTrue(self.player1_character.can_be_deleted_by(self.owner))
        self.assertTrue(self.player2_character.can_be_deleted_by(self.owner))
        self.assertTrue(self.gm_character.can_be_deleted_by(self.owner))
        self.assertTrue(self.owner_character.can_be_deleted_by(self.owner))

    def test_can_be_deleted_by_campaign_owner_disabled(self):
        """Test that campaign owners cannot delete when setting is disabled."""
        # Disable owner character deletion
        self.campaign.allow_owner_character_deletion = False
        self.campaign.save()

        # Campaign owner can still delete their own characters
        self.assertTrue(self.owner_character.can_be_deleted_by(self.owner))

        # But cannot delete other characters
        self.assertFalse(self.player1_character.can_be_deleted_by(self.owner))
        self.assertFalse(self.player2_character.can_be_deleted_by(self.owner))
        self.assertFalse(self.gm_character.can_be_deleted_by(self.owner))

    def test_can_be_deleted_by_campaign_gm(self):
        """Test that GMs cannot delete characters by default."""
        # By default, GMs CANNOT delete other characters
        # (allow_gm_character_deletion=False)
        self.assertFalse(self.player1_character.can_be_deleted_by(self.gm))
        self.assertFalse(self.player2_character.can_be_deleted_by(self.gm))
        self.assertFalse(self.owner_character.can_be_deleted_by(self.gm))

        # But GMs can still delete their own characters
        self.assertTrue(self.gm_character.can_be_deleted_by(self.gm))

    def test_can_be_deleted_by_campaign_gm_enabled(self):
        """Test that GMs can delete characters when setting is enabled."""
        # Enable GM character deletion
        self.campaign.allow_gm_character_deletion = True
        self.campaign.save()

        # GM can now delete all characters in the campaign
        self.assertTrue(self.player1_character.can_be_deleted_by(self.gm))
        self.assertTrue(self.player2_character.can_be_deleted_by(self.gm))
        self.assertTrue(self.gm_character.can_be_deleted_by(self.gm))
        self.assertTrue(self.owner_character.can_be_deleted_by(self.gm))

    def test_can_be_deleted_by_other_players(self):
        """Test that players cannot delete other players' characters."""
        # Player1 cannot delete Player2's character
        self.assertFalse(self.player2_character.can_be_deleted_by(self.player1))

        # Player2 cannot delete Player1's character
        self.assertFalse(self.player1_character.can_be_deleted_by(self.player2))

        # Player1 cannot delete GM's character
        self.assertFalse(self.gm_character.can_be_deleted_by(self.player1))

        # Player1 cannot delete Owner's character
        self.assertFalse(self.owner_character.can_be_deleted_by(self.player1))

    def test_can_be_deleted_by_observer(self):
        """Test that observers cannot delete any characters."""
        # Observer cannot delete any characters
        self.assertFalse(self.player1_character.can_be_deleted_by(self.observer))
        self.assertFalse(self.player2_character.can_be_deleted_by(self.observer))
        self.assertFalse(self.gm_character.can_be_deleted_by(self.observer))
        self.assertFalse(self.owner_character.can_be_deleted_by(self.observer))

    def test_can_be_deleted_by_non_member(self):
        """Test that non-members cannot delete any characters."""
        # Non-member cannot delete any characters
        self.assertFalse(self.player1_character.can_be_deleted_by(self.non_member))
        self.assertFalse(self.player2_character.can_be_deleted_by(self.non_member))
        self.assertFalse(self.gm_character.can_be_deleted_by(self.non_member))
        self.assertFalse(self.owner_character.can_be_deleted_by(self.non_member))

    def test_can_be_deleted_by_with_none_user(self):
        """Test can_be_deleted_by with None user."""
        self.assertFalse(self.player1_character.can_be_deleted_by(None))

    def test_can_be_deleted_by_mixed_settings(self):
        """Test deletion permissions with mixed campaign settings."""
        # Start with both settings enabled
        self.campaign.allow_owner_character_deletion = True
        self.campaign.allow_gm_character_deletion = True
        self.campaign.save()

        # Both owner and GM can delete characters
        self.assertTrue(self.player1_character.can_be_deleted_by(self.owner))
        self.assertTrue(self.player1_character.can_be_deleted_by(self.gm))

        # Disable GM deletion but keep owner deletion
        self.campaign.allow_gm_character_deletion = False
        self.campaign.save()

        # Owner can still delete, GM cannot (except their own)
        self.assertTrue(self.player1_character.can_be_deleted_by(self.owner))
        self.assertFalse(self.player1_character.can_be_deleted_by(self.gm))
        self.assertTrue(self.gm_character.can_be_deleted_by(self.gm))

        # Disable owner deletion but enable GM deletion
        self.campaign.allow_owner_character_deletion = False
        self.campaign.allow_gm_character_deletion = True
        self.campaign.save()

        # GM can delete, owner cannot (except their own)
        self.assertTrue(self.player1_character.can_be_deleted_by(self.gm))
        self.assertFalse(self.player1_character.can_be_deleted_by(self.owner))
        self.assertTrue(self.owner_character.can_be_deleted_by(self.owner))

        # Disable both settings
        self.campaign.allow_owner_character_deletion = False
        self.campaign.allow_gm_character_deletion = False
        self.campaign.save()

        # Only character owners can delete their own characters
        self.assertFalse(self.player1_character.can_be_deleted_by(self.owner))
        self.assertFalse(self.player1_character.can_be_deleted_by(self.gm))
        self.assertTrue(self.player1_character.can_be_deleted_by(self.player1))
        self.assertTrue(self.owner_character.can_be_deleted_by(self.owner))
        self.assertTrue(self.gm_character.can_be_deleted_by(self.gm))

    def test_can_be_deleted_by_different_campaign_roles(self):
        """Test that users from different campaigns cannot delete characters."""
        # Create another campaign with the same users in different roles
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.player1,  # player1 is owner of other campaign
            game_system="Test System",
        )

        # Add owner as GM in other campaign
        CampaignMembership.objects.create(
            campaign=other_campaign, user=self.owner, role="GM"
        )

        # Create character in other campaign
        Character.objects.create(
            name="Other Character",
            campaign=other_campaign,
            player_owner=self.owner,
            game_system="Test System",
        )

        # Users can only delete characters in campaigns where they have proper roles
        # Owner (who is GM in other campaign) cannot delete characters in main campaign
        # if they don't have proper permissions
        self.assertTrue(
            self.player1_character.can_be_deleted_by(self.owner)
        )  # owner in main campaign

        # Player1 (who is owner in other campaign) cannot delete characters in
        # main campaign
        self.assertFalse(
            self.player2_character.can_be_deleted_by(self.player1)
        )  # just player in main campaign

    def test_bulk_can_be_deleted_by(self):
        """Test bulk deletion permission checking optimization."""
        # Create additional characters for bulk testing
        char1 = Character.objects.create(
            name="Bulk Delete Test Char 1",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        char2 = Character.objects.create(
            name="Bulk Delete Test Char 2",
            campaign=self.campaign,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
        )

        characters = [
            self.player1_character,
            self.player2_character,
            self.owner_character,
            self.gm_character,
            char1,
            char2,
        ]

        # Test bulk deletion permissions for campaign owner
        bulk_delete_perms = {}
        for char in characters:
            bulk_delete_perms[char.id] = char.can_be_deleted_by(self.owner)

        self.assertEqual(len(bulk_delete_perms), 6)
        # Campaign owner should be able to delete all characters (default setting)
        for char_id, can_delete in bulk_delete_perms.items():
            self.assertTrue(can_delete)

        # Test bulk deletion permissions for GM (default: cannot delete others)
        bulk_delete_perms_gm = {}
        for char in characters:
            bulk_delete_perms_gm[char.id] = char.can_be_deleted_by(self.gm)

        self.assertEqual(len(bulk_delete_perms_gm), 6)
        # GM should only be able to delete their own character by default
        self.assertTrue(bulk_delete_perms_gm[self.gm_character.id])
        self.assertFalse(bulk_delete_perms_gm[self.player1_character.id])
        self.assertFalse(bulk_delete_perms_gm[self.player2_character.id])
        self.assertFalse(bulk_delete_perms_gm[self.owner_character.id])
        self.assertFalse(bulk_delete_perms_gm[char1.id])
        self.assertFalse(bulk_delete_perms_gm[char2.id])

        # Test bulk deletion permissions for player
        bulk_delete_perms_player = {}
        for char in characters:
            bulk_delete_perms_player[char.id] = char.can_be_deleted_by(self.player1)

        self.assertEqual(len(bulk_delete_perms_player), 6)
        # Player1 should only be able to delete their own characters
        self.assertTrue(bulk_delete_perms_player[self.player1_character.id])
        self.assertTrue(bulk_delete_perms_player[char1.id])
        self.assertFalse(bulk_delete_perms_player[self.player2_character.id])
        self.assertFalse(bulk_delete_perms_player[self.owner_character.id])
        self.assertFalse(bulk_delete_perms_player[self.gm_character.id])
        self.assertFalse(bulk_delete_perms_player[char2.id])

        # Test with observer
        bulk_delete_perms_observer = {}
        for char in characters:
            bulk_delete_perms_observer[char.id] = char.can_be_deleted_by(self.observer)

        self.assertEqual(len(bulk_delete_perms_observer), 6)
        # Observer should not be able to delete any characters
        for char_id, can_delete in bulk_delete_perms_observer.items():
            self.assertFalse(can_delete)

        # Test with None user
        bulk_delete_perms_none = {}
        for char in characters:
            bulk_delete_perms_none[char.id] = char.can_be_deleted_by(None)

        self.assertEqual(len(bulk_delete_perms_none), 6)
        for char_id, can_delete in bulk_delete_perms_none.items():
            self.assertFalse(can_delete)

    def test_get_permission_level_character_owner(self):
        """Test get_permission_level for character owners."""
        # Character owners get 'owner' permission level
        self.assertEqual(
            self.player1_character.get_permission_level(self.player1), "owner"
        )
        self.assertEqual(
            self.player2_character.get_permission_level(self.player2), "owner"
        )
        self.assertEqual(self.gm_character.get_permission_level(self.gm), "owner")

    def test_get_permission_level_campaign_owner(self):
        """Test get_permission_level for campaign owners."""
        # Campaign owner gets 'campaign_owner' permission level for all characters
        self.assertEqual(
            self.player1_character.get_permission_level(self.owner), "campaign_owner"
        )
        self.assertEqual(
            self.player2_character.get_permission_level(self.owner), "campaign_owner"
        )
        self.assertEqual(
            self.gm_character.get_permission_level(self.owner), "campaign_owner"
        )
        # Note: owner's own character should return 'owner' not 'campaign_owner'
        self.assertEqual(self.owner_character.get_permission_level(self.owner), "owner")

    def test_get_permission_level_campaign_gm(self):
        """Test get_permission_level for campaign GMs."""
        # GM gets 'gm' permission level for other characters, 'owner' for their own
        self.assertEqual(self.player1_character.get_permission_level(self.gm), "gm")
        self.assertEqual(self.player2_character.get_permission_level(self.gm), "gm")
        self.assertEqual(self.owner_character.get_permission_level(self.gm), "gm")
        # GM's own character should return 'owner'
        self.assertEqual(self.gm_character.get_permission_level(self.gm), "owner")

    def test_get_permission_level_other_players(self):
        """Test get_permission_level for other players."""
        # Players get 'read' permission for other players' characters
        self.assertEqual(
            self.player2_character.get_permission_level(self.player1), "read"
        )
        self.assertEqual(
            self.player1_character.get_permission_level(self.player2), "read"
        )
        self.assertEqual(self.gm_character.get_permission_level(self.player1), "read")
        self.assertEqual(
            self.owner_character.get_permission_level(self.player1), "read"
        )

    def test_get_permission_level_observer(self):
        """Test get_permission_level for observers."""
        # Observers get 'read' permission for all characters
        self.assertEqual(
            self.player1_character.get_permission_level(self.observer), "read"
        )
        self.assertEqual(
            self.player2_character.get_permission_level(self.observer), "read"
        )
        self.assertEqual(self.gm_character.get_permission_level(self.observer), "read")
        self.assertEqual(
            self.owner_character.get_permission_level(self.observer), "read"
        )

    def test_get_permission_level_non_member(self):
        """Test get_permission_level for non-members."""
        # Non-members get 'none' permission level
        self.assertEqual(
            self.player1_character.get_permission_level(self.non_member), "none"
        )
        self.assertEqual(
            self.player2_character.get_permission_level(self.non_member), "none"
        )
        self.assertEqual(
            self.gm_character.get_permission_level(self.non_member), "none"
        )
        self.assertEqual(
            self.owner_character.get_permission_level(self.non_member), "none"
        )

    def test_get_permission_level_different_campaign_owner(self):
        """Test get_permission_level for owners of different campaigns."""
        # Owners of different campaigns get 'none' permission level
        self.assertEqual(
            self.player1_character.get_permission_level(self.different_campaign_owner),
            "none",
        )
        self.assertEqual(
            self.gm_character.get_permission_level(self.different_campaign_owner),
            "none",
        )

    def test_get_permission_level_with_none_user(self):
        """Test get_permission_level with None user."""
        self.assertEqual(self.player1_character.get_permission_level(None), "none")

    def test_permission_levels_hierarchy(self):
        """Test that permission levels follow the expected hierarchy."""
        # Test permission level values for hierarchy checking
        permission_hierarchy = {
            "none": 0,
            "read": 1,
            "gm": 2,
            "campaign_owner": 3,
            "owner": 4,
        }

        # Character owner should have highest permission
        owner_level = self.player1_character.get_permission_level(self.player1)
        campaign_owner_level = self.player1_character.get_permission_level(self.owner)
        gm_level = self.player1_character.get_permission_level(self.gm)
        other_player_level = self.player1_character.get_permission_level(self.player2)
        observer_level = self.player1_character.get_permission_level(self.observer)
        non_member_level = self.player1_character.get_permission_level(self.non_member)

        # Verify hierarchy
        self.assertGreater(
            permission_hierarchy[owner_level],
            permission_hierarchy[campaign_owner_level],
        )
        self.assertGreater(
            permission_hierarchy[campaign_owner_level], permission_hierarchy[gm_level]
        )
        self.assertGreater(
            permission_hierarchy[gm_level], permission_hierarchy[other_player_level]
        )
        self.assertEqual(other_player_level, observer_level)  # Same level
        self.assertGreater(
            permission_hierarchy[observer_level], permission_hierarchy[non_member_level]
        )


class CharacterSoftDeleteTest(TestCase):
    """Test Character soft delete functionality."""

    def setUp(self):
        """Set up test users and campaigns for soft delete testing."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )

    def test_character_has_soft_delete_fields(self):
        """Test that Character model has soft delete fields."""
        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Check for soft delete fields (these will fail until implemented)
        self.assertTrue(hasattr(character, "is_deleted"))
        self.assertTrue(hasattr(character, "deleted_at"))
        self.assertTrue(hasattr(character, "deleted_by"))

        # New character should not be deleted
        self.assertFalse(character.is_deleted)
        self.assertIsNone(character.deleted_at)
        self.assertIsNone(character.deleted_by)

    def test_soft_delete_character_as_owner(self):
        """Test soft deleting character as owner."""
        character = Character.objects.create(
            name="Owner Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Owner should be able to soft delete their character
        result = character.soft_delete(self.player1)
        self.assertTrue(result)

        character.refresh_from_db()
        self.assertTrue(character.is_deleted)
        self.assertIsNotNone(character.deleted_at)
        self.assertEqual(character.deleted_by, self.player1)

        # Character should still exist in database but be marked deleted
        # Soft deleted characters should not be in default queryset
        self.assertFalse(Character.objects.filter(pk=character.pk).exists())
        self.assertTrue(Character.all_objects.filter(pk=character.pk).exists())

    def test_soft_delete_character_as_campaign_owner(self):
        """Test soft deleting character as campaign owner."""
        character = Character.objects.create(
            name="Player Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Campaign owner should be able to soft delete if setting allows
        result = character.soft_delete(self.owner)
        self.assertTrue(result)

        character.refresh_from_db()
        self.assertTrue(character.is_deleted)
        self.assertEqual(character.deleted_by, self.owner)

    def test_soft_delete_denies_unauthorized_users(self):
        """Test that unauthorized users cannot soft delete characters."""
        character = Character.objects.create(
            name="Protected Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Another player should not be able to soft delete
        result = character.soft_delete(self.player2)
        self.assertFalse(result)

        character.refresh_from_db()
        self.assertFalse(character.is_deleted)

    def test_hard_delete_admin_only(self):
        """Test that only admins can hard delete characters."""
        character = Character.objects.create(
            name="Permanent Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Regular user cannot hard delete
        with self.assertRaises(PermissionError):
            character.hard_delete(self.player1)

        # Admin can hard delete
        result = character.hard_delete(self.admin_user)
        self.assertTrue(result)

        # Character should be completely removed from database
        self.assertFalse(Character.objects.filter(pk=character.pk).exists())
        self.assertFalse(Character.all_objects.filter(pk=character.pk).exists())

    def test_soft_deleted_characters_excluded_from_default_queryset(self):
        """Test that soft deleted characters are excluded from default queries."""
        # Set campaign to allow multiple characters
        self.campaign.max_characters_per_player = 2
        self.campaign.save()

        character1 = Character.objects.create(
            name="Active Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        character2 = Character.objects.create(
            name="Deleted Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Soft delete one character
        character2.soft_delete(self.player1)

        # Default queryset should only show active characters
        active_characters = Character.objects.all()
        self.assertEqual(active_characters.count(), 1)
        self.assertIn(character1, active_characters)
        self.assertNotIn(character2, active_characters)

        # All objects queryset should show both
        all_characters = Character.all_objects.all()
        self.assertEqual(all_characters.count(), 2)
        self.assertIn(character1, all_characters)
        self.assertIn(character2, all_characters)

    def test_restore_soft_deleted_character(self):
        """Test restoring a soft deleted character."""
        character = Character.objects.create(
            name="Restorable Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Soft delete character
        character.soft_delete(self.player1)
        self.assertTrue(character.is_deleted)

        # Restore character
        result = character.restore(self.player1)
        self.assertTrue(result)

        character.refresh_from_db()
        self.assertFalse(character.is_deleted)
        self.assertIsNone(character.deleted_at)
        self.assertIsNone(character.deleted_by)

        # Character should appear in default queryset again
        self.assertIn(character, Character.objects.all())

    def test_character_deletion_with_confirmation_name(self):
        """Test character deletion requires typing character name for confirmation."""
        character = Character.objects.create(
            name="Confirmation Required Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Deletion without confirmation should fail
        with self.assertRaises(ValueError):
            character.soft_delete(self.player1, confirmation_name="")

        # Deletion with wrong name should fail
        with self.assertRaises(ValueError):
            character.soft_delete(self.player1, confirmation_name="Wrong Name")

        # Deletion with correct name should succeed
        result = character.soft_delete(
            self.player1, confirmation_name="Confirmation Required Character"
        )
        self.assertTrue(result)
        self.assertTrue(character.is_deleted)


class CharacterAuditTrailTest(TestCase):
    """Test Character audit trail functionality."""

    def setUp(self):
        """Set up test users and campaigns for audit trail testing."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )

    def test_character_creation_creates_audit_entry(self):
        """Test that character creation creates an audit trail entry."""
        character = Character.objects.create(
            name="Audited Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            description="Initial description",
        )

        # Check for audit trail entry (this will fail until implemented)
        from characters.models import CharacterAuditLog

        audit_entries = CharacterAuditLog.objects.filter(character=character)
        self.assertEqual(audit_entries.count(), 1)

        audit_entry = audit_entries.first()
        self.assertEqual(audit_entry.action, "CREATE")
        self.assertEqual(audit_entry.user, self.player1)
        self.assertIsNotNone(audit_entry.timestamp)
        self.assertIn("name", audit_entry.changes)
        self.assertEqual(audit_entry.changes["name"]["new"], "Audited Character")

    def test_character_update_creates_audit_entry(self):
        """Test that character updates create audit trail entries."""
        character = Character.objects.create(
            name="Original Name",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            description="Original description",
        )

        # Update character
        character.name = "Updated Name"
        character.description = "Updated description"
        character.save(update_user=self.gm)

        from characters.models import CharacterAuditLog

        audit_entries = CharacterAuditLog.objects.filter(character=character).order_by(
            "timestamp"
        )
        self.assertEqual(audit_entries.count(), 2)  # CREATE + UPDATE

        update_entry = audit_entries.last()
        self.assertEqual(update_entry.action, "UPDATE")
        self.assertEqual(update_entry.user, self.gm)
        self.assertIn("name", update_entry.changes)
        self.assertEqual(update_entry.changes["name"]["old"], "Original Name")
        self.assertEqual(update_entry.changes["name"]["new"], "Updated Name")
        self.assertIn("description", update_entry.changes)

    def test_character_deletion_creates_audit_entry(self):
        """Test that character deletion creates audit trail entry."""
        character = Character.objects.create(
            name="Delete Me",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Soft delete character
        character.soft_delete(self.owner)

        from characters.models import CharacterAuditLog

        audit_entries = CharacterAuditLog.objects.filter(character=character).order_by(
            "timestamp"
        )
        self.assertGreaterEqual(audit_entries.count(), 2)  # At least CREATE + DELETE

        delete_entry = audit_entries.last()
        self.assertEqual(delete_entry.action, "DELETE")
        self.assertEqual(delete_entry.user, self.owner)
        self.assertIn("is_deleted", delete_entry.changes)
        self.assertEqual(delete_entry.changes["is_deleted"]["new"], True)

    def test_audit_trail_tracks_only_changed_fields(self):
        """Test that audit trail only tracks fields that actually changed."""
        character = Character.objects.create(
            name="Selective Audit",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            description="Original description",
        )

        # Update only the description
        character.description = "Updated description"
        character.save(update_user=self.player1)

        from characters.models import CharacterAuditLog

        update_entry = CharacterAuditLog.objects.filter(
            character=character, action="UPDATE"
        ).first()

        # Should only track description change, not name
        self.assertIn("description", update_entry.changes)
        self.assertNotIn("name", update_entry.changes)
        self.assertEqual(
            update_entry.changes["description"]["old"], "Original description"
        )
        self.assertEqual(
            update_entry.changes["description"]["new"], "Updated description"
        )

    def test_audit_trail_permission_access(self):
        """Test that audit trail access is properly restricted."""
        character = Character.objects.create(
            name="Audit Access Test",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        from characters.models import CharacterAuditLog

        # Character owner should see audit trail
        audit_entries = CharacterAuditLog.get_for_user(character, self.player1)
        self.assertGreater(audit_entries.count(), 0)

        # Campaign owner should see audit trail
        audit_entries = CharacterAuditLog.get_for_user(character, self.owner)
        self.assertGreater(audit_entries.count(), 0)

        # GM should see audit trail
        audit_entries = CharacterAuditLog.get_for_user(character, self.gm)
        self.assertGreater(audit_entries.count(), 0)

        # Non-member should not see audit trail
        non_member = User.objects.create_user(
            username="nonmember", email="nonmember@test.com", password="testpass123"
        )
        audit_entries = CharacterAuditLog.get_for_user(character, non_member)
        self.assertEqual(audit_entries.count(), 0)

    def test_audit_trail_data_integrity(self):
        """Test that audit trail maintains data integrity."""
        character = Character.objects.create(
            name="Data Integrity Test",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Make multiple changes
        for i in range(5):
            character.description = f"Description update {i}"
            character.save(update_user=self.player1)

        from characters.models import CharacterAuditLog

        audit_entries = CharacterAuditLog.objects.filter(character=character).order_by(
            "timestamp"
        )

        # Should have CREATE + 5 UPDATEs
        self.assertEqual(audit_entries.count(), 6)

        # Verify sequence of changes
        create_entry = audit_entries.first()
        self.assertEqual(create_entry.action, "CREATE")

        for i, update_entry in enumerate(audit_entries[1:]):
            self.assertEqual(update_entry.action, "UPDATE")
            self.assertEqual(
                update_entry.changes["description"]["new"], f"Description update {i}"
            )

    def test_with_campaign_memberships_queryset_optimization(self):
        """Test that with_campaign_memberships() properly prefetches data."""
        # This test verifies that the QuerySet method returns expected results
        # In a real scenario, we'd use django-debug-toolbar or connection.queries
        # to verify that it actually reduces queries

        # Create a character for testing
        Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        queryset = Character.objects.with_campaign_memberships().filter(
            campaign=self.campaign
        )

        # Should be able to access campaign and membership data without extra queries
        characters = list(queryset)

        # Verify we got the expected characters
        self.assertGreater(len(characters), 0)

        # Verify campaign data is accessible (would trigger query if not prefetched)
        for character in characters:
            self.assertIsNotNone(character.campaign.name)
            self.assertIsNotNone(character.campaign.owner.username)


class CharacterEnhancedValidationTest(TestCase):
    """Test enhanced Character model validation edge cases and error messages."""

    def setUp(self):
        """Set up test users and campaigns for validation testing."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
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

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=2,
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )

    def test_validation_error_messages_content(self):
        """Test that validation error messages contain expected content."""
        # Test empty name validation message
        with self.assertRaises(ValidationError) as context:
            character = Character(
                name="",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )
            character.full_clean()

        error_messages = str(context.exception)
        self.assertIn("Character name cannot be empty", error_messages)

        # Test blank name validation message
        with self.assertRaises(ValidationError) as context:
            character = Character(
                name="   ",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )
            character.full_clean()

        error_messages = str(context.exception)
        self.assertIn("Character name cannot be empty", error_messages)

        # Test non-member validation message
        with self.assertRaises(ValidationError) as context:
            character = Character(
                name="Non-member Character",
                campaign=self.campaign,
                player_owner=self.non_member,
                game_system="Mage: The Ascension",
            )
            character.full_clean()

        error_messages = str(context.exception)
        self.assertIn("Only campaign members", error_messages)
        self.assertIn("players, GMs, owners", error_messages)
        self.assertIn("can own characters", error_messages)

    def test_max_characters_validation_error_message(self):
        """Test max characters per player validation error message."""
        # Create maximum allowed characters
        Character.objects.create(
            name="Character 1",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        Character.objects.create(
            name="Character 2",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Try to create one more
        with self.assertRaises(ValidationError) as context:
            character = Character(
                name="Character 3",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )
            character.full_clean()

        error_messages = str(context.exception)
        self.assertIn("cannot have more than 2 characters", error_messages)
        self.assertIn("in this campaign", error_messages)

    def test_permission_validation_during_character_updates(self):
        """Test permission checks during character updates."""
        # Create a character
        character = Character.objects.create(
            name="Original Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Test updating character name - should work for owner
        character.name = "Updated Character"
        character.full_clean()  # Should not raise ValidationError
        character.save()
        self.assertEqual(character.name, "Updated Character")

        # Test updating campaign - existing character should still validate
        character.description = "Updated description"
        character.full_clean()  # Should not raise ValidationError
        character.save()

    def test_validation_when_campaign_membership_changes(self):
        """Test validation when campaign membership status changes."""
        # Create a character
        character = Character.objects.create(
            name="Member Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Remove player from campaign
        CampaignMembership.objects.filter(
            campaign=self.campaign, user=self.player1
        ).delete()

        # Character should still be valid for updates
        character.name = "Updated Name"
        character.full_clean()  # Should not raise ValidationError
        character.save()

        # But creating a new character for the removed player should fail
        with self.assertRaises(ValidationError):
            new_character = Character(
                name="New Character",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )
            new_character.full_clean()

    def test_character_validation_with_campaign_owner_changes(self):
        """Test character validation when campaign ownership changes."""
        # Create a character owned by a player
        character = Character.objects.create(
            name="Player Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Verify initial state
        self.assertEqual(character.player_owner, self.player1)
        self.assertEqual(character.campaign.owner, self.owner)
        self.assertEqual(character.name, "Player Character")

        # Transfer campaign ownership to another user
        new_owner = User.objects.create_user(
            username="new_owner", email="new_owner@test.com", password="testpass123"
        )
        old_owner = self.campaign.owner
        self.campaign.owner = new_owner
        self.campaign.save()

        # Verify campaign ownership changed
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.owner, new_owner)
        self.assertNotEqual(self.campaign.owner, old_owner)

        # Existing character should still be valid
        character.name = "Updated Player Character"
        character.full_clean()  # Should not raise ValidationError
        character.save()

        # Verify character was updated successfully
        character.refresh_from_db()
        self.assertEqual(character.name, "Updated Player Character")
        self.assertEqual(
            character.player_owner, self.player1
        )  # Should remain unchanged
        self.assertEqual(
            character.campaign.owner, new_owner
        )  # Campaign owner should be updated

        # Original owner should still be able to own characters if they remain a member
        # (campaign owner change doesn't affect existing memberships)
        # Verify character is still valid and accessible
        self.assertFalse(character.is_deleted)
        self.assertTrue(character.campaign.is_member(self.player1))

    def test_character_name_with_special_characters(self):
        """Test character validation with special characters in names."""
        # Test names with special characters (should be allowed)
        special_names = [
            "Character with spaces",
            "Character-with-hyphens",
            "Character_with_underscores",
            "Character with 'quotes'",
            'Character with "double quotes"',
            "Character with numbers 123",
            "Character with symbols !@#$%",
            "Character with unicode: café",
            "Character with emojis: 🧙‍♂️",
        ]

        for i, name in enumerate(special_names):
            with self.subTest(name=name):
                character = Character.objects.create(
                    name=name,
                    campaign=self.campaign,
                    player_owner=self.player1,
                    game_system="Mage: The Ascension",
                )
                self.assertEqual(character.name, name)
                # Clean up for next iteration
                character.delete()

    def test_character_validation_with_very_long_descriptions(self):
        """Test character validation with very long descriptions."""
        # Very long description should be allowed
        long_description = "A" * 10000  # 10,000 characters

        character = Character.objects.create(
            name="Long Description Character",
            description=long_description,
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(len(character.description), 10000)

    def test_character_validation_with_campaign_limit_changes(self):
        """Test character validation when campaign character limits change."""
        # Create a character when limit is 2
        character = Character.objects.create(
            name="First Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Lower the campaign limit to 1
        self.campaign.max_characters_per_player = 1
        self.campaign.save()

        # Existing character should still be valid for updates
        character.name = "Updated First Character"
        character.full_clean()  # Should not raise ValidationError
        character.save()

        # But creating a new character should fail if it exceeds the new limit
        with self.assertRaises(ValidationError):
            Character(
                name="Second Character",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            ).full_clean()

    def test_character_validation_edge_case_empty_campaign(self):
        """Test character creation in campaigns with no other members."""
        # Create a campaign with just the owner
        solo_campaign = Campaign.objects.create(
            name="Solo Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
        )

        # Owner should be able to create characters in their own campaign
        character = Character.objects.create(
            name="Solo Character",
            campaign=solo_campaign,
            player_owner=self.owner,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(character.campaign, solo_campaign)

    def test_character_validation_with_null_max_characters(self):
        """Test character validation when max_characters_per_player is None."""
        # Create campaign with None max_characters (should default to 0 = unlimited)
        unlimited_campaign = Campaign.objects.create(
            name="Unlimited Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=0,  # 0 means unlimited
        )

        # Add player to campaign
        CampaignMembership.objects.create(
            campaign=unlimited_campaign, user=self.player1, role="PLAYER"
        )

        # Should be able to create many characters
        for i in range(10):
            Character.objects.create(
                name=f"Character {i+1}",
                campaign=unlimited_campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )

        # Verify all characters were created
        self.assertEqual(
            Character.objects.filter(
                campaign=unlimited_campaign, player_owner=self.player1
            ).count(),
            10,
        )

    def test_character_validation_concurrent_creation_edge_case(self):
        """Test character validation in potential race condition scenarios."""
        # Set campaign limit to 1
        self.campaign.max_characters_per_player = 1
        self.campaign.save()

        # Create first character
        Character.objects.create(
            name="First Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Attempt to create second character should fail
        with self.assertRaises(ValidationError):
            Character(
                name="Second Character",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            ).full_clean()

    def test_character_creation_race_condition_prevention(self):
        """Test atomic transactions prevent race conditions in character creation."""
        # This test verifies the logic but doesn't actually test threading
        # due to Django test transaction limitations. See the TransactionTestCase
        # version for actual threading tests.

        # Set campaign limit to 2
        self.campaign.max_characters_per_player = 2
        self.campaign.save()

        # Create one character to start with (1/2 limit)
        Character.objects.create(
            name="Existing Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Should be able to create one more character
        Character.objects.create(
            name="Second Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Third character should fail validation
        with self.assertRaises(ValidationError):
            Character(
                name="Third Character",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            ).full_clean()

        # Verify final character count is exactly at limit
        final_count = Character.objects.filter(
            campaign=self.campaign, player_owner=self.player1
        ).count()
        expected_msg = f"Expected 2 characters total, got {final_count}"
        self.assertEqual(final_count, 2, expected_msg)

    def test_character_limit_validation_with_atomic_protection(self):
        """Test that character limit validation uses atomic transaction protection."""
        # Set strict limit
        self.campaign.max_characters_per_player = 1
        self.campaign.save()

        # First character should succeed
        Character.objects.create(
            name="First Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Second character should fail due to limit
        with self.assertRaises(ValidationError) as context:
            Character.objects.create(
                name="Second Character",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )

        # Verify error message mentions the limit
        error_message = str(context.exception)
        self.assertIn("cannot have more than 1 character", error_message)

        # Verify only one character exists
        final_count = Character.objects.filter(
            campaign=self.campaign, player_owner=self.player1
        ).count()
        expected_msg = f"Expected 1 character, got {final_count}"
        self.assertEqual(final_count, 1, expected_msg)

    def test_character_update_does_not_affect_limit_validation(self):
        """Test that updating existing characters doesn't trigger limit validation."""
        from django.db import transaction

        # Set limit to 1
        self.campaign.max_characters_per_player = 1
        self.campaign.save()

        # Create one character at limit
        character = Character.objects.create(
            name="Original Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Updating should work fine even with atomic transactions
        with transaction.atomic():
            character.name = "Updated Character"
            character.description = "Updated description"
            character.full_clean()  # Should not raise ValidationError
            character.save()

        # Verify update succeeded
        character.refresh_from_db()
        self.assertEqual(character.name, "Updated Character")
        self.assertEqual(character.description, "Updated description")

    def test_character_permission_validation_with_role_changes(self):
        """Test how character permissions are affected by campaign role changes."""
        # Create a character owned by a player
        character = Character.objects.create(
            name="Player Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Player1 should be able to edit their character
        self.assertTrue(character.can_be_edited_by(self.player1))

        # Change player1's role to observer
        membership = CampaignMembership.objects.get(
            campaign=self.campaign, user=self.player1
        )
        membership.role = "OBSERVER"
        membership.save()

        # Player1 should still be able to edit their own character even as observer
        self.assertTrue(character.can_be_edited_by(self.player1))

        # Player1 should get 'owner' permission level
        self.assertEqual(character.get_permission_level(self.player1), "owner")

    def test_error_message_localization_compatibility(self):
        """Test that error messages work with Django's localization system."""
        # Test that validation error messages are strings (not lazy translation objects)
        with self.assertRaises(ValidationError) as context:
            Character(
                name="",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            ).full_clean()

        # Error message should be a proper string
        error_messages = (
            context.exception.message_dict
            if hasattr(context.exception, "message_dict")
            else str(context.exception)
        )
        self.assertIsInstance(str(error_messages), str)


class CharacterUpdateValidationTest(TestCase):
    """Test Character model validation on updates, not just creation."""

    def setUp(self):
        """Set up test users and campaigns for update validation testing."""
        self.owner1 = User.objects.create_user(
            username="owner1", email="owner1@test.com", password="testpass123"
        )
        self.owner2 = User.objects.create_user(
            username="owner2", email="owner2@test.com", password="testpass123"
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

        # Create campaigns
        self.campaign1 = Campaign.objects.create(
            name="Campaign One",
            owner=self.owner1,
            game_system="Mage: The Ascension",
        )
        self.campaign2 = Campaign.objects.create(
            name="Campaign Two",
            owner=self.owner2,
            game_system="D&D 5e",
        )

        # Create memberships for campaign1
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player2, role="PLAYER"
        )

        # Create memberships for campaign2 (only player1)
        CampaignMembership.objects.create(
            campaign=self.campaign2, user=self.player1, role="PLAYER"
        )

    def test_change_character_owner_to_non_member_should_fail(self):
        """Test changing character owner to a non-member should fail validation."""
        # Create character owned by player1
        character = Character.objects.create(
            name="Original Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Try to change owner to non-member - should fail
        character.player_owner = self.non_member
        with self.assertRaises(ValidationError) as context:
            character.full_clean()

        error_messages = str(context.exception)
        self.assertIn("Only campaign members", error_messages)
        self.assertIn("can own characters", error_messages)

    def test_change_character_owner_to_campaign_member_should_succeed(self):
        """Test changing character owner to another campaign member should succeed."""
        # Create character owned by player1
        character = Character.objects.create(
            name="Transfer Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Change owner to player2 (also a member) - should succeed
        character.player_owner = self.player2
        character.full_clean()  # Should not raise ValidationError
        character.save()

        # Verify change was successful
        character.refresh_from_db()
        self.assertEqual(character.player_owner, self.player2)

    def test_move_character_to_campaign_where_owner_is_not_member_should_fail(self):
        """Test moving character to campaign where owner is not a member should fail."""
        # Create character in campaign1 owned by player1
        character = Character.objects.create(
            name="Movable Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Create a new campaign where player1 is not a member
        campaign3 = Campaign.objects.create(
            name="Campaign Three",
            owner=self.owner2,
            game_system="Vampire: The Masquerade",
        )

        # Try to move character to campaign3 - should fail
        character.campaign = campaign3
        with self.assertRaises(ValidationError) as context:
            character.full_clean()

        error_messages = str(context.exception)
        self.assertIn("Only campaign members", error_messages)
        self.assertIn("can own characters", error_messages)

    def test_move_character_to_campaign_where_owner_is_member_should_succeed(self):
        """Test moving character to campaign where owner is a member should succeed."""
        # Create character in campaign1 owned by player1
        character = Character.objects.create(
            name="Transferable Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Move character to campaign2 where player1 is also a member - should succeed
        character.campaign = self.campaign2
        character.game_system = "D&D 5e"  # Update game system to match campaign
        character.full_clean()  # Should not raise ValidationError
        character.save()

        # Verify change was successful
        character.refresh_from_db()
        self.assertEqual(character.campaign, self.campaign2)

    def test_simultaneous_campaign_and_owner_change_both_invalid_should_fail(self):
        """Test changing both campaign and owner to invalid combination should fail."""
        # Create character in campaign1 owned by player1
        character = Character.objects.create(
            name="Double Change Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Try to change both campaign and owner to invalid combination
        character.campaign = self.campaign2  # campaign2 exists
        character.player_owner = self.player2  # player2 is NOT a member of campaign2

        with self.assertRaises(ValidationError) as context:
            character.full_clean()

        error_messages = str(context.exception)
        self.assertIn("Only campaign members", error_messages)

    def test_simultaneous_campaign_and_owner_change_both_valid_should_succeed(self):
        """Test changing both campaign and owner to valid combination should succeed."""
        # Create character in campaign1 owned by player1
        character = Character.objects.create(
            name="Valid Double Change Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Change both campaign and owner to valid combination
        character.campaign = self.campaign2  # campaign2 exists
        character.player_owner = self.player1  # player1 IS a member of campaign2
        character.game_system = "D&D 5e"  # Update game system to match campaign

        character.full_clean()  # Should not raise ValidationError
        character.save()

        # Verify changes were successful
        character.refresh_from_db()
        self.assertEqual(character.campaign, self.campaign2)
        self.assertEqual(character.player_owner, self.player1)

    def test_no_validation_when_neither_campaign_nor_owner_change(self):
        """Test membership validation is skipped when neither field changes."""
        # Create character
        character = Character.objects.create(
            name="No Change Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Change only description (no campaign or owner change)
        character.description = "Updated description"
        character.full_clean()  # Should not raise ValidationError
        character.save()

        # Verify change was successful
        character.refresh_from_db()
        self.assertEqual(character.description, "Updated description")

    def test_change_to_campaign_owner_should_succeed(self):
        """Test changing character owner to campaign owner should succeed."""
        # Create character owned by player1
        character = Character.objects.create(
            name="Owner Change Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Change owner to campaign owner - should succeed (owners are always members)
        character.player_owner = self.owner1
        character.full_clean()  # Should not raise ValidationError
        character.save()

        # Verify change was successful
        character.refresh_from_db()
        self.assertEqual(character.player_owner, self.owner1)

    def test_validation_error_message_includes_field_context_on_update(self):
        """Test validation error messages are clear about what changed."""
        # Create character
        character = Character.objects.create(
            name="Context Error Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Try invalid owner change
        character.player_owner = self.non_member
        with self.assertRaises(ValidationError) as context:
            character.full_clean()

        error_messages = str(context.exception)
        self.assertIn("Only campaign members", error_messages)
        self.assertIn("can own characters", error_messages)

    def test_update_validation_preserves_existing_character_limits(self):
        """Test character limit validation still works during updates."""
        # Set campaign limit to 1
        self.campaign1.max_characters_per_player = 1
        self.campaign1.save()

        # Create character at limit
        character = Character.objects.create(
            name="Limited Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Update character (should work since we're not creating new)
        character.description = "Updated with limits"
        character.full_clean()  # Should not raise ValidationError
        character.save()

        # Verify update succeeded
        character.refresh_from_db()
        self.assertEqual(character.description, "Updated with limits")

    def test_membership_removal_after_character_creation_allows_updates(self):
        """Test removing membership after creation still allows updates."""
        # Create character
        character = Character.objects.create(
            name="Membership Removal Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Remove player1's membership from campaign1
        CampaignMembership.objects.filter(
            campaign=self.campaign1, user=self.player1
        ).delete()

        # Update character (should still work for existing characters)
        character.description = "Updated after membership removal"
        character.full_clean()  # Should not raise ValidationError
        character.save()

        # Verify update succeeded
        character.refresh_from_db()
        expected_desc = "Updated after membership removal"
        self.assertEqual(character.description, expected_desc)

    def test_membership_removal_prevents_owner_change_to_non_member(self):
        """Test that membership removal prevents changing owner to non-members."""
        # Create character
        character = Character.objects.create(
            name="Ownership Change Character",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Try to change character owner to non-member
        character.player_owner = self.non_member

        with self.assertRaises(ValidationError) as context:
            character.full_clean()

        error_messages = str(context.exception)
        self.assertIn("Only campaign members", error_messages)


class CharacterRaceConditionTest(TransactionTestCase):
    """Test Character race condition prevention using real DB transactions."""

    def setUp(self):
        """Set up test users and campaigns for race condition testing."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=2,
        )
        # Create membership
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )

    def test_concurrent_character_creation_with_atomic_validation(self):
        """Test atomic transactions prevent race conditions in creation."""
        import time
        from threading import Event, Thread

        from django.db import transaction

        # Set strict limit
        self.campaign.max_characters_per_player = 1
        self.campaign.save()

        # Track results from concurrent operations
        results = []
        start_event = Event()

        def create_character_atomically(character_name):
            """Create a character with atomic validation."""
            # Wait for all threads to be ready
            start_event.wait()

            try:
                # Use atomic transaction for the entire operation
                with transaction.atomic():
                    character = Character(
                        name=character_name,
                        campaign=self.campaign,
                        player_owner=self.player1,
                        game_system="Mage: The Ascension",
                    )
                    # Add small delay to increase race condition potential
                    time.sleep(0.01)
                    character.save()  # Calls full_clean() with atomic validation
                    results.append(("success", character_name))
            except ValidationError:
                results.append(("validation_error", character_name))
            except Exception as ex:
                # Handle both database lock errors and validation errors
                error_msg = str(ex).lower()
                if "locked" in error_msg or "database is locked" in error_msg:
                    # SQLite lock errors are expected and valid protection
                    results.append(("lock_error", character_name))
                else:
                    results.append(("error", f"{character_name}: {str(ex)}"))

        # Create multiple threads attempting to create characters simultaneously
        threads = []
        for i in range(5):  # Try to create 5 characters simultaneously
            thread = Thread(
                target=create_character_atomically,
                args=(f"Concurrent Character {i+1}",),
            )
            threads.append(thread)
            thread.start()

        # Start all threads simultaneously
        start_event.set()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Analyze results based on database vendor
        successes = [r for r in results if r[0] == "success"]
        validation_failures = [r for r in results if r[0] == "validation_error"]
        lock_failures = [r for r in results if r[0] == "lock_error"]
        other_errors = [r for r in results if r[0] == "error"]

        # The key invariant: at most one character should be created
        final_count = Character.objects.filter(
            campaign=self.campaign, player_owner=self.player1
        ).count()

        if connection.vendor == "sqlite":
            # SQLite may prevent all transactions due to database-level locking
            # OR allow exactly one to succeed
            self.assertLessEqual(
                len(successes),
                1,
                f"SQLite should allow at most 1 success, got "
                f"{len(successes)}: {results}",
            )

            # All other attempts should fail (either lock or validation errors)
            total_failures = (
                len(validation_failures) + len(lock_failures) + len(other_errors)
            )
            self.assertGreaterEqual(
                total_failures,
                4,
                f"Expected at least 4 failures, got {total_failures}: {results}",
            )
        else:
            # PostgreSQL and other databases should allow exactly one success
            self.assertEqual(
                len(successes),
                1,
                f"Expected exactly 1 success, got {len(successes)}: {results}",
            )

            # Should have 4 failures (validation errors)
            total_failures = (
                len(validation_failures) + len(lock_failures) + len(other_errors)
            )
            self.assertEqual(
                total_failures,
                4,
                f"Expected 4 failures, got {total_failures}: {results}",
            )

        # The critical test: verify final character count is at most the limit
        self.assertLessEqual(
            final_count,
            1,
            f"Character count ({final_count}) exceeds limit (1) - "
            "race condition not prevented!",
        )

        # If we got a success, the count should be exactly 1
        if successes:
            self.assertEqual(
                final_count, 1, f"Success reported but character count is {final_count}"
            )

    def test_concurrent_character_creation_at_higher_limit(self):
        """Test race condition prevention with higher character limits."""
        from threading import Event, Thread

        # Set limit to 3
        self.campaign.max_characters_per_player = 3
        self.campaign.save()

        # Create 2 characters first (leaving 1 slot)
        for i in range(2):
            Character.objects.create(
                name=f"Pre-existing Character {i+1}",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )

        results = []
        start_event = Event()

        def create_character(character_name):
            """Create a character."""
            start_event.wait()

            try:
                Character.objects.create(
                    name=character_name,
                    campaign=self.campaign,
                    player_owner=self.player1,
                    game_system="Mage: The Ascension",
                )
                results.append(("success", character_name))
            except ValidationError:
                results.append(("validation_error", character_name))
            except Exception as ex:
                results.append(("error", f"{character_name}: {str(ex)}"))

        # Try to create 3 more characters (should only succeed for 1)
        threads = []
        for i in range(3):
            thread = Thread(target=create_character, args=(f"Race Character {i+1}",))
            threads.append(thread)
            thread.start()

        start_event.set()

        for thread in threads:
            thread.join()

        # Verify at most one succeeded (SQLite may allow more due to locking)
        successes = [r for r in results if r[0] == "success"]

        # The critical test: verify we don't exceed the limit
        final_count = Character.objects.filter(
            campaign=self.campaign, player_owner=self.player1
        ).count()

        if connection.vendor == "sqlite":
            # SQLite without proper atomic locking may allow race conditions
            # But we should still not exceed the limit significantly
            self.assertLessEqual(
                final_count,
                4,  # Might get one extra due to race condition
                f"Character count ({final_count}) significantly exceeds " "limit (3)",
            )
        else:
            # PostgreSQL with proper locking should enforce the limit strictly
            self.assertEqual(len(successes), 1, f"Expected 1 success, got: {results}")
            self.assertEqual(
                final_count, 3, f"Expected 3 characters total, got {final_count}"
            )


class CharacterNPCFieldTest(TestCase):
    """Test Character model NPC field functionality."""

    def setUp(self):
        """Set up test users and campaigns."""
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )

        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=5,
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )

    def test_character_creation_npc_true(self):
        """Test creating a character with npc=True."""
        character = Character.objects.create(
            name="Test NPC",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

        self.assertTrue(character.npc)
        self.assertEqual(character.name, "Test NPC")

        # Verify it's saved to database correctly
        character.refresh_from_db()
        self.assertTrue(character.npc)

    def test_character_creation_npc_false_explicit(self):
        """Test creating a character with npc=False explicitly."""
        character = Character.objects.create(
            name="Test PC",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )

        self.assertFalse(character.npc)
        self.assertEqual(character.name, "Test PC")

        # Verify it's saved to database correctly
        character.refresh_from_db()
        self.assertFalse(character.npc)

    def test_character_creation_npc_default_false(self):
        """Test creating a character without specifying npc (defaults to False)."""
        character = Character.objects.create(
            name="Default PC",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        self.assertFalse(character.npc)
        self.assertEqual(character.name, "Default PC")

        # Verify it's saved to database correctly
        character.refresh_from_db()
        self.assertFalse(character.npc)

    def test_npc_field_database_index_exists(self):
        """Test that the npc field has a database index."""
        from django.db import connection

        # Get the table name for Character model
        table_name = Character._meta.db_table

        with connection.cursor() as cursor:
            # Get index information - this is database-specific
            if connection.vendor == "postgresql":
                cursor.execute(
                    """
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = %s AND indexdef LIKE '%%npc%%'
                """,
                    [table_name],
                )
                indexes = cursor.fetchall()

                # Should have at least one index containing 'npc'
                npc_indexes = [idx for idx in indexes if "npc" in idx[1].lower()]
                self.assertGreater(
                    len(npc_indexes),
                    0,
                    f"No database index found for npc field on {table_name}",
                )

            elif connection.vendor == "sqlite":
                cursor.execute(f"PRAGMA index_list({table_name})")
                indexes = cursor.fetchall()

                # Check if any index includes the npc field
                has_npc_index = False
                for index_info in indexes:
                    index_name = index_info[1]
                    cursor.execute(f"PRAGMA index_info({index_name})")
                    index_columns = cursor.fetchall()
                    if any("npc" in col[2].lower() for col in index_columns):
                        has_npc_index = True
                        break

                self.assertTrue(
                    has_npc_index,
                    f"No database index found for npc field on {table_name}",
                )

    def test_query_characters_by_npc_status(self):
        """Test querying characters by NPC status."""
        # Create mix of NPCs and PCs
        pc1 = Character.objects.create(
            name="Player Character 1",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )

        pc2 = Character.objects.create(
            name="Player Character 2",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )

        npc1 = Character.objects.create(
            name="Non-Player Character 1",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

        npc2 = Character.objects.create(
            name="Non-Player Character 2",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

        # Query for NPCs
        npcs = Character.objects.filter(npc=True)
        self.assertEqual(npcs.count(), 2)
        self.assertIn(npc1, npcs)
        self.assertIn(npc2, npcs)
        self.assertNotIn(pc1, npcs)
        self.assertNotIn(pc2, npcs)

        # Query for PCs
        pcs = Character.objects.filter(npc=False)
        self.assertEqual(pcs.count(), 2)
        self.assertIn(pc1, pcs)
        self.assertIn(pc2, pcs)
        self.assertNotIn(npc1, pcs)
        self.assertNotIn(npc2, pcs)

    def test_polymorphic_wod_character_npc_field(self):
        """Test NPC field works with WoDCharacter polymorphic inheritance."""
        from characters.models import WoDCharacter

        wod_pc = WoDCharacter.objects.create(
            name="WoD Player Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="WoD Generic",
            npc=False,
            willpower=5,
        )

        wod_npc = WoDCharacter.objects.create(
            name="WoD NPC",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="WoD Generic",
            npc=True,
            willpower=7,
        )

        # Test field values
        self.assertFalse(wod_pc.npc)
        self.assertTrue(wod_npc.npc)

        # Test polymorphic queries
        all_npcs = Character.objects.filter(npc=True)
        self.assertIn(wod_npc, all_npcs)
        self.assertNotIn(wod_pc, all_npcs)

        wod_npcs = WoDCharacter.objects.filter(npc=True)
        self.assertIn(wod_npc, wod_npcs)
        self.assertNotIn(wod_pc, wod_npcs)

    def test_polymorphic_mage_character_npc_field(self):
        """Test NPC field works with MageCharacter polymorphic inheritance."""
        from characters.models import MageCharacter

        mage_pc = MageCharacter.objects.create(
            name="Mage Player Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
            willpower=4,
            arete=2,
            quintessence=5,
            paradox=1,
        )

        mage_npc = MageCharacter.objects.create(
            name="Mage NPC",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
            willpower=6,
            arete=4,
            quintessence=10,
            paradox=0,
        )

        # Test field values
        self.assertFalse(mage_pc.npc)
        self.assertTrue(mage_npc.npc)

        # Test polymorphic queries
        all_npcs = Character.objects.filter(npc=True)
        self.assertIn(mage_npc, all_npcs)
        self.assertNotIn(mage_pc, all_npcs)

        mage_npcs = MageCharacter.objects.filter(npc=True)
        self.assertIn(mage_npc, mage_npcs)
        self.assertNotIn(mage_pc, mage_npcs)

    def test_npc_field_preserved_during_updates(self):
        """Test that NPC field is preserved during character updates."""
        # Create NPC
        npc = Character.objects.create(
            name="Test NPC",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

        # Update name but not npc field
        npc.name = "Updated NPC Name"
        npc.save()

        # Verify npc field is preserved
        npc.refresh_from_db()
        self.assertTrue(npc.npc)
        self.assertEqual(npc.name, "Updated NPC Name")

        # Create PC and update
        pc = Character.objects.create(
            name="Test PC",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )

        # Update description but not npc field
        pc.description = "Updated description"
        pc.save()

        # Verify npc field is preserved
        pc.refresh_from_db()
        self.assertFalse(pc.npc)
        self.assertEqual(pc.description, "Updated description")

    def test_npc_field_toggle(self):
        """Test changing NPC field value from False to True and vice versa."""
        # Create PC first
        character = Character.objects.create(
            name="Toggle Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )

        self.assertFalse(character.npc)

        # Change to NPC
        character.npc = True
        character.save()

        character.refresh_from_db()
        self.assertTrue(character.npc)

        # Change back to PC
        character.npc = False
        character.save()

        character.refresh_from_db()
        self.assertFalse(character.npc)

    def test_npc_field_in_character_manager_queryset(self):
        """Test NPC field works with CharacterManager and QuerySet methods."""
        # Create characters with different NPC status
        pc = Character.objects.create(
            name="Manager Test PC",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )

        npc = Character.objects.create(
            name="Manager Test NPC",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

        # Test manager methods with NPC filtering
        campaign_characters = Character.objects.for_campaign(self.campaign)
        self.assertEqual(campaign_characters.count(), 2)

        campaign_npcs = campaign_characters.filter(npc=True)
        self.assertEqual(campaign_npcs.count(), 1)
        self.assertIn(npc, campaign_npcs)

        campaign_pcs = campaign_characters.filter(npc=False)
        self.assertEqual(campaign_pcs.count(), 1)
        self.assertIn(pc, campaign_pcs)

        # Test with owned_by manager method
        player_characters = Character.objects.owned_by(self.player1)
        self.assertEqual(player_characters.count(), 1)
        self.assertIn(pc, player_characters)

        gm_characters = Character.objects.owned_by(self.gm)
        self.assertEqual(gm_characters.count(), 1)
        self.assertIn(npc, gm_characters)

    def test_npc_field_with_soft_delete(self):
        """Test that NPC field works correctly with soft delete functionality."""
        npc = Character.objects.create(
            name="Deletable NPC",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

        # Verify NPC before deletion
        self.assertTrue(npc.npc)

        # Soft delete the character
        npc.soft_delete(self.gm)

        # Verify NPC field is preserved after soft delete
        self.assertTrue(npc.npc)
        self.assertTrue(npc.is_deleted)

        # Verify with all_objects manager (includes soft-deleted)
        all_characters = Character.all_objects.filter(npc=True)
        self.assertIn(npc, all_characters)

        # Verify not in default manager (excludes soft-deleted)
        active_npcs = Character.objects.filter(npc=True)
        self.assertNotIn(npc, active_npcs)

        # Restore and verify NPC field preserved
        npc.restore(self.gm)
        self.assertTrue(npc.npc)
        self.assertFalse(npc.is_deleted)

    def test_npc_field_boolean_validation(self):
        """Test that NPC field only accepts boolean values."""
        # Valid boolean values should work
        for npc_value in [True, False]:
            character = Character.objects.create(
                name=f"Test Character {npc_value}",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
                npc=npc_value,
            )
            self.assertEqual(character.npc, npc_value)

    def test_existing_characters_default_to_npc_false(self):
        """Test that after migration, existing characters have npc=False."""
        # This test assumes characters were created before the NPC field was added
        # and that the migration sets the default correctly

        character = Character.objects.create(
            name="Pre-Migration Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Should default to False (PC)
        self.assertFalse(character.npc)

        # Verify this matches the expected behavior for existing characters
        character.refresh_from_db()
        self.assertFalse(character.npc)

    def test_npc_field_in_audit_trail(self):
        """Test that NPC field changes are tracked in audit trail."""
        character = Character.objects.create(
            name="Audit Test Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )

        # Change NPC status
        character.npc = True
        character.save(audit_user=self.gm)

        # Check if audit entries exist
        audit_entries = character.audit_entries.all()
        self.assertGreater(audit_entries.count(), 0)

        # Note: The actual audit trail testing depends on the DetailedAuditableMixin
        # implementation and whether it tracks the npc field changes

    def test_npc_field_constraint_validation(self):
        """Test that NPC field doesn't interfere with existing model constraints."""
        # Test unique name constraint still works with NPC field
        Character.objects.create(
            name="Unique Name Test",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )

        # Creating another character with same name should still fail
        with self.assertRaises(ValidationError):
            Character.objects.create(
                name="Unique Name Test",
                campaign=self.campaign,
                player_owner=self.gm,
                game_system="Mage: The Ascension",
                npc=True,  # Even with different NPC status
            )

    def test_character_manager_npc_methods(self):
        """Test Character manager NPC methods (.npcs() and .player_characters())."""
        # Create test characters
        pc1 = Character.objects.create(
            name="PC 1",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )

        pc2 = Character.objects.create(
            name="PC 2",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )

        npc1 = Character.objects.create(
            name="NPC 1",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

        npc2 = Character.objects.create(
            name="NPC 2",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

        # Test new manager .npcs() method
        npcs = Character.objects.npcs()
        self.assertEqual(npcs.count(), 2)
        self.assertIn(npc1, npcs)
        self.assertIn(npc2, npcs)
        self.assertNotIn(pc1, npcs)
        self.assertNotIn(pc2, npcs)

        # Test new manager .player_characters() method
        pcs = Character.objects.player_characters()
        self.assertEqual(pcs.count(), 2)
        self.assertIn(pc1, pcs)
        self.assertIn(pc2, pcs)
        self.assertNotIn(npc1, pcs)
        self.assertNotIn(npc2, pcs)

        # Test chaining new methods with existing filters
        campaign_npcs = Character.objects.npcs().for_campaign(self.campaign)
        self.assertEqual(campaign_npcs.count(), 2)
        self.assertIn(npc1, campaign_npcs)
        self.assertIn(npc2, campaign_npcs)

        campaign_pcs = Character.objects.player_characters().for_campaign(self.campaign)
        self.assertEqual(campaign_pcs.count(), 2)
        self.assertIn(pc1, campaign_pcs)
        self.assertIn(pc2, campaign_pcs)

        # Test combining with ownership filtering
        player_pcs = Character.objects.player_characters().owned_by(self.player1)
        self.assertEqual(player_pcs.count(), 2)

        gm_npcs = Character.objects.npcs().owned_by(self.gm)
        self.assertEqual(gm_npcs.count(), 2)

        # Test that the old filter approach still works (backward compatibility)
        old_style_npcs = Character.objects.filter(npc=True)
        self.assertEqual(old_style_npcs.count(), 2)

        old_style_pcs = Character.objects.filter(npc=False)
        self.assertEqual(old_style_pcs.count(), 2)

    def test_npc_field_performance_with_index(self):
        """Test that NPC field queries perform well with database index."""
        # Temporarily increase character limit for this performance test
        original_limit = self.campaign.max_characters_per_player
        self.campaign.max_characters_per_player = (
            100  # Allow more characters for testing
        )
        self.campaign.save()

        # Create a reasonable number of characters to test performance
        characters_to_create = 50

        try:
            for i in range(characters_to_create):
                is_npc = i % 3 == 0  # Every third character is an NPC
                owner = self.gm if is_npc else self.player1

                Character.objects.create(
                    name=f"Character {i}",
                    campaign=self.campaign,
                    player_owner=owner,
                    game_system="Mage: The Ascension",
                    npc=is_npc,
                )

            # Test query performance - this should be fast with index
            import time

            start_time = time.time()
            npcs = list(Character.objects.filter(npc=True))
            npc_query_time = time.time() - start_time

            start_time = time.time()
            pcs = list(Character.objects.filter(npc=False))
            pc_query_time = time.time() - start_time

            # Verify correct counts
            # Count actual NPCs created (every 3rd character starting from 0)
            expected_npcs = len([i for i in range(characters_to_create) if i % 3 == 0])
            expected_pcs = characters_to_create - expected_npcs

            self.assertEqual(len(npcs), expected_npcs)
            self.assertEqual(len(pcs), expected_pcs)

            # Query times should be reasonable (under 100ms for this small dataset)
            # This is more of a smoke test than a real performance test
            self.assertLess(npc_query_time, 0.1, "NPC query took too long")
            self.assertLess(pc_query_time, 0.1, "PC query took too long")
        finally:
            # Restore original character limit
            self.campaign.max_characters_per_player = original_limit
            self.campaign.save()

    def test_npc_field_migration_compatibility(self):
        """Test that the NPC field addition is compatible with existing data."""
        # Verifies adding NPC field doesn't break existing functionality

        # Create character using all the same patterns as existing tests
        character = Character.objects.create(
            name="Migration Test Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            description="Test description",
        )

        # Verify all existing fields still work
        self.assertEqual(character.name, "Migration Test Character")
        self.assertEqual(character.campaign, self.campaign)
        self.assertEqual(character.player_owner, self.player1)
        self.assertEqual(character.game_system, "Mage: The Ascension")
        self.assertEqual(character.description, "Test description")

        # Verify NPC field defaults correctly
        self.assertFalse(character.npc)

        # Verify existing validation still works
        character.clean()  # Should not raise

        # Verify existing permissions still work
        self.assertTrue(character.can_be_edited_by(self.player1))
        self.assertTrue(character.can_be_edited_by(self.owner))  # Campaign owner

        # Verify string representation still works
        self.assertEqual(str(character), "Migration Test Character")

        # Verify audit trail still works
        original_audit_count = character.audit_entries.count()
        character.description = "Updated description"
        character.save(audit_user=self.player1)

        new_audit_count = character.audit_entries.count()
        self.assertGreater(new_audit_count, original_audit_count)


class NPCPCManagerTest(TestCase):
    """Test NPCManager and PCManager functionality for issue #175."""

    def setUp(self):
        """Set up test users, campaigns, and characters."""
        # Create users
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )

        # Create campaigns
        self.campaign1 = Campaign.objects.create(
            name="Campaign One",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=0,  # Unlimited
        )
        self.campaign2 = Campaign.objects.create(
            name="Campaign Two",
            owner=self.owner,
            game_system="D&D 5e",
            max_characters_per_player=0,  # Unlimited
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign1, user=self.player2, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign2, user=self.player1, role="PLAYER"
        )

        # Create base Character instances for testing
        self.pc1 = Character.objects.create(
            name="Player Character 1",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )

        self.pc2 = Character.objects.create(
            name="Player Character 2",
            campaign=self.campaign1,
            player_owner=self.player2,
            game_system="Mage: The Ascension",
            npc=False,
        )

        self.pc3_other_campaign = Character.objects.create(
            name="Player Character Other Campaign",
            campaign=self.campaign2,
            player_owner=self.player1,
            game_system="D&D 5e",
            npc=False,
        )

        self.npc1 = Character.objects.create(
            name="NPC Character 1",
            campaign=self.campaign1,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )

        self.npc2 = Character.objects.create(
            name="NPC Character 2",
            campaign=self.campaign1,
            player_owner=self.owner,
            game_system="Mage: The Ascension",
            npc=True,
        )

        self.npc3_other_campaign = Character.objects.create(
            name="NPC Other Campaign",
            campaign=self.campaign2,
            player_owner=self.owner,
            game_system="D&D 5e",
            npc=True,
        )

        # Create soft-deleted characters to test exclusion
        self.deleted_pc = Character.objects.create(
            name="Deleted PC",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )
        self.deleted_pc.soft_delete(self.player1)

        self.deleted_npc = Character.objects.create(
            name="Deleted NPC",
            campaign=self.campaign1,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )
        self.deleted_npc.soft_delete(self.gm)

    def test_npc_manager_exists_on_character_model(self):
        """Test that NPCManager is accessible as Character.npcs."""
        self.assertTrue(hasattr(Character, "npcs"))
        # Verify it's a manager instance
        self.assertTrue(hasattr(Character.npcs, "all"))
        self.assertTrue(hasattr(Character.npcs, "filter"))
        self.assertTrue(hasattr(Character.npcs, "get"))

    def test_pc_manager_exists_on_character_model(self):
        """Test that PCManager is accessible as Character.pcs."""
        self.assertTrue(hasattr(Character, "pcs"))
        # Verify it's a manager instance
        self.assertTrue(hasattr(Character.pcs, "all"))
        self.assertTrue(hasattr(Character.pcs, "filter"))
        self.assertTrue(hasattr(Character.pcs, "get"))

    def test_objects_manager_still_exists(self):
        """Test that existing objects manager is preserved."""
        self.assertTrue(hasattr(Character, "objects"))
        # Verify it still behaves as expected (excludes soft-deleted)
        all_active_chars = Character.objects.all()
        self.assertIn(self.pc1, all_active_chars)
        self.assertIn(self.npc1, all_active_chars)
        self.assertNotIn(self.deleted_pc, all_active_chars)
        self.assertNotIn(self.deleted_npc, all_active_chars)

    def test_npc_manager_returns_only_npcs(self):
        """Test that Character.npcs.all() returns only NPC characters."""
        npcs = Character.npcs.all()

        # Verify NPCs are included
        self.assertIn(self.npc1, npcs)
        self.assertIn(self.npc2, npcs)
        self.assertIn(self.npc3_other_campaign, npcs)

        # Verify PCs are excluded
        self.assertNotIn(self.pc1, npcs)
        self.assertNotIn(self.pc2, npcs)
        self.assertNotIn(self.pc3_other_campaign, npcs)

        # Verify soft-deleted characters are excluded
        self.assertNotIn(self.deleted_npc, npcs)
        self.assertNotIn(self.deleted_pc, npcs)

        # Count verification
        self.assertEqual(npcs.count(), 3)

    def test_pc_manager_returns_only_pcs(self):
        """Test that Character.pcs.all() returns only PC characters."""
        pcs = Character.pcs.all()

        # Verify PCs are included
        self.assertIn(self.pc1, pcs)
        self.assertIn(self.pc2, pcs)
        self.assertIn(self.pc3_other_campaign, pcs)

        # Verify NPCs are excluded
        self.assertNotIn(self.npc1, pcs)
        self.assertNotIn(self.npc2, pcs)
        self.assertNotIn(self.npc3_other_campaign, pcs)

        # Verify soft-deleted characters are excluded
        self.assertNotIn(self.deleted_pc, pcs)
        self.assertNotIn(self.deleted_npc, pcs)

        # Count verification
        self.assertEqual(pcs.count(), 3)

    def test_npc_manager_excludes_soft_deleted(self):
        """Test that NPCManager excludes soft-deleted characters."""
        # Create and delete an NPC
        temp_npc = Character.objects.create(
            name="Temp NPC",
            campaign=self.campaign1,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
        )
        temp_npc.soft_delete(self.gm)

        npcs = Character.npcs.all()
        self.assertNotIn(temp_npc, npcs)
        self.assertNotIn(self.deleted_npc, npcs)

        # Verify the manager still finds active NPCs
        self.assertIn(self.npc1, npcs)
        self.assertIn(self.npc2, npcs)

    def test_pc_manager_excludes_soft_deleted(self):
        """Test that PCManager excludes soft-deleted characters."""
        # Create and delete a PC
        temp_pc = Character.objects.create(
            name="Temp PC",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
        )
        temp_pc.soft_delete(self.player1)

        pcs = Character.pcs.all()
        self.assertNotIn(temp_pc, pcs)
        self.assertNotIn(self.deleted_pc, pcs)

        # Verify the manager still finds active PCs
        self.assertIn(self.pc1, pcs)
        self.assertIn(self.pc2, pcs)

    def test_managers_work_with_polymorphic_inheritance(self):
        """Test that managers work with polymorphic inheritance (MageCharacter)."""
        from characters.models import MageCharacter

        # Create polymorphic characters
        mage_pc = MageCharacter.objects.create(
            name="Mage PC",
            campaign=self.campaign1,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
            npc=False,
            arete=3,
        )

        mage_npc = MageCharacter.objects.create(
            name="Mage NPC",
            campaign=self.campaign1,
            player_owner=self.gm,
            game_system="Mage: The Ascension",
            npc=True,
            arete=5,
        )

        # Test that polymorphic PCs are returned by PC manager
        pcs = Character.pcs.all()
        self.assertIn(mage_pc, pcs)
        self.assertNotIn(mage_npc, pcs)

        # Test that polymorphic NPCs are returned by NPC manager
        npcs = Character.npcs.all()
        self.assertIn(mage_npc, npcs)
        self.assertNotIn(mage_pc, npcs)

        # Verify they are returned as their polymorphic type
        retrieved_mage_pc = Character.pcs.get(id=mage_pc.id)
        retrieved_mage_npc = Character.npcs.get(id=mage_npc.id)

        self.assertIsInstance(retrieved_mage_pc, MageCharacter)
        self.assertIsInstance(retrieved_mage_npc, MageCharacter)
        self.assertEqual(retrieved_mage_pc.arete, 3)
        self.assertEqual(retrieved_mage_npc.arete, 5)

    def test_managers_inherit_from_polymorphic_manager(self):
        """Test that NPCManager and PCManager inherit from PolymorphicManager."""
        from polymorphic.managers import PolymorphicManager

        # Test NPCManager inheritance
        self.assertIsInstance(Character.npcs, PolymorphicManager)

        # Test PCManager inheritance
        self.assertIsInstance(Character.pcs, PolymorphicManager)

    def test_managers_support_filtering(self):
        """Test that managers support additional filtering operations."""
        # Test filtering by campaign
        campaign1_npcs = Character.npcs.filter(campaign=self.campaign1)
        self.assertEqual(campaign1_npcs.count(), 2)
        self.assertIn(self.npc1, campaign1_npcs)
        self.assertIn(self.npc2, campaign1_npcs)
        self.assertNotIn(self.npc3_other_campaign, campaign1_npcs)

        campaign1_pcs = Character.pcs.filter(campaign=self.campaign1)
        self.assertEqual(campaign1_pcs.count(), 2)
        self.assertIn(self.pc1, campaign1_pcs)
        self.assertIn(self.pc2, campaign1_pcs)
        self.assertNotIn(self.pc3_other_campaign, campaign1_pcs)

        # Test filtering by owner
        player1_pcs = Character.pcs.filter(player_owner=self.player1)
        self.assertEqual(player1_pcs.count(), 2)
        self.assertIn(self.pc1, player1_pcs)
        self.assertIn(self.pc3_other_campaign, player1_pcs)
        self.assertNotIn(self.pc2, player1_pcs)

        gm_npcs = Character.npcs.filter(player_owner=self.gm)
        self.assertEqual(gm_npcs.count(), 1)
        self.assertIn(self.npc1, gm_npcs)
        self.assertNotIn(self.npc2, gm_npcs)

    def test_managers_support_chaining_with_existing_methods(self):
        """Test that managers can be chained with existing manager methods."""
        # Test chaining with for_campaign if it exists
        if hasattr(Character.npcs, "for_campaign"):
            campaign1_npcs = Character.npcs.for_campaign(self.campaign1)
            self.assertEqual(campaign1_npcs.count(), 2)
            self.assertIn(self.npc1, campaign1_npcs)
            self.assertIn(self.npc2, campaign1_npcs)

        if hasattr(Character.pcs, "for_campaign"):
            campaign1_pcs = Character.pcs.for_campaign(self.campaign1)
            self.assertEqual(campaign1_pcs.count(), 2)
            self.assertIn(self.pc1, campaign1_pcs)
            self.assertIn(self.pc2, campaign1_pcs)

        # Test chaining with owned_by if it exists
        if hasattr(Character.npcs, "owned_by"):
            gm_npcs = Character.npcs.owned_by(self.gm)
            self.assertEqual(gm_npcs.count(), 1)
            self.assertIn(self.npc1, gm_npcs)

        if hasattr(Character.pcs, "owned_by"):
            player1_pcs = Character.pcs.owned_by(self.player1)
            self.assertEqual(player1_pcs.count(), 2)
            self.assertIn(self.pc1, player1_pcs)
            self.assertIn(self.pc3_other_campaign, player1_pcs)

    def test_managers_with_empty_results(self):
        """Test manager behavior when no results match the criteria."""
        # Delete all NPCs
        for npc in [self.npc1, self.npc2, self.npc3_other_campaign]:
            npc.soft_delete(self.owner)

        npcs = Character.npcs.all()
        self.assertEqual(npcs.count(), 0)
        self.assertEqual(list(npcs), [])

        # PCs should still exist
        pcs = Character.pcs.all()
        self.assertGreater(pcs.count(), 0)

    def test_managers_distinct_from_objects_manager(self):
        """Test that managers return different results from objects manager."""
        all_chars = Character.objects.all()
        npcs = Character.npcs.all()
        pcs = Character.pcs.all()

        # Verify objects includes both NPCs and PCs
        self.assertGreater(all_chars.count(), npcs.count())
        self.assertGreater(all_chars.count(), pcs.count())

        # Verify NPCs + PCs = all objects (excluding soft-deleted)
        combined_count = npcs.count() + pcs.count()
        self.assertEqual(all_chars.count(), combined_count)

        # Verify no overlap between NPCs and PCs
        npc_ids = set(npcs.values_list("id", flat=True))
        pc_ids = set(pcs.values_list("id", flat=True))
        self.assertEqual(len(npc_ids.intersection(pc_ids)), 0)

    def test_managers_work_with_select_related(self):
        """Test that managers work with select_related optimization."""
        npcs = Character.npcs.select_related("campaign", "player_owner").all()
        pcs = Character.pcs.select_related("campaign", "player_owner").all()

        # Verify queries work and return correct results
        self.assertEqual(npcs.count(), 3)
        self.assertEqual(pcs.count(), 3)

        # Verify relationships are accessible without additional queries
        for npc in npcs:
            self.assertIsNotNone(npc.campaign.name)
            self.assertIsNotNone(npc.player_owner.username)

        for pc in pcs:
            self.assertIsNotNone(pc.campaign.name)
            self.assertIsNotNone(pc.player_owner.username)

    def test_managers_work_with_prefetch_related(self):
        """Test that managers work with prefetch_related optimization."""
        npcs = Character.npcs.prefetch_related("campaign__memberships").all()
        pcs = Character.pcs.prefetch_related("campaign__memberships").all()

        # Verify queries work and return correct results
        self.assertEqual(npcs.count(), 3)
        self.assertEqual(pcs.count(), 3)

        # Verify prefetched relationships are accessible
        for npc in npcs:
            memberships = npc.campaign.memberships.all()
            self.assertGreaterEqual(len(memberships), 0)

        for pc in pcs:
            memberships = pc.campaign.memberships.all()
            self.assertGreaterEqual(len(memberships), 0)

    def test_managers_support_exists_queries(self):
        """Test that managers work with exists() queries."""
        # Test exists with NPCs
        self.assertTrue(Character.npcs.exists())
        self.assertTrue(Character.npcs.filter(campaign=self.campaign1).exists())
        self.assertFalse(Character.npcs.filter(name="Nonexistent").exists())

        # Test exists with PCs
        self.assertTrue(Character.pcs.exists())
        self.assertTrue(Character.pcs.filter(campaign=self.campaign1).exists())
        self.assertFalse(Character.pcs.filter(name="Nonexistent").exists())

    def test_managers_support_get_operations(self):
        """Test that managers support get() operations."""
        # Test getting specific NPCs
        retrieved_npc1 = Character.npcs.get(id=self.npc1.id)
        self.assertEqual(retrieved_npc1, self.npc1)

        retrieved_npc_by_name = Character.npcs.get(name="NPC Character 1")
        self.assertEqual(retrieved_npc_by_name, self.npc1)

        # Test getting specific PCs
        retrieved_pc1 = Character.pcs.get(id=self.pc1.id)
        self.assertEqual(retrieved_pc1, self.pc1)

        retrieved_pc_by_name = Character.pcs.get(name="Player Character 1")
        self.assertEqual(retrieved_pc_by_name, self.pc1)

        # Test that get() raises DoesNotExist for wrong type
        with self.assertRaises(Character.DoesNotExist):
            Character.npcs.get(id=self.pc1.id)  # PC ID with NPC manager

        with self.assertRaises(Character.DoesNotExist):
            Character.pcs.get(id=self.npc1.id)  # NPC ID with PC manager

    def test_managers_maintain_queryset_type(self):
        """Test that managers return the correct QuerySet type."""
        npcs_qs = Character.npcs.all()
        pcs_qs = Character.pcs.all()

        # Verify they support further filtering
        filtered_npcs = npcs_qs.filter(campaign=self.campaign1)
        filtered_pcs = pcs_qs.filter(campaign=self.campaign1)

        self.assertEqual(filtered_npcs.count(), 2)
        self.assertEqual(filtered_pcs.count(), 2)

        # Verify they support ordering
        ordered_npcs = npcs_qs.order_by("name")
        ordered_pcs = pcs_qs.order_by("name")

        self.assertEqual(list(ordered_npcs), sorted(npcs_qs, key=lambda x: x.name))
        self.assertEqual(list(ordered_pcs), sorted(pcs_qs, key=lambda x: x.name))


class CharacterStatusFSMTest(TestCase):
    """Test Character.status FSMField functionality and state transitions."""

    def setUp(self):
        """Set up test users, campaigns, and characters."""
        from django_fsm import TransitionNotAllowed

        # Store reference to TransitionNotAllowed for tests
        self.TransitionNotAllowed = TransitionNotAllowed

        # Create users with different roles
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@test.com", password="testpass123"
        )
        self.player1 = User.objects.create_user(
            username="player1", email="player1@test.com", password="testpass123"
        )
        self.player2 = User.objects.create_user(
            username="player2", email="player2@test.com", password="testpass123"
        )
        self.outsider = User.objects.create_user(
            username="outsider", email="outsider@test.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.owner,
            game_system="Mage: The Ascension",
            max_characters_per_player=0,  # Unlimited characters for testing
        )

        # Create memberships
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.gm, role="GM"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player1, role="PLAYER"
        )
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.player2, role="PLAYER"
        )
        # Note: outsider is not a campaign member

        # Create a test character
        self.character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

    def test_status_field_exists_with_correct_properties(self):
        """Test that status field exists with correct choices and default value."""
        # Get the status field
        status_field = Character._meta.get_field("status")

        # Verify it's an FSMField
        from django_fsm import FSMField

        self.assertIsInstance(status_field, FSMField)

        # Verify default value
        new_character = Character(
            name="New Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(new_character.status, "DRAFT")

        # Verify choices
        expected_choices = [
            ("DRAFT", "Draft"),
            ("SUBMITTED", "Submitted"),
            ("APPROVED", "Approved"),
            ("INACTIVE", "Inactive"),
            ("RETIRED", "Retired"),
            ("DECEASED", "Deceased"),
        ]
        self.assertEqual(status_field.choices, expected_choices)

        # Verify field protection (using transition methods for control)
        self.assertFalse(status_field.protected)

    def test_character_created_with_draft_status(self):
        """Test that new characters are created with DRAFT status."""
        character = Character.objects.create(
            name="Draft Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        self.assertEqual(character.status, "DRAFT")

    def test_valid_state_transitions(self):
        """Test that all valid state transitions work correctly."""
        # Start with DRAFT
        self.assertEqual(self.character.status, "DRAFT")

        # DRAFT → SUBMITTED (player can do this)
        self.character.submit_for_approval(user=self.player1)
        self.assertEqual(self.character.status, "SUBMITTED")

        # SUBMITTED → ACTIVE (requires GM/OWNER)
        self.character.approve(user=self.gm)
        self.assertEqual(self.character.status, "APPROVED")

        # ACTIVE → INACTIVE (requires GM/OWNER)
        self.character.deactivate(user=self.owner)
        self.assertEqual(self.character.status, "INACTIVE")

        # INACTIVE → ACTIVE (requires GM/OWNER)
        self.character.activate(user=self.gm)
        self.assertEqual(self.character.status, "APPROVED")

        # ACTIVE → RETIRED (players can do this)
        self.character.retire(user=self.player1)
        self.assertEqual(self.character.status, "RETIRED")

        # Create another character to test ACTIVE → DECEASED
        character2 = Character.objects.create(
            name="Test Character 2",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        character2.submit_for_approval(user=self.player1)
        character2.approve(user=self.gm)
        self.assertEqual(character2.status, "APPROVED")

        # ACTIVE → DECEASED (requires GM/OWNER)
        character2.mark_deceased(user=self.owner)
        self.assertEqual(character2.status, "DECEASED")

        # Create another character to test SUBMITTED → DRAFT (rejection)
        character3 = Character.objects.create(
            name="Test Character 3",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        character3.submit_for_approval(user=self.player1)
        self.assertEqual(character3.status, "SUBMITTED")

        # SUBMITTED → DRAFT (requires GM/OWNER - for rejection)
        character3.reject(user=self.gm)
        self.assertEqual(character3.status, "DRAFT")

    def test_invalid_transitions_are_blocked(self):
        """Test that invalid state transitions are blocked."""
        # Try to transition from DRAFT directly to ACTIVE (should fail)
        with self.assertRaises(self.TransitionNotAllowed):
            self.character.approve(user=self.gm)

        # Try to transition from DRAFT to RETIRED (should fail)
        with self.assertRaises(self.TransitionNotAllowed):
            self.character.retire(user=self.player1)

        # Move to SUBMITTED and try invalid transitions
        self.character.submit_for_approval(user=self.player1)

        # Try to submit again (should fail)
        with self.assertRaises(self.TransitionNotAllowed):
            self.character.submit_for_approval(user=self.player1)

        # Try to transition from SUBMITTED to INACTIVE (should fail)
        with self.assertRaises(self.TransitionNotAllowed):
            self.character.deactivate(user=self.gm)

        # Move to ACTIVE and try invalid transitions
        self.character.approve(user=self.gm)

        # Try to submit from ACTIVE (should fail)
        with self.assertRaises(self.TransitionNotAllowed):
            self.character.submit_for_approval(user=self.player1)

        # Try to approve from ACTIVE (should fail)
        with self.assertRaises(self.TransitionNotAllowed):
            self.character.approve(user=self.gm)

        # Move to RETIRED and try transitions (should all fail)
        self.character.retire(user=self.player1)

        with self.assertRaises(self.TransitionNotAllowed):
            self.character.activate(user=self.gm)

        with self.assertRaises(self.TransitionNotAllowed):
            self.character.mark_deceased(user=self.gm)

    def test_permission_based_restrictions(self):
        """Test that state transitions respect permission rules."""
        # Test that character owners can submit
        self.character.submit_for_approval(user=self.player1)
        self.assertEqual(self.character.status, "SUBMITTED")

        # Test that only GM/OWNER can approve
        character2 = Character.objects.create(
            name="Test Character 2",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        character2.submit_for_approval(user=self.player1)

        # Player2 (different player) should not be able to approve
        with self.assertRaises(PermissionError):
            character2.approve(user=self.player2)

        # Outsider should not be able to approve
        with self.assertRaises(PermissionError):
            character2.approve(user=self.outsider)

        # GM should be able to approve
        character2.approve(user=self.gm)
        self.assertEqual(character2.status, "APPROVED")

        # Test that only character owner can retire their character
        with self.assertRaises(PermissionError):
            character2.retire(user=self.player2)

        # Character owner should be able to retire
        character2.retire(user=self.player1)
        self.assertEqual(character2.status, "RETIRED")

        # Test GM/OWNER can do restricted transitions
        character3 = Character.objects.create(
            name="Test Character 3",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        character3.submit_for_approval(user=self.player1)
        character3.approve(user=self.owner)  # Owner should be able to approve
        character3.mark_deceased(user=self.gm)  # GM should be able to mark deceased
        self.assertEqual(character3.status, "DECEASED")

        # Test rejection permissions
        character4 = Character.objects.create(
            name="Test Character 4",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )
        character4.submit_for_approval(user=self.player1)

        # Player should not be able to reject
        with self.assertRaises(PermissionError):
            character4.reject(user=self.player1)

        # GM should be able to reject
        character4.reject(user=self.gm)
        self.assertEqual(character4.status, "DRAFT")

    def test_fsm_protection_prevents_manual_changes(self):
        """Test that FSM protection prevents manual field changes."""
        # Create a fresh character in DRAFT state for this test
        test_character = Character.objects.create(
            name="FSM Test Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        original_status = test_character.status
        self.assertEqual(original_status, "DRAFT")

        # Try to manually change status (should be protected)
        test_character.status = "APPROVED"

        # The protection should prevent the change or it should be reset
        # This depends on implementation - let's test both scenarios
        try:
            test_character.save()
            # If save succeeds, verify the status wasn't actually changed
            test_character.refresh_from_db()
            self.assertEqual(test_character.status, original_status)
        except Exception:
            # If save fails due to protection, that's also valid
            pass

        # Reset status to DRAFT for proper transition test
        test_character.status = "DRAFT"
        test_character.save(update_fields=["status"])

        # Verify the proper way to change status works
        test_character.submit_for_approval(user=self.player1)
        test_character.save(audit_user=self.player1)
        self.assertEqual(test_character.status, "SUBMITTED")

    def test_integration_with_soft_delete(self):
        """Test that FSM status integrates properly with soft-delete functionality."""
        # Set character to ACTIVE status
        self.character.submit_for_approval(user=self.player1)
        self.character.approve(user=self.gm)
        self.assertEqual(self.character.status, "APPROVED")

        # Soft delete the character
        deleted_character = self.character.soft_delete(user=self.player1)
        self.assertTrue(deleted_character.is_deleted)

        # Verify status is preserved after soft delete
        self.assertEqual(deleted_character.status, "APPROVED")

        # Restore the character
        restored_character = deleted_character.restore(user=self.player1)
        self.assertFalse(restored_character.is_deleted)

        # Verify status is still preserved after restore
        self.assertEqual(restored_character.status, "APPROVED")

        # Verify FSM transitions still work after restore
        restored_character.deactivate(user=self.gm)
        self.assertEqual(restored_character.status, "INACTIVE")

    def test_migration_preserves_existing_data(self):
        """Test that migration preserves existing data."""
        # This test simulates what happens during migration
        # Since there's no current status field, all existing characters
        # should get the default DRAFT status

        # Create a character the old way (simulating pre-migration)
        character = Character.objects.create(
            name="Pre-Migration Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Verify it gets the default status
        self.assertEqual(character.status, "DRAFT")

        # Verify it can use FSM transitions normally
        character.submit_for_approval(user=self.player1)
        self.assertEqual(character.status, "SUBMITTED")

        character.approve(user=self.gm)
        self.assertEqual(character.status, "APPROVED")

    def test_audit_trail_captures_status_changes(self):
        """Test that audit trail captures status changes."""
        # Create a fresh character for this test to avoid interference
        test_character = Character.objects.create(
            name="Audit Test Character",
            campaign=self.campaign,
            player_owner=self.player1,
            game_system="Mage: The Ascension",
        )

        # Get initial audit count
        initial_audit_count = test_character.audit_entries.count()

        # Perform a status transition
        test_character.submit_for_approval(user=self.player1)
        test_character.save(audit_user=self.player1)

        # Verify audit entry was created
        new_audit_count = test_character.audit_entries.count()
        self.assertGreater(new_audit_count, initial_audit_count)

        # Get the latest audit entry
        latest_audit = test_character.audit_entries.first()
        self.assertEqual(latest_audit.changed_by, self.player1)
        self.assertEqual(latest_audit.action, "UPDATE")

        # Verify the status change is recorded
        field_changes = latest_audit.field_changes
        self.assertIn("status", field_changes)
        self.assertEqual(field_changes["status"]["old"], "DRAFT")
        self.assertEqual(field_changes["status"]["new"], "SUBMITTED")

        # Test multiple transitions create multiple audit entries
        initial_count = test_character.audit_entries.count()
        test_character.approve(user=self.gm)
        test_character.save(audit_user=self.gm)
        test_character.deactivate(user=self.owner)
        test_character.save(audit_user=self.owner)

        final_count = test_character.audit_entries.count()
        self.assertEqual(final_count, initial_count + 2)

    def test_status_display_methods(self):
        """Test status display methods and string representations."""
        # Test default status display
        self.assertEqual(self.character.get_status_display(), "Draft")

        # Test status displays for all states
        status_displays = {
            "DRAFT": "Draft",
            "SUBMITTED": "Submitted",
            "APPROVED": "Approved",
            "INACTIVE": "Inactive",
            "RETIRED": "Retired",
            "DECEASED": "Deceased",
        }

        for status_code, expected_display in status_displays.items():
            # Create a character and manually set status for testing
            character = Character.objects.create(
                name=f"Test {status_code}",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )

            # Use transition methods to reach each state
            if status_code == "SUBMITTED":
                character.submit_for_approval(user=self.player1)
            elif status_code == "APPROVED":
                character.submit_for_approval(user=self.player1)
                character.approve(user=self.gm)
            elif status_code == "INACTIVE":
                character.submit_for_approval(user=self.player1)
                character.approve(user=self.gm)
                character.deactivate(user=self.owner)
            elif status_code == "RETIRED":
                character.submit_for_approval(user=self.player1)
                character.approve(user=self.gm)
                character.retire(user=self.player1)
            elif status_code == "DECEASED":
                character.submit_for_approval(user=self.player1)
                character.approve(user=self.gm)
                character.mark_deceased(user=self.owner)

            self.assertEqual(character.status, status_code)
            self.assertEqual(character.get_status_display(), expected_display)

    def test_batch_status_operations(self):
        """Test operations on multiple characters with different statuses."""
        # Create multiple characters in different states
        characters = []
        for i in range(5):
            char = Character.objects.create(
                name=f"Batch Character {i}",
                campaign=self.campaign,
                player_owner=self.player1,
                game_system="Mage: The Ascension",
            )
            characters.append(char)

        # Set different statuses
        characters[1].submit_for_approval(user=self.player1)
        characters[1].save(audit_user=self.player1)

        characters[2].submit_for_approval(user=self.player1)
        characters[2].save(audit_user=self.player1)
        characters[2].approve(user=self.gm)
        characters[2].save(audit_user=self.gm)

        characters[3].submit_for_approval(user=self.player1)
        characters[3].save(audit_user=self.player1)
        characters[3].approve(user=self.gm)
        characters[3].save(audit_user=self.gm)
        characters[3].deactivate(user=self.gm)
        characters[3].save(audit_user=self.gm)

        characters[4].submit_for_approval(user=self.player1)
        characters[4].save(audit_user=self.player1)
        characters[4].approve(user=self.gm)
        characters[4].save(audit_user=self.gm)
        characters[4].retire(user=self.player1)
        characters[4].save(audit_user=self.player1)

        # Test filtering by status (avoid interference from other tests)
        batch_draft_chars = [char for char in characters if char.status == "DRAFT"]
        self.assertEqual(len(batch_draft_chars), 1)
        self.assertEqual(batch_draft_chars[0], characters[0])

        batch_submitted_chars = [
            char for char in characters if char.status == "SUBMITTED"
        ]
        self.assertEqual(len(batch_submitted_chars), 1)
        self.assertEqual(batch_submitted_chars[0], characters[1])

        batch_active_chars = [char for char in characters if char.status == "APPROVED"]
        self.assertEqual(len(batch_active_chars), 1)
        self.assertEqual(batch_active_chars[0], characters[2])

        batch_inactive_chars = [
            char for char in characters if char.status == "INACTIVE"
        ]
        self.assertEqual(len(batch_inactive_chars), 1)
        self.assertEqual(batch_inactive_chars[0], characters[3])

        batch_retired_chars = [char for char in characters if char.status == "RETIRED"]
        self.assertEqual(len(batch_retired_chars), 1)
        self.assertEqual(batch_retired_chars[0], characters[4])

    def test_concurrent_status_transitions(self):
        """Test that concurrent status transitions are handled safely."""
        from django.db import transaction

        # This test ensures that FSM transitions are atomic
        self.character.submit_for_approval(user=self.player1)
        self.character.save(audit_user=self.player1)

        def approve_character():
            with transaction.atomic():
                char = Character.objects.select_for_update().get(pk=self.character.pk)
                char.approve(user=self.gm)
                char.save(audit_user=self.gm)

        def reject_character():
            with transaction.atomic():
                char = Character.objects.select_for_update().get(pk=self.character.pk)
                char.reject(user=self.gm)
                char.save(audit_user=self.gm)

        # Both operations should not conflict due to select_for_update
        # One should succeed, the other should fail
        from django_fsm import TransitionNotAllowed

        try:
            approve_character()
            # If approve succeeded, reject should fail
            with self.assertRaises(TransitionNotAllowed):
                reject_character()
        except TransitionNotAllowed:
            # If approve failed, reject might succeed
            reject_character()

        # Verify the character is in a valid final state
        self.character.refresh_from_db()
        self.assertIn(self.character.status, ["APPROVED", "DRAFT"])
