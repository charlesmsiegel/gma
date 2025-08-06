"""WebSocket routing configuration for the core application."""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/test/$", consumers.TestWebSocketConsumer.as_asgi()),
]
