"""WebSocket consumers for scene chat functionality (Issue #44)."""

import json
import logging
from typing import Any, Dict, Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from .models import Message, Scene

User = get_user_model()
logger = logging.getLogger(__name__)


class SceneChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for scene-based chat."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scene_id: Optional[int] = None
        self.scene: Optional[Scene] = None
        self.room_group_name: Optional[str] = None
        self.user = None

    async def connect(self):
        """Handle WebSocket connection."""
        # Get scene ID from URL
        url_route = self.scope.get("url_route")
        if url_route and "kwargs" in url_route:
            self.scene_id = url_route["kwargs"]["scene_id"]
        else:
            # For testing, might be in path_info
            path = self.scope.get("path", "")
            import re

            match = re.search(r"/ws/scenes/(\d+)/chat/", path)
            if match:
                self.scene_id = int(match.group(1))
            else:
                await self.close()
                return

        self.user = self.scope["user"]

        # Reject unauthenticated users
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        try:
            # Get scene and validate user has access
            self.scene = await self.get_scene()
            if not await self.user_can_access_scene():
                await self.close()
                return

            # Join room group
            self.room_group_name = f"scene_chat_{self.scene_id}"
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

            await self.accept()
            logger.info(
                f"User {self.user.username} connected to scene {self.scene_id} chat"
            )

        except Scene.DoesNotExist:
            await self.close()
            return
        except Exception as e:
            logger.error(f"Error connecting to scene chat: {e}")
            await self.close()
            return

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

        logger.info(
            f"User {self.user.username if self.user else 'Unknown'} "
            f"disconnected from scene {self.scene_id} chat"
        )

    async def receive(self, text_data):
        """Handle message from WebSocket."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "chat.message":
                await self.handle_chat_message(data)
            else:
                await self.send_error(f"Unknown message type: {message_type}")

        except json.JSONDecodeError as e:
            await self.send_error(f"Invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.send_error("Internal server error")

    async def handle_chat_message(self, data: Dict[str, Any]):
        """Handle chat message from user."""
        try:
            # Extract message data
            content = data.get("content", "").strip()
            msg_type = data.get("message_type", "PUBLIC")
            character_id = data.get("character_id")
            recipients = data.get("recipients", [])

            # Validate message content
            if not content:
                await self.send_error("Message content cannot be empty")
                return

            if len(content) > 20000:
                await self.send_error("Message too long")
                return

            # Get character if provided
            character = None
            if character_id:
                character = await self.get_character(character_id)
                if not character:
                    await self.send_error("Character not found")
                    return

            # Validate message type and character requirements
            if msg_type == "PUBLIC" and not character:
                await self.send_error("Public messages require a character")
                return

            if msg_type == "OOC" and character:
                await self.send_error("OOC messages cannot have character attribution")
                return

            # Check if user can send system messages
            if msg_type == "SYSTEM":
                if not await self.user_can_send_system_messages():
                    await self.send_error("Only GMs can send system messages")
                    return

            # Create message in database
            message = await self.create_message(
                content=content,
                message_type=msg_type,
                character=character,
                recipients=recipients,
            )

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.message.send",
                    "message": await self.serialize_message(message),
                },
            )

        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            await self.send_error("Failed to send message")

    async def chat_message_send(self, event):
        """Send message to WebSocket."""
        message = event["message"]

        # Check if user can see this message
        if await self.user_can_see_message(message):
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "chat.message",
                        "message_type": message["message_type"],
                        "content": message["content"],
                        "character": message["character"],
                        "sender": message["sender"],
                        "recipients": message.get("recipients", []),
                        "timestamp": message["timestamp"],
                        "id": message["id"],
                    }
                )
            )

    async def send_error(self, error: str):
        """Send error message to client."""
        await self.send(text_data=json.dumps({"type": "error", "error": error}))

    @database_sync_to_async
    def get_scene(self):
        """Get scene from database."""
        return Scene.objects.select_related("campaign").get(id=self.scene_id)

    @database_sync_to_async
    def get_character(self, character_id):
        """Get character from database."""
        try:
            from characters.models import Character

            return Character.objects.get(
                id=character_id, campaign=self.scene.campaign, player_owner=self.user
            )
        except Character.DoesNotExist:
            return None

    @database_sync_to_async
    def user_can_access_scene(self):
        """Check if user can access this scene."""
        campaign = self.scene.campaign
        return campaign.owner == self.user or campaign.is_member(self.user)

    @database_sync_to_async
    def user_can_send_system_messages(self):
        """Check if user can send system messages."""
        campaign = self.scene.campaign
        user_role = campaign.get_user_role(self.user)
        return user_role in ["OWNER", "GM"]

    @database_sync_to_async
    def create_message(self, content, message_type, character, recipients):
        """Create message in database."""
        message = Message.objects.create(
            scene=self.scene,
            sender=self.user,
            character=character,
            content=content,
            message_type=message_type,
        )

        # Add recipients for private messages
        if message_type == "PRIVATE" and recipients:
            recipient_users = User.objects.filter(id__in=recipients)
            message.recipients.set(recipient_users)

        return message

    @database_sync_to_async
    def serialize_message(self, message):
        """Convert message to JSON-serializable format."""
        character_data = None
        if message.character:
            character_data = {
                "id": message.character.id,
                "name": message.character.name,
            }

        sender_data = None
        if message.sender:
            sender_data = {
                "id": message.sender.id,
                "username": message.sender.username,
            }

        recipients_data = []
        if message.message_type == "PRIVATE":
            for recipient in message.recipients.all():
                recipients_data.append(
                    {
                        "id": recipient.id,
                        "username": recipient.username,
                    }
                )

        return {
            "id": message.id,
            "content": message.content,
            "message_type": message.message_type,
            "character": character_data,
            "sender": sender_data,
            "recipients": recipients_data,
            "timestamp": message.created_at.isoformat(),
        }

    @database_sync_to_async
    def user_can_see_message(self, message_data):
        """Check if user can see this message."""
        message_type = message_data["message_type"]

        # Campaign owners and GMs can see all messages
        campaign = self.scene.campaign
        user_role = campaign.get_user_role(self.user)
        if user_role in ["OWNER", "GM"]:
            return True

        # Public and OOC messages can be seen by all scene participants
        if message_type in ["PUBLIC", "OOC", "SYSTEM"]:
            return campaign.is_member(self.user)

        # Private messages can be seen by sender and recipients
        if message_type == "PRIVATE":
            # Check if user is sender
            if message_data["sender"] and message_data["sender"]["id"] == self.user.id:
                return True
            # Check if user is recipient
            for recipient in message_data.get("recipients", []):
                if recipient["id"] == self.user.id:
                    return True
            return False

        return False
