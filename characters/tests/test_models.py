from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
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
        with self.assertRaises(IntegrityError):
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
        )
        self.campaign2 = Campaign.objects.create(
            name="Campaign Two",
            owner=self.owner2,
            game_system="D&D 5e",
        )
        self.campaign3 = Campaign.objects.create(
            name="Campaign Three",
            owner=self.owner1,
            game_system="Vampire: The Masquerade",
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
        with self.assertRaises(AttributeError):
            Character.objects.for_campaign(None)

        # Test owned_by with None
        none_owned = Character.objects.owned_by(None)
        self.assertEqual(none_owned.count(), 0)

        # Test editable_by with None user
        none_user_editable = Character.objects.editable_by(None, self.campaign1)
        self.assertEqual(none_user_editable.count(), 0)

        # Test editable_by with None campaign
        with self.assertRaises(AttributeError):
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
        )
        self.other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=self.different_campaign_owner,
            game_system="D&D 5e",
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
        """Test that campaign owners can delete all characters in their campaign."""
        # Campaign owner can delete all characters
        self.assertTrue(self.player1_character.can_be_deleted_by(self.owner))
        self.assertTrue(self.player2_character.can_be_deleted_by(self.owner))
        self.assertTrue(self.gm_character.can_be_deleted_by(self.owner))
        self.assertTrue(self.owner_character.can_be_deleted_by(self.owner))

    def test_can_be_deleted_by_campaign_gm(self):
        """Test that campaign GMs can delete all characters in their campaign."""
        # GM can delete all characters in the campaign
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

        # Transfer campaign ownership to another user
        new_owner = User.objects.create_user(
            username="new_owner", email="new_owner@test.com", password="testpass123"
        )
        self.campaign.owner = new_owner
        self.campaign.save()

        # Existing character should still be valid
        character.name = "Updated Player Character"
        character.full_clean()  # Should not raise ValidationError
        character.save()

        # Original owner should still be able to own characters if they remain a member
        # (campaign owner change doesn't affect existing memberships)

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
