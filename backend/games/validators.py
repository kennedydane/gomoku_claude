"""
Move validation classes for different game types.

This module contains game-specific move validators that can be used
independently or as part of game services. This separation makes it
easier to test validation logic and add new game types.
"""

from abc import ABC, abstractmethod
from typing import Tuple, List
from core.exceptions import InvalidMoveError, GameStateError, PlayerError
from .models import Game, GameStatus, Player


class BaseMoveValidator(ABC):
    """Abstract base class for move validators."""
    
    @abstractmethod
    def validate_move(self, game: Game, player_id: int, row: int, col: int) -> None:
        """
        Validate a move before it's made.
        
        Args:
            game: The game instance
            player_id: ID of the player making the move
            row: Row coordinate (0-based)
            col: Column coordinate (0-based)
            
        Raises:
            InvalidMoveError: If the move is invalid
            GameStateError: If the game state doesn't allow moves
            PlayerError: If the player cannot make this move
        """
        pass
    
    def validate_basic_conditions(self, game: Game, player_id: int, row: int, col: int) -> None:
        """
        Validate basic conditions common to all game types.
        
        This method checks:
        - Game is in active state
        - Player is valid and part of the game
        - It's the player's turn
        - Coordinates are within bounds
        """
        # Check if game is active
        if game.status != GameStatus.ACTIVE:
            raise GameStateError(
                f"Cannot make move in game with status: {game.status}",
                details={'current_status': game.status, 'game_id': str(game.id)}
            )
        
        # Validate player exists and is part of this game
        from users.models import User
        try:
            player = User.objects.get(id=player_id)
        except User.DoesNotExist:
            raise PlayerError(f"Player {player_id} does not exist")
        
        if player not in [game.black_player, game.white_player]:
            raise PlayerError(
                f"Player {player_id} is not part of this game",
                details={'game_id': str(game.id), 'player_id': player_id}
            )
        
        # Check if it's the player's turn
        current_player_user = game.get_current_player_user()
        if player != current_player_user:
            raise PlayerError(
                f"It's not player {player_id}'s turn",
                details={
                    'current_player_id': current_player_user.id,
                    'attempted_player_id': player_id
                }
            )
        
        # Validate coordinates are within bounds
        board_size = game.ruleset.board_size
        if not (0 <= row < board_size and 0 <= col < board_size):
            raise InvalidMoveError(
                f"Move coordinates ({row}, {col}) are out of bounds for {board_size}x{board_size} board",
                details={'row': row, 'col': col, 'board_size': board_size}
            )


class GomokuMoveValidator(BaseMoveValidator):
    """Move validator for Gomoku games."""
    
    def validate_move(self, game: Game, player_id: int, row: int, col: int) -> None:
        """Validate a Gomoku move."""
        # First check basic conditions
        self.validate_basic_conditions(game, player_id, row, col)
        
        # Check if position is already occupied
        board = game.board_state['board']
        if board[row][col] is not None:
            raise InvalidMoveError(
                f"Position ({row}, {col}) is already occupied",
                details={'row': row, 'col': col, 'occupied_by': board[row][col]}
            )


class GoMoveValidator(BaseMoveValidator):
    """Move validator for Go games."""
    
    def validate_move(self, game: Game, player_id: int, row: int, col: int) -> None:
        """Validate a Go move."""
        # Handle pass moves (indicated by -1, -1)
        if row == -1 and col == -1:
            # Pass moves are always valid in Go
            self.validate_basic_conditions(game, player_id, 0, 0)  # Just check game state and turn
            return
        
        # First check basic conditions for regular moves
        self.validate_basic_conditions(game, player_id, row, col)
        
        # Check if position is already occupied
        board = game.board_state['board']
        if board[row][col] is not None:
            raise InvalidMoveError(
                f"Position ({row}, {col}) is already occupied",
                details={'row': row, 'col': col, 'occupied_by': board[row][col]}
            )
        
        # Check suicide rule - prevent moves that would result in immediate capture
        # of the player's own stones unless they capture opponent stones first
        service = game.get_service()
        if hasattr(service, 'check_suicide_rule'):
            current_player = game.get_current_player_user()
            player_color = 'BLACK' if current_player == game.black_player else 'WHITE'
            
            if service.check_suicide_rule(board, row, col, player_color):
                raise InvalidMoveError(
                    f"Move at ({row}, {col}) would be suicide - it would capture your own stones without capturing opponent stones",
                    details={'row': row, 'col': col, 'player_color': player_color}
                )
        
        # Check Ko rule - prevent immediate recapture that would restore previous board position
        if hasattr(service, 'is_ko_violation'):
            if service.is_ko_violation(game, row, col, player_color):
                raise InvalidMoveError(
                    f"Ko rule violation: cannot immediately recapture at ({row}, {col}) to restore previous board position",
                    details={'row': row, 'col': col, 'player_color': player_color}
                )


class ChessMoveValidator(BaseMoveValidator):
    """
    Move validator for Chess games.
    
    This is a placeholder showing how a new game type could be added.
    Chess would require much more complex validation including:
    - Piece-specific movement rules
    - Check and checkmate detection
    - Castling rules
    - En passant rules
    - Pawn promotion rules
    """
    
    def validate_move(self, game: Game, player_id: int, row: int, col: int) -> None:
        """Validate a Chess move (placeholder implementation)."""
        # First check basic conditions
        self.validate_basic_conditions(game, player_id, row, col)
        
        # Chess validation would need additional parameters:
        # - Source position (from_row, from_col)
        # - Piece type and color
        # - Special move flags (castling, en passant, etc.)
        
        # For now, just validate that the destination is within bounds
        # Real chess validation would be much more complex
        
        raise NotImplementedError("Chess move validation not yet implemented")


class MoveValidatorFactory:
    """Factory for creating move validators."""
    
    _validators = {
        'GOMOKU': GomokuMoveValidator,
        'GO': GoMoveValidator,
        'CHESS': ChessMoveValidator  # Placeholder for future implementation
    }
    
    @classmethod
    def get_validator(cls, game_type: str) -> BaseMoveValidator:
        """Get the appropriate validator for a game type."""
        if game_type not in cls._validators:
            raise ValueError(f"No validator available for game type: {game_type}")
        
        return cls._validators[game_type]()
    
    @classmethod
    def register_validator(cls, game_type: str, validator_class: type) -> None:
        """Register a validator for a new game type."""
        if not issubclass(validator_class, BaseMoveValidator):
            raise TypeError(f"Validator must inherit from BaseMoveValidator")
        
        cls._validators[game_type] = validator_class