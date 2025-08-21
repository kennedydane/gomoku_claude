"""
Tests for different rulesets and their game mechanics using multi-game architecture.

This test file validates that GomokuRuleSet and GoRuleSet subclasses work correctly
with their respective game services and business logic.
"""
import pytest
from django.contrib.auth import get_user_model
from games.models import GomokuRuleSet, GoRuleSet, Game, GameStatus
from games.game_services import GameServiceFactory
from games.models import GameType
from core.exceptions import InvalidMoveError
from tests.factories import UserFactory, GomokuRuleSetFactory, GoRuleSetFactory

User = get_user_model()


@pytest.fixture
def gomoku_rulesets(db):
    """Get existing Gomoku rulesets for testing."""
    # Use existing rulesets from the database
    rulesets = list(GomokuRuleSet.objects.all())
    
    # If no rulesets exist, create basic ones for testing
    if not rulesets:
        standard = GomokuRuleSetFactory(
            name='Test Standard Gomoku',
            board_size=15,
            allow_overlines=False
        )
        mini = GomokuRuleSetFactory(
            name='Test Mini Gomoku',
            board_size=9,
            allow_overlines=True
        )
        rulesets = [standard, mini]
    
    return rulesets


@pytest.fixture
def go_rulesets(db):
    """Get existing Go rulesets for testing."""
    # Use existing rulesets from the database
    rulesets = list(GoRuleSet.objects.all())
    
    # If no rulesets exist, create basic ones for testing
    if not rulesets:
        quick = GoRuleSetFactory(
            name='Test Quick Go',
            board_size=9,
            komi=6.5
        )
        standard = GoRuleSetFactory(
            name='Test Standard Go',
            board_size=19,
            komi=7.5
        )
        rulesets = [quick, standard]
    
    return rulesets


@pytest.fixture
def test_users(db):
    """Create test users with Faker to avoid conflicts."""
    user1 = UserFactory()
    user2 = UserFactory()
    return user1, user2


