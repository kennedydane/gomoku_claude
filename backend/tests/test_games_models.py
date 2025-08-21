"""
pytest tests for games model functionality.

Migrated from games/test_models.py to pytest format for better test management.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import timedelta

from tests.factories import UserFactory, GomokuRuleSetFactory, GoRuleSetFactory, GameFactory, GameMoveFactory
from games.models import (
    Game, GomokuRuleSet, GoRuleSet, GameMove, GameStatus, Player,
    GameType, ScoringMethod
)


@pytest.mark.django_db
class TestGomokuRuleSet:
    """Test cases for GomokuRuleSet model."""
    
    # Using pytest-django's database transaction handling
        
    def test_gomoku_ruleset_creation_with_valid_data(self):
        """Test creating a Gomoku ruleset with valid data."""
        ruleset = GomokuRuleSetFactory(
            board_size=15,
            allow_overlines=False
        )
        assert ruleset.board_size == 15
        assert ruleset.allow_overlines is False
        assert ruleset.name is not None
        assert ruleset.description is not None
        assert ruleset.game_type == GameType.GOMOKU
        assert ruleset.is_gomoku is True
        assert ruleset.is_go is False
        assert ruleset.forbidden_moves == {}
    
    def test_gomoku_ruleset_name_uniqueness(self):
        """Test that Gomoku ruleset names must be unique."""
        with transaction.atomic():
            ruleset1 = GomokuRuleSetFactory()
            
            with pytest.raises(IntegrityError):
                GomokuRuleSet.objects.create(name=ruleset1.name, board_size=15)
    
    def test_gomoku_board_size_validation(self):
        """Test Gomoku board size constraints."""
        # Valid board sizes
        for size in [9, 15, 19, 25]:
            ruleset = GomokuRuleSetFactory(board_size=size)
            ruleset.full_clean()  # Should not raise
        
        # Invalid board sizes
        for size in [8, 26]:
            with pytest.raises(ValidationError):
                ruleset = GomokuRuleSetFactory.build(board_size=size)
                ruleset.full_clean()
    
    def test_gomoku_string_representation(self):
        """Test GomokuRuleSet string representation."""
        ruleset = GomokuRuleSetFactory()
        assert str(ruleset) == ruleset.name
    
    def test_gomoku_forbidden_moves_default(self):
        """Test that forbidden_moves defaults to empty dict."""
        ruleset = GomokuRuleSetFactory()
        assert ruleset.forbidden_moves == {}
    
    def test_gomoku_allow_overlines_default(self):
        """Test that allow_overlines defaults to True."""
        ruleset = GomokuRuleSetFactory()
        assert ruleset.allow_overlines is True


@pytest.mark.django_db
class TestGoRuleSet:
    """Test cases for GoRuleSet model."""
    
    # Using pytest-django's database transaction handling
        
    def test_go_ruleset_creation_with_valid_data(self):
        """Test creating a Go ruleset with valid data."""
        ruleset = GoRuleSetFactory(
            board_size=19,
            komi=7.5,
            handicap_stones=2,
            scoring_method=ScoringMethod.AREA
        )
        assert ruleset.name is not None
        assert ruleset.board_size == 19
        assert ruleset.komi == 7.5
        assert ruleset.handicap_stones == 2
        assert ruleset.scoring_method == ScoringMethod.AREA
        assert ruleset.description is not None
        assert ruleset.game_type == GameType.GO
        assert ruleset.is_go is True
        assert ruleset.is_gomoku is False
    
    def test_go_ruleset_name_uniqueness(self):
        """Test that Go ruleset names must be unique."""
        with transaction.atomic():
            ruleset1 = GoRuleSetFactory()
            
            with pytest.raises(IntegrityError):
                GoRuleSet.objects.create(name=ruleset1.name, board_size=19)
    
    def test_go_board_size_validation(self):
        """Test Go board size constraints."""
        # Valid board sizes
        for size in [9, 13, 19]:
            ruleset = GoRuleSetFactory(board_size=size)
            ruleset.full_clean()  # Should not raise
        
        # Invalid board sizes
        for size in [8, 26]:
            with pytest.raises(ValidationError):
                ruleset = GoRuleSetFactory.build(board_size=size)
                ruleset.full_clean()
    
    def test_go_komi_validation(self):
        """Test Go komi field validation."""
        # Valid komi values
        ruleset = GoRuleSetFactory(board_size=19, komi=0.5)
        ruleset.full_clean()  # Should not raise
        
        # Komi can be negative (unusual but valid)
        ruleset.komi = -5.5
        ruleset.full_clean()  # Should not raise
    
    def test_go_handicap_validation(self):
        """Test Go handicap_stones field validation."""
        ruleset = GoRuleSetFactory(board_size=19, handicap_stones=9)
        ruleset.full_clean()  # Should not raise
        
        # Negative handicap should be invalid
        with pytest.raises(ValidationError):
            ruleset.handicap_stones = -1
            ruleset.full_clean()
    
    def test_go_scoring_method_choices(self):
        """Test Go scoring_method field choices."""
        # Valid scoring methods
        for method in [ScoringMethod.TERRITORY, ScoringMethod.AREA]:
            ruleset = GoRuleSetFactory(
                board_size=19,
                scoring_method=method
            )
            ruleset.full_clean()  # Should not raise
    
    def test_go_string_representation(self):
        """Test GoRuleSet string representation."""
        ruleset = GoRuleSetFactory()
        assert str(ruleset) == ruleset.name


@pytest.mark.django_db
class TestGame:
    """Test cases for Game model."""
    
    # Using pytest-django's database transaction handling
    
    def test_game_creation_with_gomoku_ruleset(self):
        """Test creating a game with Gomoku ruleset."""
        game = GameFactory()
        assert isinstance(game.ruleset, GomokuRuleSet)
        assert game.status == GameStatus.ACTIVE
        assert game.current_player == Player.BLACK
        assert game.is_gomoku is True
        assert game.is_go is False
    
    def test_game_creation_with_go_ruleset(self):
        """Test creating a game with Go ruleset."""
        go_ruleset = GoRuleSetFactory()
        game = GameFactory(ruleset=go_ruleset)
        game.refresh_from_db()  # Ensure the generic FK is properly set
        assert isinstance(game.ruleset, GoRuleSet)
        assert game.is_go is True
        assert game.is_gomoku is False
    
    def test_game_string_representation(self):
        """Test Game string representation includes game type."""
        game = GameFactory()
        game_str = str(game)
        assert 'Gomoku Game' in game_str
        # Just check that player info is in the string representation
        assert ' vs ' in game_str
    
    def test_game_initialize_gomoku_board(self):
        """Test Gomoku board initialization."""
        game = GameFactory()
        game.initialize_board()
        
        assert game.board_state['game_type'] == GameType.GOMOKU
        assert game.board_state['size'] == game.ruleset.board_size
        assert len(game.board_state['board']) == game.ruleset.board_size
        assert len(game.board_state['board'][0]) == game.ruleset.board_size
        
        # Gomoku doesn't need Go-specific fields
        assert 'captured_stones' not in game.board_state
        assert 'ko_position' not in game.board_state
        assert 'consecutive_passes' not in game.board_state
    
    def test_game_initialize_go_board(self):
        """Test Go board initialization."""
        go_ruleset = GoRuleSetFactory()
        game = GameFactory(ruleset=go_ruleset)
        game.refresh_from_db()  # Ensure the generic FK is properly set
        game.initialize_board()
        
        assert game.board_state['game_type'] == GameType.GO
        assert game.board_state['size'] == go_ruleset.board_size
        assert len(game.board_state['board']) == go_ruleset.board_size
        
        # Go-specific fields
        assert game.board_state['captured_stones'] == {'black': 0, 'white': 0}
        assert game.board_state['ko_position'] is None
        assert game.board_state['consecutive_passes'] == 0
    
    def test_game_get_service_method(self):
        """Test Game.get_service() returns appropriate service."""
        # Test Gomoku game service
        gomoku_game = GameFactory()
        gomoku_service = gomoku_game.get_service()
        assert gomoku_service.__class__.__name__ == 'GomokuGameService'
        
        # Test Go game service
        go_ruleset = GoRuleSetFactory()
        go_game = GameFactory(ruleset=go_ruleset)
        go_game.refresh_from_db()  # Ensure the generic FK is properly set
        go_service = go_game.get_service()
        assert go_service.__class__.__name__ == 'GoGameService'
        
        # Services should have the required interface
        for service in [gomoku_service, go_service]:
            assert hasattr(service, 'validate_move')
            assert hasattr(service, 'make_move')
            assert hasattr(service, 'check_win')
            assert hasattr(service, 'get_valid_moves')
    
    def test_game_current_player_user(self):
        """Test get_current_player_user method."""
        game = GameFactory()
        
        # Black player's turn initially
        assert game.current_player == Player.BLACK
        assert game.get_current_player_user() == game.black_player
        
        # Switch to white player
        game.current_player = Player.WHITE
        assert game.get_current_player_user() == game.white_player
    
    def test_game_unique_id(self):
        """Test that games have unique UUIDs."""
        game1 = GameFactory()
        game2 = GameFactory()
        assert game1.id != game2.id
        assert str(game1.id) != str(game2.id)


@pytest.mark.django_db
class TestGameMove:
    """Test cases for GameMove model."""
    
    # Using pytest-django's database transaction handling
    
    def test_game_move_creation(self):
        """Test creating a game move."""
        move = GameMoveFactory()
        assert move.game is not None
        assert move.player_color in ['BLACK', 'WHITE']
        assert isinstance(move.row, int)
        assert isinstance(move.col, int)
        assert isinstance(move.move_number, int)
        assert move.created_at is not None
    
    def test_game_move_string_representation(self):
        """Test GameMove string representation."""
        move = GameMoveFactory(player_color='BLACK', row=5, col=7)
        move_str = str(move)
        assert 'BLACK' in move_str or '(5, 7)' in move_str
    
    def test_game_move_ordering(self):
        """Test that moves are ordered by move_number."""
        game = GameFactory()
        move1 = GameMoveFactory(game=game, move_number=1)
        move2 = GameMoveFactory(game=game, move_number=2)
        
        moves = GameMove.objects.filter(game=game).order_by('move_number')
        assert list(moves) == [move1, move2]


@pytest.mark.django_db
class TestGameTypeValidation:
    """Test game type validation and consistency."""
    
    # Using pytest-django's database transaction handling
    
    def test_gomoku_game_type_consistency(self):
        """Test that Gomoku games have consistent game type."""
        gomoku_ruleset = GomokuRuleSetFactory()
        game = GameFactory(
            ruleset_content_type_id=gomoku_ruleset.get_content_type().id,
            ruleset_object_id=gomoku_ruleset.id
        )
        
        assert game.ruleset.game_type == GameType.GOMOKU
        assert game.is_gomoku is True
        assert game.is_go is False
    
    def test_go_game_type_consistency(self):
        """Test that Go games have consistent game type."""
        go_ruleset = GoRuleSetFactory()
        game = GameFactory(ruleset=go_ruleset)
        game.refresh_from_db()  # Ensure the generic FK is properly set
        
        assert game.ruleset.game_type == GameType.GO
        assert game.is_go is True
        assert game.is_gomoku is False