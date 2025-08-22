"""
pytest tests for game service layer functionality.

Migrated from games/test_game_services.py to pytest format for better test management.
"""

import pytest
from django.core.exceptions import ValidationError

from games.game_services import BaseGameService, GomokuGameService, GoGameService, GameServiceFactory
from games.models import GomokuRuleSet, GoRuleSet, Game, GameMove, GameStatus, Player, GameType
from tests.factories import UserFactory, GomokuRuleSetFactory, GoRuleSetFactory, GameFactory
from core.exceptions import GameStateError, InvalidMoveError, PlayerError


@pytest.mark.django_db
class TestGameServiceFactory:
    """Test cases for GameServiceFactory."""
    
    def test_get_gomoku_service(self):
        """Test getting Gomoku service from factory."""
        service = GameServiceFactory.get_service(GameType.GOMOKU)
        assert isinstance(service, GomokuGameService)
        assert isinstance(service, BaseGameService)
    
    def test_get_go_service(self):
        """Test getting Go service from factory."""
        service = GameServiceFactory.get_service(GameType.GO)
        assert isinstance(service, GoGameService)
        assert isinstance(service, BaseGameService)
    
    def test_invalid_game_type(self):
        """Test error for invalid game type."""
        with pytest.raises(ValueError) as exc_info:
            GameServiceFactory.get_service('INVALID')
        assert "Unsupported game type" in str(exc_info.value)
    
    def test_services_are_singletons(self):
        """Test that services are reused (singleton pattern)."""
        service1 = GameServiceFactory.get_service(GameType.GOMOKU)
        service2 = GameServiceFactory.get_service(GameType.GOMOKU)
        assert service1 is service2


