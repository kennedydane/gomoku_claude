"""
Tests for the GameService class.

This module contains comprehensive tests for the GameService class,
covering move validation, win detection, and game state management.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from backend.db.models import Game, GameMove, GameStatus, Player
from backend.services.game_service import GameService


@pytest_asyncio.fixture
async def mock_db_session():
    """Create a mock database session."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    return mock_session


@pytest_asyncio.fixture
async def game_service_mock(mock_db_session):
    """Create a GameService instance with mock database session."""
    return GameService(mock_db_session)


@pytest_asyncio.fixture
async def game_service_real(db_session):
    """Create a GameService instance with real database session."""
    return GameService(db_session)


@pytest_asyncio.fixture
async def sample_active_game(sample_user, sample_user2, sample_ruleset):
    """Create a sample active game for testing."""
    game = Game(
        black_player_id=sample_user.id,
        white_player_id=sample_user2.id,
        ruleset_id=sample_ruleset.id,
        status=GameStatus.ACTIVE,
        current_player=Player.BLACK,
        move_count=0
    )
    # Initialize empty 15x15 board
    game.board_state = {
        "size": 15,
        "board": [[None for _ in range(15)] for _ in range(15)]
    }
    return game


@pytest_asyncio.fixture
async def sample_finished_game(sample_user, sample_user2, sample_ruleset):
    """Create a sample finished game for testing."""
    game = Game(
        black_player_id=sample_user.id,
        white_player_id=sample_user2.id,
        ruleset_id=sample_ruleset.id,
        status=GameStatus.FINISHED,
        current_player=Player.BLACK,
        move_count=10,
        winner_id=sample_user.id
    )
    game.board_state = {
        "size": 15,
        "board": [[None for _ in range(15)] for _ in range(15)]
    }
    return game


class TestValidateMove:
    """Test cases for the validate_move method."""

    async def test_validate_move_valid_black_turn(self, game_service_real, sample_active_game):
        """Test validating a valid move on black player's turn."""
        # Should not raise any exception
        await game_service_real.validate_move(sample_active_game, sample_active_game.black_player_id, 7, 7)

    async def test_validate_move_valid_white_turn(self, game_service_real, sample_active_game):
        """Test validating a valid move on white player's turn."""
        sample_active_game.current_player = Player.WHITE
        # Should not raise any exception
        await game_service_real.validate_move(sample_active_game, sample_active_game.white_player_id, 7, 7)

    async def test_validate_move_game_not_active(self, game_service_real, sample_finished_game):
        """Test validating a move when game is not active."""
        with pytest.raises(ValueError, match="Game is not active"):
            await game_service_real.validate_move(sample_finished_game, sample_finished_game.black_player_id, 7, 7)

    async def test_validate_move_wrong_player_turn(self, game_service_real, sample_active_game):
        """Test validating a move when it's not the player's turn."""
        # It's black's turn, but white player tries to move
        with pytest.raises(ValueError, match="It's black player's turn"):
            await game_service_real.validate_move(sample_active_game, sample_active_game.white_player_id, 7, 7)

    async def test_validate_move_out_of_bounds_negative(self, game_service_real, sample_active_game):
        """Test validating a move with negative coordinates."""
        with pytest.raises(ValueError, match="Move position \\(-1, 5\\) is out of bounds"):
            await game_service_real.validate_move(sample_active_game, sample_active_game.black_player_id, -1, 5)

    async def test_validate_move_out_of_bounds_too_large(self, game_service_real, sample_active_game):
        """Test validating a move with coordinates too large."""
        with pytest.raises(ValueError, match="Move position \\(15, 7\\) is out of bounds"):
            await game_service_real.validate_move(sample_active_game, sample_active_game.black_player_id, 15, 7)

    async def test_validate_move_position_occupied(self, game_service_real, sample_active_game):
        """Test validating a move on an occupied position."""
        # Place a stone at (7, 7)
        sample_active_game.board_state["board"][7][7] = "black"
        
        with pytest.raises(ValueError, match="Position \\(7, 7\\) is already occupied"):
            await game_service_real.validate_move(sample_active_game, sample_active_game.black_player_id, 7, 7)

    async def test_validate_move_edge_positions(self, game_service_real, sample_active_game):
        """Test validating moves at board edges."""
        # Test all four corners
        await game_service_real.validate_move(sample_active_game, sample_active_game.black_player_id, 0, 0)
        await game_service_real.validate_move(sample_active_game, sample_active_game.black_player_id, 0, 14)
        await game_service_real.validate_move(sample_active_game, sample_active_game.black_player_id, 14, 0)
        await game_service_real.validate_move(sample_active_game, sample_active_game.black_player_id, 14, 14)

    async def test_validate_move_different_board_size(self, game_service_real, sample_active_game):
        """Test validating moves on different board size."""
        # Change board size to 19x19
        sample_active_game.board_state = {
            "size": 19,
            "board": [[None for _ in range(19)] for _ in range(19)]
        }
        
        # Valid move on 19x19 board
        await game_service_real.validate_move(sample_active_game, sample_active_game.black_player_id, 18, 18)
        
        # Invalid move beyond 19x19 board
        with pytest.raises(ValueError, match="Move position \\(19, 18\\) is out of bounds"):
            await game_service_real.validate_move(sample_active_game, sample_active_game.black_player_id, 19, 18)


