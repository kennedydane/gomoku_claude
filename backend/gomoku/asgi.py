"""
ASGI config for gomoku project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')

# Initialize Django ASGI application first to ensure settings are configured
django_asgi_app = get_asgi_application()

# Import after Django is initialized
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from web.routing import websocket_urlpatterns

# Combined ASGI application with WebSocket support
application = ProtocolTypeRouter({
    # HTTP protocol uses Django ASGI app (includes django-eventstream for SSE)
    "http": django_asgi_app,
    
    # WebSocket protocol uses Channels routing with authentication
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
