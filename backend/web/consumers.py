"""
WebSocket Consumer for Real-time Game Communication

This module implements a Django Channels WebSocket consumer that replaces
multiple SSE connections with a single bidirectional WebSocket per user.

Phase 5.8.2: GREEN Phase - Implement consumer to make tests pass
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)
User = get_user_model()


class UserWebSocketConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user-specific real-time communication.
    
    Handles:
    - User authentication and channel subscription
    - Message routing for different event types
    - Bidirectional communication between client and server
    - Connection management and cleanup
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.user_channel_group = None
        
    async def connect(self):
        """
        Handle WebSocket connection establishment.
        
        Authenticates the user and subscribes to their personal channel group.
        """
        # Extract user ID from URL - handle both test and production routing
        try:
            if 'url_route' in self.scope and 'kwargs' in self.scope['url_route']:
                self.user_id = self.scope['url_route']['kwargs']['user_id']
            elif hasattr(self.scope, 'path_info'):
                # Extract from path for testing
                import re
                match = re.search(r'/ws/user/(\w+)/', self.scope.get('path', ''))
                if match:
                    self.user_id = match.group(1)
                else:
                    await self.close()
                    return
            else:
                await self.close()
                return
        except (KeyError, AttributeError):
            await self.close()
            return
        
        # Authenticate user
        self.user = await self.get_user_from_scope()
        if not self.user or self.user.is_anonymous:
            logger.warning(f"WebSocket connection rejected: unauthenticated user {self.user_id}")
            await self.close()
            return
        
        # Verify user owns this channel
        if str(self.user.id) != str(self.user_id):
            logger.warning(f"WebSocket connection rejected: user {self.user.id} attempted to connect to channel {self.user_id}")
            await self.close()
            return
        
        # Set up channel group for this user
        self.user_channel_group = f'user_{self.user_id}'
        
        # Join user's channel group
        await self.channel_layer.group_add(
            self.user_channel_group,
            self.channel_name
        )
        
        # Accept WebSocket connection
        await self.accept()
        
        logger.info(f"WebSocket connected: user {self.user.username} (ID: {self.user_id}) on channel {self.channel_name}")
        
        # Send connection confirmation
        await self.send_message({
            'type': 'connection_status',
            'status': 'connected',
            'user_id': self.user_id,
            'username': self.user.username
        })
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        
        Cleans up channel group subscriptions.
        """
        if self.user_channel_group:
            await self.channel_layer.group_discard(
                self.user_channel_group,
                self.channel_name
            )
            
        if self.user:
            logger.info(f"WebSocket disconnected: user {self.user.username} (ID: {self.user_id}) with code {close_code}")
        else:
            logger.info(f"WebSocket disconnected: unauthenticated connection with code {close_code}")
    
    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages from client.
        
        Supports bidirectional communication for future features like:
        - Move acknowledgments
        - Typing indicators
        - Real-time chat
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'unknown')
            
            logger.debug(f"WebSocket received message from user {self.user_id}: {message_type}")
            
            # Route message based on type
            if message_type == 'ping':
                await self.handle_ping(data)
            elif message_type == 'move_acknowledgment':
                await self.handle_move_acknowledgment(data)
            elif message_type == 'presence_update':
                await self.handle_presence_update(data)
            else:
                logger.warning(f"Unknown WebSocket message type: {message_type} from user {self.user_id}")
                await self.send_error(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in WebSocket message from user {self.user_id}: {e}")
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing WebSocket message from user {self.user_id}: {e}")
            await self.send_error("Message processing error")
    
    async def handle_ping(self, data):
        """Handle ping messages for connection keepalive."""
        await self.send_message({
            'type': 'pong',
            'timestamp': data.get('timestamp')
        })
    
    async def handle_move_acknowledgment(self, data):
        """Handle move acknowledgment messages."""
        # Future implementation for move confirmation
        pass
    
    async def handle_presence_update(self, data):
        """Handle presence status updates."""
        # Future implementation for online/offline status
        pass
    
    # Channel group message handlers (called when messages are sent to the group)
    
    async def game_move_message(self, event):
        """
        Handle game move messages sent to this user's channel group.
        
        Forwards game board updates to the WebSocket client.
        """
        await self.send_htmx_message(
            event_type='game_move',
            content=event['content'],
            metadata=event.get('metadata', {})
        )
    
    async def dashboard_update_message(self, event):
        """
        Handle dashboard update messages sent to this user's channel group.
        
        Forwards dashboard panel updates to the WebSocket client.
        """
        await self.send_htmx_message(
            event_type='dashboard_update',
            content=event['content'],
            metadata=event.get('metadata', {})
        )
    
    async def dashboard_game_update_message(self, event):
        """
        Handle dashboard embedded game updates sent to this user's channel group.
        
        Forwards dashboard embedded game panel updates to the WebSocket client.
        """
        await self.send_htmx_message(
            event_type='dashboard_game_update',
            content=event['content'],
            metadata=event.get('metadata', {})
        )
    
    async def friends_update_message(self, event):
        """
        Handle friends panel update messages sent to this user's channel group.
        
        Forwards friends panel updates to the WebSocket client.
        """
        await self.send_htmx_message(
            event_type='friends_update',
            content=event['content'],
            metadata=event.get('metadata', {})
        )
    
    async def connection_status_message(self, event):
        """
        Handle connection status messages sent to this user's channel group.
        
        Forwards connection status updates to the WebSocket client.
        """
        await self.send_htmx_message(
            event_type='connection_status',
            content=event.get('content', ''),
            metadata={'status': event.get('status', 'unknown')}
        )
    
    # Utility methods
    
    async def send_htmx_message(self, event_type, content, metadata=None):
        """
        Send an HTMX-compatible message to the WebSocket client.
        
        Format compatible with HTMX WebSocket extension expectations.
        """
        message = {
            'type': event_type,
            'content': content,
            'timestamp': self.get_current_timestamp()
        }
        
        if metadata:
            message['metadata'] = metadata
        
        await self.send(text_data=json.dumps(message))
        logger.debug(f"Sent {event_type} message to user {self.user_id}")
    
    async def send_message(self, data):
        """Send a general message to the WebSocket client."""
        await self.send(text_data=json.dumps(data))
    
    async def send_error(self, error_message):
        """Send an error message to the WebSocket client."""
        await self.send_message({
            'type': 'error',
            'message': error_message,
            'timestamp': self.get_current_timestamp()
        })
    
    def get_current_timestamp(self):
        """Get current timestamp for message metadata."""
        import time
        return int(time.time() * 1000)  # milliseconds
    
    @database_sync_to_async
    def get_user_from_scope(self):
        """
        Extract authenticated user from WebSocket scope.
        
        Uses Django's session authentication from the WebSocket scope.
        """
        user = self.scope.get('user')
        if user and not isinstance(user, AnonymousUser):
            return user
        return None


class WebSocketMessageSender:
    """
    Utility class for sending messages to WebSocket consumers.
    
    Replaces the SSE send_event functionality with WebSocket channel messaging.
    """
    
    @staticmethod
    async def send_to_user(user_id, event_type, content, metadata=None):
        """
        Send a message to a specific user's WebSocket connection.
        
        Args:
            user_id: Target user ID
            event_type: Type of event (game_move, dashboard_update, etc.)
            content: HTML content or data to send
            metadata: Optional metadata dictionary
        """
        from channels.layers import get_channel_layer
        
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.error("Channel layer not configured for WebSocket messaging")
            return False
        
        user_channel_group = f'user_{user_id}'
        message_type = f'{event_type}_message'
        
        message = {
            'type': message_type,
            'content': content
        }
        
        if metadata:
            message['metadata'] = metadata
        
        try:
            await channel_layer.group_send(user_channel_group, message)
            logger.info(f"WebSocket message sent: {event_type} to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send WebSocket message to user {user_id}: {e}")
            return False
    
    @staticmethod
    def send_to_user_sync(user_id, event_type, content, metadata=None):
        """
        Synchronous wrapper for sending WebSocket messages.
        
        Used when calling from synchronous contexts like Django views.
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new task
                task = asyncio.create_task(
                    WebSocketMessageSender.send_to_user(user_id, event_type, content, metadata)
                )
                return task
            else:
                # If we're in a sync context, run the async function
                return loop.run_until_complete(
                    WebSocketMessageSender.send_to_user(user_id, event_type, content, metadata)
                )
        except RuntimeError:
            # No event loop running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    WebSocketMessageSender.send_to_user(user_id, event_type, content, metadata)
                )
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in sync WebSocket send to user {user_id}: {e}")
            return False