class TestMakeMove:
    """Test cases for the make_move method."""

    async def test_make_move_first_black_move(self, game_service_real, sample_active_game, db_session):
        """Test making the first move as black player."""
        # Add game to session so it can be refreshed
        db_session.add(sample_active_game)
        await db_session.commit()
        await db_session.refresh(sample_active_game)
        
        move = await game_service_real.make_move(sample_active_game, sample_active_game.black_player_id, 7, 7)
        
        # Check move properties
        assert move.game_id == sample_active_game.id
        assert move.player_id == sample_active_game.black_player_id
        assert move.move_number == 1
        assert move.row == 7
        assert move.col == 7
        assert move.player_color == Player.BLACK
        assert move.is_winning_move == False
        
        # Check game state updates
        assert sample_active_game.board_state["board"][7][7] == "black"
        assert sample_active_game.move_count == 1
        assert sample_active_game.current_player == Player.WHITE
        assert sample_active_game.status == GameStatus.ACTIVE

    async def test_make_move_second_white_move(self, game_service_real, sample_active_game, db_session):
        """Test making the second move as white player."""
        # Add game to session
        db_session.add(sample_active_game)
        await db_session.commit()
        await db_session.refresh(sample_active_game)
        
        # Make first black move
        await game_service_real.make_move(sample_active_game, sample_active_game.black_player_id, 7, 7)
        
        # Make second white move
        move = await game_service_real.make_move(sample_active_game, sample_active_game.white_player_id, 8, 8)
        
        # Check move properties
        assert move.move_number == 2
        assert move.player_color == Player.WHITE
        assert move.is_winning_move == False
        
        # Check game state
        assert sample_active_game.board_state["board"][8][8] == "white"
        assert sample_active_game.move_count == 2
        assert sample_active_game.current_player == Player.BLACK

    async def test_make_move_invalid_move_validation(self, game_service_real, sample_active_game, db_session):
        """Test that make_move validates moves properly."""
        db_session.add(sample_active_game)
        await db_session.commit()
        
        # Try to make move with wrong player
        with pytest.raises(ValueError, match="It's black player's turn"):
            await game_service_real.make_move(sample_active_game, sample_active_game.white_player_id, 7, 7)

    async def test_make_move_winning_move_horizontal(self, game_service_real, sample_active_game, db_session):
        """Test making a winning move (5 in a row horizontally)."""
        db_session.add(sample_active_game)
        await db_session.commit()
        await db_session.refresh(sample_active_game)
        
        # Set up 4 black stones in a row
        board = sample_active_game.board_state["board"]
        board[7][3] = "black"
        board[7][4] = "black"
        board[7][5] = "black"
        board[7][6] = "black"
        sample_active_game.move_count = 4
        
        # Make the winning move
        move = await game_service_real.make_move(sample_active_game, sample_active_game.black_player_id, 7, 7)
        
        # Check winning move
        assert move.is_winning_move == True
        assert sample_active_game.status == GameStatus.FINISHED
        assert sample_active_game.winner_id == sample_active_game.black_player_id
        # Should not switch turns after winning
        assert sample_active_game.current_player == Player.BLACK


