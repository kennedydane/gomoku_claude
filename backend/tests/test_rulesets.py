"""
Tests for different rulesets and their game mechanics.
"""
import pytest
from django.contrib.auth import get_user_model
from games.models import RuleSet, Game, GameStatus
from games.services import GameService
from core.exceptions import InvalidMoveError

User = get_user_model()


@pytest.fixture
def rulesets(db):
    """Get or create all the rulesets for testing."""
    rulesets_data = [
        {
            'name': 'Standard Gomoku',
            'board_size': 15,
            'allow_overlines': False,
            'description': 'Classic Gomoku rules on a 15×15 board. First player to get exactly 5 stones in a row wins. Overlines (6+ stones) do not count as wins.'
        },
        {
            'name': 'Freestyle Gomoku',
            'board_size': 15,
            'allow_overlines': True,
            'description': 'Freestyle Gomoku on a 15×15 board. First player to get 5 or more stones in a row wins. Overlines count as wins.'
        },
        {
            'name': 'Renju',
            'board_size': 15,
            'allow_overlines': False,
            'forbidden_moves': {
                'black_forbidden_3x3': True,
                'black_forbidden_4x4': True,
                'black_forbidden_overlines': True,
                'description': 'Black player cannot create double-three, double-four, or overlines'
            },
            'description': 'Traditional Renju rules on a 15×15 board. Black has forbidden moves: cannot create simultaneous double-three, double-four, or overlines. White has no restrictions.'
        },
        {
            'name': 'Pro Gomoku',
            'board_size': 19,
            'allow_overlines': False,
            'description': 'Professional tournament rules on a 19×19 Go board. Exactly 5 stones in a row wins. Used in international competitions.'
        },
        {
            'name': 'Caro',
            'board_size': 15,
            'allow_overlines': True,
            'forbidden_moves': {
                'requires_unblocked': True,
                'description': 'Five-in-a-row must be unblocked on at least one end'
            },
            'description': 'Vietnamese Caro rules on a 15×15 board. Must have an unblocked five-in-a-row to win. Popular in Southeast Asia.'
        },
        {
            'name': 'Mini Gomoku',
            'board_size': 8,
            'allow_overlines': True,
            'description': 'Quick-play freestyle Gomoku on a compact 8×8 board. Perfect for fast games and learning. First to get 5 or more stones in a row wins.'
        },
        {
            'name': 'Swap2 Tournament',
            'board_size': 15,
            'allow_overlines': False,
            'forbidden_moves': {
                'swap2_opening': True,
                'description': 'Uses Swap2 opening protocol for tournament balance'
            },
            'description': 'Modern tournament standard with Swap2 opening rule. Balances first-player advantage used in international competitions since 2009.'
        },
        {
            'name': 'Beginner Friendly',
            'board_size': 11,
            'allow_overlines': True,
            'description': 'Simplified rules on an 11×11 board perfect for new players. Shorter games with freestyle rules make learning easier and more enjoyable.'
        },
        {
            'name': 'Giant Gomoku',
            'board_size': 25,
            'allow_overlines': False,
            'description': 'Epic Gomoku on the maximum 25×25 board. Longer, more strategic games with complex positional play. Exactly 5 stones in a row wins.'
        },
        {
            'name': 'Speed Gomoku',
            'board_size': 9,
            'allow_overlines': True,
            'forbidden_moves': {
                'time_limit': '30_seconds_per_move',
                'description': 'Fast-paced games with time pressure'
            },
            'description': 'Lightning-fast Gomoku on a minimal 9×9 board. Designed for quick games with time pressure. Perfect for tournaments and rapid-fire matches.'
        },
    ]
    
    created_rulesets = []
    for data in rulesets_data:
        ruleset, created = RuleSet.objects.get_or_create(
            name=data['name'],
            defaults=data
        )
        created_rulesets.append(ruleset)
    
    return created_rulesets


@pytest.fixture
def test_users(db):
    """Get or create test users."""
    from tests.factories import UserFactory
    user1 = UserFactory(username='rulesets_player1')
    user2 = UserFactory(username='rulesets_player2') 
    return user1, user2


