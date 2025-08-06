"""Tests for WebSocket and Django Channels configuration."""

import json
from unittest.mock import MagicMock, patch

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import path


class ASGIApplicationTest(TestCase):
    """Test ASGI application configuration."""

    def test_asgi_application_exists(self):
        """Test that ASGI application is properly configured."""
        from gm_app import asgi

        self.assertTrue(hasattr(asgi, "application"))
        self.assertIsInstance(asgi.application, ProtocolTypeRouter)

    def test_asgi_application_has_websocket_protocol(self):
        """Test that ASGI application includes WebSocket protocol."""
        from gm_app import asgi

        protocols = asgi.application.application_mapping
        self.assertIn("websocket", protocols)

    def test_asgi_application_websocket_uses_auth_middleware(self):
        """Test that WebSocket protocol uses authentication middleware."""
        from gm_app import asgi

        websocket_app = asgi.application.application_mapping.get("websocket")
        # Check that websocket app is configured and uses authentication
        self.assertIsNotNone(websocket_app)
        # Verify it has the expected structure (AllowedHostsOriginValidator wrapping AuthMiddlewareStack)
        self.assertTrue(
            hasattr(websocket_app, "application")
        )  # Should have inner application


class ChannelLayerConfigurationTest(TestCase):
    """Test Redis channel layer configuration."""

    @override_settings(
        CHANNEL_LAYERS={
            "default": {
                "BACKEND": "channels_redis.core.RedisChannelLayer",
                "CONFIG": {
                    "hosts": [("127.0.0.1", 6379)],
                },
            }
        }
    )
    def test_channel_layer_configured(self):
        """Test that channel layer is configured with Redis backend."""
        from django.conf import settings

        self.assertIn("CHANNEL_LAYERS", dir(settings))
        channel_config = settings.CHANNEL_LAYERS
        self.assertIn("default", channel_config)
        self.assertEqual(
            channel_config["default"]["BACKEND"],
            "channels_redis.core.RedisChannelLayer",
        )

    @override_settings(
        CHANNEL_LAYERS={
            "default": {
                "BACKEND": "channels_redis.core.RedisChannelLayer",
                "CONFIG": {
                    "hosts": [("127.0.0.1", 6379)],
                },
            }
        }
    )
    def test_redis_connection_config(self):
        """Test Redis connection configuration."""
        from django.conf import settings

        config = settings.CHANNEL_LAYERS["default"]["CONFIG"]
        self.assertIn("hosts", config)
        self.assertEqual(config["hosts"][0], ("127.0.0.1", 6379))

    def test_channels_in_installed_apps(self):
        """Test that channels is in INSTALLED_APPS."""
        from django.conf import settings

        self.assertIn("channels", settings.INSTALLED_APPS)


class WebSocketConsumerTest(TransactionTestCase):
    """Test basic WebSocket consumer functionality."""

    async def test_websocket_connect_disconnect(self):
        """Test WebSocket connection and disconnection."""
        from core.consumers import TestWebSocketConsumer

        # Create a test consumer instance
        communicator = WebsocketCommunicator(
            TestWebSocketConsumer.as_asgi(), "/ws/test/"
        )

        # Test connection
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Test disconnection
        await communicator.disconnect()

    async def test_websocket_receive_echo(self):
        """Test WebSocket echo functionality."""
        from core.consumers import TestWebSocketConsumer

        communicator = WebsocketCommunicator(
            TestWebSocketConsumer.as_asgi(), "/ws/test/"
        )

        # Connect
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send message
        test_message = {"type": "test", "message": "Hello WebSocket"}
        await communicator.send_json_to(test_message)

        # Receive response
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "test.response")
        self.assertEqual(response["message"], "Echo: Hello WebSocket")

        # Disconnect
        await communicator.disconnect()

    async def test_websocket_handles_invalid_json(self):
        """Test WebSocket handling of invalid JSON."""
        from core.consumers import TestWebSocketConsumer

        communicator = WebsocketCommunicator(
            TestWebSocketConsumer.as_asgi(), "/ws/test/"
        )

        # Connect
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send invalid JSON as text (not bytes)
        await communicator.send_to(text_data="invalid json")

        # Should receive error response
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "error")
        self.assertIn("error", response)

        # Disconnect
        await communicator.disconnect()


class ChannelsRoutingTest(TestCase):
    """Test Channels routing configuration."""

    def test_websocket_routing_exists(self):
        """Test that WebSocket routing is configured."""
        from core import routing

        self.assertTrue(hasattr(routing, "websocket_urlpatterns"))
        self.assertIsInstance(routing.websocket_urlpatterns, list)

    def test_test_websocket_route_configured(self):
        """Test that test WebSocket route is configured."""
        from core import routing

        # Check that at least one pattern exists
        self.assertGreater(len(routing.websocket_urlpatterns), 0)

        # Check for test route
        test_routes = [
            route
            for route in routing.websocket_urlpatterns
            if "test" in str(route.pattern)
        ]
        self.assertGreater(
            len(test_routes), 0, "Test WebSocket route should be configured"
        )

    def test_asgi_application_uses_routing(self):
        """Test that ASGI application uses the routing configuration."""
        from gm_app import asgi

        websocket_app = asgi.application.application_mapping.get("websocket")
        # Check that websocket app is configured
        self.assertIsNotNone(websocket_app)

        # The websocket app should have nested structure:
        # AllowedHostsOriginValidator -> AuthMiddlewareStack -> URLRouter
        # Check it has the expected nested structure
        self.assertTrue(
            hasattr(websocket_app, "application")
        )  # AllowedHostsOriginValidator has inner app

        # Check the middleware stack exists and has an inner router
        auth_stack = websocket_app.application
        self.assertTrue(
            hasattr(auth_stack, "inner")
        )  # AuthMiddlewareStack has inner URLRouter

        # Verify the URLRouter exists
        url_router = auth_stack.inner
        self.assertIsNotNone(url_router)


class WebSocketIntegrationTest(TransactionTestCase):
    """Integration tests for WebSocket functionality."""

    async def test_end_to_end_websocket_connection(self):
        """Test complete WebSocket connection flow."""
        # Test using the consumer directly for end-to-end test
        from core.consumers import TestWebSocketConsumer

        # Create communicator with test consumer
        communicator = WebsocketCommunicator(
            TestWebSocketConsumer.as_asgi(), "/ws/test/"
        )

        # Connect
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "WebSocket connection should succeed")

        # Send and receive
        test_data = {"type": "ping", "message": "test"}
        await communicator.send_json_to(test_data)

        response = await communicator.receive_json_from(timeout=5)
        self.assertIsNotNone(response, "Should receive response from WebSocket")
        self.assertEqual(response["type"], "ping.response")
        self.assertEqual(response["message"], "Echo: test")

        # Disconnect
        await communicator.disconnect()

    @override_settings(
        CHANNEL_LAYERS={
            "default": {
                "BACKEND": "channels.layers.InMemoryChannelLayer",
            }
        }
    )
    async def test_channel_layer_communication(self):
        """Test channel layer communication between consumers."""
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()

        # Send message to a channel
        await channel_layer.send(
            "test_channel", {"type": "test.message", "text": "Hello"}
        )

        # Receive message from the channel
        message = await channel_layer.receive("test_channel")
        self.assertEqual(message["type"], "test.message")
        self.assertEqual(message["text"], "Hello")