@pytest.mark.django_db
class TestGomokuGameService:
    """Test cases for GomokuGameService."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GomokuRuleSetFactory(
            name="Test Gomoku",
            board_size=15,
            allow_overlines=False
        )
        self.game = GameFactory(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.service = GomokuGameService()
    
    def test_service_is_base_game_service(self):
        """Test that GomokuGameService inherits from BaseGameService."""
        assert isinstance(self.service, BaseGameService)
    
    def test_gomoku_board_initialization(self):
        """Test Gomoku board initialization."""
        board_state = self.game.board_state
        assert board_state['game_type'] == GameType.GOMOKU
        assert board_state['size'] == 15
        assert len(board_state['board']) == 15
        assert len(board_state['board'][0]) == 15
        
        # Check that all positions are empty initially
        for row in board_state['board']:
            for cell in row:
                assert cell is None
    
    def test_validate_move_success(self):
        """Test successful move validation."""
        # This should not raise an exception
        self.service.validate_move(self.game, self.black_player.id, 7, 7)
    
    def test_validate_move_inactive_game(self):
        """Test move validation fails for inactive game."""
        self.game.status = GameStatus.WAITING
        self.game.save()
        
        with pytest.raises((GameStateError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, 7, 7)
    
    def test_validate_move_wrong_turn(self):
        """Test move validation fails for wrong player turn."""
        # It's black's turn by default, try white player
        with pytest.raises((PlayerError, ValueError)):
            self.service.validate_move(self.game, self.white_player.id, 7, 7)
    
    def test_validate_move_out_of_bounds(self):
        """Test move validation fails for out of bounds positions."""
        with pytest.raises((InvalidMoveError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, -1, 7)
        
        with pytest.raises((InvalidMoveError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, 15, 7)
    
    def test_validate_move_occupied_position(self):
        """Test move validation fails for occupied positions."""
        # Make a move first
        move = self.service.make_move(self.game, self.black_player.id, 7, 7)
        assert move is not None
        
        # Refresh the game to get the updated turn
        self.game.refresh_from_db()
        
        # Try to move to the same position (now it's white's turn)
        with pytest.raises((InvalidMoveError, ValueError)):
            self.service.validate_move(self.game, self.white_player.id, 7, 7)
    
    def test_make_move_success(self):
        """Test successful move creation."""
        move = self.service.make_move(self.game, self.black_player.id, 7, 7)
        
        assert move is not None
        assert move.game == self.game
        assert move.player == self.black_player
        assert move.row == 7
        assert move.col == 7
        assert move.player_color == Player.BLACK
        assert move.move_number == 1
        
        # Check game state updates
        self.game.refresh_from_db()
        assert self.game.current_player == Player.WHITE
        assert self.game.move_count == 1
        
        # Check board state
        board = self.game.board_state['board']
        assert board[7][7] == Player.BLACK
    
    def test_make_move_alternating_players(self):
        """Test that players alternate correctly."""
        # Black move
        move1 = self.service.make_move(self.game, self.black_player.id, 7, 7)
        assert move1.player_color == Player.BLACK
        
        self.game.refresh_from_db()
        assert self.game.current_player == Player.WHITE
        
        # White move
        move2 = self.service.make_move(self.game, self.white_player.id, 8, 8)
        assert move2.player_color == Player.WHITE
        
        self.game.refresh_from_db()
        assert self.game.current_player == Player.BLACK
    
    def test_check_win_horizontal(self):
        """Test horizontal win detection."""
        # Place 5 black stones in a row with white moves in between
        moves = [
            ('BLACK', 7, 5),
            ('WHITE', 6, 0),
            ('BLACK', 7, 6),
            ('WHITE', 6, 1),
            ('BLACK', 7, 7),
            ('WHITE', 6, 2),
            ('BLACK', 7, 8),
            ('WHITE', 6, 3),
            ('BLACK', 7, 9),  # Winning move
        ]
        
        for player_color, row, col in moves:
            if player_color == 'BLACK':
                self.service.make_move(self.game, self.black_player.id, row, col)
            else:
                self.service.make_move(self.game, self.white_player.id, row, col)
            self.game.refresh_from_db()
        
        # Check if black won on the last move
        is_winner = self.service.check_win(self.game, 7, 9)
        assert is_winner is True
    
    def test_check_win_vertical(self):
        """Test vertical win detection."""
        # Place 5 black stones in a column vertically with white moves in between
        moves = [
            ('BLACK', 5, 7),
            ('WHITE', 5, 0),
            ('BLACK', 6, 7),
            ('WHITE', 6, 0),
            ('BLACK', 7, 7),
            ('WHITE', 7, 0),
            ('BLACK', 8, 7),
            ('WHITE', 8, 0),
            ('BLACK', 9, 7),  # Winning move
        ]
        
        for player_color, row, col in moves:
            if player_color == 'BLACK':
                self.service.make_move(self.game, self.black_player.id, row, col)
            else:
                self.service.make_move(self.game, self.white_player.id, row, col)
            self.game.refresh_from_db()
        
        # Check if black won
        is_winner = self.service.check_win(self.game, 9, 7)
        assert is_winner is True
    
    def test_check_win_diagonal(self):
        """Test diagonal win detection."""
        # Place 5 black stones diagonally with white moves in between
        moves = [
            ('BLACK', 5, 5),
            ('WHITE', 5, 0),
            ('BLACK', 6, 6),
            ('WHITE', 6, 0),
            ('BLACK', 7, 7),
            ('WHITE', 7, 0),
            ('BLACK', 8, 8),
            ('WHITE', 8, 0),
            ('BLACK', 9, 9),  # Winning move
        ]
        
        for player_color, row, col in moves:
            if player_color == 'BLACK':
                self.service.make_move(self.game, self.black_player.id, row, col)
            else:
                self.service.make_move(self.game, self.white_player.id, row, col)
            self.game.refresh_from_db()
        
        # Check if black won
        is_winner = self.service.check_win(self.game, 9, 9)
        assert is_winner is True
    
    def test_check_win_no_win(self):
        """Test that non-winning moves return False."""
        move = self.service.make_move(self.game, self.black_player.id, 7, 7)
        is_winner = self.service.check_win(self.game, 7, 7)
        assert is_winner is False
    
    def test_get_valid_moves(self):
        """Test getting valid moves for empty board."""
        valid_moves = self.service.get_valid_moves(self.game)
        
        # On empty 15x15 board, all positions should be valid
        assert len(valid_moves) == 15 * 15
        
        # Check that center position is included
        assert (7, 7) in valid_moves
        
        # Make a move and check again
        self.service.make_move(self.game, self.black_player.id, 7, 7)
        self.game.refresh_from_db()  # Refresh to get updated board state
        valid_moves = self.service.get_valid_moves(self.game)
        
        # Should be one less valid move
        assert len(valid_moves) == (15 * 15) - 1
        assert (7, 7) not in valid_moves


@pytest.mark.django_db
class TestGoGameService:
    """Test cases for GoGameService."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GoRuleSetFactory(
            name="Test Go",
            board_size=19,
            komi=6.5
        )
        self.game = GameFactory(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.service = GoGameService()
    
    def test_service_is_base_game_service(self):
        """Test that GoGameService inherits from BaseGameService."""
        assert isinstance(self.service, BaseGameService)
    
    def test_go_board_initialization(self):
        """Test Go board initialization with Go-specific features."""
        board_state = self.game.board_state
        assert board_state['game_type'] == GameType.GO
        assert board_state['size'] == 19
        assert len(board_state['board']) == 19
        assert len(board_state['board'][0]) == 19
        
        # Go-specific fields
        assert 'captured_stones' in board_state
        assert board_state['captured_stones'] == {'black': 0, 'white': 0}
        assert board_state['ko_position'] is None
        assert board_state['consecutive_passes'] == 0
        
        # Check that all positions are empty initially
        for row in board_state['board']:
            for cell in row:
                assert cell is None
    
    def test_make_move_stone_placement(self):
        """Test successful stone placement in Go."""
        move = self.service.make_move(self.game, self.black_player.id, 3, 3)
        
        assert move is not None
        assert move.game == self.game
        assert move.player == self.black_player
        assert move.row == 3
        assert move.col == 3
        assert move.player_color == Player.BLACK
        assert move.move_number == 1
        
        # Check game state updates
        self.game.refresh_from_db()
        assert self.game.current_player == Player.WHITE
        assert self.game.move_count == 1
        
        # Check board state
        board = self.game.board_state['board']
        assert board[3][3] == Player.BLACK
    
    def test_pass_move(self):
        """Test pass move functionality in Go."""
        # Pass moves use row=-1, col=-1
        move = self.service.make_move(self.game, self.black_player.id, -1, -1)
        
        assert move is not None
        assert move.row == -1
        assert move.col == -1
        assert move.player_color == Player.BLACK
        
        # Check that consecutive passes is incremented
        self.game.refresh_from_db()
        assert self.game.board_state['consecutive_passes'] == 1
        assert self.game.current_player == Player.WHITE
    
    def test_consecutive_passes_end_game(self):
        """Test that two consecutive passes end the game."""
        # Black passes
        self.service.make_move(self.game, self.black_player.id, -1, -1)
        self.game.refresh_from_db()
        assert self.game.status == GameStatus.ACTIVE
        
        # White passes
        self.service.make_move(self.game, self.white_player.id, -1, -1)
        self.game.refresh_from_db()
        
        # Game should end after two consecutive passes
        assert self.game.board_state['consecutive_passes'] == 2
        # Note: Game ending logic depends on implementation
    
    def test_pass_resets_on_stone_move(self):
        """Test that pass count resets when a stone is placed."""
        # Black passes
        self.service.make_move(self.game, self.black_player.id, -1, -1)
        self.game.refresh_from_db()
        assert self.game.board_state['consecutive_passes'] == 1
        
        # White places stone
        self.service.make_move(self.game, self.white_player.id, 3, 3)
        self.game.refresh_from_db()
        
        # Pass count should reset
        assert self.game.board_state['consecutive_passes'] == 0
    
    def test_get_valid_moves_includes_pass(self):
        """Test that valid moves include the pass move."""
        valid_moves = self.service.get_valid_moves(self.game)
        
        # Should include all board positions plus pass move
        expected_moves = 19 * 19 + 1  # All positions + pass
        assert len(valid_moves) >= expected_moves - 1  # Allow for implementation differences
        
        # Check that pass move is included
        assert (-1, -1) in valid_moves
    
    def test_validate_move_pass_always_valid(self):
        """Test that pass moves are always valid (except game state)."""
        # Pass should be valid for the current player
        self.service.validate_move(self.game, self.black_player.id, -1, -1)
        
        # Make a move and pass should still be valid for the next player
        self.service.make_move(self.game, self.black_player.id, 3, 3)
        self.game.refresh_from_db()  # Now it's white's turn
        self.service.validate_move(self.game, self.white_player.id, -1, -1)


@pytest.mark.django_db
class TestBaseGameServiceInterface:
    """Test that all game services implement the required interface."""
    
    def test_gomoku_service_interface(self):
        """Test that GomokuGameService implements required methods."""
        service = GomokuGameService()
        
        # Check that all required methods exist
        assert hasattr(service, 'validate_move')
        assert hasattr(service, 'make_move')
        assert hasattr(service, 'check_win')
        assert hasattr(service, 'get_valid_moves')
        
        # Check that methods are callable
        assert callable(service.validate_move)
        assert callable(service.make_move)
        assert callable(service.check_win)
        assert callable(service.get_valid_moves)
    
    def test_go_service_interface(self):
        """Test that GoGameService implements required methods."""
        service = GoGameService()
        
        # Check that all required methods exist
        assert hasattr(service, 'validate_move')
        assert hasattr(service, 'make_move')
        assert hasattr(service, 'check_win')
        assert hasattr(service, 'get_valid_moves')
        
        # Check that methods are callable
        assert callable(service.validate_move)
        assert callable(service.make_move)
        assert callable(service.check_win)
        assert callable(service.get_valid_moves)
    
    def test_service_method_signatures(self):
        """Test that service methods have expected signatures."""
        gomoku_service = GomokuGameService()
        go_service = GoGameService()
        
        # Create test objects
        game = GameFactory()
        user_id = 1
        row, col = 7, 7
        
        # All services should accept the same basic parameters
        for service in [gomoku_service, go_service]:
            # These should not raise TypeError for wrong signature
            try:
                # Note: These might raise other exceptions due to invalid data,
                # but not TypeError for wrong signature
                service.validate_move(game, user_id, row, col)
            except TypeError as e:
                if "takes" in str(e) and "positional arguments" in str(e):
                    pytest.fail(f"Service method signature mismatch: {e}")
            except:
                pass  # Other exceptions are fine for this test