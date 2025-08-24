"""WebSocket routing configuration for the core application."""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/test/$", consumers.TestWebSocketConsumer.as_asgi()),
]

# Import scene routing
try:
    from scenes.routing import websocket_urlpatterns as scenes_websocket_urlpatterns

    websocket_urlpatterns.extend(scenes_websocket_urlpatterns)
except ImportError:
    pass
