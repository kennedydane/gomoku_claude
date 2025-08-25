"""
Test Go suicide rule validation.

This module tests the specific suicide rule validation scenario reported:
White stones surrounded by black stones with one open liberty. When that
liberty is filled with a white stone, it should be detected as an illegal
suicide move and rejected with InvalidMoveError.
"""

import pytest
from tests.factories import UserFactory, GoRuleSetFactory, GameFactory
from games.models import GameStatus, Player
from games.game_services import GoGameService
from games.validators import GoMoveValidator
from core.exceptions import InvalidMoveError


@pytest.mark.django_db
class TestGoSuicideValidation:
    """Test Go suicide rule validation in the validator layer."""
    
    def test_suicide_move_rejected_by_validator(self):
        """
        Test that suicide moves are rejected at the validation layer.
        
        This reproduces the reported scenario:
        - White stones surrounded by black stones
        - One open liberty remaining
        - Attempting to fill that liberty with white stone should be rejected
        """
        # Create test game
        black_player = UserFactory()
        white_player = UserFactory() 
        ruleset = GoRuleSetFactory(name='Test Suicide Validation', board_size=9)
        game = GameFactory(
            black_player=black_player,
            white_player=white_player,
            ruleset=ruleset,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        # Set current player to white for the suicide move test
        game.current_player = Player.WHITE
        
        # Set up the board state: white stones surrounded by black
        board = game.board_state['board']
        
        # Create white group that will be in atari (one liberty)
        board[4][4] = Player.WHITE  # Center white stone
        board[4][5] = Player.WHITE  # Adjacent white stone
        
        # Surround with black stones, leaving only one liberty at (3,4)
        board[2][4] = Player.BLACK  # Block the liberty at (2,4) too!
        board[3][3] = Player.BLACK
        # (3,4) is left empty - this will be the liberty we try to fill
        board[3][5] = Player.BLACK
        board[3][6] = Player.BLACK
        board[4][3] = Player.BLACK
        board[4][6] = Player.BLACK
        board[5][3] = Player.BLACK
        board[5][4] = Player.BLACK
        board[5][5] = Player.BLACK
        board[5][6] = Player.BLACK
        
        # Save the board state
        game.save()
        
        # Create validator
        validator = GoMoveValidator()
        
        # Attempt to play white stone at the last liberty (3,4)
        # This should be rejected as a suicide move
        with pytest.raises(InvalidMoveError, match="suicide"):
            validator.validate_move(game, white_player.id, 3, 4)
    
    def test_suicide_move_allowed_when_captures_opponent(self):
        """
        Test that suicide moves are allowed when they capture opponent stones.
        
        This tests the exception to the suicide rule: if placing a stone
        captures opponent stones, the move should be allowed even if it
        would otherwise be suicide.
        """
        # Create test game
        black_player = UserFactory()
        white_player = UserFactory()
        ruleset = GoRuleSetFactory(name='Test Suicide with Capture', board_size=9)
        game = GameFactory(
            black_player=black_player,
            white_player=white_player,
            ruleset=ruleset,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        # Set current player to white for the move test
        game.current_player = Player.WHITE
        
        # Set up a scenario where white can capture black stones
        # even though it would normally be suicide
        board = game.board_state['board']
        
        # Black stones in atari
        board[4][4] = Player.BLACK
        board[4][5] = Player.BLACK
        
        # White stones surrounding most of black group
        board[3][4] = Player.WHITE
        board[3][5] = Player.WHITE
        board[5][4] = Player.WHITE
        board[5][5] = Player.WHITE
        board[4][6] = Player.WHITE
        
        # The move at (4,3) would capture the black stones
        # and should be allowed even if it's technically suicide
        game.save()
        
        validator = GoMoveValidator()
        
        # This should NOT raise an exception because it captures opponent stones
        try:
            validator.validate_move(game, white_player.id, 4, 3)
        except InvalidMoveError:
            pytest.fail("Suicide move that captures opponent stones should be allowed")
    
    def test_validator_now_prevents_suicide_moves(self):
        """
        Test that demonstrates the fix: validator now prevents suicide moves.
        
        This test initially showed the bug (validator allowed suicide moves) 
        but should now pass showing that suicide moves are properly rejected.
        """
        # Create test game
        black_player = UserFactory()
        white_player = UserFactory()
        ruleset = GoRuleSetFactory(name='Test Current Bug', board_size=9)
        game = GameFactory(
            black_player=black_player,
            white_player=white_player,
            ruleset=ruleset,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        # Set current player to white for the suicide move test
        game.current_player = Player.WHITE
        
        # Set up the same suicide scenario as the main test
        board = game.board_state['board']
        
        # Create white group that will be in atari (one liberty) 
        board[4][4] = Player.WHITE  # Center white stone
        board[4][5] = Player.WHITE  # Adjacent white stone
        
        # Surround with black stones, leaving only one liberty at (3,4)
        board[2][4] = Player.BLACK  # Block all liberties
        board[3][3] = Player.BLACK
        # (3,4) is left empty - this will be the liberty we try to fill
        board[3][5] = Player.BLACK
        board[3][6] = Player.BLACK
        board[4][3] = Player.BLACK
        board[4][6] = Player.BLACK
        board[5][3] = Player.BLACK
        board[5][4] = Player.BLACK
        board[5][5] = Player.BLACK
        board[5][6] = Player.BLACK
        
        game.save()
        
        validator = GoMoveValidator()
        
        # The validator should now raise an exception (demonstrating the fix)
        with pytest.raises(InvalidMoveError, match="suicide"):
            validator.validate_move(game, white_player.id, 3, 4)