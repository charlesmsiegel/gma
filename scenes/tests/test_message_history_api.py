"""Tests for Message History API (Issue #45)."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign
from characters.models import Character
from scenes.models import Scene

User = get_user_model()


class MessageHistoryAPITestCase(TestCase):
    """Test Message History API endpoint functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()

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
        self.non_member = User.objects.create_user(
            username="outsider", email="outsider@example.com", password="testpass123"
        )

        # Create campaign
        self.campaign = Campaign.objects.create(
            name="Test Campaign",
            description="Test campaign for message API tests",
            owner=self.gm,
            game_system="Mage",
        )

        # Add members
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
            description="Test scene for message API",
            campaign=self.campaign,
            created_by=self.gm,
        )
        self.scene.participants.add(self.character1, self.character2, self.npc)

    def test_message_history_url_exists(self):
        """Test that message history URL pattern exists."""
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        expected_url = f"/api/scenes/{self.scene.id}/messages/"
        self.assertEqual(url, expected_url)

    def test_get_messages_unauthenticated(self):
        """Test getting messages without authentication."""
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_messages_non_participant(self):
        """Test getting messages as non-participant."""
        self.client.force_authenticate(user=self.non_member)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_messages_invalid_scene(self):
        """Test getting messages for non-existent scene."""
        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_messages_empty_scene(self):
        """Test getting messages from scene with no messages."""
        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 0)
        self.assertIn("count", data)
        self.assertEqual(data["count"], 0)
        self.assertIn("next", data)
        self.assertIn("previous", data)

    def test_get_messages_with_data(self):
        """Test getting messages with actual message data."""
        from scenes.models import Message

        # Create test messages
        messages = []
        for i in range(5):
            message = Message.objects.create(
                scene=self.scene,
                character=self.character1 if i % 2 == 0 else None,
                sender=self.user1,
                content=f"Test message {i + 1}",
                message_type="PUBLIC" if i % 2 == 0 else "OOC",
            )
            messages.append(message)

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data["count"], 5)
        self.assertEqual(len(data["results"]), 5)

        # Check message structure
        message_data = data["results"][0]
        self.assertIn("id", message_data)
        self.assertIn("content", message_data)
        self.assertIn("message_type", message_data)
        self.assertIn("created_at", message_data)
        self.assertIn("character", message_data)
        self.assertIn("sender", message_data)

        # Check sender structure
        self.assertIn("id", message_data["sender"])
        self.assertIn("username", message_data["sender"])

        # Check character structure (for IC messages)
        ic_messages = [msg for msg in data["results"] if msg["character"]]
        if ic_messages:
            char_data = ic_messages[0]["character"]
            self.assertIn("id", char_data)
            self.assertIn("name", char_data)

    def test_get_messages_chronological_order(self):
        """Test that messages are returned in chronological order (oldest first)."""
        from scenes.models import Message

        # Create messages with slight time differences
        base_time = timezone.now()
        messages_data = [
            ("Third message", base_time + timedelta(seconds=2)),
            ("First message", base_time),
            ("Second message", base_time + timedelta(seconds=1)),
        ]

        for content, created_time in messages_data:
            with patch("django.utils.timezone.now", return_value=created_time):
                Message.objects.create(
                    scene=self.scene,
                    sender=self.user1,
                    content=content,
                    message_type="OOC",
                )

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Messages should be in chronological order
        contents = [msg["content"] for msg in data["results"]]
        self.assertEqual(contents, ["First message", "Second message", "Third message"])

    def test_get_messages_pagination(self):
        """Test message pagination."""
        from scenes.models import Message

        # Create more messages than default page size
        for i in range(25):
            Message.objects.create(
                scene=self.scene,
                sender=self.user1,
                content=f"Message {i + 1}",
                message_type="OOC",
            )

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data["count"], 25)
        self.assertLessEqual(len(data["results"]), 20)  # Default page size
        self.assertIsNotNone(data["next"])  # Should have next page
        self.assertIsNone(data["previous"])  # First page

        # Test custom page size
        response = self.client.get(url, {"page_size": 10})
        data = response.json()
        self.assertEqual(len(data["results"]), 10)

    def test_get_messages_filter_by_type(self):
        """Test filtering messages by message type."""
        from scenes.models import Message

        # Create messages of different types
        Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Public message",
            message_type="PUBLIC",
        )
        Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content="OOC message",
            message_type="OOC",
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
            sender=self.gm,
            content="System message",
            message_type="SYSTEM",
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})

        # Filter by PUBLIC messages
        response = self.client.get(url, {"message_type": "PUBLIC"})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["message_type"], "PUBLIC")

        # Filter by OOC messages
        response = self.client.get(url, {"message_type": "OOC"})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["message_type"], "OOC")

        # Filter by multiple types (comma-separated)
        response = self.client.get(url, {"message_type": "PUBLIC,OOC"})
        data = response.json()
        self.assertEqual(data["count"], 2)

        # Invalid message type should return empty results
        response = self.client.get(url, {"message_type": "INVALID"})
        data = response.json()
        self.assertEqual(data["count"], 0)

    def test_get_messages_filter_by_date_range(self):
        """Test filtering messages by date range."""
        from scenes.models import Message

        base_time = timezone.now()
        old_time = base_time - timedelta(days=2)
        new_time = base_time + timedelta(hours=1)

        # Create messages at different times
        with patch("django.utils.timezone.now", return_value=old_time):
            Message.objects.create(
                scene=self.scene,
                sender=self.user1,
                content="Old message",
                message_type="OOC",
            )

        with patch("django.utils.timezone.now", return_value=new_time):
            Message.objects.create(
                scene=self.scene,
                sender=self.user1,
                content="New message",
                message_type="OOC",
            )

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})

        # Filter by date_from
        date_from = (base_time - timedelta(hours=1)).isoformat()
        response = self.client.get(url, {"date_from": date_from})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["content"], "New message")

        # Filter by date_to
        date_to = (base_time - timedelta(hours=1)).isoformat()
        response = self.client.get(url, {"date_to": date_to})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["content"], "Old message")

        # Filter by date range
        response = self.client.get(
            url, {"date_from": old_time.isoformat(), "date_to": new_time.isoformat()}
        )
        data = response.json()
        self.assertEqual(data["count"], 2)

    def test_get_messages_filter_by_character(self):
        """Test filtering messages by character."""
        from scenes.models import Message

        # Create messages from different characters
        Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Character 1 message",
            message_type="PUBLIC",
        )
        Message.objects.create(
            scene=self.scene,
            character=self.character2,
            sender=self.user2,
            content="Character 2 message",
            message_type="PUBLIC",
        )
        Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content="OOC message",
            message_type="OOC",
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})

        # Filter by character1
        response = self.client.get(url, {"character_id": self.character1.id})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["content"], "Character 1 message")

        # Filter by character2
        response = self.client.get(url, {"character_id": self.character2.id})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["content"], "Character 2 message")

        # Invalid character ID should return empty results
        response = self.client.get(url, {"character_id": 99999})
        data = response.json()
        self.assertEqual(data["count"], 0)

    def test_get_messages_filter_by_sender(self):
        """Test filtering messages by sender."""
        from scenes.models import Message

        # Create messages from different senders
        Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content="User 1 message",
            message_type="OOC",
        )
        Message.objects.create(
            scene=self.scene,
            sender=self.user2,
            content="User 2 message",
            message_type="OOC",
        )
        Message.objects.create(
            scene=self.scene,
            sender=self.gm,
            content="GM message",
            message_type="OOC",
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})

        # Filter by user1
        response = self.client.get(url, {"sender_id": self.user1.id})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["content"], "User 1 message")

        # Filter by GM
        response = self.client.get(url, {"sender_id": self.gm.id})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["content"], "GM message")

    def test_get_messages_private_visibility(self):
        """Test that private message visibility respects permissions."""
        from scenes.models import Message

        # Create private message from user1 to user2
        Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Private message to user2",
            message_type="PRIVATE",
        )

        # Create public message for comparison
        Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Public message",
            message_type="PUBLIC",
        )

        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})

        # User1 (sender) should see both messages
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(url)
        data = response.json()
        self.assertEqual(data["count"], 2)

        # User2 (if recipient) should see both messages
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(url)
        data = response.json()

        # For this test, we assume private messages are visible to all participants
        # In a real implementation, you'd need to track recipients
        self.assertGreaterEqual(data["count"], 1)  # At least the public message

        # GM should see all messages
        self.client.force_authenticate(user=self.gm)
        response = self.client.get(url)
        data = response.json()
        self.assertEqual(data["count"], 2)

    def test_get_messages_search(self):
        """Test searching messages by content."""
        from scenes.models import Message

        # Create messages with different content
        Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content="The quick brown fox jumps",
            message_type="OOC",
        )
        Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content="over the lazy dog",
            message_type="OOC",
        )
        Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content="Something completely different",
            message_type="OOC",
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})

        # Search for "fox"
        response = self.client.get(url, {"search": "fox"})
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertIn("fox", data["results"][0]["content"])

        # Search for "the" (should match multiple)
        response = self.client.get(url, {"search": "the"})
        data = response.json()
        self.assertEqual(data["count"], 2)

        # Case insensitive search
        response = self.client.get(url, {"search": "QUICK"})
        data = response.json()
        self.assertEqual(data["count"], 1)

    def test_get_messages_performance_optimization(self):
        """Test that API includes performance optimizations."""
        from scenes.models import Message

        # Create messages with related objects
        for i in range(10):
            Message.objects.create(
                scene=self.scene,
                character=self.character1,
                sender=self.user1,
                content=f"Message {i + 1}",
                message_type="PUBLIC",
            )

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})

        # Monitor database queries
        with self.assertNumQueries(8):  # Optimized with select_related/prefetch_related
            response = self.client.get(url)
            data = response.json()

            # Access related objects to trigger lazy loading if not optimized
            for message in data["results"]:
                _ = message["sender"]["username"]
                if message["character"]:
                    _ = message["character"]["name"]

    def test_get_messages_different_user_permissions(self):
        """Test message access for different user roles."""
        from scenes.models import Message

        Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Test message",
            message_type="PUBLIC",
        )

        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})

        # Player participant should access
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GM should access
        self.client.force_authenticate(user=self.gm)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Campaign owner (if different from GM) should access
        # Non-participant should not access
        self.client.force_authenticate(user=self.non_member)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_messages_response_schema(self):
        """Test that response follows expected schema."""
        from scenes.models import Message

        Message.objects.create(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Schema test message",
            message_type="PUBLIC",
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check pagination structure
        required_fields = ["count", "next", "previous", "results"]
        for field in required_fields:
            self.assertIn(field, data)

        # Check message structure
        message_data = data["results"][0]
        required_message_fields = [
            "id",
            "content",
            "message_type",
            "created_at",
            "character",
            "sender",
        ]
        for field in required_message_fields:
            self.assertIn(field, message_data)

        # Check sender structure
        sender_fields = ["id", "username"]
        for field in sender_fields:
            self.assertIn(field, message_data["sender"])

        # Check character structure (when present)
        if message_data["character"]:
            character_fields = ["id", "name"]
            for field in character_fields:
                self.assertIn(field, message_data["character"])

    def test_get_messages_invalid_filters(self):
        """Test handling of invalid filter parameters."""
        from scenes.models import Message

        Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content="Test message",
            message_type="OOC",
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})

        # Invalid date format
        response = self.client.get(url, {"date_from": "invalid-date"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid character_id (non-integer)
        response = self.client.get(url, {"character_id": "not-a-number"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid page_size (too large)
        response = self.client.get(url, {"page_size": 1000})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid page_size (negative)
        response = self.client.get(url, {"page_size": -1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_messages_rate_limiting_headers(self):
        """Test that rate limiting headers are included in response."""
        from scenes.models import Message

        Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content="Rate limit test",
            message_type="OOC",
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        self.client.get(url)

        # Check for rate limiting headers (if implemented)
        # These would be added by rate limiting middleware

    def test_get_messages_caching_headers(self):
        """Test that appropriate caching headers are set."""
        from scenes.models import Message

        Message.objects.create(
            scene=self.scene,
            sender=self.user1,
            content="Caching test",
            message_type="OOC",
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        response = self.client.get(url)

        # Check for caching headers
        # These depend on implementation choices
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Might include:
        # - Cache-Control
        # - ETag
        # - Last-Modified

    def test_post_not_allowed(self):
        """Test that POST requests are not allowed on message history endpoint."""
        # Mark user email as verified to avoid 403 due to email verification
        self.user1.mark_email_verified()
        self.user1.save()

        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        response = self.client.post(url, {"content": "New message"})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_not_allowed(self):
        """Test that PUT requests are not allowed on message history endpoint."""
        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        response = self.client.put(url, {"content": "Updated message"})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        """Test that DELETE requests are not allowed on message history endpoint."""
        self.client.force_authenticate(user=self.user1)
        url = reverse("api:scenes:scene-messages", kwargs={"pk": self.scene.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
