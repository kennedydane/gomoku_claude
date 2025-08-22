"""
Tests for Go stone capture mechanics.

Comprehensive pytest-style tests for Go capture functionality following TDD methodology:
- Basic single stone captures
- Multi-stone group captures
- Corner and edge captures
- Ko rule enforcement
- Suicide rule prevention
- Complex capture scenarios
"""

import pytest
from django.core.exceptions import ValidationError

from games.game_services import GoGameService
from games.models import GoRuleSet, Game, GameMove, GameStatus, Player, GameType
from tests.factories import UserFactory, GoRuleSetFactory, GameFactory
from core.exceptions import GameStateError, InvalidMoveError, PlayerError


@pytest.mark.django_db
class TestGoBasicCapture:
    """Test basic Go stone capture mechanics."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data for basic capture tests."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GoRuleSetFactory(
            name="Test Go Capture",
            board_size=9,  # Smaller board for easier testing
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
    
    def test_single_stone_capture_horizontal(self):
        """Test capturing a single white stone surrounded horizontally and vertically."""
        # Set up: Place white stone at (4,4) surrounded by black stones
        # W is at (4,4), B stones at (3,4), (5,4), (4,3), (4,5)
        board = self.game.board_state['board']
        
        # Place white stone
        board[4][4] = Player.WHITE
        
        # Place 3 black stones around it, leaving one open
        board[3][4] = Player.BLACK  # North
        board[5][4] = Player.BLACK  # South  
        board[4][3] = Player.BLACK  # West
        # (4,5) is still open - this will be the capturing move
        
        self.game.save()
        
        # Black plays the capturing move at (4,5) - East
        move = self.service.make_move(self.game, self.black_player.id, 4, 5)
        
        # Verify the move was successful
        assert move is not None
        assert move.row == 4
        assert move.col == 5
        
        # Refresh game state
        self.game.refresh_from_db()
        board = self.game.board_state['board']
        
        # White stone at (4,4) should be captured (removed)
        assert board[4][4] is None
        
        # Black stone should be placed at (4,5)
        assert board[4][5] == Player.BLACK
        
        # Other black stones should remain
        assert board[3][4] == Player.BLACK
        assert board[5][4] == Player.BLACK
        assert board[4][3] == Player.BLACK
        
        # Captured stones count should be updated
        captured_stones = self.game.board_state['captured_stones']
        assert captured_stones['white'] == 1
        assert captured_stones['black'] == 0
    
    def test_single_stone_capture_corner(self):
        """Test capturing a single stone in corner position."""
        board = self.game.board_state['board']
        
        # Place white stone in corner (0,0)
        board[0][0] = Player.WHITE
        
        # Place black stone at (0,1), leaving (1,0) for capturing move
        board[0][1] = Player.BLACK
        
        self.game.save()
        
        # Black plays capturing move at (1,0)
        move = self.service.make_move(self.game, self.black_player.id, 1, 0)
        
        # Verify capture
        self.game.refresh_from_db()
        board = self.game.board_state['board']
        
        # White stone should be captured
        assert board[0][0] is None
        
        # Black stones should be present
        assert board[0][1] == Player.BLACK
        assert board[1][0] == Player.BLACK
        
        # Captured count updated
        captured_stones = self.game.board_state['captured_stones']
        assert captured_stones['white'] == 1
    
    def test_single_stone_capture_edge(self):
        """Test capturing a single stone along board edge."""
        board = self.game.board_state['board']
        
        # Place white stone on edge at (0,4)
        board[0][4] = Player.WHITE
        
        # Surround with black stones, leaving one for capturing move
        board[0][3] = Player.BLACK  # West
        board[0][5] = Player.BLACK  # East
        # (1,4) will be the capturing move - South
        
        self.game.save()
        
        # Black plays capturing move
        move = self.service.make_move(self.game, self.black_player.id, 1, 4)
        
        # Verify capture
        self.game.refresh_from_db()
        board = self.game.board_state['board']
        
        assert board[0][4] is None  # White captured
        assert board[1][4] == Player.BLACK  # Capturing stone placed
        
        captured_stones = self.game.board_state['captured_stones']
        assert captured_stones['white'] == 1
    
    def test_no_capture_with_liberties(self):
        """Test that stones with liberties are not captured."""
        board = self.game.board_state['board']
        
        # Place white stone with multiple liberties
        board[4][4] = Player.WHITE
        
        # Place only 2 black stones around it (not enough to capture)
        board[3][4] = Player.BLACK
        board[5][4] = Player.BLACK
        # (4,3) and (4,5) remain open as liberties
        
        self.game.save()
        
        # Black plays adjacent move at (4,3) - still leaves (4,5) as liberty
        move = self.service.make_move(self.game, self.black_player.id, 4, 3)
        
        # Verify no capture occurred
        self.game.refresh_from_db()
        board = self.game.board_state['board']
        
        # White stone should still be there
        assert board[4][4] == Player.WHITE
        
        # No captures recorded
        captured_stones = self.game.board_state['captured_stones']
        assert captured_stones['white'] == 0
        assert captured_stones['black'] == 0


@pytest.mark.django_db
class TestGoMultiStoneCapture:
    """Test capturing multiple stones as a group."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data for multi-stone capture tests."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GoRuleSetFactory(
            name="Test Multi Capture",
            board_size=9,
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
    
    def test_two_stone_horizontal_capture(self):
        """Test capturing a horizontal line of two white stones."""
        board = self.game.board_state['board']
        
        # Place two white stones horizontally
        board[4][4] = Player.WHITE
        board[4][5] = Player.WHITE
        
        # Surround the group with black stones
        board[3][4] = Player.BLACK  # North of first stone
        board[3][5] = Player.BLACK  # North of second stone
        board[5][4] = Player.BLACK  # South of first stone
        board[5][5] = Player.BLACK  # South of second stone
        board[4][3] = Player.BLACK  # West of group
        # (4,6) will be the capturing move - East of group
        
        self.game.save()
        
        # Black plays capturing move
        move = self.service.make_move(self.game, self.black_player.id, 4, 6)
        
        # Verify both stones captured
        self.game.refresh_from_db()
        board = self.game.board_state['board']
        
        assert board[4][4] is None  # First white stone captured
        assert board[4][5] is None  # Second white stone captured
        assert board[4][6] == Player.BLACK  # Capturing stone placed
        
        # Two stones captured
        captured_stones = self.game.board_state['captured_stones']
        assert captured_stones['white'] == 2
    
    def test_l_shaped_group_capture(self):
        """Test capturing an L-shaped group of stones."""
        board = self.game.board_state['board']
        
        # Create L-shaped white group
        board[4][4] = Player.WHITE  # Corner of L
        board[4][5] = Player.WHITE  # Horizontal part
        board[5][4] = Player.WHITE  # Vertical part
        
        # Surround the L-shaped group
        board[3][4] = Player.BLACK
        board[3][5] = Player.BLACK
        board[4][6] = Player.BLACK
        board[5][5] = Player.BLACK  # Added missing black stone
        board[5][6] = Player.BLACK
        board[6][4] = Player.BLACK
        board[6][5] = Player.BLACK
        board[5][3] = Player.BLACK
        # (4,3) will be the capturing move
        
        self.game.save()
        
        # Black plays capturing move
        move = self.service.make_move(self.game, self.black_player.id, 4, 3)
        
        # Verify entire L-group captured
        self.game.refresh_from_db()
        board = self.game.board_state['board']
        
        assert board[4][4] is None  # L corner captured
        assert board[4][5] is None  # Horizontal part captured  
        assert board[5][4] is None  # Vertical part captured
        
        # Three stones captured
        captured_stones = self.game.board_state['captured_stones']
        assert captured_stones['white'] == 3


@pytest.mark.django_db
class TestGoSuicideRule:
    """Test suicide rule prevention in Go."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data for suicide rule tests."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GoRuleSetFactory(
            name="Test Suicide Rule",
            board_size=9,
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
    
    def test_suicide_move_prevented(self):
        """Test that suicide moves are prevented."""
        board = self.game.board_state['board']
        
        # Create a white formation that would capture a black stone if placed at (4,4)
        board[3][4] = Player.WHITE
        board[5][4] = Player.WHITE
        board[4][3] = Player.WHITE
        board[4][5] = Player.WHITE
        # (4,4) is surrounded by white stones - placing black there would be suicide
        
        self.game.save()
        
        # Black attempts suicide move - should fail
        with pytest.raises(InvalidMoveError) as exc_info:
            self.service.make_move(self.game, self.black_player.id, 4, 4)
        
        assert "suicide" in str(exc_info.value).lower()
    
    def test_suicide_allowed_if_captures_opponent(self):
        """Test that suicide is allowed if it captures opponent stones."""
        board = self.game.board_state['board']
        
        # Set up situation where black move would normally be suicide
        # but it captures a white group, making it legal
        
        # White group with one liberty at (4,4)
        board[3][3] = Player.WHITE
        board[3][4] = Player.WHITE
        board[4][3] = Player.WHITE
        
        # Black stones surrounding white group
        board[2][3] = Player.BLACK
        board[2][4] = Player.BLACK
        board[3][2] = Player.BLACK
        board[4][2] = Player.BLACK
        board[5][3] = Player.BLACK
        board[3][5] = Player.BLACK  # Close off the other liberty
        board[4][4] = Player.BLACK  # This completes the surrounding
        
        # Remove the black stone at (4,4) temporarily to test the move
        board[4][4] = None
        
        self.game.save()
        
        # Black plays at (4,4) - this captures the white group
        move = self.service.make_move(self.game, self.black_player.id, 4, 4)
        
        # Should succeed because it captures white stones
        assert move is not None
        
        self.game.refresh_from_db()
        board = self.game.board_state['board']
        
        # White group should be captured
        assert board[3][3] is None
        assert board[3][4] is None
        assert board[4][3] is None
        
        # Black stone at (4,4) should remain (not suicide because it captured)
        assert board[4][4] == Player.BLACK
        
        # Capture count
        captured_stones = self.game.board_state['captured_stones']
        assert captured_stones['white'] == 3
        assert captured_stones['black'] == 0


@pytest.mark.django_db
class TestGoKoRule:
    """Test Ko rule implementation."""
    
    @pytest.fixture(autouse=True) 
    def setup_method(self):
        """Set up test data for Ko rule tests."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GoRuleSetFactory(
            name="Test Ko Rule",
            board_size=9,
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
    
    def test_ko_situation_detected(self):
        """Test that Ko situation is properly detected and stored."""
        # Simple Ko situation:
        # Pattern before white move:
        #   . . . . .
        #   . W B W .
        #   . B . B .
        #   . W B W .
        #   . . . . .
        # White plays at (2,2) capturing black at (2,1), creating Ko
        
        board = [[None for _ in range(9)] for _ in range(9)]
        
        # Set up Ko pattern - black stone that will be captured
        board[2][1] = Player.BLACK  # Black stone to be captured
        board[1][1] = Player.WHITE  # White stones surrounding it
        board[2][0] = Player.WHITE
        board[3][1] = Player.WHITE
        
        # Black stones around the area
        board[1][2] = Player.BLACK
        board[2][3] = Player.BLACK  
        board[3][2] = Player.BLACK
        
        # White stones to create the Ko pattern
        board[1][3] = Player.WHITE
        board[3][3] = Player.WHITE
        
        self.game.board_state['board'] = board
        self.game.current_player = 'WHITE'
        self.game.save()
        
        # White captures black stone at (2,1) by playing at (2,2)
        move = self.service.make_move(self.game, self.white_player.id, 2, 2)
        
        self.game.refresh_from_db()
        
        # Ko position should be recorded
        ko_position = self.game.board_state.get('ko_position')
        assert ko_position is not None
        assert ko_position == [2, 1], f"Expected Ko position [2, 1], got {ko_position}"
        
        # Verify capture happened
        captured_stones = self.game.board_state.get('captured_stones', {})
        assert captured_stones.get('black', 0) == 1, "Black stone should have been captured"
    
    def test_ko_recapture_prevented(self):
        """Test that immediate Ko recapture is prevented using recursive Ko detection."""
        # Create a proper Ko situation with mutual atari using sequential moves
        # This creates the same pattern as the working board history test:
        # W B W
        # B . B  <- Ko fight at center (1,1) ↔ (1,2)  
        # W B W
        
        # Set up the framework for mutual atari Ko with proper move sequence
        move1 = self.service.make_move(self.game, self.black_player.id, 1, 0)  # Black left
        move2 = self.service.make_move(self.game, self.white_player.id, 0, 0)  # White top-left
        move3 = self.service.make_move(self.game, self.black_player.id, 0, 1)  # Black top
        move4 = self.service.make_move(self.game, self.white_player.id, 0, 2)  # White top-right
        move5 = self.service.make_move(self.game, self.black_player.id, 2, 1)  # Black bottom
        move6 = self.service.make_move(self.game, self.white_player.id, 2, 2)  # White bottom-right
        move7 = self.service.make_move(self.game, self.black_player.id, 8, 8)  # Black neutral
        move8 = self.service.make_move(self.game, self.white_player.id, 2, 0)  # White bottom-left
        move9 = self.service.make_move(self.game, self.black_player.id, 7, 7)  # Black neutral
        move10 = self.service.make_move(self.game, self.white_player.id, 1, 3)  # White right (complete surrounding)
        move11 = self.service.make_move(self.game, self.black_player.id, 6, 6)  # Black neutral
        move12 = self.service.make_move(self.game, self.white_player.id, 1, 1)  # White Ko stone
        move13 = self.service.make_move(self.game, self.black_player.id, 1, 2)  # Black captures
        
        # Verify Black captured the White stone and Ko situation is created
        self.game.refresh_from_db()
        board = self.game.board_state['board']
        assert board[1][1] is None  # White Ko stone should be captured
        assert board[1][2] == Player.BLACK  # Black capturing stone
        
        # Verify Black Ko stone is in atari (proper Ko condition)
        black_group = self.service.find_group(board, 1, 2)
        black_liberties = self.service.get_group_liberties(board, black_group)
        assert len(black_liberties) == 1  # Should be in atari
        assert (1, 1) in black_liberties  # Liberty should be at Ko point
        
        # Now White should NOT be able to immediately recapture (Ko rule)
        with pytest.raises(InvalidMoveError, match="Ko rule violation"):
            self.service.make_move(self.game, self.white_player.id, 1, 1)


@pytest.mark.django_db  
class TestGoKoRuleBoardHistory:
    """Test Ko rule implementation using board history approach."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data for Ko rule board history tests."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GoRuleSetFactory(
            name="Test Ko Rule Board History",
            board_size=9,
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

    def test_ko_prevention_with_board_history(self):
        """Test that Ko is detected using board history comparison."""
        # Create a proper Ko situation with mutual atari
        # Pattern creates situation where both stones can capture each other:
        # W B W
        # B . B  <- Ko fight at center (1,1) ↔ (1,2)  
        # W B W
        
        # Set up the framework for mutual atari Ko
        # Move 1: Black left of Ko area
        move1 = self.service.make_move(self.game, self.black_player.id, 1, 0)
        
        # Move 2: White top-left
        move2 = self.service.make_move(self.game, self.white_player.id, 0, 0)
        
        # Move 3: Black top
        move3 = self.service.make_move(self.game, self.black_player.id, 0, 1)
        
        # Move 4: White top-right  
        move4 = self.service.make_move(self.game, self.white_player.id, 0, 2)
        
        # Move 5: Black bottom
        move5 = self.service.make_move(self.game, self.black_player.id, 2, 1)
        
        # Move 6: White bottom-right
        move6 = self.service.make_move(self.game, self.white_player.id, 2, 2)
        
        # Move 7: Black neutral move
        move7 = self.service.make_move(self.game, self.black_player.id, 8, 8)
        
        # Move 8: White bottom-left  
        move8 = self.service.make_move(self.game, self.white_player.id, 2, 0)
        
        # Move 9: Black neutral move
        move9 = self.service.make_move(self.game, self.black_player.id, 7, 7)
        
        # Move 10: White right (to complete surrounding)
        move10 = self.service.make_move(self.game, self.white_player.id, 1, 3)
        
        # Move 11: Black neutral move
        move11 = self.service.make_move(self.game, self.black_player.id, 6, 6)
        
        # Move 12: White plays Ko stone (will be in atari)
        move12 = self.service.make_move(self.game, self.white_player.id, 1, 1)
        
        # Move 13: Black captures White Ko stone, creating Ko situation
        move13 = self.service.make_move(self.game, self.black_player.id, 1, 2)
        
        # Verify the capture happened and Ko situation is created
        self.game.refresh_from_db()
        board = self.game.board_state['board']
        assert board[1][1] is None  # White Ko stone should be captured
        assert board[1][2] == Player.BLACK  # Black capturing stone
        
        # Verify Black Ko stone is in atari (proper Ko condition)
        black_group = self.service.find_group(board, 1, 2)
        black_liberties = self.service.get_group_liberties(board, black_group)
        assert len(black_liberties) == 1  # Should be in atari
        assert (1, 1) in black_liberties  # Liberty should be at Ko point
        
        # Now White should NOT be able to immediately recapture (Ko rule)
        with pytest.raises(InvalidMoveError, match="Ko rule violation"):
            self.service.make_move(self.game, self.white_player.id, 1, 1)

    def test_ko_becomes_available_after_other_moves(self):
        """Test that Ko position becomes available after both players play elsewhere."""
        # Set up the same Ko situation as previous test - MUST use complete setup
        move1 = self.service.make_move(self.game, self.black_player.id, 1, 0)
        move2 = self.service.make_move(self.game, self.white_player.id, 0, 0)
        move3 = self.service.make_move(self.game, self.black_player.id, 0, 1)
        move4 = self.service.make_move(self.game, self.white_player.id, 0, 2)
        move5 = self.service.make_move(self.game, self.black_player.id, 2, 1)
        move6 = self.service.make_move(self.game, self.white_player.id, 2, 2)
        move7 = self.service.make_move(self.game, self.black_player.id, 8, 8)
        move8 = self.service.make_move(self.game, self.white_player.id, 2, 0)
        move9 = self.service.make_move(self.game, self.black_player.id, 7, 7)
        move10 = self.service.make_move(self.game, self.white_player.id, 1, 3)  # Complete surrounding
        move11 = self.service.make_move(self.game, self.black_player.id, 6, 6)
        move12 = self.service.make_move(self.game, self.white_player.id, 1, 1)   # White Ko stone
        move13 = self.service.make_move(self.game, self.black_player.id, 1, 2)   # Black captures
        
        # Verify Ko is blocked immediately
        with pytest.raises(InvalidMoveError, match="Ko rule violation"):
            self.service.make_move(self.game, self.white_player.id, 1, 1)
        
        # Move 8: White plays elsewhere (not Ko recapture)
        move8 = self.service.make_move(self.game, self.white_player.id, 5, 5)
        
        # Move 9: Black plays elsewhere
        move9 = self.service.make_move(self.game, self.black_player.id, 4, 4)
        
        # Move 10: Now white should be able to play at the Ko position
        # (because it won't recreate the board position from 1 move ago)
        move10 = self.service.make_move(self.game, self.white_player.id, 1, 1)
        assert move10.row == 1
        assert move10.col == 1
        
        # Verify board history shows the Ko is now legal
        self.game.refresh_from_db()
        board = self.game.board_state['board']
        assert board[1][1] == Player.WHITE

    def test_board_reconstruction_functionality(self):
        """Test that board reconstruction from move history works properly."""
        # Make some moves and verify board reconstruction at each step
        move1 = self.service.make_move(self.game, self.black_player.id, 4, 4)
        
        self.game.refresh_from_db()
        
        # Test board reconstruction at move 0 (empty) and move 1
        empty_board = self.service.reconstruct_board_state_at_move(self.game, 0)
        assert empty_board is not None
        assert all(cell is None for row in empty_board for cell in row)
        
        move1_board = self.service.reconstruct_board_state_at_move(self.game, 1)
        assert move1_board is not None
        assert move1_board[4][4] == Player.BLACK
        
        # Make second move
        move2 = self.service.make_move(self.game, self.white_player.id, 4, 5)
        self.game.refresh_from_db()
        
        # Test reconstruction at move 2
        move2_board = self.service.reconstruct_board_state_at_move(self.game, 2)
        assert move2_board is not None
        assert move2_board[4][4] == Player.BLACK
        assert move2_board[4][5] == Player.WHITE
        
        # Verify boards at different moves are different
        assert not self.service.boards_equal(empty_board, move1_board)
        assert not self.service.boards_equal(move1_board, move2_board)

    def test_board_comparison_utility(self):
        """Test the boards_equal utility function."""
        service = self.service
        
        # Test identical boards
        board1 = [[None, None], [None, None]]
        board2 = [[None, None], [None, None]]
        assert service.boards_equal(board1, board2)
        
        # Test different boards
        board3 = [[Player.BLACK, None], [None, None]]
        board4 = [[None, None], [None, None]]
        assert not service.boards_equal(board3, board4)
        
        # Test different sizes
        board5 = [[None, None, None], [None, None, None]]
        board6 = [[None, None], [None, None]]
        assert not service.boards_equal(board5, board6)


@pytest.mark.django_db
class TestGoComplexCaptures:
    """Test complex capture scenarios."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data for complex capture tests."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GoRuleSetFactory(
            name="Test Complex Captures",
            board_size=9,
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
    
    def test_multiple_group_capture(self):
        """Test capturing multiple separate groups in one move."""
        board = self.game.board_state['board']
        
        # Create two separate white groups that share a liberty
        # Group 1: (3,3)
        board[3][3] = Player.WHITE
        board[2][3] = Player.BLACK
        board[3][2] = Player.BLACK
        board[4][3] = Player.BLACK
        
        # Group 2: (3,5) 
        board[3][5] = Player.WHITE
        board[2][5] = Player.BLACK
        board[3][6] = Player.BLACK
        board[4][5] = Player.BLACK
        
        # Both groups share liberty at (3,4)
        
        self.game.save()
        
        # Black plays at shared liberty (3,4) - captures both groups
        move = self.service.make_move(self.game, self.black_player.id, 3, 4)
        
        self.game.refresh_from_db()
        board = self.game.board_state['board']
        
        # Both white groups should be captured
        assert board[3][3] is None
        assert board[3][5] is None
        
        # Two white stones captured
        captured_stones = self.game.board_state['captured_stones']
        assert captured_stones['white'] == 2
    
    def test_chain_reaction_capture(self):
        """Test chain reaction where capturing one group leads to capturing another."""
        # This is a more advanced scenario - implementing as a placeholder
        pytest.skip("Chain reaction captures - advanced scenario for future implementation")


@pytest.mark.django_db
class TestGoStoneReOccupation:
    """Test cases for placing stones at previously captured positions."""
    
    def setup_method(self):
        """Set up test game for each test."""
        self.black_player = UserFactory()
        self.white_player = UserFactory()
        self.ruleset = GoRuleSetFactory(name='Test Go', board_size=9)
        self.game = GameFactory(
            black_player=self.black_player,
            white_player=self.white_player,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.service = GoGameService()
    
    def test_stone_reoccupation_after_capture(self):
        """Test that a stone can be placed at a position after the original stone is captured."""
        # First, place a black stone (it's black's turn first)
        black_move1 = self.service.make_move(self.game, self.black_player.id, 3, 3)
        self.game.refresh_from_db()
        
        # Now place a white stone at (4,4) via proper move (it's white's turn now)
        white_move1 = self.service.make_move(self.game, self.white_player.id, 4, 4)
        self.game.refresh_from_db()
        
        # Verify white stone is placed
        board = self.game.board_state['board']
        assert board[4][4] == Player.WHITE
        
        # Set up capture scenario by manually placing black stones
        board[3][4] = Player.BLACK
        board[5][4] = Player.BLACK
        board[4][3] = Player.BLACK
        self.game.save()
        
        # Black captures the white stone (it's black's turn)
        capture_move = self.service.make_move(self.game, self.black_player.id, 4, 5)
        self.game.refresh_from_db()
        
        # Verify white stone was captured
        board = self.game.board_state['board']
        assert board[4][4] is None  # Position should be empty after capture
        assert self.game.board_state['captured_stones']['white'] == 1
        
        # Clear some space for white to play at (4,4) without immediate capture
        board = self.game.board_state['board']
        board[3][4] = None  # Remove one of the surrounding black stones
        self.game.save()
        
        # White places a stone at the previously captured position (4,4) (it's white's turn)
        reoccupation_move = self.service.make_move(self.game, self.white_player.id, 4, 4)
        self.game.refresh_from_db()
        
        # Verify the position is now occupied by white
        board = self.game.board_state['board']
        assert board[4][4] == Player.WHITE
        
        # Verify this is recorded as a separate move
        assert reoccupation_move.row == 4
        assert reoccupation_move.col == 4
        assert reoccupation_move.player == self.white_player
        assert reoccupation_move.player_color == Player.WHITE
        
        # Check that we have two moves at the same position in move history
        moves_at_position = self.game.moves.filter(row=4, col=4)
        print(f"DEBUG: Moves at position (4,4): {list(moves_at_position.values('move_number', 'player_color', 'row', 'col'))}")
        assert moves_at_position.count() == 2  # Original white stone + re-occupation
        
        # Verify the moves are in correct sequence
        first_move_record = moves_at_position.order_by('move_number').first()
        second_move_record = moves_at_position.order_by('move_number').last()
        
        assert first_move_record.player_color == Player.WHITE
        assert second_move_record.player_color == Player.WHITE
        assert second_move_record.move_number > first_move_record.move_number
    
    def test_different_players_can_reoccupy_position(self):
        """Test that different players can occupy the same position after captures."""
        # Black places first stone (it's black's turn first)
        black_move1 = self.service.make_move(self.game, self.black_player.id, 3, 3)
        self.game.refresh_from_db()
        
        # White places stone at (4,4) 
        white_move1 = self.service.make_move(self.game, self.white_player.id, 4, 4)
        self.game.refresh_from_db()
        assert self.game.board_state['board'][4][4] == Player.WHITE
        
        # Set up capture scenario by manually placing black stones
        board = self.game.board_state['board']
        board[3][4] = Player.BLACK
        board[5][4] = Player.BLACK  
        board[4][3] = Player.BLACK
        self.game.save()
        
        # Black captures white stone (it's black's turn)
        black_capture = self.service.make_move(self.game, self.black_player.id, 4, 5)
        self.game.refresh_from_db()
        assert self.game.board_state['board'][4][4] is None  # White stone captured
        
        # White makes a different move (it's white's turn)
        white_move2 = self.service.make_move(self.game, self.white_player.id, 6, 6)
        self.game.refresh_from_db()
        
        # Black can now place a stone at (4,4) - same position, different player
        black_move2 = self.service.make_move(self.game, self.black_player.id, 4, 4)
        self.game.refresh_from_db()
        assert self.game.board_state['board'][4][4] == Player.BLACK
        
        # Verify we have moves from both players at the same position
        moves_at_position = self.game.moves.filter(row=4, col=4)
        assert moves_at_position.count() == 2
        
        white_moves = moves_at_position.filter(player_color=Player.WHITE)
        black_moves = moves_at_position.filter(player_color=Player.BLACK)
        
        assert white_moves.count() == 1
        assert black_moves.count() == 1