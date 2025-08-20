"""
Tests for game service layer.

Testing the BaseGameService, GomokuGameService, GoGameService, and GameServiceFactory
to ensure proper separation of game logic.
"""

from django.test import TestCase, TransactionTestCase

from .game_services import BaseGameService, GomokuGameService, GoGameService, GameServiceFactory
from .models import RuleSet, Game, GameMove, GameStatus, Player, GameType
from tests.factories import UserFactory
from core.exceptions import GameStateError, InvalidMoveError, PlayerError


class GameServiceFactoryTestCase(TestCase):
    """Test cases for GameServiceFactory."""
    
    def test_get_gomoku_service(self):
        """Test getting Gomoku service from factory."""
        service = GameServiceFactory.get_service(GameType.GOMOKU)
        self.assertIsInstance(service, GomokuGameService)
        self.assertIsInstance(service, BaseGameService)
    
    def test_get_go_service(self):
        """Test getting Go service from factory."""
        service = GameServiceFactory.get_service(GameType.GO)
        self.assertIsInstance(service, GoGameService)
        self.assertIsInstance(service, BaseGameService)
    
    def test_invalid_game_type(self):
        """Test error for invalid game type."""
        with self.assertRaises(ValueError) as context:
            GameServiceFactory.get_service('INVALID')
        self.assertIn("Unsupported game type", str(context.exception))
    
    def test_services_are_singletons(self):
        """Test that services are reused (singleton pattern)."""
        service1 = GameServiceFactory.get_service(GameType.GOMOKU)
        service2 = GameServiceFactory.get_service(GameType.GOMOKU)
        self.assertIs(service1, service2)