class TestCheckWin:
    """Test cases for the check_win method."""

    def test_check_win_horizontal_5_in_row(self, game_service_mock):
        """Test win detection for 5 stones in a row horizontally."""
        board = [[None for _ in range(15)] for _ in range(15)]
        
        # Place 5 black stones in a row
        for col in range(5, 10):
            board[7][col] = "black"
        
        # Check win at different positions
        assert game_service_mock.check_win(board, 7, 5, "black") == True
        assert game_service_mock.check_win(board, 7, 7, "black") == True
        assert game_service_mock.check_win(board, 7, 9, "black") == True

    def test_check_win_vertical_5_in_row(self, game_service_mock):
        """Test win detection for 5 stones in a column vertically."""
        board = [[None for _ in range(15)] for _ in range(15)]
        
        # Place 5 black stones in a column
        for row in range(5, 10):
            board[row][7] = "black"
        
        # Check win at different positions
        assert game_service_mock.check_win(board, 5, 7, "black") == True
        assert game_service_mock.check_win(board, 7, 7, "black") == True
        assert game_service_mock.check_win(board, 9, 7, "black") == True

    def test_check_win_diagonal_right_5_in_row(self, game_service_mock):
        """Test win detection for 5 stones diagonally (\\)."""
        board = [[None for _ in range(15)] for _ in range(15)]
        
        # Place 5 black stones diagonally
        for i in range(5):
            board[5 + i][5 + i] = "black"
        
        # Check win at different positions
        assert game_service_mock.check_win(board, 5, 5, "black") == True
        assert game_service_mock.check_win(board, 7, 7, "black") == True
        assert game_service_mock.check_win(board, 9, 9, "black") == True

    def test_check_win_diagonal_left_5_in_row(self, game_service_mock):
        """Test win detection for 5 stones diagonally (/)."""
        board = [[None for _ in range(15)] for _ in range(15)]
        
        # Place 5 black stones diagonally
        for i in range(5):
            board[5 + i][9 - i] = "black"
        
        # Check win at different positions
        assert game_service_mock.check_win(board, 5, 9, "black") == True
        assert game_service_mock.check_win(board, 7, 7, "black") == True
        assert game_service_mock.check_win(board, 9, 5, "black") == True

    def test_check_win_no_win_4_in_row(self, game_service_mock):
        """Test that 4 stones in a row don't count as a win."""
        board = [[None for _ in range(15)] for _ in range(15)]
        
        # Place 4 black stones in a row
        for col in range(5, 9):
            board[7][col] = "black"
        
        # Should not be a win
        assert game_service_mock.check_win(board, 7, 5, "black") == False
        assert game_service_mock.check_win(board, 7, 8, "black") == False

    def test_check_win_blocked_by_opponent(self, game_service_mock):
        """Test that opponent stones block a potential win."""
        board = [[None for _ in range(15)] for _ in range(15)]
        
        # Place 4 black stones with white stone in between
        board[7][5] = "black"
        board[7][6] = "black"
        board[7][7] = "white"  # White stone blocks
        board[7][8] = "black"
        board[7][9] = "black"
        
        # Should not be a win for any black stone
        assert game_service_mock.check_win(board, 7, 5, "black") == False
        assert game_service_mock.check_win(board, 7, 6, "black") == False
        assert game_service_mock.check_win(board, 7, 8, "black") == False
        assert game_service_mock.check_win(board, 7, 9, "black") == False

    def test_check_win_6_in_row_counts_as_win(self, game_service_mock):
        """Test that 6 stones in a row count as a win."""
        board = [[None for _ in range(15)] for _ in range(15)]
        
        # Place 6 black stones in a row
        for col in range(5, 11):
            board[7][col] = "black"
        
        # Should be a win
        assert game_service_mock.check_win(board, 7, 7, "black") == True
        assert game_service_mock.check_win(board, 7, 10, "black") == True

    def test_check_win_edge_cases(self, game_service_mock):
        """Test win detection at board edges."""
        board = [[None for _ in range(15)] for _ in range(15)]
        
        # Win at left edge
        for col in range(5):
            board[7][col] = "black"
        assert game_service_mock.check_win(board, 7, 0, "black") == True
        
        # Win at right edge  
        board = [[None for _ in range(15)] for _ in range(15)]
        for col in range(10, 15):
            board[7][col] = "black"
        assert game_service_mock.check_win(board, 7, 14, "black") == True
        
        # Win at top edge
        board = [[None for _ in range(15)] for _ in range(15)]
        for row in range(5):
            board[row][7] = "black"
        assert game_service_mock.check_win(board, 0, 7, "black") == True

    def test_check_win_different_colors(self, game_service_mock):
        """Test win detection for different player colors."""
        board = [[None for _ in range(15)] for _ in range(15)]
        
        # Black wins
        for col in range(5, 10):
            board[7][col] = "black"
        assert game_service_mock.check_win(board, 7, 7, "black") == True
        assert game_service_mock.check_win(board, 7, 7, "white") == False
        
        # White wins
        board = [[None for _ in range(15)] for _ in range(15)]
        for col in range(5, 10):
            board[8][col] = "white"
        assert game_service_mock.check_win(board, 8, 7, "white") == True
        assert game_service_mock.check_win(board, 8, 7, "black") == False


