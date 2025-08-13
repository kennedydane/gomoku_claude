"""
Tests for different rulesets and their game mechanics.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from games.models import RuleSet, Game, GameStatus
from games.services import GameService
from core.exceptions import InvalidMoveError

User = get_user_model()


class RuleSetTests(TestCase):
    """Test different ruleset configurations."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test rulesets."""
        # Create all the rulesets for testing
        cls.rulesets = [
            RuleSet.objects.create(
                name='Standard Gomoku',
                board_size=15,
                allow_overlines=False,
                description='Classic Gomoku rules on a 15×15 board. First player to get exactly 5 stones in a row wins. Overlines (6+ stones) do not count as wins.'
            ),
            RuleSet.objects.create(
                name='Freestyle Gomoku',
                board_size=15,
                allow_overlines=True,
                description='Freestyle Gomoku on a 15×15 board. First player to get 5 or more stones in a row wins. Overlines count as wins.'
            ),
            RuleSet.objects.create(
                name='Renju',
                board_size=15,
                allow_overlines=False,
                forbidden_moves={
                    'black_forbidden_3x3': True,
                    'black_forbidden_4x4': True,
                    'black_forbidden_overlines': True,
                    'description': 'Black player cannot create double-three, double-four, or overlines'
                },
                description='Traditional Renju rules on a 15×15 board. Black has forbidden moves: cannot create simultaneous double-three, double-four, or overlines. White has no restrictions.'
            ),
            RuleSet.objects.create(
                name='Pro Gomoku',
                board_size=19,
                allow_overlines=False,
                description='Professional tournament rules on a 19×19 Go board. Exactly 5 stones in a row wins. Used in international competitions.'
            ),
            RuleSet.objects.create(
                name='Caro',
                board_size=15,
                allow_overlines=True,
                forbidden_moves={
                    'requires_unblocked': True,
                    'description': 'Five-in-a-row must be unblocked on at least one end'
                },
                description='Vietnamese Caro rules on a 15×15 board. Must have an unblocked five-in-a-row to win. Popular in Southeast Asia.'
            ),
            RuleSet.objects.create(
                name='Mini Gomoku',
                board_size=8,
                allow_overlines=True,
                description='Quick-play freestyle Gomoku on a compact 8×8 board. Perfect for fast games and learning. First to get 5 or more stones in a row wins.'
            ),
            RuleSet.objects.create(
                name='Swap2 Tournament',
                board_size=15,
                allow_overlines=False,
                forbidden_moves={
                    'swap2_opening': True,
                    'description': 'Uses Swap2 opening protocol for tournament balance'
                },
                description='Modern tournament standard with Swap2 opening rule. Balances first-player advantage used in international competitions since 2009.'
            ),
            RuleSet.objects.create(
                name='Beginner Friendly',
                board_size=11,
                allow_overlines=True,
                description='Simplified rules on an 11×11 board perfect for new players. Shorter games with freestyle rules make learning easier and more enjoyable.'
            ),
            RuleSet.objects.create(
                name='Giant Gomoku',
                board_size=25,
                allow_overlines=False,
                description='Epic Gomoku on the maximum 25×25 board. Longer, more strategic games with complex positional play. Exactly 5 stones in a row wins.'
            ),
            RuleSet.objects.create(
                name='Speed Gomoku',
                board_size=9,
                allow_overlines=True,
                forbidden_moves={
                    'time_limit': '30_seconds_per_move',
                    'description': 'Fast-paced games with time pressure'
                },
                description='Lightning-fast Gomoku on a minimal 9×9 board. Designed for quick games with time pressure. Perfect for tournaments and rapid-fire matches.'
            ),
        ]
    
    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(username='player1', password='test')
        self.user2 = User.objects.create_user(username='player2', password='test')
    
    def test_mini_gomoku_ruleset(self):
        """Test Mini Gomoku 8x8 freestyle rules."""
        mini_ruleset = RuleSet.objects.get(name='Mini Gomoku')
        
        # Verify ruleset properties
        self.assertEqual(mini_ruleset.board_size, 8)
        self.assertTrue(mini_ruleset.allow_overlines)
        self.assertIn('8×8', mini_ruleset.description)
        
        # Create a game with Mini Gomoku rules
        game = Game.objects.create(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=mini_ruleset,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        
        # Verify board is 8x8
        self.assertEqual(len(game.board_state['board']), 8)
        self.assertEqual(len(game.board_state['board'][0]), 8)
        
        # Test moves on mini board
        # Make alternating moves to get 5 in a row for black player
        for i in range(5):
            # Black player moves
            move = GameService.make_move(game, self.user1.id, 0, i)
            self.assertIsNotNone(move)
            game.refresh_from_db()
            
            if game.status == GameStatus.FINISHED:
                break
                
            # White player moves (if game not finished)
            if i < 4:  # Don't need white's last move if black wins
                move = GameService.make_move(game, self.user2.id, 1, i)
                self.assertIsNotNone(move)
                game.refresh_from_db()
        
        # Game should be finished (5 in a row)
        self.assertEqual(game.status, GameStatus.FINISHED)
        self.assertEqual(game.winner, self.user1)
    
    def test_mini_gomoku_overlines_allowed(self):
        """Test that overlines are allowed in Mini Gomoku."""
        mini_ruleset = RuleSet.objects.get(name='Mini Gomoku')
        
        game = Game.objects.create(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=mini_ruleset,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        
        # Fill a row with 6 stones (overline)
        for i in range(6):
            if i < 6:  # Black moves
                GameService.make_move(game, self.user1.id, 0, i)
                game.refresh_from_db()
                if game.status == GameStatus.FINISHED:
                    break
            if i < 5:  # White moves (to keep game going)
                GameService.make_move(game, self.user2.id, 1, i)
                game.refresh_from_db()
        
        # Should win with 5 stones (before getting to 6)
        self.assertEqual(game.status, GameStatus.FINISHED)
        self.assertEqual(game.winner, self.user1)
    
    def test_standard_gomoku_no_overlines(self):
        """Test Standard Gomoku doesn't allow overlines."""
        standard_ruleset = RuleSet.objects.get(name='Standard Gomoku')
        self.assertFalse(standard_ruleset.allow_overlines)
        self.assertEqual(standard_ruleset.board_size, 15)
    
    def test_renju_forbidden_moves(self):
        """Test Renju ruleset has forbidden moves configured."""
        renju_ruleset = RuleSet.objects.get(name='Renju')
        
        self.assertFalse(renju_ruleset.allow_overlines)
        self.assertEqual(renju_ruleset.board_size, 15)
        self.assertIn('black_forbidden_3x3', renju_ruleset.forbidden_moves)
        self.assertIn('black_forbidden_4x4', renju_ruleset.forbidden_moves)
    
    def test_board_size_varieties(self):
        """Test different board sizes work correctly."""
        # Test Speed Gomoku (9x9)
        speed_ruleset = RuleSet.objects.get(name='Speed Gomoku')
        self.assertEqual(speed_ruleset.board_size, 9)
        
        # Test Giant Gomoku (25x25)
        giant_ruleset = RuleSet.objects.get(name='Giant Gomoku')
        self.assertEqual(giant_ruleset.board_size, 25)
        
        # Test Pro Gomoku (19x19)
        pro_ruleset = RuleSet.objects.get(name='Pro Gomoku')
        self.assertEqual(pro_ruleset.board_size, 19)
    
    def test_all_rulesets_valid(self):
        """Test all loaded rulesets have valid configurations."""
        all_rulesets = RuleSet.objects.all()
        
        # Should have all 10 rulesets
        self.assertGreaterEqual(all_rulesets.count(), 10)
        
        for ruleset in all_rulesets:
            # All should have valid names and descriptions
            self.assertTrue(ruleset.name)
            self.assertTrue(ruleset.description)
            
            # Board sizes should be within valid range
            self.assertGreaterEqual(ruleset.board_size, 8)  # Mini is minimum
            self.assertLessEqual(ruleset.board_size, 25)   # Giant is maximum
            
            # Should be either True or False, not None
            self.assertIn(ruleset.allow_overlines, [True, False])
    
    def test_mini_vs_speed_gomoku_differences(self):
        """Test differences between Mini and Speed Gomoku."""
        mini = RuleSet.objects.get(name='Mini Gomoku')
        speed = RuleSet.objects.get(name='Speed Gomoku')
        
        # Mini is 8x8, Speed is 9x9
        self.assertEqual(mini.board_size, 8)
        self.assertEqual(speed.board_size, 9)
        
        # Both allow overlines
        self.assertTrue(mini.allow_overlines)
        self.assertTrue(speed.allow_overlines)
        
        # Different descriptions
        self.assertIn('compact', mini.description.lower())
        self.assertIn('lightning', speed.description.lower())
    
    def test_freestyle_vs_standard_differences(self):
        """Test differences between Freestyle and Standard Gomoku."""
        freestyle = RuleSet.objects.get(name='Freestyle Gomoku')
        standard = RuleSet.objects.get(name='Standard Gomoku')
        
        # Same board size
        self.assertEqual(freestyle.board_size, 15)
        self.assertEqual(standard.board_size, 15)
        
        # Different overline rules
        self.assertTrue(freestyle.allow_overlines)
        self.assertFalse(standard.allow_overlines)


class MiniGomokuGameplayTests(TestCase):
    """Specific gameplay tests for Mini Gomoku."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up Mini Gomoku ruleset."""
        cls.mini_ruleset = RuleSet.objects.create(
            name='Mini Gomoku',
            board_size=8,
            allow_overlines=True,
            description='Quick-play freestyle Gomoku on a compact 8×8 board. Perfect for fast games and learning. First to get 5 or more stones in a row wins.'
        )
    
    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(username='black', password='test')
        self.user2 = User.objects.create_user(username='white', password='test')
        
        self.game = Game.objects.create(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.mini_ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
    
    def test_mini_board_boundaries(self):
        """Test moves at board boundaries work correctly."""
        # Valid moves at corners and edges
        valid_positions = [
            (0, 0),   # Top-left corner
            (0, 7),   # Top-right corner
            (7, 0),   # Bottom-left corner
            (7, 7),   # Bottom-right corner
            (3, 3),   # Center
        ]
        
        for i, (row, col) in enumerate(valid_positions):
            player_id = self.user1.id if i % 2 == 0 else self.user2.id
            move = GameService.make_move(self.game, player_id, row, col)
            self.assertIsNotNone(move)
            self.game.refresh_from_db()
    
    def test_mini_board_invalid_moves(self):
        """Test invalid moves on mini board are rejected."""
        invalid_positions = [
            (-1, 0),   # Row too small
            (0, -1),   # Col too small
            (8, 0),    # Row too large (8x8 board, max index is 7)
            (0, 8),    # Col too large
            (10, 10),  # Way out of bounds
        ]
        
        for row, col in invalid_positions:
            with self.assertRaises(InvalidMoveError):
                GameService.make_move(self.game, self.user1.id, row, col)
    
    def test_mini_quick_game(self):
        """Test a complete quick game on mini board."""
        # Simulate a quick 5-move win
        moves = [
            (self.user1.id, 2, 2),  # Black
            (self.user2.id, 3, 2),  # White
            (self.user1.id, 2, 3),  # Black
            (self.user2.id, 3, 3),  # White
            (self.user1.id, 2, 4),  # Black
            (self.user2.id, 3, 4),  # White
            (self.user1.id, 2, 5),  # Black
            (self.user2.id, 3, 5),  # White
            (self.user1.id, 2, 6),  # Black - should win (5 in a row)
        ]
        
        for i, (player_id, row, col) in enumerate(moves):
            move = GameService.make_move(self.game, player_id, row, col)
            self.assertIsNotNone(move)
            self.game.refresh_from_db()
            
            # Check if game ended on the winning move
            if i == 8:  # Last move should win
                self.assertEqual(self.game.status, GameStatus.FINISHED)
                self.assertEqual(self.game.winner, self.user1)
                break
    
    def test_mini_diagonal_win(self):
        """Test diagonal win on mini board."""
        # Create a diagonal win for black
        moves = [
            (self.user1.id, 0, 0),  # Black
            (self.user2.id, 0, 1),  # White
            (self.user1.id, 1, 1),  # Black
            (self.user2.id, 0, 2),  # White
            (self.user1.id, 2, 2),  # Black
            (self.user2.id, 0, 3),  # White
            (self.user1.id, 3, 3),  # Black
            (self.user2.id, 0, 4),  # White
            (self.user1.id, 4, 4),  # Black - diagonal win
        ]
        
        for i, (player_id, row, col) in enumerate(moves):
            move = GameService.make_move(self.game, player_id, row, col)
            self.assertIsNotNone(move)
            self.game.refresh_from_db()
            
            if i == 8:  # Last move should win
                self.assertEqual(self.game.status, GameStatus.FINISHED)
                self.assertEqual(self.game.winner, self.user1)
                break