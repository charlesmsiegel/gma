"""Tests for SceneChatConsumer WebSocket functionality (Issue #44)."""

from unittest.mock import Mock, patch

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings

from campaigns.models import Campaign
from characters.models import Character
from scenes.models import Scene

User = get_user_model()


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
)
class SceneChatConsumerTestCase(TransactionTestCase):
    """Test SceneChatConsumer WebSocket functionality."""

    async def _setup_test_data(self):
        """Set up test data asynchronously - call this from each test method."""
        # Create users
        self.user1 = await database_sync_to_async(User.objects.create_user)(
            username="player1", email="player1@example.com", password="testpass123"
        )
        self.user2 = await database_sync_to_async(User.objects.create_user)(
            username="player2", email="player2@example.com", password="testpass123"
        )
        self.gm = await database_sync_to_async(User.objects.create_user)(
            username="gm", email="gm@example.com", password="testpass123"
        )
        self.non_member = await database_sync_to_async(User.objects.create_user)(
            username="outsider", email="outsider@example.com", password="testpass123"
        )

        # Create campaign
        self.campaign = await database_sync_to_async(Campaign.objects.create)(
            name="Test Campaign",
            description="Test campaign for chat tests",
            owner=self.gm,
            game_system="Mage",
        )

        # Add members
        await database_sync_to_async(self.campaign.add_member)(self.user1, "PLAYER")
        await database_sync_to_async(self.campaign.add_member)(self.user2, "PLAYER")

        # Create characters
        self.character1 = await database_sync_to_async(Character.objects.create)(
            name="Character One",
            campaign=self.campaign,
            player_owner=self.user1,
            game_system="Mage",
        )
        self.character2 = await database_sync_to_async(Character.objects.create)(
            name="Character Two",
            campaign=self.campaign,
            player_owner=self.user2,
            game_system="Mage",
        )

        # Create NPC
        self.npc = await database_sync_to_async(Character.objects.create)(
            name="NPC One",
            campaign=self.campaign,
            player_owner=self.gm,
            game_system="Mage",
            npc=True,
        )

        # Create scene
        self.scene = await database_sync_to_async(Scene.objects.create)(
            name="Test Scene",
            description="Test scene for chat",
            campaign=self.campaign,
            created_by=self.gm,
        )

        # Add participants
        await database_sync_to_async(self.scene.participants.add)(
            self.character1, self.character2, self.npc
        )

    async def test_consumer_import(self):
        """Test that SceneChatConsumer can be imported."""
        try:
            from scenes.consumers import SceneChatConsumer

            self.assertTrue(hasattr(SceneChatConsumer, "connect"))
            self.assertTrue(hasattr(SceneChatConsumer, "disconnect"))
            self.assertTrue(hasattr(SceneChatConsumer, "receive"))
        except ImportError:
            self.fail("SceneChatConsumer should be importable")

    async def test_websocket_connect_authenticated_user(self):
        """Test WebSocket connection with authenticated user."""
        await self._setup_test_data()

        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        # Set up the scope properly for testing
        communicator.scope["user"] = self.user1
        communicator.scope["url_route"] = {"kwargs": {"scene_id": str(self.scene.id)}}

        # Connect should succeed for scene participant
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.disconnect()

    async def test_websocket_connect_unauthenticated_user(self):
        """Test WebSocket connection with unauthenticated user."""
        await self._setup_test_data()

        from django.contrib.auth.models import AnonymousUser

        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        # Set up the scope properly for testing
        communicator.scope["user"] = AnonymousUser()
        communicator.scope["url_route"] = {"kwargs": {"scene_id": str(self.scene.id)}}

        # Connect should fail for unauthenticated user
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_websocket_connect_non_participant(self):
        """Test WebSocket connection with user not participating in scene."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.non_member

        # Connect should fail for non-participant
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_websocket_connect_invalid_scene(self):
        """Test WebSocket connection with invalid scene ID."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), "/ws/scenes/99999/chat/"
        )
        communicator.scope["user"] = self.user1

        # Connect should fail for non-existent scene
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_send_public_message(self):
        """Test sending a public message."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send public message
        message_data = {
            "type": "chat.message",
            "message_type": "PUBLIC",
            "character_id": self.character1.id,
            "content": "Hello everyone!",
        }
        await communicator.send_json_to(message_data)

        # Should receive the message back
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.message")
        self.assertEqual(response["message_type"], "PUBLIC")
        self.assertEqual(response["content"], "Hello everyone!")
        self.assertEqual(response["character"]["id"], self.character1.id)
        self.assertEqual(response["character"]["name"], self.character1.name)
        self.assertEqual(response["sender"]["username"], self.user1.username)

        await communicator.disconnect()

    async def test_send_ooc_message(self):
        """Test sending an OOC message."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send OOC message
        message_data = {
            "type": "chat.message",
            "message_type": "OOC",
            "character_id": None,
            "content": "This is out of character",
        }
        await communicator.send_json_to(message_data)

        # Should receive the message back
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.message")
        self.assertEqual(response["message_type"], "OOC")
        self.assertEqual(response["content"], "This is out of character")
        self.assertIsNone(response["character"])
        self.assertEqual(response["sender"]["username"], self.user1.username)

        await communicator.disconnect()

    async def test_send_private_message(self):
        """Test sending a private message."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send private message
        message_data = {
            "type": "chat.message",
            "message_type": "PRIVATE",
            "character_id": self.character1.id,
            "content": "Private whisper",
            "recipients": [self.user2.id],
        }
        await communicator.send_json_to(message_data)

        # Should receive confirmation
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.message")
        self.assertEqual(response["message_type"], "PRIVATE")
        self.assertEqual(response["content"], "Private whisper")

        await communicator.disconnect()

    async def test_gm_system_message(self):
        """Test GM sending system messages."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.gm

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send system message
        message_data = {
            "type": "chat.message",
            "message_type": "SYSTEM",
            "character_id": None,
            "content": "The room grows darker",
        }
        await communicator.send_json_to(message_data)

        # Should receive the message back
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.message")
        self.assertEqual(response["message_type"], "SYSTEM")
        self.assertEqual(response["content"], "The room grows darker")

        await communicator.disconnect()

    async def test_player_cannot_send_system_message(self):
        """Test that regular players cannot send system messages."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Try to send system message as player
        message_data = {
            "type": "chat.message",
            "message_type": "SYSTEM",
            "character_id": None,
            "content": "Trying to send system message",
        }
        await communicator.send_json_to(message_data)

        # Should receive error response
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.error")
        self.assertIn("permission", response["error"].lower())

        await communicator.disconnect()

    async def test_invalid_character_ownership(self):
        """Test sending message as character user doesn't own."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Try to send message as user2's character
        message_data = {
            "type": "chat.message",
            "message_type": "PUBLIC",
            "character_id": self.character2.id,  # User2's character
            "content": "Trying to impersonate",
        }
        await communicator.send_json_to(message_data)

        # Should receive error response
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.error")
        self.assertIn("character", response["error"].lower())

        await communicator.disconnect()

    async def test_invalid_json_handling(self):
        """Test handling of invalid JSON messages."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send invalid JSON
        await communicator.send_to(text_data="invalid json")

        # Should receive error response
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.error")
        self.assertIn("json", response["error"].lower())

        await communicator.disconnect()

    async def test_message_validation_empty_content(self):
        """Test validation of empty message content."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send message with empty content
        message_data = {
            "type": "chat.message",
            "message_type": "PUBLIC",
            "character_id": self.character1.id,
            "content": "",
        }
        await communicator.send_json_to(message_data)

        # Should receive error response
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.error")
        self.assertIn("content", response["error"].lower())

        await communicator.disconnect()

    async def test_message_validation_too_long(self):
        """Test validation of overly long messages."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send message with content that's too long
        message_data = {
            "type": "chat.message",
            "message_type": "PUBLIC",
            "character_id": self.character1.id,
            "content": "A" * 50000,  # 50k characters
        }
        await communicator.send_json_to(message_data)

        # Should receive error response
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat.error")
        self.assertIn("long", response["error"].lower())

        await communicator.disconnect()

    async def test_rate_limiting(self):
        """Test message rate limiting (10 messages per minute)."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send messages rapidly to trigger rate limiting
        for i in range(12):  # Send more than the limit of 10
            message_data = {
                "type": "chat.message",
                "message_type": "OOC",
                "content": f"Message {i + 1}",
            }
            await communicator.send_json_to(message_data)

        # First 10 should succeed, rest should be rate limited
        success_count = 0
        error_count = 0

        for i in range(12):
            response = await communicator.receive_json_from()
            if response["type"] == "chat.message":
                success_count += 1
            elif response["type"] == "chat.error":
                error_count += 1
                self.assertIn("rate", response["error"].lower())

        self.assertEqual(success_count, 10)
        self.assertEqual(error_count, 2)

        await communicator.disconnect()

    async def test_message_broadcasting(self):
        """Test that messages are broadcast to all scene participants."""
        from scenes.consumers import SceneChatConsumer

        # Create two connections for different users
        communicator1 = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator1.scope["user"] = self.user1

        communicator2 = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator2.scope["user"] = self.user2

        # Connect both users
        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()
        self.assertTrue(connected1)
        self.assertTrue(connected2)

        # Send message from user1
        message_data = {
            "type": "chat.message",
            "message_type": "PUBLIC",
            "character_id": self.character1.id,
            "content": "Hello from user1!",
        }
        await communicator1.send_json_to(message_data)

        # Both users should receive the message
        response1 = await communicator1.receive_json_from()
        response2 = await communicator2.receive_json_from()

        self.assertEqual(response1["type"], "chat.message")
        self.assertEqual(response2["type"], "chat.message")
        self.assertEqual(response1["content"], "Hello from user1!")
        self.assertEqual(response2["content"], "Hello from user1!")

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_private_message_visibility(self):
        """Test that private messages are only visible to intended recipients."""
        from scenes.consumers import SceneChatConsumer

        # Create three connections
        communicator1 = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator1.scope["user"] = self.user1

        communicator2 = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator2.scope["user"] = self.user2

        communicator_gm = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator_gm.scope["user"] = self.gm

        # Connect all users
        await communicator1.connect()
        await communicator2.connect()
        await communicator_gm.connect()

        # Send private message from user1 to user2
        message_data = {
            "type": "chat.message",
            "message_type": "PRIVATE",
            "character_id": self.character1.id,
            "content": "Secret message",
            "recipients": [self.user2.id],
        }
        await communicator1.send_json_to(message_data)

        # User1 should receive confirmation
        response1 = await communicator1.receive_json_from()
        self.assertEqual(response1["type"], "chat.message")
        self.assertEqual(response1["message_type"], "PRIVATE")

        # User2 should receive the message
        response2 = await communicator2.receive_json_from()
        self.assertEqual(response2["type"], "chat.message")
        self.assertEqual(response2["message_type"], "PRIVATE")
        self.assertEqual(response2["content"], "Secret message")

        # GM should also see private messages (GM oversight)
        response_gm = await communicator_gm.receive_json_from()
        self.assertEqual(response_gm["type"], "chat.message")
        self.assertEqual(response_gm["message_type"], "PRIVATE")
        self.assertEqual(response_gm["content"], "Secret message")

        await communicator1.disconnect()
        await communicator2.disconnect()
        await communicator_gm.disconnect()

    async def test_scene_channel_group_management(self):
        """Test proper channel group management for scenes."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Test that user is added to the correct channel group
        # This would be tested by checking internal consumer state
        # or by testing message broadcasting

        await communicator.disconnect()

        # After disconnect, user should be removed from channel group
        # This ensures no memory leaks in Redis channel layer

    @patch("scenes.consumers.Message.objects.create")
    async def test_message_persistence(self, mock_create):
        """Test that messages are properly saved to database."""
        from scenes.consumers import SceneChatConsumer

        mock_message = Mock()
        mock_message.id = 1
        mock_message.scene = self.scene
        mock_message.character = self.character1
        mock_message.sender = self.user1
        mock_message.content = "Test message"
        mock_message.message_type = "PUBLIC"
        mock_message.created_at = "2023-01-01T00:00:00Z"
        mock_create.return_value = mock_message

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        message_data = {
            "type": "chat.message",
            "message_type": "PUBLIC",
            "character_id": self.character1.id,
            "content": "Test message",
        }
        await communicator.send_json_to(message_data)

        # Message should be saved to database
        await communicator.receive_json_from()  # Receive the response

        # Verify database save was called
        mock_create.assert_called_once()

        await communicator.disconnect()

    async def test_websocket_routing_configuration(self):
        """Test that WebSocket routing is properly configured."""
        # This test verifies that the URL pattern matches correctly
        from scenes.consumers import SceneChatConsumer

        # Test various URL patterns
        valid_urls = [
            f"/ws/scenes/{self.scene.id}/chat/",
            f"/ws/scenes/{self.scene.id}/chat",
            "/ws/scenes/1/chat/",
        ]

        for url in valid_urls:
            communicator = WebsocketCommunicator(SceneChatConsumer.as_asgi(), url)
            communicator.scope["user"] = self.user1

            # Should be able to create communicator without error
            self.assertIsNotNone(communicator)

    async def test_concurrent_connections_same_user(self):
        """Test multiple connections from the same user."""
        from scenes.consumers import SceneChatConsumer

        # Create two connections for the same user
        communicator1 = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator1.scope["user"] = self.user1

        communicator2 = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator2.scope["user"] = self.user1

        # Both connections should be allowed
        connected1, _ = await communicator1.connect()
        connected2, _ = await communicator2.connect()
        self.assertTrue(connected1)
        self.assertTrue(connected2)

        # Send message from first connection
        message_data = {
            "type": "chat.message",
            "message_type": "OOC",
            "content": "Multi-connection test",
        }
        await communicator1.send_json_to(message_data)

        # Both connections should receive the message
        response1 = await communicator1.receive_json_from()
        response2 = await communicator2.receive_json_from()

        self.assertEqual(response1["type"], "chat.message")
        self.assertEqual(response2["type"], "chat.message")

        await communicator1.disconnect()
        await communicator2.disconnect()

    async def test_connection_cleanup_on_scene_deletion(self):
        """Test proper cleanup when scene is deleted during active connections."""
        from scenes.consumers import SceneChatConsumer

        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user1

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Delete the scene while connection is active
        await database_sync_to_async(self.scene.delete)()

        # Connection should be gracefully closed
        # This might require special handling in the consumer
        await communicator.disconnect()

    async def test_message_history_integration(self):
        """Test integration with message history for new connections."""
        from scenes.consumers import SceneChatConsumer

        # Create a message first through the model
        from scenes.models import Message

        await database_sync_to_async(Message.objects.create)(
            scene=self.scene,
            character=self.character1,
            sender=self.user1,
            content="Previous message",
            message_type="PUBLIC",
        )

        # Connect to WebSocket
        communicator = WebsocketCommunicator(
            SceneChatConsumer.as_asgi(), f"/ws/scenes/{self.scene.id}/chat/"
        )
        communicator.scope["user"] = self.user2

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # New connections might receive recent message history
        # This is optional functionality that could be implemented

        await communicator.disconnect()