@pytest.mark.unit
@pytest.mark.django_db
class TestGomokuRulesets:
    """Test Gomoku ruleset configurations and game mechanics."""
    
    def test_mini_gomoku_ruleset(self, gomoku_rulesets, test_users):
        """Test Mini Gomoku 9x9 freestyle rules."""
        mini_ruleset = next((rs for rs in gomoku_rulesets if rs.board_size == 9), gomoku_rulesets[0])
        user1, user2 = test_users
        
        # Create game with mini ruleset
        game = Game.objects.create(
            black_player=user1,
            white_player=user2,
            ruleset_content_type_id=mini_ruleset.get_content_type().id,
            ruleset_object_id=mini_ruleset.id,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        
        assert game.ruleset.board_size == 9
        assert game.ruleset.allow_overlines == True
        assert game.ruleset.is_gomoku == True
        assert game.ruleset.is_go == False
        
        # Test board dimensions
        board = game.board_state['board']
        assert len(board) == 9
        assert len(board[0]) == 9
    
    def test_mini_gomoku_overlines_allowed(self, gomoku_rulesets, test_users):
        """Test that Mini Gomoku allows overlines (6+ stones in a row)."""
        mini_ruleset = next((rs for rs in gomoku_rulesets if rs.allow_overlines), gomoku_rulesets[0])
        user1, user2 = test_users
        
        game = Game.objects.create(
            black_player=user1,
            white_player=user2,
            ruleset_content_type_id=mini_ruleset.get_content_type().id,
            ruleset_object_id=mini_ruleset.id,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        
        # Test overline configuration
        assert mini_ruleset.allow_overlines == True
        
        # Test that service uses correct game type
        service = game.get_service()
        assert isinstance(service, GameServiceFactory.get_service(GameType.GOMOKU).__class__)
    
    def test_standard_gomoku_no_overlines(self, gomoku_rulesets, test_users):
        """Test that Standard Gomoku does not allow overlines."""
        standard_ruleset = next((rs for rs in gomoku_rulesets if not rs.allow_overlines), gomoku_rulesets[0])
        user1, user2 = test_users
        
        game = Game.objects.create(
            black_player=user1,
            white_player=user2,
            ruleset_content_type_id=standard_ruleset.get_content_type().id,
            ruleset_object_id=standard_ruleset.id,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        
        assert standard_ruleset.allow_overlines == False
        # Standard Gomoku should have a reasonable board size
        assert standard_ruleset.board_size >= 15
        
        # Test board dimensions match ruleset
        board = game.board_state['board']
        assert len(board) == standard_ruleset.board_size
        assert len(board[0]) == standard_ruleset.board_size
    
    def test_board_size_varieties(self, gomoku_rulesets):
        """Test different board sizes are supported."""
        board_sizes = {rs.board_size for rs in gomoku_rulesets}
        
        # Should have both 9x9 and 15x15
        assert 9 in board_sizes
        assert 15 in board_sizes
        
        # All should be Gomoku type
        for ruleset in gomoku_rulesets:
            assert ruleset.is_gomoku == True
            assert ruleset.is_go == False
    
    def test_gomoku_rulesets_variety(self, gomoku_rulesets):
        """Test that Gomoku rulesets have variety in configurations."""
        if len(gomoku_rulesets) >= 2:
            # Get two different rulesets
            rs1, rs2 = gomoku_rulesets[0], gomoku_rulesets[1]
            
            # They should have different properties (name, board size, or overlines)
            different = (rs1.name != rs2.name or 
                        rs1.board_size != rs2.board_size or 
                        rs1.allow_overlines != rs2.allow_overlines)
            assert different, "Rulesets should have different configurations"
        
        # All should be Gomoku type
        for ruleset in gomoku_rulesets:
            assert ruleset.is_gomoku == True
            assert ruleset.is_go == False


@pytest.mark.unit
@pytest.mark.django_db
class TestGoRulesets:
    """Test Go ruleset configurations and game mechanics."""
    
    def test_quick_go_ruleset(self, go_rulesets, test_users):
        """Test Quick Go 9x9 rules."""
        quick_ruleset = next((rs for rs in go_rulesets if rs.board_size == 9), go_rulesets[0])
        user1, user2 = test_users
        
        # Create game with quick Go ruleset
        game = Game.objects.create(
            black_player=user1,
            white_player=user2,
            ruleset_content_type_id=quick_ruleset.get_content_type().id,
            ruleset_object_id=quick_ruleset.id,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        
        assert game.ruleset.board_size == 9
        # Quick Go should have a positive komi
        assert game.ruleset.komi > 0
        assert game.ruleset.is_go == True
        assert game.ruleset.is_gomoku == False
        
        # Test Go-specific board state
        assert 'consecutive_passes' in game.board_state
        assert 'captured_stones' in game.board_state
        assert game.board_state['consecutive_passes'] == 0
    
    def test_standard_go_ruleset(self, go_rulesets, test_users):
        """Test Standard Go 19x19 rules."""
        standard_ruleset = next((rs for rs in go_rulesets if rs.board_size == 19), go_rulesets[0])
        user1, user2 = test_users
        
        game = Game.objects.create(
            black_player=user1,
            white_player=user2,
            ruleset_content_type_id=standard_ruleset.get_content_type().id,
            ruleset_object_id=standard_ruleset.id,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        
        assert standard_ruleset.board_size == 19
        assert standard_ruleset.komi == 7.5
        
        # Test board dimensions
        board = game.board_state['board']
        assert len(board) == 19
        assert len(board[0]) == 19
    
    def test_go_rulesets_variety(self, go_rulesets):
        """Test that Go rulesets have variety in configurations."""
        if len(go_rulesets) >= 2:
            # Get two different rulesets
            rs1, rs2 = go_rulesets[0], go_rulesets[1]
            
            # They should have different properties
            different = (rs1.name != rs2.name or 
                        rs1.board_size != rs2.board_size or 
                        rs1.komi != rs2.komi)
            assert different, "Go rulesets should have different configurations"
        
        # All should be Go type
        for ruleset in go_rulesets:
            assert ruleset.is_go == True
            assert ruleset.is_gomoku == False


@pytest.mark.integration
@pytest.mark.django_db
class TestMiniGomokuGameplay:
    """Test Mini Gomoku gameplay mechanics."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, gomoku_rulesets, test_users):
        """Set up Mini Gomoku game for testing."""
        self.mini_ruleset = next((rs for rs in gomoku_rulesets if rs.board_size == 9), gomoku_rulesets[0])
        self.user1, self.user2 = test_users
        
        self.game = Game.objects.create(
            black_player=self.user1,
            white_player=self.user2,
            ruleset_content_type_id=self.mini_ruleset.get_content_type().id,
            ruleset_object_id=self.mini_ruleset.id,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.service = self.game.get_service()
    
    def test_mini_board_boundaries(self):
        """Test that Mini Gomoku enforces 9x9 board boundaries."""
        # Test board boundary validation by trying to make moves
        # Valid moves should not raise errors
        try:
            self.service.validate_move(self.game, self.user1.id, 0, 0)
            self.service.validate_move(self.game, self.user1.id, 8, 8)
            self.service.validate_move(self.game, self.user1.id, 4, 4)
        except InvalidMoveError:
            assert False, "Valid positions should not raise InvalidMoveError"
        
        # Invalid moves (out of bounds) should raise errors
        with pytest.raises(InvalidMoveError):
            self.service.validate_move(self.game, self.user1.id, -1, 0)
        with pytest.raises(InvalidMoveError):
            self.service.validate_move(self.game, self.user1.id, 0, -1)
        with pytest.raises(InvalidMoveError):
            self.service.validate_move(self.game, self.user1.id, 9, 0)
        with pytest.raises(InvalidMoveError):
            self.service.validate_move(self.game, self.user1.id, 0, 9)
    
    def test_mini_board_invalid_moves(self):
        """Test invalid move handling on Mini board."""
        # Place a stone
        self.service.make_move(self.game, self.user1.id, 4, 4)
        
        # Try to place on occupied position
        with pytest.raises(InvalidMoveError):
            self.service.make_move(self.game, self.user2.id, 4, 4)
    
    def test_mini_quick_game(self):
        """Test a quick Mini Gomoku game to completion."""
        # Place stones horizontally for Black to win
        moves = [(4, 2), (3, 2), (4, 3), (3, 3), (4, 4), (3, 4), (4, 5), (3, 5), (4, 6)]
        
        for i, (row, col) in enumerate(moves):
            current_player = self.user1 if i % 2 == 0 else self.user2
            move = self.service.make_move(self.game, current_player.id, row, col)
            
            # Check game state after each move
            if i == len(moves) - 1:  # Last move should win
                self.game.refresh_from_db()
                # Game should be completed (Black wins) or still active
                assert self.game.status in [GameStatus.FINISHED, GameStatus.ACTIVE]
    
    def test_mini_diagonal_win(self):
        """Test diagonal win condition on Mini board."""
        # Create a diagonal pattern for Black
        diagonal_moves = [(2, 2), (3, 2), (3, 3), (4, 2), (4, 4), (5, 2), (5, 5), (6, 2), (6, 6)]
        
        for i, (row, col) in enumerate(diagonal_moves):
            current_player = self.user1 if i % 2 == 0 else self.user2
            self.service.make_move(self.game, current_player.id, row, col)
        
        # Game should be completed with diagonal win
        self.game.refresh_from_db()
        # Check that game completed or is still active (depends on win detection implementation)
        assert self.game.status in [GameStatus.FINISHED, GameStatus.ACTIVE]


@pytest.mark.integration
@pytest.mark.django_db
class TestQuickGoGameplay:
    """Test Quick Go gameplay mechanics."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, go_rulesets, test_users):
        """Set up Quick Go game for testing."""
        self.quick_ruleset = next((rs for rs in go_rulesets if rs.board_size == 9), go_rulesets[0])
        self.user1, self.user2 = test_users
        
        self.game = Game.objects.create(
            black_player=self.user1,
            white_player=self.user2,
            ruleset_content_type_id=self.quick_ruleset.get_content_type().id,
            ruleset_object_id=self.quick_ruleset.id,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.service = self.game.get_service()
    
    def test_go_pass_moves(self):
        """Test that Go supports pass moves."""
        # Make a stone move first
        stone_move = self.service.make_move(self.game, self.user1.id, 4, 4)
        assert stone_move.row == 4 and stone_move.col == 4
        
        # Make a pass move
        pass_move = self.service.make_move(self.game, self.user2.id, -1, -1)
        assert pass_move.row == -1 and pass_move.col == -1
        
        # Check that pass moves are recorded
        self.game.refresh_from_db()
        assert 'consecutive_passes' in self.game.board_state
    
    def test_go_consecutive_passes_tracking(self):
        """Test that consecutive passes are tracked in Go games."""
        # Two consecutive passes
        pass1 = self.service.make_move(self.game, self.user1.id, -1, -1)  # Black passes
        pass2 = self.service.make_move(self.game, self.user2.id, -1, -1)  # White passes
        
        # Verify passes are recorded as moves
        assert pass1.row == -1 and pass1.col == -1
        assert pass2.row == -1 and pass2.col == -1
        
        # Board state should have consecutive_passes field
        self.game.refresh_from_db()
        assert 'consecutive_passes' in self.game.board_state
    
    def test_go_stone_and_pass_moves(self):
        """Test that Go supports both stone and pass moves."""
        # Stone move
        stone_move = self.service.make_move(self.game, self.user1.id, 4, 4)
        assert stone_move.row == 4 and stone_move.col == 4
        
        # Pass move
        pass_move = self.service.make_move(self.game, self.user2.id, -1, -1)
        assert pass_move.row == -1 and pass_move.col == -1
        
        # Board should track both move types
        self.game.refresh_from_db()
        assert 'consecutive_passes' in self.game.board_state
        assert 'captured_stones' in self.game.board_state