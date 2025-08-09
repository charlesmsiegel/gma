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