class GomokuGameServiceTestCase(TestCase):
    """Test cases for GomokuGameService."""
    
    def setUp(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = RuleSet.objects.create(
            name="Test Gomoku",
            game_type=GameType.GOMOKU,
            board_size=15,
            allow_overlines=False
        )
        self.game = Game.objects.create(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.service = GomokuGameService()
    
    def test_service_is_base_game_service(self):
        """Test that GomokuGameService inherits from BaseGameService."""
        self.assertIsInstance(self.service, BaseGameService)
    
    def test_validate_move_success(self):
        """Test successful move validation."""
        # This should not raise an exception
        try:
            self.service.validate_move(self.game, self.black_player.id, 7, 7)
        except Exception as e:
            self.fail(f"validate_move raised an exception: {e}")
    
    def test_validate_move_inactive_game(self):
        """Test move validation fails for inactive game."""
        self.game.status = GameStatus.WAITING
        self.game.save()
        
        with self.assertRaises((GameStateError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, 7, 7)
    
    def test_validate_move_wrong_turn(self):
        """Test move validation fails for wrong player turn."""
        # It's black's turn by default, try white player
        with self.assertRaises((PlayerError, ValueError)):
            self.service.validate_move(self.game, self.white_player.id, 7, 7)
    
    def test_validate_move_out_of_bounds(self):
        """Test move validation fails for out of bounds positions."""
        with self.assertRaises((InvalidMoveError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, -1, 7)
        
        with self.assertRaises((InvalidMoveError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, 15, 7)
    
    def test_validate_move_occupied_position(self):
        """Test move validation fails for occupied positions."""
        # Place a stone first
        self.game.board_state['board'][7][7] = Player.BLACK
        self.game.save()
        
        with self.assertRaises((InvalidMoveError, ValueError)):
            self.service.validate_move(self.game, self.black_player.id, 7, 7)


class GomokuGameServiceMoveTestCase(TransactionTestCase):
    """Test cases for GomokuGameService move operations."""
    
    def setUp(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = RuleSet.objects.create(
            name="Test Gomoku",
            game_type=GameType.GOMOKU,
            board_size=15,
            allow_overlines=False
        )
        self.game = Game.objects.create(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.service = GomokuGameService()
    
    def test_make_move_success(self):
        """Test successful move creation."""
        move = self.service.make_move(self.game, self.black_player.id, 7, 7)
        
        self.assertIsInstance(move, GameMove)
        self.assertEqual(move.row, 7)
        self.assertEqual(move.col, 7)
        self.assertEqual(move.player, self.black_player)
        self.assertEqual(move.player_color, Player.BLACK)
        self.assertEqual(move.move_number, 1)
        
        # Check game state updated
        self.game.refresh_from_db()
        self.assertEqual(self.game.move_count, 1)
        self.assertEqual(self.game.current_player, Player.WHITE)
        self.assertEqual(self.game.board_state['board'][7][7], Player.BLACK)
    
    def test_make_move_alternates_players(self):
        """Test moves alternate between players."""
        # Black move
        move1 = self.service.make_move(self.game, self.black_player.id, 7, 7)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_player, Player.WHITE)
        
        # White move
        move2 = self.service.make_move(self.game, self.white_player.id, 7, 8)
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_player, Player.BLACK)
    
    def test_make_winning_move(self):
        """Test making a winning move."""
        # Set up near-winning position (4 in a row horizontally)
        board = self.game.board_state['board']
        for col in range(4):
            board[7][col] = Player.BLACK
        self.game.save()
        
        # Make the winning move
        move = self.service.make_move(self.game, self.black_player.id, 7, 4)
        
        self.assertTrue(move.is_winning_move)
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(self.game.winner, self.black_player)
    
    def test_check_win_horizontal(self):
        """Test horizontal win detection."""
        board = self.game.board_state['board']
        # Place 5 stones horizontally
        for col in range(5):
            board[7][col] = Player.BLACK
        
        self.assertTrue(self.service.check_win(self.game, 7, 2))
    
    def test_check_win_vertical(self):
        """Test vertical win detection."""
        board = self.game.board_state['board']
        # Place 5 stones vertically
        for row in range(5):
            board[row][7] = Player.WHITE
        
        self.assertTrue(self.service.check_win(self.game, 2, 7))
    
    def test_check_win_diagonal(self):
        """Test diagonal win detection."""
        board = self.game.board_state['board']
        # Place 5 stones diagonally
        for i in range(5):
            board[i][i] = Player.BLACK
        
        self.assertTrue(self.service.check_win(self.game, 2, 2))
    
    def test_check_win_no_overlines(self):
        """Test that overlines don't win when not allowed."""
        board = self.game.board_state['board']
        # Place 6 stones horizontally
        for col in range(6):
            board[7][col] = Player.BLACK
        
        self.assertFalse(self.service.check_win(self.game, 7, 2))
    
    def test_check_win_with_overlines_allowed(self):
        """Test that overlines win when allowed."""
        self.game.ruleset.allow_overlines = True
        self.game.ruleset.save()
        
        board = self.game.board_state['board']
        # Place 6 stones horizontally
        for col in range(6):
            board[7][col] = Player.BLACK
        
        self.assertTrue(self.service.check_win(self.game, 7, 2))
    
    def test_get_valid_moves_empty_board(self):
        """Test getting valid moves from empty board."""
        valid_moves = self.service.get_valid_moves(self.game)
        
        # 15x15 board should have 225 valid moves
        self.assertEqual(len(valid_moves), 225)
        self.assertIn((0, 0), valid_moves)
        self.assertIn((7, 7), valid_moves)
        self.assertIn((14, 14), valid_moves)
    
    def test_get_valid_moves_with_stones(self):
        """Test getting valid moves with some stones on board."""
        # Place some stones
        board = self.game.board_state['board']
        board[7][7] = Player.BLACK
        board[7][8] = Player.WHITE
        self.game.save()
        
        valid_moves = self.service.get_valid_moves(self.game)
        
        # Should have 225 - 2 = 223 valid moves
        self.assertEqual(len(valid_moves), 223)
        self.assertNotIn((7, 7), valid_moves)
        self.assertNotIn((7, 8), valid_moves)
        self.assertIn((7, 6), valid_moves)
    
    def test_resign_game(self):
        """Test game resignation."""
        self.service.resign_game(self.game, self.black_player.id)
        
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(self.game.winner, self.white_player)
    
    def test_resign_invalid_player(self):
        """Test resignation by non-player fails."""
        other_player = UserFactory()
        
        with self.assertRaises((PlayerError, ValueError)):
            self.service.resign_game(self.game, other_player.id)


class GoGameServiceTestCase(TestCase):
    """Test cases for GoGameService (basic structure tests)."""
    
    def setUp(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = RuleSet.objects.create(
            name="Test Go",
            game_type=GameType.GO,
            board_size=19,
            komi=6.5,
            handicap_stones=0
        )
        self.game = Game.objects.create(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.service = GoGameService()
    
    def test_service_is_base_game_service(self):
        """Test that GoGameService inherits from BaseGameService."""
        self.assertIsInstance(self.service, BaseGameService)
    
    def test_go_board_has_capture_tracking(self):
        """Test that Go board includes capture tracking."""
        self.assertIn('captured_stones', self.game.board_state)
        self.assertEqual(self.game.board_state['captured_stones'], {'black': 0, 'white': 0})
    
    def test_go_board_has_ko_tracking(self):
        """Test that Go board includes ko position tracking."""
        self.assertIn('ko_position', self.game.board_state)
        self.assertIsNone(self.game.board_state['ko_position'])
    
    def test_go_board_has_pass_tracking(self):
        """Test that Go board includes consecutive pass tracking."""
        self.assertIn('consecutive_passes', self.game.board_state)
        self.assertEqual(self.game.board_state['consecutive_passes'], 0)
    
    def test_service_methods_exist(self):
        """Test that all required methods exist and work correctly."""
        # Test validate_move works for a valid position
        try:
            self.service.validate_move(self.game, self.black_player.id, 10, 10)
        except Exception as e:
            self.fail(f"validate_move raised an exception: {e}")
        
        # Go games don't end on single moves - check_win returns False until both players pass
        self.assertFalse(self.service.check_win(self.game, 10, 10))
        
        # Get valid moves should return all empty positions (19x19 = 361)
        valid_moves = self.service.get_valid_moves(self.game)
        self.assertEqual(len(valid_moves), 361)  # 19x19 Go board
        self.assertIn((10, 10), valid_moves)
        
        # Test resign_game works correctly
        self.service.resign_game(self.game, self.black_player.id)
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(self.game.winner, self.white_player)
    
    def test_make_move_basic(self):
        """Test making a basic Go move."""
        move = self.service.make_move(self.game, self.black_player.id, 10, 10)
        
        self.assertIsInstance(move, GameMove)
        self.assertEqual(move.row, 10)
        self.assertEqual(move.col, 10)
        self.assertEqual(move.player, self.black_player)
        self.assertEqual(move.player_color, Player.BLACK)
        
        # Check game state updated
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_player, Player.WHITE)
        self.assertEqual(self.game.board_state['board'][10][10], Player.BLACK)
        self.assertEqual(self.game.board_state['consecutive_passes'], 0)
    
    def test_ko_rule_validation(self):
        """Test that Ko rule prevents immediate recapture."""
        # Set up a Ko situation
        self.game.board_state['ko_position'] = [10, 10]
        self.game.save()
        
        with self.assertRaises(InvalidMoveError) as context:
            self.service.validate_move(self.game, self.black_player.id, 10, 10)
        
        self.assertIn("Ko rule violation", str(context.exception))
    
    def test_valid_moves_excludes_ko_position(self):
        """Test that valid moves excludes Ko position."""
        # Set Ko position
        self.game.board_state['ko_position'] = [10, 10]
        self.game.save()
        
        valid_moves = self.service.get_valid_moves(self.game)
        
        # Should have all positions except Ko position
        self.assertEqual(len(valid_moves), 360)  # 361 - 1 Ko position
        self.assertNotIn((10, 10), valid_moves)
    
    def test_pass_move(self):
        """Test making a pass move."""
        move = self.service.pass_turn(self.game, self.black_player.id)
        
        self.assertIsInstance(move, GameMove)
        self.assertEqual(move.row, -1)  # Pass move indicator
        self.assertEqual(move.col, -1)  # Pass move indicator
        self.assertEqual(move.player, self.black_player)
        self.assertEqual(move.player_color, Player.BLACK)
        
        # Check consecutive passes incremented
        self.game.refresh_from_db()
        self.assertEqual(self.game.board_state['consecutive_passes'], 1)
        self.assertEqual(self.game.current_player, Player.WHITE)
        self.assertEqual(self.game.status, GameStatus.ACTIVE)  # Game still active after one pass
    
    def test_two_passes_end_game(self):
        """Test that two consecutive passes end the game."""
        # Black passes
        self.service.pass_turn(self.game, self.black_player.id)
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, GameStatus.ACTIVE)
        
        # White passes - this should end the game
        self.service.pass_turn(self.game, self.white_player.id)
        self.game.refresh_from_db()
        
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(self.game.board_state['consecutive_passes'], 2)
        # Winner is None for now (draw) since we haven't implemented territory scoring
        self.assertIsNone(self.game.winner)
    
    def test_move_resets_consecutive_passes(self):
        """Test that making a move resets consecutive pass count."""
        # Set up some consecutive passes
        self.game.board_state['consecutive_passes'] = 1
        self.game.save()
        
        # Make a move
        self.service.make_move(self.game, self.black_player.id, 10, 10)
        
        # Check consecutive passes reset
        self.game.refresh_from_db()
        self.assertEqual(self.game.board_state['consecutive_passes'], 0)