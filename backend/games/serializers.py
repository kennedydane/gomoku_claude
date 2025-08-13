"""
DRF serializers for game models.
"""

from rest_framework import serializers
from users.serializers import UserSerializer
from .models import (
    RuleSet, Game, GameMove, PlayerSession,
    GameEvent, Challenge
)


class RuleSetSerializer(serializers.ModelSerializer):
    """
    Serializer for RuleSet model.
    """
    class Meta:
        model = RuleSet
        fields = [
            'id', 'name', 'board_size', 'allow_overlines',
            'forbidden_moves', 'description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GameMoveSerializer(serializers.ModelSerializer):
    """
    Serializer for GameMove model.
    """
    player_username = serializers.CharField(source='player.username', read_only=True)
    
    class Meta:
        model = GameMove
        fields = [
            'id', 'game', 'player', 'player_username', 'move_number',
            'row', 'col', 'player_color', 'is_winning_move', 'created_at'
        ]
        read_only_fields = ['id', 'game', 'player', 'move_number', 'player_color', 'created_at']


class GameSerializer(serializers.ModelSerializer):
    """
    Serializer for Game model.
    """
    black_player = UserSerializer(read_only=True)
    white_player = UserSerializer(read_only=True)
    winner = UserSerializer(read_only=True)
    ruleset = RuleSetSerializer(read_only=True)
    
    black_player_id = serializers.IntegerField(write_only=True)
    white_player_id = serializers.IntegerField(write_only=True)
    ruleset_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Game
        fields = [
            'id', 'black_player', 'white_player', 'ruleset', 'status',
            'current_player', 'board_state', 'winner', 'move_count',
            'started_at', 'finished_at', 'created_at', 'updated_at',
            'black_player_id', 'white_player_id', 'ruleset_id'
        ]
        read_only_fields = [
            'id', 'status', 'current_player', 'board_state', 'winner',
            'move_count', 'started_at', 'finished_at', 'created_at', 'updated_at'
        ]
    
    def validate(self, data):
        """Custom validation for game creation."""
        black_player_id = data.get('black_player_id')
        white_player_id = data.get('white_player_id')
        ruleset_id = data.get('ruleset_id')
        
        # Validate players are different
        if black_player_id and white_player_id:
            if black_player_id == white_player_id:
                raise serializers.ValidationError(
                    "Black player and white player must be different users."
                )
        
        # Validate ruleset exists
        if ruleset_id:
            from .models import RuleSet
            if not RuleSet.objects.filter(id=ruleset_id).exists():
                raise serializers.ValidationError(
                    f"RuleSet with ID {ruleset_id} does not exist."
                )
        
        return data


class GameListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for game lists.
    """
    black_player_username = serializers.CharField(source='black_player.username', read_only=True)
    white_player_username = serializers.CharField(source='white_player.username', read_only=True)
    winner_username = serializers.CharField(source='winner.username', read_only=True, default=None)
    
    class Meta:
        model = Game
        fields = [
            'id', 'black_player_username', 'white_player_username',
            'status', 'current_player', 'move_count', 'winner_username',
            'created_at'
        ]


class MakeMoveSerializer(serializers.Serializer):
    """
    Serializer for making a move.
    """
    row = serializers.IntegerField(min_value=0, max_value=24)
    col = serializers.IntegerField(min_value=0, max_value=24)
    
    def validate(self, data):
        """Additional validation for move coordinates."""
        row = data.get('row')
        col = data.get('col')
        
        # Ensure coordinates are within valid range
        if not (0 <= row <= 24 and 0 <= col <= 24):
            raise serializers.ValidationError(
                "Move coordinates must be between 0 and 24."
            )
        
        # Additional validation - ensure integer types
        if not isinstance(row, int) or not isinstance(col, int):
            raise serializers.ValidationError(
                "Move coordinates must be integers."
            )
        
        return data


class PlayerSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for PlayerSession model.
    """
    user = UserSerializer(read_only=True)
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = PlayerSession
        fields = [
            'session_id', 'user', 'current_game', 'status',
            'last_activity', 'created_at', 'is_active'
        ]
        read_only_fields = ['session_id', 'created_at']


class GameEventSerializer(serializers.ModelSerializer):
    """
    Serializer for GameEvent model.
    """
    class Meta:
        model = GameEvent
        fields = [
            'id', 'user', 'event_type', 'event_data',
            'consumed', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChallengeSerializer(serializers.ModelSerializer):
    """
    Serializer for Challenge model.
    """
    challenger = UserSerializer(read_only=True)
    challenged = UserSerializer(read_only=True)
    is_expired = serializers.ReadOnlyField()
    
    challenger_id = serializers.IntegerField(write_only=True)
    challenged_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Challenge
        fields = [
            'id', 'challenger', 'challenged', 'status',
            'created_at', 'expires_at', 'responded_at', 'is_expired',
            'challenger_id', 'challenged_id'
        ]
        read_only_fields = [
            'id', 'status', 'created_at', 'expires_at', 'responded_at'
        ]


class ChallengeResponseSerializer(serializers.Serializer):
    """
    Serializer for responding to a challenge.
    """
    accept = serializers.BooleanField()