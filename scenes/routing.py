"""WebSocket routing for scenes app."""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/scenes/(?P<scene_id>\d+)/chat/$", consumers.SceneChatConsumer.as_asgi()
    ),
]
