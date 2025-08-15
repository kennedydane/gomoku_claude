"""
WebSocket URL Routing Configuration

Defines WebSocket URL patterns for the web application.
Phase 5.8.2: GREEN Phase - WebSocket routing implementation
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # User-specific WebSocket connection
    # Pattern: /ws/user/{user_id}/
    re_path(
        r'ws/user/(?P<user_id>\w+)/$',
        consumers.UserWebSocketConsumer.as_asgi(),
        name='user_websocket'
    ),
]