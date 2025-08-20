"""
Tests for multi-game model extensions.

Testing the GameType enum, RuleSet extensions, and Game model updates
to support both Gomoku and Go games.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError

from .models import RuleSet, Game, GameType, GameStatus, Player
from tests.factories import UserFactory


class GameTypeTestCase(TestCase):
    """Test cases for GameType enumeration."""

    def test_game_type_choices(self):
        """Test GameType enum has correct choices."""
        expected_choices = [
            ('GOMOKU', 'Gomoku'),
            ('GO', 'Go'),
        ]
        self.assertEqual(GameType.choices, expected_choices)

    def test_game_type_values(self):
        """Test GameType enum values."""
        self.assertEqual(GameType.GOMOKU, 'GOMOKU')
        self.assertEqual(GameType.GO, 'GO')


class RuleSetMultiGameTestCase(TestCase):
    """Test cases for RuleSet multi-game support."""

    def test_create_gomoku_ruleset(self):
        """Test creating a Gomoku ruleset."""
        ruleset = RuleSet.objects.create(
            name="Standard Gomoku",
            game_type=GameType.GOMOKU,
            board_size=15,
            allow_overlines=False,
            forbidden_moves={"double_three": True}
        )
        
        self.assertEqual(ruleset.name, "Standard Gomoku")
        self.assertEqual(ruleset.game_type, GameType.GOMOKU)
        self.assertEqual(ruleset.board_size, 15)
        self.assertFalse(ruleset.allow_overlines)
        self.assertEqual(ruleset.forbidden_moves, {"double_three": True})
        
        # Go-specific fields should have default values
        self.assertEqual(ruleset.komi, 6.5)
        self.assertEqual(ruleset.handicap_stones, 0)
        self.assertEqual(ruleset.scoring_method, 'TERRITORY')

    def test_create_go_ruleset(self):
        """Test creating a Go ruleset."""
        ruleset = RuleSet.objects.create(
            name="Standard Go",
            game_type=GameType.GO,
            board_size=19,
            komi=7.5,
            handicap_stones=2,
            scoring_method='AREA'
        )
        
        self.assertEqual(ruleset.name, "Standard Go")
        self.assertEqual(ruleset.game_type, GameType.GO)
        self.assertEqual(ruleset.board_size, 19)
        self.assertEqual(ruleset.komi, 7.5)
        self.assertEqual(ruleset.handicap_stones, 2)
        self.assertEqual(ruleset.scoring_method, 'AREA')
        
        # Gomoku-specific fields should have default values
        self.assertFalse(ruleset.allow_overlines)
        self.assertEqual(ruleset.forbidden_moves, {})

    def test_ruleset_game_type_required(self):
        """Test that game_type is required for RuleSet."""
        with self.assertRaises(ValidationError):
            ruleset = RuleSet(
                name="Invalid Ruleset",
                board_size=15
                # Missing game_type
            )
            ruleset.full_clean()

    def test_ruleset_komi_validation(self):
        """Test komi field validation."""
        # Valid komi values
        ruleset = RuleSet.objects.create(
            name="Go with komi",
            game_type=GameType.GO,
            board_size=19,
            komi=0.5
        )
        self.assertEqual(ruleset.komi, 0.5)

        # Komi can be negative (unusual but valid)
        ruleset.komi = -5.5
        ruleset.full_clean()  # Should not raise

    def test_ruleset_handicap_validation(self):
        """Test handicap_stones field validation."""
        ruleset = RuleSet.objects.create(
            name="Handicap Go",
            game_type=GameType.GO,
            board_size=19,
            handicap_stones=9
        )
        self.assertEqual(ruleset.handicap_stones, 9)

        # Negative handicap should be invalid
        with self.assertRaises(ValidationError):
            ruleset.handicap_stones = -1
            ruleset.full_clean()

    def test_scoring_method_choices(self):
        """Test scoring_method field choices."""
        # Valid scoring methods
        for method in ['TERRITORY', 'AREA']:
            ruleset = RuleSet.objects.create(
                name=f"Go {method}",
                game_type=GameType.GO,
                board_size=19,
                scoring_method=method
            )
            self.assertEqual(ruleset.scoring_method, method)

    def test_ruleset_str_representation(self):
        """Test RuleSet string representation includes game type."""
        gomoku_rules = RuleSet.objects.create(
            name="Standard Gomoku",
            game_type=GameType.GOMOKU,
            board_size=15
        )
        
        go_rules = RuleSet.objects.create(
            name="Standard Go",
            game_type=GameType.GO,
            board_size=19
        )
        
        self.assertEqual(str(gomoku_rules), "Standard Gomoku")
        self.assertEqual(str(go_rules), "Standard Go")

    def test_is_gomoku_property(self):
        """Test is_gomoku convenience property."""
        gomoku_rules = RuleSet.objects.create(
            name="Gomoku",
            game_type=GameType.GOMOKU,
            board_size=15
        )
        
        go_rules = RuleSet.objects.create(
            name="Go",
            game_type=GameType.GO,
            board_size=19
        )
        
        self.assertTrue(gomoku_rules.is_gomoku)
        self.assertFalse(go_rules.is_gomoku)

    def test_is_go_property(self):
        """Test is_go convenience property."""
        gomoku_rules = RuleSet.objects.create(
            name="Gomoku",
            game_type=GameType.GOMOKU,
            board_size=15
        )
        
        go_rules = RuleSet.objects.create(
            name="Go",
            game_type=GameType.GO,
            board_size=19
        )
        
        self.assertFalse(gomoku_rules.is_go)
        self.assertTrue(go_rules.is_go)


class GameMultiGameTestCase(TestCase):
    """Test cases for Game model multi-game support."""

    def setUp(self):
        """Set up test data."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        
        self.gomoku_ruleset = RuleSet.objects.create(
            name="Test Gomoku",
            game_type=GameType.GOMOKU,
            board_size=15
        )
        
        self.go_ruleset = RuleSet.objects.create(
            name="Test Go",
            game_type=GameType.GO,
            board_size=19
        )

    def test_create_gomoku_game(self):
        """Test creating a Gomoku game."""
        game = Game.objects.create(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.gomoku_ruleset
        )
        
        self.assertEqual(game.ruleset.game_type, GameType.GOMOKU)
        self.assertTrue(game.is_gomoku)
        self.assertFalse(game.is_go)

    def test_create_go_game(self):
        """Test creating a Go game."""
        game = Game.objects.create(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.go_ruleset
        )
        
        self.assertEqual(game.ruleset.game_type, GameType.GO)
        self.assertFalse(game.is_gomoku)
        self.assertTrue(game.is_go)

    def test_initialize_gomoku_board(self):
        """Test Gomoku board initialization."""
        game = Game.objects.create(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.gomoku_ruleset,
            status=GameStatus.ACTIVE
        )
        
        game.initialize_board()
        
        self.assertEqual(game.board_state['game_type'], GameType.GOMOKU)
        self.assertEqual(game.board_state['size'], 15)
        self.assertEqual(len(game.board_state['board']), 15)
        self.assertEqual(len(game.board_state['board'][0]), 15)
        
        # Gomoku doesn't need these fields
        self.assertNotIn('captured_stones', game.board_state)
        self.assertNotIn('ko_position', game.board_state)
        self.assertNotIn('consecutive_passes', game.board_state)

    def test_initialize_go_board(self):
        """Test Go board initialization."""
        game = Game.objects.create(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.go_ruleset,
            status=GameStatus.ACTIVE
        )
        
        game.initialize_board()
        
        self.assertEqual(game.board_state['game_type'], GameType.GO)
        self.assertEqual(game.board_state['size'], 19)
        self.assertEqual(len(game.board_state['board']), 19)
        self.assertEqual(len(game.board_state['board'][0]), 19)
        
        # Go-specific fields
        self.assertEqual(game.board_state['captured_stones'], {'black': 0, 'white': 0})
        self.assertIsNone(game.board_state['ko_position'])
        self.assertEqual(game.board_state['consecutive_passes'], 0)

    def test_get_service_method(self):
        """Test Game.get_service() returns appropriate service."""
        gomoku_game = Game.objects.create(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.gomoku_ruleset
        )
        
        go_game = Game.objects.create(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.go_ruleset
        )
        
        # Test that games return different service types
        gomoku_service = gomoku_game.get_service()
        go_service = go_game.get_service()
        
        self.assertNotEqual(type(gomoku_service), type(go_service))
        
        # Services should have the required interface
        for service in [gomoku_service, go_service]:
            self.assertTrue(hasattr(service, 'validate_move'))
            self.assertTrue(hasattr(service, 'make_move'))
            self.assertTrue(hasattr(service, 'check_win'))
            self.assertTrue(hasattr(service, 'get_valid_moves'))

    def test_game_string_includes_game_type(self):
        """Test Game string representation includes game type."""
        gomoku_game = Game.objects.create(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.gomoku_ruleset
        )
        
        go_game = Game.objects.create(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.go_ruleset
        )
        
        gomoku_str = str(gomoku_game)
        go_str = str(go_game)
        
        self.assertIn("Gomoku", gomoku_str)
        self.assertIn("Go", go_str)