class TestGetGameStatus:
    """Test cases for the get_game_status method."""

    async def test_get_game_status_active_game(self, game_service_mock, sample_active_game):
        """Test getting status for an active game."""
        status = await game_service_mock.get_game_status(sample_active_game)
        
        expected_status = {
            "id": sample_active_game.id,
            "status": "active",
            "current_player": "black",
            "move_count": 0,
            "is_game_over": False,
            "winner_id": None,
            "board_state": {
                "size": 15,
                "board": [[None for _ in range(15)] for _ in range(15)]
            }
        }
        
        assert status == expected_status

    async def test_get_game_status_finished_game(self, game_service_mock, sample_finished_game):
        """Test getting status for a finished game."""
        status = await game_service_mock.get_game_status(sample_finished_game)
        
        expected_status = {
            "id": sample_finished_game.id,
            "status": "finished",
            "current_player": "black",
            "move_count": 10,
            "is_game_over": True,
            "winner_id": sample_finished_game.winner_id,
            "board_state": {
                "size": 15,
                "board": [[None for _ in range(15)] for _ in range(15)]
            }
        }
        
        assert status == expected_status


class TestGameServiceIntegration:
    """Integration tests for GameService with real database."""

    async def test_complete_game_workflow(self, game_service_real, db_session, sample_user, sample_user2, sample_ruleset):
        """Test complete game workflow from start to win."""
        # Create a new game
        game = Game(
            black_player_id=sample_user.id,
            white_player_id=sample_user2.id,
            ruleset_id=sample_ruleset.id,
            status=GameStatus.ACTIVE,
            current_player=Player.BLACK,
            move_count=0
        )
        game.board_state = {
            "size": 15,
            "board": [[None for _ in range(15)] for _ in range(15)]
        }
        
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        # Make several moves leading to a win
        # Create horizontal 5-in-a-row for black at row 7, columns 7-11
        moves = [
            (sample_user.id, 7, 7),     # Black move 1
            (sample_user2.id, 8, 7),    # White move 1
            (sample_user.id, 7, 8),     # Black move 2
            (sample_user2.id, 8, 8),    # White move 2
            (sample_user.id, 7, 9),     # Black move 3
            (sample_user2.id, 8, 9),    # White move 3
            (sample_user.id, 7, 10),    # Black move 4
            (sample_user2.id, 8, 10),   # White move 4
            (sample_user.id, 7, 11),    # Black move 5 - WINNING MOVE
        ]
        
        for i, (player_id, row, col) in enumerate(moves):
            move = await game_service_real.make_move(game, player_id, row, col)
            
            if i == 8:  # Last move should be winning
                assert move.is_winning_move == True
                assert game.status == GameStatus.FINISHED
                assert game.winner_id == sample_user.id
            else:
                assert move.is_winning_move == False
                assert game.status == GameStatus.ACTIVE
        
        # Verify final game state
        status = await game_service_real.get_game_status(game)
        assert status["status"] == "finished"
        assert status["winner_id"] == sample_user.id
        assert status["move_count"] == 9

    async def test_alternating_turns_enforcement(self, game_service_real, db_session, sample_user, sample_user2, sample_ruleset):
        """Test that the service enforces alternating turns."""
        game = Game(
            black_player_id=sample_user.id,
            white_player_id=sample_user2.id,
            ruleset_id=sample_ruleset.id,
            status=GameStatus.ACTIVE,
            current_player=Player.BLACK,
            move_count=0
        )
        game.board_state = {
            "size": 15,
            "board": [[None for _ in range(15)] for _ in range(15)]
        }
        
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        # Black makes first move
        await game_service_real.make_move(game, sample_user.id, 7, 7)
        assert game.current_player == Player.WHITE
        
        # Black tries to make another move (should fail)
        with pytest.raises(ValueError, match="It's white player's turn"):
            await game_service_real.make_move(game, sample_user.id, 8, 8)
        
        # White makes proper move
        await game_service_real.make_move(game, sample_user2.id, 8, 8)
        assert game.current_player == Player.BLACK