@pytest.mark.unit
@pytest.mark.django_db
class TestRuleSet:
    """Test different ruleset configurations."""
    
    def test_mini_gomoku_ruleset(self, rulesets, test_users):
        """Test Mini Gomoku 8x8 freestyle rules."""
        user1, user2 = test_users
        mini_ruleset = RuleSet.objects.get(name='Mini Gomoku')
        
        # Verify ruleset properties
        assert mini_ruleset.board_size == 8
        assert mini_ruleset.allow_overlines == True
        assert '8×8' in mini_ruleset.description
        
        # Create a game with Mini Gomoku rules
        game = Game.objects.create(
            black_player=user1,
            white_player=user2,
            ruleset=mini_ruleset,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        
        # Verify board is 8x8
        assert len(game.board_state['board']) == 8
        assert len(game.board_state['board'][0]) == 8
        
        # Test moves on mini board
        # Make alternating moves to get 5 in a row for black player
        for i in range(5):
            # Black player moves
            move = GameService.make_move(game, user1.id, 0, i)
            assert move is not None
            game.refresh_from_db()
            
            if game.status == GameStatus.FINISHED:
                break
                
            # White player moves (if game not finished)
            if i < 4:  # Don't need white's last move if black wins
                move = GameService.make_move(game, user2.id, 1, i)
                assert move is not None
                game.refresh_from_db()
        
        # Game should be finished (5 in a row)
        assert game.status == GameStatus.FINISHED
        assert game.winner == user1
    
    def test_mini_gomoku_overlines_allowed(self, rulesets, test_users):
        """Test that overlines are allowed in Mini Gomoku."""
        user1, user2 = test_users
        mini_ruleset = RuleSet.objects.get(name='Mini Gomoku')
        
        game = Game.objects.create(
            black_player=user1,
            white_player=user2,
            ruleset=mini_ruleset,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        
        # Fill a row with 6 stones (overline)
        for i in range(6):
            if i < 6:  # Black moves
                GameService.make_move(game, user1.id, 0, i)
                game.refresh_from_db()
                if game.status == GameStatus.FINISHED:
                    break
            if i < 5:  # White moves (to keep game going)
                GameService.make_move(game, user2.id, 1, i)
                game.refresh_from_db()
        
        # Should win with 5 stones (before getting to 6)
        assert game.status == GameStatus.FINISHED
        assert game.winner == user1
    
    def test_standard_gomoku_no_overlines(self, rulesets):
        """Test Standard Gomoku doesn't allow overlines."""
        standard_ruleset = RuleSet.objects.get(name='Standard Gomoku')
        assert standard_ruleset.allow_overlines == False
        assert standard_ruleset.board_size == 15
    
    def test_renju_forbidden_moves(self, rulesets):
        """Test Renju ruleset has forbidden moves configured."""
        renju_ruleset = RuleSet.objects.get(name='Renju')
        
        assert renju_ruleset.allow_overlines == False
        assert renju_ruleset.board_size == 15
        assert 'black_forbidden_3x3' in renju_ruleset.forbidden_moves
        assert 'black_forbidden_4x4' in renju_ruleset.forbidden_moves
    
    def test_board_size_varieties(self, rulesets):
        """Test different board sizes work correctly."""
        # Test Speed Gomoku (9x9)
        speed_ruleset = RuleSet.objects.get(name='Speed Gomoku')
        assert speed_ruleset.board_size == 9
        
        # Test Giant Gomoku (25x25)
        giant_ruleset = RuleSet.objects.get(name='Giant Gomoku')
        assert giant_ruleset.board_size == 25
        
        # Test Pro Gomoku (19x19)
        pro_ruleset = RuleSet.objects.get(name='Pro Gomoku')
        assert pro_ruleset.board_size == 19
    
    def test_all_rulesets_valid(self, rulesets):
        """Test all loaded rulesets have valid configurations."""
        all_rulesets = RuleSet.objects.all()
        
        # Should have all 10 rulesets
        assert all_rulesets.count() >= 10
        
        for ruleset in all_rulesets:
            # All should have valid names and descriptions
            assert ruleset.name
            assert ruleset.description
            
            # Board sizes should be within valid range
            assert ruleset.board_size >= 8  # Mini is minimum
            assert ruleset.board_size <= 25   # Giant is maximum
            
            # Should be either True or False, not None
            assert ruleset.allow_overlines in [True, False]
    
    def test_mini_vs_speed_gomoku_differences(self, rulesets):
        """Test differences between Mini and Speed Gomoku."""
        mini = RuleSet.objects.get(name='Mini Gomoku')
        speed = RuleSet.objects.get(name='Speed Gomoku')
        
        # Mini is 8x8, Speed is 9x9
        assert mini.board_size == 8
        assert speed.board_size == 9
        
        # Both allow overlines
        assert mini.allow_overlines == True
        assert speed.allow_overlines == True
        
        # Different descriptions
        assert 'compact' in mini.description.lower()
        assert 'lightning' in speed.description.lower()
    
    def test_freestyle_vs_standard_differences(self, rulesets):
        """Test differences between Freestyle and Standard Gomoku."""
        freestyle = RuleSet.objects.get(name='Freestyle Gomoku')
        standard = RuleSet.objects.get(name='Standard Gomoku')
        
        # Same board size
        assert freestyle.board_size == 15
        assert standard.board_size == 15
        
        # Different overline rules
        assert freestyle.allow_overlines == True
        assert standard.allow_overlines == False


@pytest.fixture
def mini_ruleset(db):
    """Get or create Mini Gomoku ruleset for gameplay tests."""
    ruleset, created = RuleSet.objects.get_or_create(
        name='Mini Gomoku',
        defaults={
            'board_size': 8,
            'allow_overlines': True,
            'description': 'Quick-play freestyle Gomoku on a compact 8×8 board. Perfect for fast games and learning. First to get 5 or more stones in a row wins.'
        }
    )
    return ruleset


@pytest.fixture
def mini_game_users(db):
    """Create test users for mini game tests."""
    from tests.factories import UserFactory
    user1 = UserFactory(username='mini_black_player')
    user2 = UserFactory(username='mini_white_player')
    return user1, user2


@pytest.fixture
def mini_game(mini_ruleset, mini_game_users):
    """Create a Mini Gomoku game for testing."""
    user1, user2 = mini_game_users
    game = Game.objects.create(
        black_player=user1,
        white_player=user2,
        ruleset=mini_ruleset,
        status=GameStatus.ACTIVE
    )
    game.initialize_board()
    return game


@pytest.mark.unit
@pytest.mark.django_db
class TestMiniGomokuGameplay:
    """Specific gameplay tests for Mini Gomoku."""
    
    def test_mini_board_boundaries(self, mini_game, mini_game_users):
        """Test moves at board boundaries work correctly."""
        user1, user2 = mini_game_users
        
        # Valid moves at corners and edges
        valid_positions = [
            (0, 0),   # Top-left corner
            (0, 7),   # Top-right corner
            (7, 0),   # Bottom-left corner
            (7, 7),   # Bottom-right corner
            (3, 3),   # Center
        ]
        
        for i, (row, col) in enumerate(valid_positions):
            player_id = user1.id if i % 2 == 0 else user2.id
            move = GameService.make_move(mini_game, player_id, row, col)
            assert move is not None
            mini_game.refresh_from_db()
    
    def test_mini_board_invalid_moves(self, mini_game, mini_game_users):
        """Test invalid moves on mini board are rejected."""
        user1, _ = mini_game_users
        
        invalid_positions = [
            (-1, 0),   # Row too small
            (0, -1),   # Col too small
            (8, 0),    # Row too large (8x8 board, max index is 7)
            (0, 8),    # Col too large
            (10, 10),  # Way out of bounds
        ]
        
        for row, col in invalid_positions:
            with pytest.raises(InvalidMoveError):
                GameService.make_move(mini_game, user1.id, row, col)
    
    def test_mini_quick_game(self, mini_game, mini_game_users):
        """Test a complete quick game on mini board."""
        user1, user2 = mini_game_users
        
        # Simulate a quick 5-move win
        moves = [
            (user1.id, 2, 2),  # Black
            (user2.id, 3, 2),  # White
            (user1.id, 2, 3),  # Black
            (user2.id, 3, 3),  # White
            (user1.id, 2, 4),  # Black
            (user2.id, 3, 4),  # White
            (user1.id, 2, 5),  # Black
            (user2.id, 3, 5),  # White
            (user1.id, 2, 6),  # Black - should win (5 in a row)
        ]
        
        for i, (player_id, row, col) in enumerate(moves):
            move = GameService.make_move(mini_game, player_id, row, col)
            assert move is not None
            mini_game.refresh_from_db()
            
            # Check if game ended on the winning move
            if i == 8:  # Last move should win
                assert mini_game.status == GameStatus.FINISHED
                assert mini_game.winner == user1
                break
    
    def test_mini_diagonal_win(self, mini_game, mini_game_users):
        """Test diagonal win on mini board."""
        user1, user2 = mini_game_users
        
        # Create a diagonal win for black
        moves = [
            (user1.id, 0, 0),  # Black
            (user2.id, 0, 1),  # White
            (user1.id, 1, 1),  # Black
            (user2.id, 0, 2),  # White
            (user1.id, 2, 2),  # Black
            (user2.id, 0, 3),  # White
            (user1.id, 3, 3),  # Black
            (user2.id, 0, 4),  # White
            (user1.id, 4, 4),  # Black - diagonal win
        ]
        
        for i, (player_id, row, col) in enumerate(moves):
            move = GameService.make_move(mini_game, player_id, row, col)
            assert move is not None
            mini_game.refresh_from_db()
            
            if i == 8:  # Last move should win
                assert mini_game.status == GameStatus.FINISHED
                assert mini_game.winner == user1
                break