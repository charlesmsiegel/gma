"""WebSocket consumers for the core application."""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class TestWebSocketConsumer(AsyncWebsocketConsumer):
    """Basic WebSocket consumer for testing connectivity."""

    async def connect(self):
        """Accept WebSocket connection."""
        await self.accept()
        logger.info("WebSocket connection established")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        logger.info(f"WebSocket disconnected with code: {close_code}")

    async def receive(self, text_data):
        """
        Receive message from WebSocket.
        
        Echo back messages with a response type.
        """
        try:
            data = json.loads(text_data)
            response_type = data.get("type", "unknown") + ".response"
            
            # Echo the message back with response type
            await self.send(text_data=json.dumps({
                "type": response_type,
                "message": f"Echo: {data.get('message', '')}"
            }))
            
        except json.JSONDecodeError as e:
            # Send error response for invalid JSON
            await self.send(text_data=json.dumps({
                "type": "error",
                "error": f"Invalid JSON: {str(e)}"
            }))
            logger.error(f"Received invalid JSON: {text_data}")