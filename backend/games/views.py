"""
DRF viewsets for game management.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from core.exceptions import GameError, InvalidMoveError, GameStateError, PlayerError

from .models import (
    RuleSet, Game, GameMove, PlayerSession,
    GameEvent, Challenge, GameStatus
)
from .serializers import (
    RuleSetSerializer, GameSerializer, GameListSerializer,
    GameMoveSerializer, MakeMoveSerializer, PlayerSessionSerializer,
    GameEventSerializer, ChallengeSerializer, ChallengeResponseSerializer
)
from .services import GameService


class RuleSetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for RuleSet CRUD operations.
    """
    queryset = RuleSet.objects.all()
    serializer_class = RuleSetSerializer


class GameViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Game management.
    """
    queryset = Game.objects.select_related(
        'black_player', 'white_player', 'winner', 'ruleset'
    ).prefetch_related('moves')
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post']  # Only allow GET (list/retrieve) and POST (create/actions)
    
    def update(self, request, *args, **kwargs):
        """Disable PUT/PATCH updates."""
        return Response(
            {'error': {'code': 'METHOD_NOT_ALLOWED', 'message': 'Games cannot be updated directly'}},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def partial_update(self, request, *args, **kwargs):
        """Disable PATCH updates."""
        return Response(
            {'error': {'code': 'METHOD_NOT_ALLOWED', 'message': 'Games cannot be updated directly'}},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        """Disable DELETE."""
        return Response(
            {'error': {'code': 'METHOD_NOT_ALLOWED', 'message': 'Games cannot be deleted'}},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'list':
            return GameListSerializer
        return GameSerializer
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a game."""
        game = self.get_object()
        try:
            game.start_game()
            serializer = GameSerializer(game)
            return Response(serializer.data)
        except (ValueError, GameError) as e:
            # Convert to DRF exception for proper handling
            raise ValidationError(str(e))
    
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """Make a move in the game."""
        game = self.get_object()
        
        # Check if authenticated user is a player in this game
        user = request.user
        if user.id not in [game.black_player_id, game.white_player_id]:
            return Response(
                {'error': 'You are not a player in this game'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MakeMoveSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            move = GameService.make_move(
                game,
                user.id,
                serializer.validated_data['row'],
                serializer.validated_data['col']
            )
            
            # Create game event for SSE
            # Notify both players
            for player in [game.black_player, game.white_player]:
                GameEvent.objects.create(
                    user=player,
                    event_type='move',
                    event_data={
                        'game_id': str(game.id),
                        'move': {
                            'row': move.row,
                            'col': move.col,
                            'player': move.player_color,
                            'move_number': move.move_number,
                            'is_winning_move': move.is_winning_move
                        },
                        'game_status': game.status,
                        'current_player': game.current_player,
                        'winner_id': game.winner_id
                    }
                )
            
            return Response(GameMoveSerializer(move).data)
            
        except (InvalidMoveError, GameStateError, PlayerError) as e:
            # These will be handled by our custom exception handler
            raise ValidationError(str(e))
        except ValueError as e:
            # Fallback for any other ValueError
            raise ValidationError(str(e))
    
    @action(detail=True, methods=['get'])
    def moves(self, request, pk=None):
        """Get all moves for a game."""
        game = self.get_object()
        moves = game.moves.select_related('player').all()
        serializer = GameMoveSerializer(moves, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resign(self, request, pk=None):
        """Resign from a game."""
        game = self.get_object()
        
        # Check if authenticated user is a player in this game
        user = request.user
        if user.id not in [game.black_player_id, game.white_player_id]:
            return Response(
                {'error': 'You are not a player in this game'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            GameService.resign_game(game, user.id)
            
            # Create game event
            for player in [game.black_player, game.white_player]:
                GameEvent.objects.create(
                    user=player,
                    event_type='resign',
                    event_data={
                        'game_id': str(game.id),
                        'resigned_player_id': user.id,
                        'winner_id': game.winner_id
                    }
                )
            
            return Response(GameSerializer(game).data)
            
        except (GameStateError, PlayerError) as e:
            # These will be handled by our custom exception handler
            raise ValidationError(str(e))
        except ValueError as e:
            # Fallback for any other ValueError
            raise ValidationError(str(e))


class PlayerSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for PlayerSession management.
    """
    queryset = PlayerSession.objects.all()
    serializer_class = PlayerSessionSerializer
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active sessions."""
        sessions = PlayerSession.objects.filter(
            status__in=['ONLINE', 'IDLE', 'IN_GAME']
        )
        # Filter for actually active (not timed out)
        active_sessions = [s for s in sessions if s.is_active]
        serializer = self.get_serializer(active_sessions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def heartbeat(self, request, pk=None):
        """Update session activity."""
        session = self.get_object()
        session.update_activity()
        return Response({'status': 'ok'})


class ChallengeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Challenge management.
    """
    queryset = Challenge.objects.select_related('challenger', 'challenged')
    serializer_class = ChallengeSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new challenge."""
        response = super().create(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_201_CREATED:
            challenge = Challenge.objects.get(id=response.data['id'])
            
            # Create event for challenged player
            GameEvent.objects.create(
                user=challenge.challenged,
                event_type='challenge_received',
                event_data={
                    'challenge_id': str(challenge.id),
                    'challenger': {
                        'id': challenge.challenger.id,
                        'username': challenge.challenger.username,
                        'display_name': challenge.challenger.display_name
                    }
                }
            )
        
        return response
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Respond to a challenge."""
        challenge = self.get_object()
        serializer = ChallengeResponseSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if serializer.validated_data['accept']:
                challenge.accept()
                
                # Create a game if accepted
                if challenge.status == 'ACCEPTED':
                    # Default to standard ruleset
                    ruleset = RuleSet.objects.first()
                    if not ruleset:
                        ruleset = RuleSet.objects.create(
                            name='Standard Gomoku',
                            board_size=15,
                            allow_overlines=False
                        )
                    
                    game = Game.objects.create(
                        black_player=challenge.challenger,
                        white_player=challenge.challenged,
                        ruleset=ruleset
                    )
                    
                    # Notify both players
                    for player in [challenge.challenger, challenge.challenged]:
                        GameEvent.objects.create(
                            user=player,
                            event_type='game_created',
                            event_data={
                                'game_id': str(game.id),
                                'challenge_id': str(challenge.id)
                            }
                        )
                    
                    return Response({
                        'challenge': ChallengeSerializer(challenge).data,
                        'game_id': str(game.id)
                    })
            else:
                challenge.reject()
                
                # Notify challenger
                GameEvent.objects.create(
                    user=challenge.challenger,
                    event_type='challenge_rejected',
                    event_data={
                        'challenge_id': str(challenge.id),
                        'challenged_username': challenge.challenged.username
                    }
                )
            
            return Response(ChallengeSerializer(challenge).data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending challenges for a user."""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id query parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        challenges = Challenge.objects.filter(
            challenged_id=user_id,
            status='PENDING'
        )
        # Filter out expired challenges
        active_challenges = [c for c in challenges if not c.is_expired]
        serializer = self.get_serializer(active_challenges, many=True)
        return Response(serializer.data)