"""Tests for Message model (Issue #43)."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from campaigns.models import Campaign
from characters.models import Character
from scenes.models import Scene

User = get_user_model()


class MessageModelTestCase(TestCase):
    """Test Message model functionality."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.user1 = User.objects.create_user(
            username="player1", email="player1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="player2", email="player2@example.com", password="testpass123"
        )
        self.gm = User.objects.create_user(
            username="gm", email="gm@example.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            description="Test campaign for message tests",
            owner=self.gm,
            game_system="Mage",
        )

        # Add users as members
        self.campaign.add_member(self.user1, "PLAYER")
        self.campaign.add_member(self.user2, "PLAYER")

        # Create characters
        self.character1 = Character.objects.create(
            name="Character One",
            campaign=self.campaign,
            player_owner=self.user1,
            game_system="Mage",
        )
        self.character2 = Character.objects.create(
            name="Character Two",
            campaign=self.campaign,
            player_owner=self.user2,
            game_system="Mage",
        )

        # Create NPC
        self.npc = Character.objects.create(
            name="NPC One",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage",
            npc=True,
        )

        # Create scene
        self.scene = Scene.objects.create(
            name="Test Scene",
            description="Test scene for message tests",
            campaign=self.campaign,
            created_by=self.gm,
        )
        self.scene.participants.add(self.character1, self.character2, self.npc)

    def test_message_model_exists(self):
        """Test that Message model exists and can be imported."""
        from scenes.models import Message

        self.assertTrue(hasattr(Message, "objects"))

    def test_message_creation_public(self):
        """Test creating a public message."""
        from scenes.models import Message

        message = Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="This is a public message",
            message_type="PUBLIC",
        )

        self.assertEqual(message.scene, self.scene)
        self.assertEqual(message.character, self.character1)
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.content, "This is a public message")
        self.assertEqual(message.message_type, "PUBLIC")
        self.assertIsNotNone(message.created_at)
        self.assertTrue(message.created_at <= timezone.now())

    def test_message_creation_ooc(self):
        """Test creating an OOC message without character."""
        from scenes.models import Message

        message = Message.objects.create(
            scene=self.scene,
            character=None,  # OOC messages don't have character attribution
            sender=self.user1,
            content="This is an OOC message",
            message_type="OOC",
        )

        self.assertEqual(message.scene, self.scene)
        self.assertIsNone(message.character)
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.content, "This is an OOC message")
        self.assertEqual(message.message_type, "OOC")

    def test_message_creation_private(self):
        """Test creating a private message."""
        from scenes.models import Message

        message = Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="This is a private message",
            message_type="PRIVATE",
        )

        self.assertEqual(message.message_type, "PRIVATE")

    def test_message_creation_system(self):
        """Test creating a system message."""
        from scenes.models import Message

        message = Message.objects.create(
            scene=self.scene,
            character=None,
            sender=self.gm,
            content="Character One enters the room",
            message_type="SYSTEM",
        )

        self.assertEqual(message.message_type, "SYSTEM")
        self.assertIsNone(message.character)

    def test_message_required_fields(self):
        """Test that required fields are enforced."""
        from django.db import transaction

        from scenes.models import Message

        # Scene is required
        with self.assertRaises((IntegrityError, ValidationError)):
            try:
                with transaction.atomic():
                    Message.objects.create(
                        scene=None,
                        sender=self.user1,
                        content="Test message",
                        message_type="PUBLIC",
                    )
            except Exception as e:
                raise e

        # Sender is required - but now it's nullable, so this won't fail at DB level
        # Instead test that it can be created but validation fails
        with self.assertRaises(ValidationError):
            message = Message(
                scene=self.scene,
                sender=None,
                content="Test message",
                message_type="PUBLIC",
            )
            message.full_clean()

        # Content is required
        with self.assertRaises(ValidationError):
            message = Message(
                scene=self.scene,
                sender=self.user1,
                content="",
                message_type="PUBLIC",
            )
            message.full_clean()

        # Invalid message type should fail
        with self.assertRaises(ValidationError):
            message = Message(
                scene=self.scene,
                sender=self.user1,
                content="Test message",
                message_type="INVALID",
            )
            message.full_clean()

    def test_message_content_validation(self):
        """Test message content validation."""
        from scenes.models import Message

        # Empty content should fail
        with self.assertRaises(ValidationError):
            message = Message(
                scene=self.scene,
                sender=self.user1,
                content="",
                message_type="PUBLIC",
            )
            message.full_clean()

        # Very long content should be allowed but reasonable limit
        long_content = "A" * 10000  # 10k characters
        message = Message(
            scene=self.scene,
            sender=self.user1,
            content=long_content,
            message_type="PUBLIC",
        )
        message.full_clean()  # Should not raise

        # Extremely long content should fail
        with self.assertRaises(ValidationError):
            very_long_content = "A" * 50000  # 50k characters
            message = Message(
                scene=self.scene,
                sender=self.user1,
                content=very_long_content,
                message_type="PUBLIC",
            )
            message.full_clean()

    def test_message_type_choices(self):
        """Test message type choices are enforced."""
        from scenes.models import Message

        # Test valid message types - use appropriate user for each type
        user_types = [
            ("PUBLIC", self.user1),
            ("PRIVATE", self.user1),
            ("SYSTEM", self.gm),  # Only GMs can send system messages
            ("OOC", self.user1),
        ]
        for message_type, sender in user_types:
            message = Message(
                scene=self.scene,
                sender=sender,
                content=f"Test {message_type} message",
                message_type=message_type,
            )
            message.full_clean()  # Should not raise

        # Invalid message type should fail
        with self.assertRaises(ValidationError):
            message = Message(
                scene=self.scene,
                sender=self.user1,
                content="Test message",
                message_type="INVALID_TYPE",
            )
            message.full_clean()

    def test_character_scene_validation(self):
        """Test that character belongs to the scene's campaign."""
        from scenes.models import Message

        # Create a character from different campaign
        other_campaign = Campaign.objects.create(
            name="Other Campaign",
            description="Different campaign",
            owner=self.gm,
            game_system="Vampire",
        )
        # Add user1 as member so they can own characters in this campaign
        other_campaign.add_member(self.user1, "PLAYER")
        other_character = Character.objects.create(
            name="Other Character",
            campaign=other_campaign,
            player_owner=self.user1,
            game_system="Vampire",
        )

        # Character from different campaign should fail validation
        with self.assertRaises(ValidationError):
            message = Message(
                scene=self.scene,
                character=other_character,
                sender=self.user1,
                content="Test message",
                message_type="PUBLIC",
            )
            message.full_clean()

    def test_character_ownership_validation(self):
        """Test that sender owns the character (for IC messages)."""
        from scenes.models import Message

        # User1 sending message as their own character should work
        message = Message(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Test message",
            message_type="PUBLIC",
        )
        message.full_clean()  # Should not raise

        # User1 sending message as user2's character should fail
        with self.assertRaises(ValidationError):
            message = Message(
                scene=self.scene,
                character=self.character2,  # User2's character
                sender=self.user1,  # User1 as sender
                content="Test message",
                message_type="PUBLIC",
            )
            message.full_clean()

        # GM should be able to send as NPC
        message = Message(
            scene=self.scene,
            character=self.npc,
            sender=self.gm,
            content="NPC message",
            message_type="PUBLIC",
        )
        message.full_clean()  # Should not raise

        # GM should be able to send as any character (GM privileges)
        message = Message(
            scene=self.scene,
            character=self.character1,
            sender=self.gm,
            content="GM override message",
            message_type="SYSTEM",
        )
        message.full_clean()  # Should not raise for GMs

    def test_ooc_messages_no_character(self):
        """Test that OOC messages cannot have character attribution."""
        from scenes.models import Message

        # OOC message with character should fail
        with self.assertRaises(ValidationError):
            message = Message(
                scene=self.scene,
                character=self.character1,  # OOC shouldn't have character
                sender=self.user1,
                content="OOC message",
                message_type="OOC",
            )
            message.full_clean()

    def test_system_messages_validation(self):
        """Test system message validation rules."""
        from scenes.models import Message

        # System messages can have character (e.g., "Character enters")
        message = Message(
            scene=self.scene,
            character=self.character1,
            sender=self.gm,
            content="Character One enters the room",
            message_type="SYSTEM",
        )
        message.full_clean()  # Should not raise

        # System messages without character should also work
        message = Message(
            scene=self.scene,
            character=None,
            sender=self.gm,
            content="The room grows darker",
            message_type="SYSTEM",
        )
        message.full_clean()  # Should not raise

        # Only GMs should be able to create system messages
        with self.assertRaises(ValidationError):
            message = Message(
                scene=self.scene,
                character=None,
                sender=self.user1,  # Regular player
                content="System message",
                message_type="SYSTEM",
            )
            message.full_clean()

    def test_message_ordering(self):
        """Test that messages are ordered by creation time."""
        from scenes.models import Message

        # Create messages with slight time delay
        message1 = Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content="First message",
            message_type="OOC",
        )

        message2 = Message.objects.create(
            scene=self.scene,
            sender=self.user2,
            content="Second message",
            message_type="OOC",
        )

        # Fetch messages in default order
        messages = list(Message.objects.filter(scene=self.scene))
        self.assertEqual(messages[0], message1)
        self.assertEqual(messages[1], message2)

        # Test that created_at is properly set
        self.assertLess(message1.created_at, message2.created_at)

    def test_message_str_representation(self):
        """Test message string representation."""
        from scenes.models import Message

        # Message with character
        message = Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Test message",
            message_type="PUBLIC",
        )
        expected = f"[{self.scene.name}] {self.character1.name}: Test message"
        self.assertEqual(str(message), expected)

        # OOC message without character
        ooc_message = Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content="OOC message",
            message_type="OOC",
        )
        expected_ooc = f"[{self.scene.name}] {self.user1.username} (OOC): OOC message"
        self.assertEqual(str(ooc_message), expected_ooc)

    def test_message_queryset_methods(self):
        """Test custom queryset methods."""
        from scenes.models import Message

        # Create various message types
        Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Public message",
            message_type="PUBLIC",
        )

        Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Private message",
            message_type="PRIVATE",
        )

        Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content="OOC message",
            message_type="OOC",
        )

        Message.objects.create(
            scene=self.scene,
            sender=self.gm,
            content="System message",
            message_type="SYSTEM",
        )

        # Test filtering by message type
        public_messages = Message.objects.filter(message_type="PUBLIC")
        self.assertEqual(public_messages.count(), 1)

        private_messages = Message.objects.filter(message_type="PRIVATE")
        self.assertEqual(private_messages.count(), 1)

        # Test filtering by scene
        scene_messages = Message.objects.filter(scene=self.scene)
        self.assertEqual(scene_messages.count(), 4)

        # Test filtering by sender
        user1_messages = Message.objects.filter(sender=self.user1)
        self.assertEqual(user1_messages.count(), 3)

    def test_message_meta_properties(self):
        """Test Message model meta properties."""
        from scenes.models import Message

        # Check table name
        self.assertEqual(Message._meta.db_table, "scenes_message")

        # Check ordering
        self.assertEqual(Message._meta.ordering, ["created_at"])

        # Check verbose names
        self.assertEqual(Message._meta.verbose_name, "Message")
        self.assertEqual(Message._meta.verbose_name_plural, "Messages")

    def test_message_database_indexes(self):
        """Test that proper database indexes exist."""
        from scenes.models import Message

        # Check that indexes are defined for performance
        indexes = Message._meta.indexes
        index_fields = [tuple(index.fields) for index in indexes]

        # Should have indexes for common query patterns
        expected_indexes = [
            ("scene", "created_at"),
            ("sender", "created_at"),
            ("message_type", "created_at"),
            ("scene", "message_type"),
        ]

        for expected_index in expected_indexes:
            self.assertIn(expected_index, index_fields)

    def test_message_cascade_deletion(self):
        """Test cascade behavior when related objects are deleted."""
        from scenes.models import Message

        message = Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Test message",
            message_type="PUBLIC",
        )

        # Delete character - message should remain but character should be None
        self.character1.delete()
        message.refresh_from_db()
        self.assertIsNone(message.character)

        # Delete scene - message should be deleted
        scene_id = self.scene.id
        self.scene.delete()
        with self.assertRaises(Message.DoesNotExist):
            Message.objects.get(scene_id=scene_id)

        # Create new message to test user deletion
        new_scene = Scene.objects.create(
            name="New Scene",
            campaign=self.campaign,
            created_by=self.gm,
        )
        message2 = Message.objects.create(
            scene=new_scene,
            sender=self.user2,
            content="Test message 2",
            message_type="OOC",
        )

        # Delete user - message should remain but sender should be None
        self.user2.delete()
        message2.refresh_from_db()
        self.assertIsNone(message2.sender)

    def test_message_permissions_integration(self):
        """Test integration with scene permissions."""
        from scenes.models import Message

        # This test verifies that message creation respects scene participation
        # The actual permission checking will be in the view/API layer
        # Create message for participating character
        message = Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Test message",
            message_type="PUBLIC",
        )
        self.assertIsNotNone(message.pk)

        # Test that we can check if sender's character participates in scene
        self.assertIn(self.character1, self.scene.participants.all())
        self.assertIn(self.character2, self.scene.participants.all())

    def test_message_content_sanitization_ready(self):
        """Test that message content can handle various inputs safely."""
        from scenes.models import Message

        # Test HTML content (should be stored as-is, sanitized at display)
        html_content = "<script>alert('xss')</script>Hello <b>world</b>"
        message = Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content=html_content,
            message_type="OOC",
        )
        self.assertEqual(message.content, html_content)

        # Test Unicode content
        unicode_content = "Hello 世界 🎲 ñoño"
        message2 = Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content=unicode_content,
            message_type="OOC",
        )
        self.assertEqual(message2.content, unicode_content)

        # Test newlines and formatting
        multiline_content = "Line 1\nLine 2\n\nLine 4"
        message3 = Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content=multiline_content,
            message_type="OOC",
        )
        self.assertEqual(message3.content, multiline_content)

    def test_message_bulk_operations(self):
        """Test bulk operations on messages."""
        from scenes.models import Message

        # Create multiple messages
        messages_data = [
            {"content": f"Message {i}", "sender": self.user1, "message_type": "OOC"}
            for i in range(5)
        ]

        messages = []
        for data in messages_data:
            message = Message(scene=self.scene, **data)
            messages.append(message)

        # Bulk create
        Message.objects.bulk_create(messages)

        # Verify all messages were created
        scene_message_count = Message.objects.filter(scene=self.scene).count()
        self.assertEqual(scene_message_count, 5)

        # Test bulk filtering
        ooc_messages = Message.objects.filter(scene=self.scene, message_type="OOC")
        self.assertEqual(ooc_messages.count(), 5)
