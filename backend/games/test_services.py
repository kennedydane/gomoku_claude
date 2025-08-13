"""
Comprehensive tests for GameService business logic.
"""

from django.test import TestCase, TransactionTestCase
from django.db import transaction

from tests.factories import UserFactory, RuleSetFactory, GameFactory
from .models import Game, GameMove, GameStatus, Player
from .services import GameService


class GameServiceValidateMoveTestCase(TestCase):
    """Test cases for GameService.validate_move method."""
    
    def setUp(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = RuleSetFactory(board_size=15)
        self.game = GameFactory(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
    
    def test_validate_move_valid(self):
        """Test validating a valid move."""
        # Should not raise exception
        GameService.validate_move(self.game, self.black_player.id, 7, 7)
    
    def test_validate_move_inactive_game(self):
        """Test validating move on inactive game fails."""
        self.game.status = GameStatus.WAITING
        self.game.save()
        
        with self.assertRaises(ValueError) as context:
            GameService.validate_move(self.game, self.black_player.id, 7, 7)
        
        self.assertIn("Game is not active", str(context.exception))
    
    def test_validate_move_wrong_player_turn(self):
        """Test validating move when it's not player's turn."""
        # It's black player's turn by default, try white player
        with self.assertRaises(ValueError) as context:
            GameService.validate_move(self.game, self.white_player.id, 7, 7)
        
        self.assertIn("It's not your turn", str(context.exception))
    
    def test_validate_move_out_of_bounds_negative(self):
        """Test validating move with negative coordinates."""
        with self.assertRaises(ValueError) as context:
            GameService.validate_move(self.game, self.black_player.id, -1, 7)
        
        self.assertIn("Move out of bounds", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            GameService.validate_move(self.game, self.black_player.id, 7, -1)
        
        self.assertIn("Move out of bounds", str(context.exception))
    
    def test_validate_move_out_of_bounds_too_large(self):
        """Test validating move with coordinates too large."""
        with self.assertRaises(ValueError) as context:
            GameService.validate_move(self.game, self.black_player.id, 15, 7)
        
        self.assertIn("Move out of bounds", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            GameService.validate_move(self.game, self.black_player.id, 7, 15)
        
        self.assertIn("Move out of bounds", str(context.exception))
    
    def test_validate_move_position_occupied(self):
        """Test validating move on occupied position."""
        # Place a stone first
        self.game.board_state['board'][7][7] = Player.BLACK
        self.game.save()
        
        with self.assertRaises(ValueError) as context:
            GameService.validate_move(self.game, self.black_player.id, 7, 7)
        
        self.assertIn("Position already occupied", str(context.exception))
    
    def test_validate_move_white_player_turn(self):
        """Test validating move when it's white player's turn."""
        self.game.current_player = Player.WHITE
        self.game.save()
        
        # Should not raise exception
        GameService.validate_move(self.game, self.white_player.id, 7, 7)
    
    def test_validate_move_board_size_boundaries(self):
        """Test move validation on board boundaries."""
        # Valid boundary moves
        GameService.validate_move(self.game, self.black_player.id, 0, 0)
        GameService.validate_move(self.game, self.black_player.id, 14, 14)
        GameService.validate_move(self.game, self.black_player.id, 0, 14)
        GameService.validate_move(self.game, self.black_player.id, 14, 0)


class GameServiceMakeMoveTestCase(TransactionTestCase):
    """Test cases for GameService.make_move method."""
    
    def setUp(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = RuleSetFactory(board_size=15)
        self.game = GameFactory(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
    
    def test_make_move_successful(self):
        """Test making a successful move."""
        move = GameService.make_move(self.game, self.black_player.id, 7, 7)
        
        self.assertEqual(move.game, self.game)
        self.assertEqual(move.player, self.black_player)
        self.assertEqual(move.row, 7)
        self.assertEqual(move.col, 7)
        self.assertEqual(move.player_color, Player.BLACK)
        self.assertEqual(move.move_number, 1)
        self.assertFalse(move.is_winning_move)
        
        # Check game state updated
        self.game.refresh_from_db()
        self.assertEqual(self.game.move_count, 1)
        self.assertEqual(self.game.current_player, Player.WHITE)
        self.assertEqual(self.game.board_state['board'][7][7], Player.BLACK)
    
    def test_make_move_initializes_board(self):
        """Test that make_move initializes board if needed."""
        # Clear board state
        self.game.board_state = {}
        self.game.save()
        
        move = GameService.make_move(self.game, self.black_player.id, 7, 7)
        
        self.game.refresh_from_db()
        self.assertEqual(self.game.board_state['size'], 15)
        self.assertEqual(len(self.game.board_state['board']), 15)
    
    def test_make_move_alternates_players(self):
        """Test that moves alternate between players."""
        # Black player move
        move1 = GameService.make_move(self.game, self.black_player.id, 7, 7)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_player, Player.WHITE)
        
        # White player move
        move2 = GameService.make_move(self.game, self.white_player.id, 7, 8)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_player, Player.BLACK)
    
    def test_make_move_increments_count(self):
        """Test that move count is incremented."""
        GameService.make_move(self.game, self.black_player.id, 7, 7)
        self.game.refresh_from_db()
        self.assertEqual(self.game.move_count, 1)
        
        GameService.make_move(self.game, self.white_player.id, 7, 8)
        self.game.refresh_from_db()
        self.assertEqual(self.game.move_count, 2)
    
    def test_make_move_invalid_raises_error(self):
        """Test that invalid moves raise errors."""
        with self.assertRaises(ValueError):
            GameService.make_move(self.game, self.white_player.id, 7, 7)  # Wrong turn
        
        with self.assertRaises(ValueError):
            GameService.make_move(self.game, self.black_player.id, -1, 7)  # Out of bounds
    
    def test_make_winning_move(self):
        """Test making a winning move."""
        # Set up a winning scenario (4 in a row, need 5th)
        board = self.game.board_state['board']
        for col in range(4):
            board[7][col] = Player.BLACK
        self.game.save()
        
        # Make the winning move
        move = GameService.make_move(self.game, self.black_player.id, 7, 4)
        
        self.assertTrue(move.is_winning_move)
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(self.game.winner, self.black_player)
    
    def test_make_move_white_player(self):
        """Test making move as white player."""
        # Make black move first
        GameService.make_move(self.game, self.black_player.id, 7, 7)
        
        # Make white move
        move = GameService.make_move(self.game, self.white_player.id, 8, 8)
        
        self.assertEqual(move.player_color, Player.WHITE)
        self.assertEqual(move.player, self.white_player)


class GameServiceCheckWinTestCase(TestCase):
    """Test cases for GameService.check_win method."""
    
    def setUp(self):
        """Set up test data."""
        self.ruleset = RuleSetFactory(board_size=15, allow_overlines=False)
        self.game = GameFactory(ruleset=self.ruleset)
        self.game.initialize_board()
    
    def test_check_win_horizontal_five(self):
        """Test horizontal win detection."""
        board = self.game.board_state['board']
        # Place 5 stones horizontally
        for col in range(5):
            board[7][col] = Player.BLACK
        
        self.assertTrue(GameService.check_win(self.game, 7, 2))  # Check middle stone
        self.assertTrue(GameService.check_win(self.game, 7, 0))  # Check edge stone
    
    def test_check_win_vertical_five(self):
        """Test vertical win detection."""
        board = self.game.board_state['board']
        # Place 5 stones vertically
        for row in range(5):
            board[row][7] = Player.WHITE
        
        self.assertTrue(GameService.check_win(self.game, 2, 7))  # Check middle stone
        self.assertTrue(GameService.check_win(self.game, 4, 7))  # Check edge stone
    
    def test_check_win_diagonal_descending(self):
        """Test descending diagonal win detection."""
        board = self.game.board_state['board']
        # Place 5 stones in descending diagonal (\)
        for i in range(5):
            board[i][i] = Player.BLACK
        
        self.assertTrue(GameService.check_win(self.game, 2, 2))  # Check middle
        self.assertTrue(GameService.check_win(self.game, 0, 0))  # Check start
    
    def test_check_win_diagonal_ascending(self):
        """Test ascending diagonal win detection."""
        board = self.game.board_state['board']
        # Place 5 stones in ascending diagonal (/)
        for i in range(5):
            board[4-i][i] = Player.WHITE
        
        self.assertTrue(GameService.check_win(self.game, 2, 2))  # Check middle
        self.assertTrue(GameService.check_win(self.game, 4, 0))  # Check start
    
    def test_check_win_four_stones_no_win(self):
        """Test that 4 stones don't win."""
        board = self.game.board_state['board']
        # Place only 4 stones horizontally
        for col in range(4):
            board[7][col] = Player.BLACK
        
        self.assertFalse(GameService.check_win(self.game, 7, 2))
    
    def test_check_win_six_stones_no_overlines(self):
        """Test that 6 stones don't win when overlines not allowed."""
        board = self.game.board_state['board']
        # Place 6 stones horizontally
        for col in range(6):
            board[7][col] = Player.BLACK
        
        self.assertFalse(GameService.check_win(self.game, 7, 2))
    
    def test_check_win_six_stones_with_overlines(self):
        """Test that 6 stones win when overlines allowed."""
        self.game.ruleset.allow_overlines = True
        self.game.ruleset.save()
        
        board = self.game.board_state['board']
        # Place 6 stones horizontally
        for col in range(6):
            board[7][col] = Player.BLACK
        
        self.assertTrue(GameService.check_win(self.game, 7, 2))
    
    def test_check_win_interrupted_line(self):
        """Test that interrupted lines don't win."""
        board = self.game.board_state['board']
        # Place stones with a gap
        board[7][0] = Player.BLACK
        board[7][1] = Player.BLACK
        board[7][2] = Player.WHITE  # Interruption
        board[7][3] = Player.BLACK
        board[7][4] = Player.BLACK
        
        self.assertFalse(GameService.check_win(self.game, 7, 1))
        self.assertFalse(GameService.check_win(self.game, 7, 4))
    
    def test_check_win_empty_board(self):
        """Test win check on empty board."""
        # Empty board should never have a win
        self.assertFalse(GameService.check_win(self.game, 7, 7))
    
    def test_check_win_board_edges(self):
        """Test win detection at board edges."""
        board = self.game.board_state['board']
        # Horizontal win at top edge
        for col in range(5):
            board[0][col] = Player.BLACK
        self.assertTrue(GameService.check_win(self.game, 0, 2))
        
        # Vertical win at left edge
        for row in range(5):
            board[row][0] = Player.WHITE
        self.assertTrue(GameService.check_win(self.game, 2, 0))


class GameServiceUtilityMethodsTestCase(TestCase):
    """Test cases for GameService utility methods."""
    
    def setUp(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = RuleSetFactory(board_size=9)  # Smaller board for testing
        self.game = GameFactory(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
    
    def test_get_valid_moves_empty_board(self):
        """Test getting valid moves from empty board."""
        valid_moves = GameService.get_valid_moves(self.game)
        
        # 9x9 board should have 81 valid moves
        self.assertEqual(len(valid_moves), 81)
        
        # Check some specific moves
        self.assertIn((0, 0), valid_moves)
        self.assertIn((4, 4), valid_moves)  # Center
        self.assertIn((8, 8), valid_moves)
    
    def test_get_valid_moves_with_stones(self):
        """Test getting valid moves with stones on board."""
        # Place some stones
        board = self.game.board_state['board']
        board[4][4] = Player.BLACK
        board[4][5] = Player.WHITE
        self.game.save()
        
        valid_moves = GameService.get_valid_moves(self.game)
        
        # Should have 81 - 2 = 79 valid moves
        self.assertEqual(len(valid_moves), 79)
        self.assertNotIn((4, 4), valid_moves)
        self.assertNotIn((4, 5), valid_moves)
        self.assertIn((4, 3), valid_moves)  # Adjacent empty position
    
    def test_get_valid_moves_inactive_game(self):
        """Test getting valid moves from inactive game."""
        self.game.status = GameStatus.FINISHED
        self.game.save()
        
        valid_moves = GameService.get_valid_moves(self.game)
        self.assertEqual(len(valid_moves), 0)
    
    def test_get_valid_moves_uninitialized_board(self):
        """Test getting valid moves when board not initialized."""
        self.game.board_state = {}
        self.game.save()
        
        valid_moves = GameService.get_valid_moves(self.game)
        self.assertEqual(len(valid_moves), 81)  # Should initialize and return all positions
    
    def test_resign_game_black_player(self):
        """Test black player resigning."""
        GameService.resign_game(self.game, self.black_player.id)
        
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(self.game.winner, self.white_player)
    
    def test_resign_game_white_player(self):
        """Test white player resigning."""
        GameService.resign_game(self.game, self.white_player.id)
        
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(self.game.winner, self.black_player)
    
    def test_resign_game_inactive_game(self):
        """Test resigning from inactive game."""
        self.game.status = GameStatus.FINISHED
        self.game.save()
        
        with self.assertRaises(ValueError) as context:
            GameService.resign_game(self.game, self.black_player.id)
        
        self.assertIn("Can only resign from active games", str(context.exception))
    
    def test_resign_game_invalid_player(self):
        """Test resigning with player not in game."""
        other_player = UserFactory()
        
        with self.assertRaises(ValueError) as context:
            GameService.resign_game(self.game, other_player.id)
        
        self.assertIn("Player not in this game", str(context.exception))


class GameServiceIntegrationTestCase(TransactionTestCase):
    """Integration tests for GameService methods working together."""
    
    def setUp(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = RuleSetFactory(board_size=15)
        self.game = GameFactory(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
    
    def test_complete_game_scenario(self):
        """Test a complete game scenario from start to finish."""
        # Start with empty game
        self.assertEqual(self.game.move_count, 0)
        
        # Make some moves
        move1 = GameService.make_move(self.game, self.black_player.id, 7, 7)
        self.assertEqual(move1.move_number, 1)
        
        move2 = GameService.make_move(self.game, self.white_player.id, 7, 8)
        self.assertEqual(move2.move_number, 2)
        
        move3 = GameService.make_move(self.game, self.black_player.id, 8, 7)
        self.assertEqual(move3.move_number, 3)
        
        # Check game state
        self.game.refresh_from_db()
        self.assertEqual(self.game.move_count, 3)
        self.assertEqual(self.game.current_player, Player.WHITE)
        self.assertEqual(self.game.status, GameStatus.ACTIVE)
        
        # Check valid moves decreased
        valid_moves = GameService.get_valid_moves(self.game)
        self.assertEqual(len(valid_moves), 15*15 - 3)  # Total minus placed stones
    
    def test_winning_game_scenario(self):
        """Test a game that ends in a win."""
        # Set up near-winning position for black
        moves = [
            (7, 7), (8, 8),   # Black, White
            (7, 8), (8, 9),   # Black, White  
            (7, 9), (8, 10),  # Black, White
            (7, 10),          # Black - 4 in a row horizontally
        ]
        
        for i, (row, col) in enumerate(moves):
            player_id = self.black_player.id if i % 2 == 0 else self.white_player.id
            move = GameService.make_move(self.game, player_id, row, col)
            
            if i == len(moves) - 1:  # Last move should not be winning yet
                self.assertFalse(move.is_winning_move)
        
        # Make the winning move
        winning_move = GameService.make_move(self.game, self.white_player.id, 8, 11)
        # Wait, this should be black's move to win...
        
        # Reset and try again with correct scenario
        self.setUp()  # Reset game
        
        # Black makes 4 in a row, white plays elsewhere
        GameService.make_move(self.game, self.black_player.id, 7, 7)
        GameService.make_move(self.game, self.white_player.id, 8, 8)
        GameService.make_move(self.game, self.black_player.id, 7, 8)
        GameService.make_move(self.game, self.white_player.id, 8, 9)
        GameService.make_move(self.game, self.black_player.id, 7, 9)
        GameService.make_move(self.game, self.white_player.id, 8, 10)
        GameService.make_move(self.game, self.black_player.id, 7, 10)
        GameService.make_move(self.game, self.white_player.id, 8, 11)
        
        # Black makes winning move (5 in a row)
        winning_move = GameService.make_move(self.game, self.black_player.id, 7, 11)
        
        self.assertTrue(winning_move.is_winning_move)
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(self.game.winner, self.black_player)
        
        # No more valid moves after game ends
        valid_moves = GameService.get_valid_moves(self.game)
        self.assertEqual(len(valid_moves), 0)