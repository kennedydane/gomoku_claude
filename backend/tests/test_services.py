"""
pytest tests for game service layer business logic.

Migrated from games/test_services.py to pytest format for better test management.
This file contains comprehensive tests for game service validation, move handling,
win detection, and other core business logic.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction

from games.game_services import BaseGameService, GomokuGameService, GoGameService, GameServiceFactory
from games.models import GomokuRuleSet, GoRuleSet, Game, GameMove, GameStatus, Player, GameType
from tests.factories import UserFactory, GomokuRuleSetFactory, GoRuleSetFactory, GameFactory
from core.exceptions import GameStateError, InvalidMoveError, PlayerError


@pytest.mark.django_db
class TestGameServiceValidateMove:
    """Test cases for game service move validation functionality."""
    
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
    
    def test_validate_move_valid_position(self):
        """Test validation succeeds for valid move."""
        # Should not raise any exception
        self.service.validate_move(self.game, self.black_player.id, 7, 7)
    
    def test_validate_move_game_not_active(self):
        """Test validation fails when game is not active."""
        self.game.status = GameStatus.WAITING
        self.game.save()
        
        with pytest.raises((GameStateError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, 7, 7)
    
    def test_validate_move_wrong_player_turn(self):
        """Test validation fails when it's not player's turn."""
        # Game starts with black player's turn
        with pytest.raises((PlayerError, ValueError)):
            self.service.validate_move(self.game, self.white_player.id, 7, 7)
    
    def test_validate_move_invalid_player(self):
        """Test validation fails for player not in game."""
        other_player = UserFactory()
        
        with pytest.raises((PlayerError, ValueError)):
            self.service.validate_move(self.game, other_player.id, 7, 7)
    
    def test_validate_move_out_of_bounds_negative(self):
        """Test validation fails for negative coordinates."""
        with pytest.raises((InvalidMoveError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, -1, 7)
        
        with pytest.raises((InvalidMoveError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, 7, -1)
    
    def test_validate_move_out_of_bounds_too_large(self):
        """Test validation fails for coordinates too large."""
        board_size = self.game.ruleset.board_size
        
        with pytest.raises((InvalidMoveError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, board_size, 7)
        
        with pytest.raises((InvalidMoveError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, 7, board_size)
    
    def test_validate_move_position_occupied(self):
        """Test validation fails for occupied position."""
        # Place a stone directly in the board state without using make_move
        # to avoid changing turns
        self.game.board_state['board'][7][7] = Player.BLACK
        self.game.save()
        
        # Try to place on the same position - should fail due to occupied position
        with pytest.raises((InvalidMoveError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, 7, 7)
    
    def test_validate_move_finished_game(self):
        """Test validation fails for finished game."""
        self.game.status = GameStatus.FINISHED
        self.game.save()
        
        with pytest.raises((GameStateError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, 7, 7)


@pytest.mark.django_db
class TestGameServiceMakeMove:
    """Test cases for game service move creation functionality."""
    
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
    
    def test_make_move_creates_game_move(self):
        """Test that making a move creates a GameMove object."""
        move = self.service.make_move(self.game, self.black_player.id, 7, 7)
        
        assert isinstance(move, GameMove)
        assert move.game == self.game
        assert move.player == self.black_player
        assert move.row == 7
        assert move.col == 7
        assert move.player_color == Player.BLACK
        assert move.move_number == 1
    
    def test_make_move_updates_board_state(self):
        """Test that making a move updates the board state."""
        self.service.make_move(self.game, self.black_player.id, 7, 7)
        
        self.game.refresh_from_db()
        board = self.game.board_state['board']
        assert board[7][7] == Player.BLACK
    
    def test_make_move_updates_game_state(self):
        """Test that making a move updates game state."""
        self.service.make_move(self.game, self.black_player.id, 7, 7)
        
        self.game.refresh_from_db()
        assert self.game.current_player == Player.WHITE
        assert self.game.move_count == 1
    
    def test_make_move_alternates_players(self):
        """Test that consecutive moves alternate between players."""
        # Black move
        move1 = self.service.make_move(self.game, self.black_player.id, 7, 7)
        self.game.refresh_from_db()
        assert self.game.current_player == Player.WHITE
        assert move1.player_color == Player.BLACK
        
        # White move
        move2 = self.service.make_move(self.game, self.white_player.id, 8, 8)
        self.game.refresh_from_db()
        assert self.game.current_player == Player.BLACK
        assert move2.player_color == Player.WHITE
        
        # Black move again
        move3 = self.service.make_move(self.game, self.black_player.id, 9, 9)
        self.game.refresh_from_db()
        assert self.game.current_player == Player.WHITE
        assert move3.player_color == Player.BLACK
    
    def test_make_move_increments_move_numbers(self):
        """Test that move numbers increment correctly."""
        move1 = self.service.make_move(self.game, self.black_player.id, 7, 7)
        move2 = self.service.make_move(self.game, self.white_player.id, 8, 8)
        move3 = self.service.make_move(self.game, self.black_player.id, 9, 9)
        
        assert move1.move_number == 1
        assert move2.move_number == 2
        assert move3.move_number == 3
    
    def test_make_winning_move_ends_game(self):
        """Test that a winning move ends the game."""
        # Set up near-winning position (4 in a row horizontally)
        board = self.game.board_state['board']
        for col in range(4):
            board[7][col] = Player.BLACK
        self.game.save()
        
        # Make the winning move
        move = self.service.make_move(self.game, self.black_player.id, 7, 4)
        
        assert move.is_winning_move is True
        self.game.refresh_from_db()
        assert self.game.status == GameStatus.FINISHED
        assert self.game.winner == self.black_player
    
    def test_make_move_validation_called(self):
        """Test that move validation is called during make_move."""
        # Try to make move for wrong player
        with pytest.raises((PlayerError, ValueError)):
            self.service.make_move(self.game, self.white_player.id, 7, 7)
        
        # Try to make move on occupied position
        self.service.make_move(self.game, self.black_player.id, 7, 7)
        with pytest.raises((InvalidMoveError, ValueError)):
            self.service.make_move(self.game, self.white_player.id, 7, 7)


@pytest.mark.django_db
class TestGameServiceCheckWin:
    """Test cases for game service win detection functionality."""
    
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
    
    def test_check_win_horizontal_line(self):
        """Test horizontal win detection."""
        board = self.game.board_state['board']
        # Place 5 stones horizontally
        for col in range(5):
            board[7][col] = Player.BLACK
        
        assert self.service.check_win(self.game, 7, 2) is True
        assert self.service.check_win(self.game, 7, 0) is True
        assert self.service.check_win(self.game, 7, 4) is True
    
    def test_check_win_vertical_line(self):
        """Test vertical win detection."""
        board = self.game.board_state['board']
        # Place 5 stones vertically
        for row in range(5):
            board[row][7] = Player.WHITE
        
        assert self.service.check_win(self.game, 2, 7) is True
        assert self.service.check_win(self.game, 0, 7) is True
        assert self.service.check_win(self.game, 4, 7) is True
    
    def test_check_win_diagonal_down_right(self):
        """Test diagonal (down-right) win detection."""
        board = self.game.board_state['board']
        # Place 5 stones diagonally
        for i in range(5):
            board[i][i] = Player.BLACK
        
        assert self.service.check_win(self.game, 2, 2) is True
        assert self.service.check_win(self.game, 0, 0) is True
        assert self.service.check_win(self.game, 4, 4) is True
    
    def test_check_win_diagonal_down_left(self):
        """Test diagonal (down-left) win detection."""
        board = self.game.board_state['board']
        # Place 5 stones diagonally
        for i in range(5):
            board[i][4-i] = Player.WHITE
        
        assert self.service.check_win(self.game, 2, 2) is True
        assert self.service.check_win(self.game, 0, 4) is True
        assert self.service.check_win(self.game, 4, 0) is True
    
    def test_check_win_no_win_four_stones(self):
        """Test that 4 stones don't trigger a win."""
        board = self.game.board_state['board']
        # Place only 4 stones horizontally
        for col in range(4):
            board[7][col] = Player.BLACK
        
        assert self.service.check_win(self.game, 7, 2) is False
    
    def test_check_win_blocked_line(self):
        """Test that blocked lines don't win."""
        board = self.game.board_state['board']
        # Place 4 black stones with white stone blocking
        for col in range(4):
            board[7][col] = Player.BLACK
        board[7][4] = Player.WHITE  # Block the line
        
        assert self.service.check_win(self.game, 7, 2) is False
    
    def test_check_win_overlines_not_allowed(self):
        """Test that overlines don't win when not allowed."""
        # Ruleset has allow_overlines=False
        board = self.game.board_state['board']
        # Place 6 stones horizontally (overline)
        for col in range(6):
            board[7][col] = Player.BLACK
        
        assert self.service.check_win(self.game, 7, 2) is False
    
    def test_check_win_overlines_allowed(self):
        """Test that overlines win when allowed."""
        self.game.ruleset.allow_overlines = True
        self.game.ruleset.save()
        
        board = self.game.board_state['board']
        # Place 6 stones horizontally (overline)
        for col in range(6):
            board[7][col] = Player.BLACK
        
        assert self.service.check_win(self.game, 7, 2) is True
    
    def test_check_win_empty_position(self):
        """Test checking win on empty position returns False."""
        assert self.service.check_win(self.game, 7, 7) is False
    
    def test_check_win_mixed_colors_no_win(self):
        """Test that mixed colors don't create a win."""
        board = self.game.board_state['board']
        # Alternate colors horizontally
        board[7][0] = Player.BLACK
        board[7][1] = Player.WHITE
        board[7][2] = Player.BLACK
        board[7][3] = Player.WHITE
        board[7][4] = Player.BLACK
        
        assert self.service.check_win(self.game, 7, 2) is False


