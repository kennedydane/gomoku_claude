"""
Centralized WebSocket Notification Service

This module provides a unified service for sending WebSocket notifications
for all game-related events, replacing scattered update logic across views.
"""

import logging
from typing import Dict, List, Optional, Any
from django.template.loader import render_to_string
from django.middleware.csrf import get_token
from django.db.models import Q
from django.contrib.auth import get_user_model

from games.models import Game, GameStatus
from .consumers import WebSocketMessageSender

logger = logging.getLogger(__name__)
User = get_user_model()


class WebSocketNotificationService:
    """
    Centralized service for sending WebSocket notifications for game events.
    
    This service handles all WebSocket updates in a consistent, centralized way,
    ensuring both players receive appropriate notifications for all game events.
    """
    
    # Event type definitions - what gets updated for each event
    EVENT_DEFINITIONS = {
        'challenge_sent': {
            'description': 'A challenge was sent from one user to another',
            'updates': {
                'challenger': ['friends_panel'],
                'challenged': ['friends_panel']
            }
        },
        'challenge_accepted': {
            'description': 'A challenge was accepted, creating a new game',
            'updates': {
                'challenger': ['friends_panel', 'games_panel'],
                'challenged': ['friends_panel', 'games_panel']
            }
        },
        'challenge_rejected': {
            'description': 'A challenge was rejected or cancelled',
            'updates': {
                'challenger': ['friends_panel'],
                'challenged': ['friends_panel']
            }
        },
        'game_move_made': {
            'description': 'A move was made in a game',
            'updates': {
                'current_player': ['game_board', 'games_panel'],
                'other_player': ['game_board', 'turn_display', 'games_panel']
            }
        },
        'game_resigned': {
            'description': 'A player resigned from a game',
            'updates': {
                'resigning_player': ['game_panel', 'games_panel'],
                'other_player': ['game_panel', 'games_panel']
            }
        },
        'game_completed': {
            'description': 'A game was completed (win/draw)',
            'updates': {
                'black_player': ['game_panel', 'games_panel'],
                'white_player': ['game_panel', 'games_panel']
            }
        }
    }
    
    @classmethod
    def notify_game_event(cls, event_type: str, game: Game, triggering_user: User, 
                         request, **context) -> bool:
        """
        Send WebSocket notifications for a game event.
        
        Args:
            event_type: The type of event (see EVENT_DEFINITIONS)
            game: The game instance involved in the event
            triggering_user: The user who triggered the event
            request: Django request object (for CSRF tokens and rendering)
            **context: Additional context for the event (e.g., challenge info)
            
        Returns:
            bool: True if notifications were sent successfully, False otherwise
        """
        if event_type not in cls.EVENT_DEFINITIONS:
            logger.error(f"Unknown event type: {event_type}")
            return False
        
        event_def = cls.EVENT_DEFINITIONS[event_type]
        logger.info(f"📤 Sending WebSocket notifications for '{event_type}': {event_def['description']}")
        
        try:
            # Generate fresh CSRF token for WebSocket updates
            csrf_token = get_token(request)
            
            # Determine which users need updates
            users_to_notify = cls._get_users_for_event(event_type, game, triggering_user, context)
            
            success_count = 0
            for user_role, user in users_to_notify.items():
                if user:
                    update_types = event_def['updates'].get(user_role, [])
                    for update_type in update_types:
                        if cls._send_update(update_type, user, game, request, csrf_token, context):
                            success_count += 1
            
            logger.info(f"✅ Sent {success_count} WebSocket notifications for {event_type}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to send WebSocket notifications for {event_type}: {e}")
            return False
    
    @classmethod
    def _get_users_for_event(cls, event_type: str, game: Game, triggering_user: User, 
                           context: Dict) -> Dict[str, Optional[User]]:
        """
        Determine which users need notifications for a given event.
        
        Returns:
            Dict mapping user roles to User instances
        """
        users = {}
        
        if event_type in ['challenge_sent', 'challenge_accepted', 'challenge_rejected']:
            # Challenge events involve challenger and challenged users
            challenge = context.get('challenge')
            if challenge:
                users['challenger'] = challenge.challenger
                users['challenged'] = challenge.challenged
        
        elif event_type in ['game_move_made']:
            # Move events involve current player and other player
            if game:
                users['current_player'] = triggering_user
                users['other_player'] = game.white_player if triggering_user == game.black_player else game.black_player
        
        elif event_type in ['game_resigned']:
            # Resign events involve the resigning player and other player
            if game:
                users['resigning_player'] = triggering_user
                users['other_player'] = game.white_player if triggering_user == game.black_player else game.black_player
        
        elif event_type in ['game_completed']:
            # Completion events involve both players
            if game:
                users['black_player'] = game.black_player
                users['white_player'] = game.white_player
        
        return users
    
    @classmethod
    def _send_update(cls, update_type: str, user: User, game: Game, request, 
                   csrf_token: str, context: Dict) -> bool:
        """
        Send a specific type of update to a user.
        
        Args:
            update_type: Type of update ('friends_panel', 'games_panel', etc.)
            user: User to send update to
            game: Game instance
            request: Django request object
            csrf_token: CSRF token for the update
            context: Additional context
            
        Returns:
            bool: True if update was sent successfully
        """
        try:
            if update_type == 'friends_panel':
                return cls._send_friends_panel_update(user, request, csrf_token, context)
            
            elif update_type == 'games_panel':
                return cls._send_games_panel_update(user, request, csrf_token, context)
            
            elif update_type == 'game_panel':
                return cls._send_game_panel_update(user, game, request, csrf_token, context)
            
            elif update_type == 'game_board':
                return cls._send_game_board_update(user, game, request, csrf_token, context)
            
            elif update_type == 'turn_display':
                return cls._send_turn_display_update(user, game, request, csrf_token, context)
            
            else:
                logger.warning(f"Unknown update type: {update_type}")
                return False
                
        except Exception as e:
            logger.error("Failed to send %s update to %s: %s", update_type, user.username, str(e))
            return False
    
    @classmethod
    def _send_friends_panel_update(cls, user: User, request, csrf_token: str, context: Dict) -> bool:
        """Send friends panel update to user."""
        from web.models import Friendship, FriendshipStatus
        from games.models import Challenge, ChallengeStatus
        from django.test import RequestFactory
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.middleware.csrf import get_token
        
        # Get friends
        friends = Friendship.objects.get_friends(user)
        
        # Get pending challenges
        pending_sent_challenges = Challenge.objects.select_related(
            'challenger', 'challenged'
        ).prefetch_related('ruleset').filter(
            challenger=user,
            status=ChallengeStatus.PENDING
        )
        
        pending_received_challenges = Challenge.objects.select_related(
            'challenger', 'challenged'
        ).prefetch_related('ruleset').filter(
            challenged=user, 
            status=ChallengeStatus.PENDING
        )
        
        # DEBUG: Log CSRF token details
        logger.info(f"🔐 CSRF DEBUG for user {user.username}: no CSRF token in WebSocket HTML")
        logger.info(f"📋 Pending received challenges: {pending_received_challenges.count()}")
        
        # Don't include CSRF tokens in WebSocket-delivered HTML
        # Let the client-side JavaScript handle CSRF tokens from the page context
        friends_html = render_to_string('web/partials/friends_panel.html', {
            'user': user,
            'friends': friends,
            'pending_sent_challenges': pending_sent_challenges,
            'pending_received_challenges': pending_received_challenges,
            # No csrf_token - handled by JavaScript
        }, request=request).strip()
        
        logger.info(f"✅ Friends panel rendered without server-side CSRF token")
        
        WebSocketMessageSender.send_to_user_sync(
            user.id,
            'friends_update',
            friends_html,
            metadata=context.get('metadata', {})
        )
        return True
    
    @classmethod
    def _send_games_panel_update(cls, user: User, request, csrf_token: str, context: Dict) -> bool:
        """Send games panel (dashboard left sidebar) update to user."""
        user_games_query = Q(black_player=user) | Q(white_player=user)
        
        # Get updated active games and recent finished games
        active_games = Game.objects.select_related(
            'black_player', 'white_player'
        ).prefetch_related('ruleset').filter(user_games_query, status=GameStatus.ACTIVE).order_by('-created_at')
        
        recent_finished_games = Game.objects.select_related(
            'black_player', 'white_player', 'winner'
        ).prefetch_related('ruleset').filter(
            user_games_query, 
            status=GameStatus.FINISHED
        ).order_by('-finished_at')[:5]
        
        # Render updated games panel
        panel_html = render_to_string('web/partials/games_panel.html', {
            'user': user,
            'active_games': active_games,
            'recent_finished_games': recent_finished_games,
            'selected_game': None  # Don't force game selection
        }, request=request).strip()
        
        # Send dashboard panel update
        panel_html_clean = panel_html.replace('\n\n', ' ').replace('\r\n\r\n', ' ').strip()
        WebSocketMessageSender.send_to_user_sync(
            user.id,
            'dashboard_update',
            panel_html_clean,
            metadata=context.get('metadata', {'panel_type': 'games_list'})
        )
        return True
    
    @classmethod
    def _send_game_panel_update(cls, user: User, game: Game, request, csrf_token: str, context: Dict) -> bool:
        """Send game panel (center dashboard panel) update to user."""
        game_context = {
            'selected_game': game,
            'user': user,
            'csrf_token': csrf_token
        }
        game_panel_html = render_to_string('web/partials/dashboard_game_panel.html', game_context, request=request)
        
        WebSocketMessageSender.send_to_user_sync(
            user.id,
            'dashboard_game_update',
            game_panel_html,
            metadata=context.get('metadata', {})
        )
        return True
    
    @classmethod
    def _send_game_board_update(cls, user: User, game: Game, request, csrf_token: str, context: Dict) -> bool:
        """Send game board update to user."""
        board_html = render_to_string('web/partials/game_board.html', {
            'game': game,
            'selected_game': game,  # For template compatibility
            'user': user,
            'wrapper_id': 'dashboard-game-board-content'
        }, request=request).strip()
        
        WebSocketMessageSender.send_to_user_sync(
            user.id,
            'game_move',
            board_html,
            metadata=context.get('metadata', {})
        )
        
        # Also send move history update
        cls._send_move_history_update(user, game, request, csrf_token, context)
        
        return True
    
    @classmethod
    def _send_move_history_update(cls, user: User, game: Game, request, csrf_token: str, context: Dict) -> bool:
        """Send move history update to user."""
        history_html = render_to_string('web/partials/move_history.html', {
            'game': game,
        }, request=request).strip()
        
        WebSocketMessageSender.send_to_user_sync(
            user.id,
            'move_history_update',
            history_html,
            metadata={'target': 'dashboard-move-history', **context.get('metadata', {})}
        )
        return True
    
    @classmethod
    def _send_turn_display_update(cls, user: User, game: Game, request, csrf_token: str, context: Dict) -> bool:
        """Send turn display update to user."""
        turn_html = render_to_string('web/partials/game_turn_display.html', {
            'game': game,
            'user': user,
        }, request=request).strip()
        
        WebSocketMessageSender.send_to_user_sync(
            user.id,
            'game_turn_update',
            turn_html,
            metadata=context.get('metadata', {})
        )
        
        # Also send move history update when turn changes (indicating a move was made)
        cls._send_move_history_update(user, game, request, csrf_token, context)
        
        return True