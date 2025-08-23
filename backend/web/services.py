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
                'current_player': ['game_board', 'games_panel', 'move_history'],
                'other_player': ['game_board', 'game_panel', 'turn_display', 'games_panel', 'move_history']
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
            
            elif update_type == 'move_history':
                return cls._send_move_history_update(user, game, request, csrf_token, context)
            
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
        
        # Don't include CSRF tokens in WebSocket-delivered HTML
        # Let the client-side JavaScript handle CSRF tokens from the page context
        friends_html = render_to_string('web/partials/friends_panel.html', {
            'user': user,
            'friends': friends,
            'pending_sent_challenges': pending_sent_challenges,
            'pending_received_challenges': pending_received_challenges,
            # No csrf_token - handled by JavaScript
        }, request=request).strip()
        
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
        """Send optimized move update to user (targeted intersection only)."""
        # Get the most recent move for targeted updates
        latest_move = game.moves.order_by('-move_number').first()
        
        # For Go games, detect capture moves and use full board update
        use_targeted_update = context.get('use_targeted_update', True)
        if latest_move and game.ruleset.is_go and use_targeted_update:
            # Check if this move involved captures by comparing stone counts
            if cls._move_involved_captures(game, latest_move):
                logger.info(f"🎯 Capture move detected - using full board update for move #{latest_move.move_number}")
                use_targeted_update = False
        
        if latest_move and use_targeted_update:
            # Send minimal targeted update (~1KB instead of 85KB)
            move_html = render_to_string('web/partials/single_move_update.html', {
                'move': latest_move,
                'game': game
            }, request=request).strip()
            
            # Send as targeted DOM update
            WebSocketMessageSender.send_to_user_sync(
                user.id,
                'targeted_move_update',
                move_html,
                metadata={
                    'target_selector': f'.board-intersection[data-row="{latest_move.row}"][data-col="{latest_move.col}"]',
                    'move_number': latest_move.move_number,
                    'player': str(latest_move.player),
                    **context.get('metadata', {})
                }
            )
        else:
            # Fallback to full board update if needed
            board_html = render_to_string('web/partials/game_board.html', {
                'game': game,
                'selected_game': game,
                'user': user,
                'wrapper_id': 'dashboard-game-board-content'
            }, request=request).strip()
            
            WebSocketMessageSender.send_to_user_sync(
                user.id,
                'game_move',
                board_html,
                metadata=context.get('metadata', {})
            )
        
        return True
    
    @classmethod
    def _send_move_history_update(cls, user: User, game: Game, request, csrf_token: str, context: Dict) -> bool:
        """Send optimized move history update to user (recent moves only)."""
        # Only show last 20 moves to prevent exponential payload growth
        recent_moves = game.moves.select_related('player').order_by('-move_number')[:20]
        
        history_html = render_to_string('web/partials/move_history.html', {
            'game': game,
            'recent_moves': list(reversed(recent_moves))  # Show in chronological order
        }, request=request).strip()
        
        WebSocketMessageSender.send_to_user_sync(
            user.id,
            'move_history_update',
            history_html,
            metadata={'target': 'dashboard-move-history', **context.get('metadata', {})}
        )
        return True
    
    @classmethod
    def _move_involved_captures(cls, game: Game, move) -> bool:
        """
        Detect if a move involved captures by checking if opponent stones were removed.
        
        Args:
            game: Game instance
            move: GameMove instance
            
        Returns:
            bool: True if captures occurred, False otherwise
        """
        try:
            if not game.ruleset.is_go:
                return False
            
            # For Go games, check captured_stones tracking in board_state
            captured_stones = game.board_state.get('captured_stones', {'black': 0, 'white': 0})
            
            # Get the move before this one to compare captures
            previous_move = game.moves.filter(move_number__lt=move.move_number).order_by('-move_number').first()
            
            if not previous_move:
                # First move cannot involve captures
                return False
            
            # Reconstruct board state at previous move to compare
            service = game.get_service()
            previous_board_state = service.reconstruct_board_state_at_move(game, previous_move.move_number)
            current_board_state = game.board_state
            
            # Compare captured stone counts
            prev_captures = previous_board_state.get('captured_stones', {'black': 0, 'white': 0})
            curr_captures = current_board_state.get('captured_stones', {'black': 0, 'white': 0})
            
            # If captured counts increased, this move involved captures
            captures_occurred = (
                curr_captures.get('black', 0) > prev_captures.get('black', 0) or
                curr_captures.get('white', 0) > prev_captures.get('white', 0)
            )
            
            if captures_occurred:
                logger.info(f"🎯 Capture detected for move #{move.move_number}: "
                           f"Previous captures: {prev_captures}, Current: {curr_captures}")
            
            return captures_occurred
            
        except Exception as e:
            logger.error(f"Error detecting captures for move #{move.move_number}: {e}")
            # On error, assume captures occurred to be safe (use full update)
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
        
        # Move history update removed - handled centrally to avoid duplicates
        
        return True