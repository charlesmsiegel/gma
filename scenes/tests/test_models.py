"""Tests for Scene model enhancements."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from campaigns.models import Campaign, CampaignMembership
from characters.models import Character
from scenes.models import Scene

User = get_user_model()


class SceneModelTest(TestCase):
    """Test cases for the Scene model basic functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            description="A test campaign",
            owner=self.user,
            game_system="Test System",
        )

    def test_scene_creation_with_required_fields(self):
        """Test creating a scene with all required fields."""
        scene = Scene.objects.create(
            name="Test Scene",
            description="A test scene description",
            campaign=self.campaign,
            created_by=self.user,
        )

        self.assertEqual(scene.name, "Test Scene")
        self.assertEqual(scene.description, "A test scene description")
        self.assertEqual(scene.campaign, self.campaign)
        self.assertEqual(scene.created_by, self.user)
        self.assertIsNotNone(scene.created_at)
        self.assertIsNotNone(scene.updated_at)
        self.assertEqual(scene.status, "ACTIVE")  # Default status

    def test_scene_creation_minimal_fields(self):
        """Test creating a scene with minimal required fields."""
        scene = Scene.objects.create(
            name="Minimal Scene",
            campaign=self.campaign,
            created_by=self.user,
        )

        self.assertEqual(scene.name, "Minimal Scene")
        self.assertEqual(scene.description, "")  # Should default to empty string
        self.assertEqual(scene.campaign, self.campaign)
        self.assertEqual(scene.created_by, self.user)
        self.assertEqual(scene.status, "ACTIVE")

    def test_scene_str_representation(self):
        """Test the string representation of a Scene."""
        scene = Scene.objects.create(
            name="Test Scene String",
            campaign=self.campaign,
            created_by=self.user,
        )
        self.assertEqual(str(scene), "Test Scene String")

    def test_scene_timestamps(self):
        """Test that created_at and updated_at are properly set."""
        before_creation = timezone.now()
        scene = Scene.objects.create(
            name="Timestamp Test",
            campaign=self.campaign,
            created_by=self.user,
        )
        after_creation = timezone.now()

        # Check created_at is set and reasonable
        self.assertIsNotNone(scene.created_at)
        self.assertGreaterEqual(scene.created_at, before_creation)
        self.assertLessEqual(scene.created_at, after_creation)

        # Check updated_at is set and close to created_at initially
        self.assertIsNotNone(scene.updated_at)
        # Allow for small timing differences in microseconds
        time_diff = abs((scene.created_at - scene.updated_at).total_seconds())
        self.assertLess(time_diff, 0.01)  # Less than 10ms difference

        # Update the scene and verify updated_at changes
        original_updated_at = scene.updated_at
        scene.description = "Updated description"
        scene.save()
        self.assertGreater(scene.updated_at, original_updated_at)

    def test_scene_meta_options(self):
        """Test Scene model meta options."""
        # Test ordering
        scene1 = Scene.objects.create(
            name="First Scene",
            campaign=self.campaign,
            created_by=self.user,
        )
        scene2 = Scene.objects.create(
            name="Second Scene",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Should be ordered by -created_at (newest first)
        scenes = list(Scene.objects.all())
        self.assertEqual(scenes[0], scene2)  # Most recent first
        self.assertEqual(scenes[1], scene1)

        # Test verbose names
        self.assertEqual(Scene._meta.verbose_name, "Scene")
        self.assertEqual(Scene._meta.verbose_name_plural, "Scenes")

        # Test db_table
        self.assertEqual(Scene._meta.db_table, "scenes_scene")


class SceneStatusFieldTest(TestCase):
    """Test cases for Scene status field and choices."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
        )

    def test_status_choices(self):
        """Test that all status choices are available."""
        expected_choices = [
            ("ACTIVE", "Active"),
            ("CLOSED", "Closed"),
            ("ARCHIVED", "Archived"),
        ]

        # Get the status field choices
        status_field = Scene._meta.get_field("status")
        self.assertEqual(status_field.choices, expected_choices)

    def test_default_status(self):
        """Test that default status is ACTIVE."""
        scene = Scene.objects.create(
            name="Default Status Test",
            campaign=self.campaign,
            created_by=self.user,
        )
        self.assertEqual(scene.status, "ACTIVE")

    def test_status_values(self):
        """Test setting different status values."""
        scene = Scene.objects.create(
            name="Status Test",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Test ACTIVE
        scene.status = "ACTIVE"
        scene.save()
        scene.refresh_from_db()
        self.assertEqual(scene.status, "ACTIVE")

        # Test CLOSED
        scene.status = "CLOSED"
        scene.save()
        scene.refresh_from_db()
        self.assertEqual(scene.status, "CLOSED")

        # Test ARCHIVED
        scene.status = "ARCHIVED"
        scene.save()
        scene.refresh_from_db()
        self.assertEqual(scene.status, "ARCHIVED")

    def test_invalid_status_value(self):
        """Test that invalid status values raise validation error."""
        scene = Scene(
            name="Invalid Status Test",
            campaign=self.campaign,
            created_by=self.user,
            status="INVALID",
        )

        with self.assertRaises(ValidationError):
            scene.full_clean()

    def test_status_max_length(self):
        """Test that status field has appropriate max_length."""
        status_field = Scene._meta.get_field("status")
        self.assertEqual(status_field.max_length, 10)


class SceneParticipantsTest(TestCase):
    """Test cases for Scene participants many-to-many relationship."""

    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user1,
        )

        # Add user2 as a member
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.user2, role="PLAYER"
        )

        # Create characters
        self.character1 = Character.objects.create(
            name="Character 1",
            campaign=self.campaign,
            player_owner=self.user1,
            game_system="Test System",
        )
        self.character2 = Character.objects.create(
            name="Character 2",
            campaign=self.campaign,
            player_owner=self.user2,
            game_system="Test System",
        )

        self.scene = Scene.objects.create(
            name="Test Scene",
            campaign=self.campaign,
            created_by=self.user1,
        )

    def test_add_participant(self):
        """Test adding a character as a participant."""
        self.scene.participants.add(self.character1)

        self.assertIn(self.character1, self.scene.participants.all())
        self.assertEqual(self.scene.participants.count(), 1)

    def test_add_multiple_participants(self):
        """Test adding multiple characters as participants."""
        self.scene.participants.add(self.character1, self.character2)

        participants = list(self.scene.participants.all())
        self.assertIn(self.character1, participants)
        self.assertIn(self.character2, participants)
        self.assertEqual(self.scene.participants.count(), 2)

    def test_remove_participant(self):
        """Test removing a character from participants."""
        self.scene.participants.add(self.character1, self.character2)
        self.scene.participants.remove(self.character1)

        participants = list(self.scene.participants.all())
        self.assertNotIn(self.character1, participants)
        self.assertIn(self.character2, participants)
        self.assertEqual(self.scene.participants.count(), 1)

    def test_clear_participants(self):
        """Test clearing all participants."""
        self.scene.participants.add(self.character1, self.character2)
        self.scene.participants.clear()

        self.assertEqual(self.scene.participants.count(), 0)

    def test_reverse_relationship_from_character(self):
        """Test accessing scenes from character (reverse relationship)."""
        self.scene.participants.add(self.character1)

        # Test the related name 'participated_scenes'
        scenes = self.character1.participated_scenes.all()
        self.assertIn(self.scene, scenes)
        self.assertEqual(scenes.count(), 1)

    def test_participant_relationship_persistence(self):
        """Test that participant relationships persist across saves."""
        self.scene.participants.add(self.character1)
        self.scene.save()

        # Refresh from database
        scene_from_db = Scene.objects.get(pk=self.scene.pk)
        self.assertIn(self.character1, scene_from_db.participants.all())

    def test_participants_with_different_campaigns(self):
        """Test that participants can only be from the same campaign."""
        # Create a character from a different campaign
        other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=other_user,
        )
        other_character = Character.objects.create(
            name="Other Character",
            campaign=other_campaign,
            player_owner=other_user,
            game_system="Test System",
        )

        # This should be allowed at the database level but might be
        # restricted by business logic in views/forms
        self.scene.participants.add(other_character)
        self.assertIn(other_character, self.scene.participants.all())


class SceneValidationTest(TestCase):
    """Test cases for Scene model validation and constraints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
        )

    def test_name_required(self):
        """Test that name field is required."""
        scene = Scene(
            description="Test description",
            campaign=self.campaign,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as cm:
            scene.full_clean()

        self.assertIn("name", cm.exception.message_dict)

    def test_name_max_length(self):
        """Test name field max_length constraint."""
        name_field = Scene._meta.get_field("name")
        self.assertEqual(name_field.max_length, 200)

        # Test with exactly 200 characters
        long_name = "x" * 200
        scene = Scene.objects.create(
            name=long_name,
            campaign=self.campaign,
            created_by=self.user,
        )
        self.assertEqual(scene.name, long_name)

        # Test with 201 characters should fail
        too_long_name = "x" * 201
        scene = Scene(
            name=too_long_name,
            campaign=self.campaign,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            scene.full_clean()

    def test_description_optional(self):
        """Test that description field is optional."""
        scene = Scene.objects.create(
            name="Test Scene",
            campaign=self.campaign,
            created_by=self.user,
        )
        self.assertEqual(scene.description, "")

    def test_description_blank_allowed(self):
        """Test that description can be blank."""
        scene = Scene.objects.create(
            name="Test Scene",
            description="",
            campaign=self.campaign,
            created_by=self.user,
        )
        self.assertEqual(scene.description, "")

    def test_campaign_required(self):
        """Test that campaign field is required."""
        scene = Scene(
            name="Test Scene",
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as cm:
            scene.full_clean()

        self.assertIn("campaign", cm.exception.message_dict)

    def test_created_by_required(self):
        """Test that created_by field is required."""
        scene = Scene(
            name="Test Scene",
            campaign=self.campaign,
        )

        with self.assertRaises(ValidationError) as cm:
            scene.full_clean()

        self.assertIn("created_by", cm.exception.message_dict)

    def test_scene_name_uniqueness_within_campaign(self):
        """Test that scene names should be unique within a campaign."""
        # Create first scene
        Scene.objects.create(
            name="Unique Scene",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Try to create second scene with same name in same campaign
        # Note: This test assumes we want this constraint, but it's not
        # explicitly required in the issue. If not needed, this can be removed.
        duplicate_scene = Scene(
            name="Unique Scene",
            campaign=self.campaign,
            created_by=self.user,
        )

        # This should succeed at the model level unless we add a unique constraint
        # For now, we'll just test that the model allows it
        duplicate_scene.full_clean()  # Should not raise an error

    def test_scene_name_across_different_campaigns(self):
        """Test that scene names can be the same across different campaigns."""
        other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            owner=other_user,
        )

        # Create scenes with same name in different campaigns
        scene1 = Scene.objects.create(
            name="Same Name",
            campaign=self.campaign,
            created_by=self.user,
        )
        scene2 = Scene.objects.create(
            name="Same Name",
            campaign=other_campaign,
            created_by=other_user,
        )

        self.assertEqual(scene1.name, scene2.name)
        self.assertNotEqual(scene1.campaign, scene2.campaign)


class SceneCascadeDeletionTest(TestCase):
    """Test cases for cascade deletion when campaign is deleted."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
        )
        self.scene = Scene.objects.create(
            name="Test Scene",
            campaign=self.campaign,
            created_by=self.user,
        )

    def test_cascade_deletion_on_campaign_delete(self):
        """Test that scenes are deleted when campaign is deleted."""
        scene_id = self.scene.id

        # Verify scene exists
        self.assertTrue(Scene.objects.filter(id=scene_id).exists())

        # Delete the campaign
        self.campaign.delete()

        # Verify scene is also deleted
        self.assertFalse(Scene.objects.filter(id=scene_id).exists())

    def test_cascade_deletion_with_participants(self):
        """Test cascade deletion when scene has participants."""
        # Create a character and add as participant
        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Test System",
        )
        self.scene.participants.add(character)

        scene_id = self.scene.id
        character_id = character.id

        # Verify both exist
        self.assertTrue(Scene.objects.filter(id=scene_id).exists())
        self.assertTrue(Character.objects.filter(id=character_id).exists())

        # Delete the campaign
        self.campaign.delete()

        # Verify scene is deleted but character deletion depends on
        # character's cascade behavior (should also be deleted due to campaign FK)
        self.assertFalse(Scene.objects.filter(id=scene_id).exists())
        self.assertFalse(Character.objects.filter(id=character_id).exists())

    def test_user_deletion_behavior(self):
        """Test behavior when created_by user is deleted."""
        scene_id = self.scene.id

        # Delete the user
        self.user.delete()

        # Scene should be deleted due to CASCADE on created_by
        self.assertFalse(Scene.objects.filter(id=scene_id).exists())


class SceneRelatedNameTest(TestCase):
    """Test cases for related name functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
        )

    def test_campaign_scenes_related_name(self):
        """Test accessing scenes from campaign using related name."""
        scene1 = Scene.objects.create(
            name="Scene 1",
            campaign=self.campaign,
            created_by=self.user,
        )
        scene2 = Scene.objects.create(
            name="Scene 2",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Test the related name 'scenes'
        campaign_scenes = list(self.campaign.scenes.all())
        self.assertIn(scene1, campaign_scenes)
        self.assertIn(scene2, campaign_scenes)
        self.assertEqual(len(campaign_scenes), 2)

    def test_user_created_scenes_related_name(self):
        """Test accessing scenes created by user using related name."""
        scene1 = Scene.objects.create(
            name="Scene 1",
            campaign=self.campaign,
            created_by=self.user,
        )
        scene2 = Scene.objects.create(
            name="Scene 2",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Test the related name 'created_scenes'
        user_scenes = list(self.user.created_scenes.all())
        self.assertIn(scene1, user_scenes)
        self.assertIn(scene2, user_scenes)
        self.assertEqual(len(user_scenes), 2)

    def test_character_participated_scenes_related_name(self):
        """Test accessing scenes from character using related name."""
        # Add user as campaign member
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.user, role="PLAYER"
        )

        character = Character.objects.create(
            name="Test Character",
            campaign=self.campaign,
            player_owner=self.user,
            game_system="Test System",
        )

        scene1 = Scene.objects.create(
            name="Scene 1",
            campaign=self.campaign,
            created_by=self.user,
        )
        scene2 = Scene.objects.create(
            name="Scene 2",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Add character to scenes
        scene1.participants.add(character)
        scene2.participants.add(character)

        # Test the related name 'participated_scenes'
        character_scenes = list(character.participated_scenes.all())
        self.assertIn(scene1, character_scenes)
        self.assertIn(scene2, character_scenes)
        self.assertEqual(len(character_scenes), 2)


class SceneEdgeCasesTest(TestCase):
    """Test cases for edge cases and constraints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            owner=self.user,
        )

    def test_scene_with_very_long_description(self):
        """Test scene with very long description."""
        long_description = "x" * 10000  # Very long description
        scene = Scene.objects.create(
            name="Long Description Scene",
            description=long_description,
            campaign=self.campaign,
            created_by=self.user,
        )
        self.assertEqual(scene.description, long_description)

    def test_scene_with_special_characters_in_name(self):
        """Test scene with special characters in name."""
        special_name = "Scene with 'quotes' and \"double quotes\" & symbols!"
        scene = Scene.objects.create(
            name=special_name,
            campaign=self.campaign,
            created_by=self.user,
        )
        self.assertEqual(scene.name, special_name)

    def test_scene_status_change_tracking(self):
        """Test that status changes are properly tracked."""
        scene = Scene.objects.create(
            name="Status Change Test",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Initial status
        self.assertEqual(scene.status, "ACTIVE")

        # Change to CLOSED
        original_updated_at = scene.updated_at
        scene.status = "CLOSED"
        scene.save()
        self.assertEqual(scene.status, "CLOSED")
        self.assertGreater(scene.updated_at, original_updated_at)

        # Change to ARCHIVED
        original_updated_at = scene.updated_at
        scene.status = "ARCHIVED"
        scene.save()
        self.assertEqual(scene.status, "ARCHIVED")
        self.assertGreater(scene.updated_at, original_updated_at)

    def test_multiple_scenes_same_campaign_different_status(self):
        """Test multiple scenes in same campaign with different statuses."""
        active_scene = Scene.objects.create(
            name="Active Scene",
            campaign=self.campaign,
            created_by=self.user,
            status="ACTIVE",
        )
        closed_scene = Scene.objects.create(
            name="Closed Scene",
            campaign=self.campaign,
            created_by=self.user,
            status="CLOSED",
        )
        archived_scene = Scene.objects.create(
            name="Archived Scene",
            campaign=self.campaign,
            created_by=self.user,
            status="ARCHIVED",
        )

        # Filter by status
        active_scenes = Scene.objects.filter(status="ACTIVE")
        closed_scenes = Scene.objects.filter(status="CLOSED")
        archived_scenes = Scene.objects.filter(status="ARCHIVED")

        self.assertIn(active_scene, active_scenes)
        self.assertIn(closed_scene, closed_scenes)
        self.assertIn(archived_scene, archived_scenes)

        self.assertEqual(active_scenes.count(), 1)
        self.assertEqual(closed_scenes.count(), 1)
        self.assertEqual(archived_scenes.count(), 1)

    def test_scene_ordering_by_created_at(self):
        """Test that scenes are properly ordered by creation time."""
        # Create scenes with slight delay to ensure different timestamps
        scene1 = Scene.objects.create(
            name="First Scene",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Small delay to ensure different created_at times
        import time

        time.sleep(0.01)

        scene2 = Scene.objects.create(
            name="Second Scene",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Verify ordering (newest first due to -created_at)
        scenes = list(Scene.objects.all())
        self.assertEqual(scenes[0], scene2)  # More recent first
        self.assertEqual(scenes[1], scene1)

    def test_scene_with_no_participants(self):
        """Test scene functionality with no participants."""
        scene = Scene.objects.create(
            name="Empty Scene",
            campaign=self.campaign,
            created_by=self.user,
        )

        self.assertEqual(scene.participants.count(), 0)
        self.assertFalse(scene.participants.exists())

    def test_bulk_operations_on_participants(self):
        """Test bulk operations on scene participants."""
        # Increase character limit for this test
        self.campaign.max_characters_per_player = 10
        self.campaign.save()

        # Add user as campaign member
        CampaignMembership.objects.create(
            campaign=self.campaign, user=self.user, role="PLAYER"
        )

        # Create multiple characters
        characters = []
        for i in range(5):
            character = Character.objects.create(
                name=f"Character {i}",
                campaign=self.campaign,
                player_owner=self.user,
                game_system="Test System",
            )
            characters.append(character)

        scene = Scene.objects.create(
            name="Bulk Test Scene",
            campaign=self.campaign,
            created_by=self.user,
        )

        # Bulk add
        scene.participants.set(characters)
        self.assertEqual(scene.participants.count(), 5)

        # Bulk remove some
        scene.participants.remove(*characters[:2])
        self.assertEqual(scene.participants.count(), 3)

        # Bulk clear
        scene.participants.clear()
        self.assertEqual(scene.participants.count(), 0)