@pytest.mark.django_db
class TestGameServiceUtilityMethods:
    """Test cases for game service utility methods."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GomokuRuleSetFactory(
            name="Test Gomoku",
            board_size=15,
            allow_overlines=True
        )
        self.game = GameFactory(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.service = GomokuGameService()
    
    def test_get_valid_moves_empty_board(self):
        """Test getting valid moves from empty board."""
        valid_moves = self.service.get_valid_moves(self.game)
        
        # 15x15 board should have 225 valid moves
        assert len(valid_moves) == 225
        assert (0, 0) in valid_moves
        assert (7, 7) in valid_moves
        assert (14, 14) in valid_moves
    
    def test_get_valid_moves_with_stones(self):
        """Test getting valid moves with some stones placed."""
        # Place some stones
        board = self.game.board_state['board']
        board[7][7] = Player.BLACK
        board[8][8] = Player.WHITE
        self.game.save()
        
        valid_moves = self.service.get_valid_moves(self.game)
        
        # Should have 225 - 2 = 223 valid moves
        assert len(valid_moves) == 223
        assert (7, 7) not in valid_moves
        assert (8, 8) not in valid_moves
        assert (7, 8) in valid_moves
        assert (8, 7) in valid_moves
    
    def test_resign_game_black_player(self):
        """Test game resignation by black player."""
        self.service.resign_game(self.game, self.black_player.id)
        
        self.game.refresh_from_db()
        assert self.game.status == GameStatus.FINISHED
        assert self.game.winner == self.white_player
    
    def test_resign_game_white_player(self):
        """Test game resignation by white player."""
        self.service.resign_game(self.game, self.white_player.id)
        
        self.game.refresh_from_db()
        assert self.game.status == GameStatus.FINISHED
        assert self.game.winner == self.black_player
    
    def test_resign_game_invalid_player(self):
        """Test resignation by player not in game fails."""
        other_player = UserFactory()
        
        with pytest.raises((PlayerError, ValueError)):
            self.service.resign_game(self.game, other_player.id)
    
    def test_resign_finished_game(self):
        """Test resignation of already finished game fails."""
        self.game.status = GameStatus.FINISHED
        self.game.save()
        
        with pytest.raises((GameStateError, ValueError)):
            self.service.resign_game(self.game, self.black_player.id)
    
    def test_get_player_color_black(self):
        """Test getting player color for black player."""
        if hasattr(self.service, 'get_player_color'):
            color = self.service.get_player_color(self.game, self.black_player.id)
            assert color == Player.BLACK
    
    def test_get_player_color_white(self):
        """Test getting player color for white player."""
        if hasattr(self.service, 'get_player_color'):
            color = self.service.get_player_color(self.game, self.white_player.id)
            assert color == Player.WHITE
    
    def test_get_player_color_invalid(self):
        """Test getting player color for invalid player."""
        if hasattr(self.service, 'get_player_color'):
            other_player = UserFactory()
            with pytest.raises((PlayerError, ValueError)):
                self.service.get_player_color(self.game, other_player.id)


@pytest.mark.django_db
class TestGameServiceStoneCountingMethods:
    """Test cases for stone counting utility methods."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GomokuRuleSetFactory(
            name="Test Gomoku",
            board_size=15,
            allow_overlines=True
        )
        self.game = GameFactory(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.service = GomokuGameService()
    
    def test_count_stones_horizontal_direction(self):
        """Test counting stones in horizontal direction."""
        if not hasattr(self.service, 'count_stones_in_direction'):
            pytest.skip("count_stones_in_direction method not implemented")
        
        board = self.game.board_state['board']
        board_size = self.game.ruleset.board_size
        
        # Place 3 black stones horizontally
        for col in range(7, 10):
            board[7][col] = Player.BLACK
        
        # Count from middle stone to the right (direction is a tuple)
        count_info = self.service.count_stones_in_direction(
            board, board_size, 7, 8, (0, 1), Player.BLACK
        )
        # Method returns tuple (consecutive_count, count_with_gap, max_potential)
        consecutive_count = count_info[0] if isinstance(count_info, tuple) else count_info
        assert consecutive_count == 1  # One stone to the right
        
        # Count from middle stone to the left
        count_info = self.service.count_stones_in_direction(
            board, board_size, 7, 8, (0, -1), Player.BLACK
        )
        consecutive_count = count_info[0] if isinstance(count_info, tuple) else count_info
        assert consecutive_count == 1  # One stone to the left
    
    def test_count_stones_vertical_direction(self):
        """Test counting stones in vertical direction."""
        if not hasattr(self.service, 'count_stones_in_direction'):
            pytest.skip("count_stones_in_direction method not implemented")
        
        board = self.game.board_state['board']
        board_size = self.game.ruleset.board_size
        
        # Place 3 white stones vertically
        for row in range(7, 10):
            board[row][7] = Player.WHITE
        
        # Count from middle stone downward
        count_info = self.service.count_stones_in_direction(
            board, board_size, 8, 7, (1, 0), Player.WHITE
        )
        consecutive_count = count_info[0] if isinstance(count_info, tuple) else count_info
        assert consecutive_count == 1  # One stone below
        
        # Count from middle stone upward
        count_info = self.service.count_stones_in_direction(
            board, board_size, 8, 7, (-1, 0), Player.WHITE
        )
        consecutive_count = count_info[0] if isinstance(count_info, tuple) else count_info
        assert consecutive_count == 1  # One stone above
    
    def test_count_stones_diagonal_direction(self):
        """Test counting stones in diagonal direction."""
        if not hasattr(self.service, 'count_stones_in_direction'):
            pytest.skip("count_stones_in_direction method not implemented")
        
        board = self.game.board_state['board']
        board_size = self.game.ruleset.board_size
        
        # Place 3 black stones diagonally
        for i in range(3):
            board[7+i][7+i] = Player.BLACK
        
        # Count from middle stone diagonally down-right
        count_info = self.service.count_stones_in_direction(
            board, board_size, 8, 8, (1, 1), Player.BLACK
        )
        consecutive_count = count_info[0] if isinstance(count_info, tuple) else count_info
        assert consecutive_count == 1  # One stone diagonally down-right
        
        # Count from middle stone diagonally up-left
        count_info = self.service.count_stones_in_direction(
            board, board_size, 8, 8, (-1, -1), Player.BLACK
        )
        consecutive_count = count_info[0] if isinstance(count_info, tuple) else count_info
        assert consecutive_count == 1  # One stone diagonally up-left
    
    def test_count_stones_different_color(self):
        """Test counting stops at different colored stone."""
        if not hasattr(self.service, 'count_stones_in_direction'):
            pytest.skip("count_stones_in_direction method not implemented")
        
        board = self.game.board_state['board']
        board_size = self.game.ruleset.board_size
        
        # Place stones: Black, Black, White, Black
        board[7][7] = Player.BLACK
        board[7][8] = Player.BLACK
        board[7][9] = Player.WHITE
        board[7][10] = Player.BLACK
        
        # Count black stones from position [7,7] to the right
        count_info = self.service.count_stones_in_direction(
            board, board_size, 7, 7, (0, 1), Player.BLACK
        )
        consecutive_count = count_info[0] if isinstance(count_info, tuple) else count_info
        assert consecutive_count == 1  # Only count until white stone
    
    def test_count_stones_board_boundary(self):
        """Test counting stops at board boundary."""
        if not hasattr(self.service, 'count_stones_in_direction'):
            pytest.skip("count_stones_in_direction method not implemented")
        
        board = self.game.board_state['board']
        board_size = self.game.ruleset.board_size
        
        # Place stones at edge
        board[0][0] = Player.BLACK
        board[0][1] = Player.BLACK
        
        # Count from edge position - should stop at boundary
        count_info = self.service.count_stones_in_direction(
            board, board_size, 0, 0, (-1, 0), Player.BLACK  # Try to count upward from top edge
        )
        consecutive_count = count_info[0] if isinstance(count_info, tuple) else count_info
        assert consecutive_count == 0  # No stones above top edge
        
        count_info = self.service.count_stones_in_direction(
            board, board_size, 0, 0, (0, 1), Player.BLACK  # Count to the right
        )
        consecutive_count = count_info[0] if isinstance(count_info, tuple) else count_info
        assert consecutive_count == 1  # One stone to the right


@pytest.mark.django_db
class TestGameServiceIntegration:
    """Integration tests for game service functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GomokuRuleSetFactory(
            name="Integration Test Gomoku",
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
    
    def test_complete_game_simulation(self):
        """Test a complete game from start to finish."""
        moves = [
            (self.black_player.id, 7, 7),   # Black center
            (self.white_player.id, 8, 8),   # White diagonal
            (self.black_player.id, 7, 8),   # Black right
            (self.white_player.id, 9, 9),   # White diagonal
            (self.black_player.id, 7, 9),   # Black right
            (self.white_player.id, 10, 10), # White diagonal
            (self.black_player.id, 7, 10),  # Black right
            (self.white_player.id, 6, 6),   # White diagonal
            (self.black_player.id, 7, 11),  # Black right (winning move)
        ]
        
        for i, (player_id, row, col) in enumerate(moves):
            move = self.service.make_move(self.game, player_id, row, col)
            
            self.game.refresh_from_db()
            assert move.move_number == i + 1
            
            if i < len(moves) - 1:  # Not the last move
                assert self.game.status == GameStatus.ACTIVE
            else:  # Last move should win
                assert self.game.status == GameStatus.FINISHED
                assert self.game.winner == self.black_player
                assert move.is_winning_move is True
    
    def test_invalid_move_sequence(self):
        """Test that invalid moves are properly rejected."""
        # Make first move
        self.service.make_move(self.game, self.black_player.id, 7, 7)
        
        # Try to make move with same player (should fail)
        with pytest.raises((PlayerError, ValueError)):
            self.service.make_move(self.game, self.black_player.id, 8, 8)
        
        # Try to make move on occupied position (should fail)
        with pytest.raises((InvalidMoveError, ValueError)):
            self.service.make_move(self.game, self.white_player.id, 7, 7)
        
        # Make valid move
        self.service.make_move(self.game, self.white_player.id, 8, 8)
        
        # Game should still be active and state should be correct
        self.game.refresh_from_db()
        assert self.game.status == GameStatus.ACTIVE
        assert self.game.move_count == 2
        assert self.game.current_player == Player.BLACK
    
    def test_game_statistics_update(self):
        """Test that game and player statistics are updated correctly."""
        initial_black_games = self.black_player.games_played
        initial_white_games = self.white_player.games_played
        
        # Simulate a game where black wins
        moves = [
            (self.black_player.id, 7, 7),
            (self.white_player.id, 8, 8),
            (self.black_player.id, 7, 8),
            (self.white_player.id, 9, 9),
            (self.black_player.id, 7, 9),
            (self.white_player.id, 10, 10),
            (self.black_player.id, 7, 10),
            (self.white_player.id, 6, 6),
            (self.black_player.id, 7, 11),  # Winning move
        ]
        
        for player_id, row, col in moves:
            self.service.make_move(self.game, player_id, row, col)
        
        self.game.refresh_from_db()
        assert self.game.status == GameStatus.FINISHED
        assert self.game.winner == self.black_player
        
        # Check that game has proper move count
        assert self.game.move_count == len(moves)
        
        # Check that moves are recorded properly
        game_moves = GameMove.objects.filter(game=self.game).order_by('move_number')
        assert game_moves.count() == len(moves)
        
        for i, move in enumerate(game_moves):
            expected_player_id, expected_row, expected_col = moves[i]
            assert move.row == expected_row
            assert move.col == expected_col
            assert move.move_number == i + 1
            
            if i == len(moves) - 1:  # Last move
                assert move.is_winning_move is True
            else:
                assert move.is_winning_move is False
    
    def test_concurrent_game_handling(self):
        """Test handling multiple games simultaneously."""
        # Create second game
        other_player1 = UserFactory()
        other_player2 = UserFactory()
        other_ruleset = GomokuRuleSetFactory(board_size=9)
        other_game = GameFactory(
            black_player=other_player1,
            white_player=other_player2,
            ruleset=other_ruleset,
            status=GameStatus.ACTIVE
        )
        other_game.initialize_board()
        
        # Make moves in both games
        move1_game1 = self.service.make_move(self.game, self.black_player.id, 7, 7)
        move1_game2 = self.service.make_move(other_game, other_player1.id, 4, 4)
        
        move2_game1 = self.service.make_move(self.game, self.white_player.id, 8, 8)
        move2_game2 = self.service.make_move(other_game, other_player2.id, 5, 5)
        
        # Verify games are independent
        self.game.refresh_from_db()
        other_game.refresh_from_db()
        
        assert self.game.move_count == 2
        assert other_game.move_count == 2
        
        assert self.game.current_player == Player.BLACK
        assert other_game.current_player == Player.BLACK
        
        # Verify board states are independent
        assert self.game.board_state['board'][7][7] == Player.BLACK
        assert self.game.board_state['board'][4][4] is None
        
        assert other_game.board_state['board'][4][4] == Player.BLACK
        assert other_game.board_state['board'][7][7] is None
    
    def test_service_error_handling(self):
        """Test that service properly handles various error conditions."""
        # Test with None game - should raise AttributeError or ValueError
        with pytest.raises((TypeError, ValueError, AttributeError)):
            self.service.validate_move(None, self.black_player.id, 7, 7)
        
        # Test with invalid player ID 
        with pytest.raises((TypeError, ValueError, PlayerError)):
            self.service.validate_move(self.game, None, 7, 7)
        
        # Test after game is finished
        self.game.status = GameStatus.FINISHED
        self.game.save()
        
        with pytest.raises((GameStateError, ValueError)):
            self.service.make_move(self.game, self.black_player.id, 7, 7)


@pytest.mark.django_db
class TestGoGameServiceSpecific:
    """Test cases specific to Go game service functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data for Go games."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GoRuleSetFactory(
            name="Test Go",
            board_size=19,
            komi=6.5,
            handicap_stones=0
        )
        self.game = GameFactory(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.service = GoGameService()
    
    def test_go_pass_move_functionality(self):
        """Test Go-specific pass move functionality."""
        # Make a pass move (using -1, -1 coordinates)
        if hasattr(self.service, 'pass_turn'):
            move = self.service.pass_turn(self.game, self.black_player.id)
        else:
            # If pass_turn doesn't exist, use make_move with pass coordinates
            move = self.service.make_move(self.game, self.black_player.id, -1, -1)
        
        assert move.row == -1
        assert move.col == -1
        assert move.player_color == Player.BLACK
        
        self.game.refresh_from_db()
        assert self.game.board_state['consecutive_passes'] == 1
        assert self.game.current_player == Player.WHITE
    
    def test_go_consecutive_passes_end_game(self):
        """Test that two consecutive passes end a Go game."""
        # Black passes
        if hasattr(self.service, 'pass_turn'):
            self.service.pass_turn(self.game, self.black_player.id)
        else:
            self.service.make_move(self.game, self.black_player.id, -1, -1)
        
        self.game.refresh_from_db()
        assert self.game.status == GameStatus.ACTIVE
        assert self.game.board_state['consecutive_passes'] == 1
        
        # White passes - should end game
        if hasattr(self.service, 'pass_turn'):
            self.service.pass_turn(self.game, self.white_player.id)
        else:
            self.service.make_move(self.game, self.white_player.id, -1, -1)
        
        self.game.refresh_from_db()
        assert self.game.status == GameStatus.FINISHED
        assert self.game.board_state['consecutive_passes'] == 2
    
    def test_go_move_resets_pass_count(self):
        """Test that making a stone move resets consecutive pass count."""
        # Set up a pass
        self.game.board_state['consecutive_passes'] = 1
        self.game.save()
        
        # Make a stone move
        self.service.make_move(self.game, self.black_player.id, 10, 10)
        
        self.game.refresh_from_db()
        assert self.game.board_state['consecutive_passes'] == 0
    
    def test_go_ko_rule_validation(self):
        """Test Ko rule enforcement in Go."""
        # Set up Ko position
        self.game.board_state['ko_position'] = [10, 10]
        self.game.save()
        
        # Try to make move on Ko position
        with pytest.raises(InvalidMoveError):
            self.service.validate_move(self.game, self.black_player.id, 10, 10)
    
    def test_go_capture_tracking(self):
        """Test that Go board properly tracks captures."""
        board_state = self.game.board_state
        assert 'captured_stones' in board_state
        assert board_state['captured_stones'] == {'black': 0, 'white': 0}
        assert 'ko_position' in board_state
        assert board_state['ko_position'] is None
    
    def test_go_board_size_validation(self):
        """Test Go board size constraints."""
        # Go typically supports 9x9, 13x13, 19x19
        valid_moves = self.service.get_valid_moves(self.game)
        expected_moves = 19 * 19
        
        # Go get_valid_moves returns only board positions (pass is handled separately)
        assert len(valid_moves) == expected_moves
        
        # Verify all positions are valid board positions
        for row, col in valid_moves:
            assert 0 <= row < 19
            assert 0 <= col < 19