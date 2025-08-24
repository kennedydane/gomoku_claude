"""
Game state management classes.

This module contains game-specific state managers that handle board
initialization, state updates, and serialization. This separation
makes it easier to test state management and add new game types.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
import copy
from .models import Game, Player


class BaseStateManager(ABC):
    """Abstract base class for game state managers."""
    
    @abstractmethod
    def initialize_board(self, game: Game) -> Dict[str, Any]:
        """
        Initialize the board state for a new game.
        
        Args:
            game: The game instance
            
        Returns:
            Dict containing the initial board state
        """
        pass
    
    @abstractmethod
    def update_board_state(self, game: Game, row: int, col: int, player: Player) -> None:
        """
        Update the board state after a move.
        
        Args:
            game: The game instance
            row: Row coordinate of the move
            col: Column coordinate of the move
            player: Player making the move (BLACK or WHITE)
        """
        pass
    
    def get_board_copy(self, board: List[List[Optional[str]]]) -> List[List[Optional[str]]]:
        """Get a deep copy of the board state."""
        return copy.deepcopy(board)


class GomokuStateManager(BaseStateManager):
    """State manager for Gomoku games."""
    
    def initialize_board(self, game: Game) -> Dict[str, Any]:
        """Initialize the board state for a new Gomoku game."""
        size = game.ruleset.board_size
        board = [[None for _ in range(size)] for _ in range(size)]
        
        return {
            'board': board,
            'last_move': None,
            'move_count': 0,
            'game_over': False,
            'winner': None
        }
    
    def update_board_state(self, game: Game, row: int, col: int, player: Player) -> None:
        """Update the Gomoku board state after a move."""
        # Update the board position
        game.board_state['board'][row][col] = player.value
        
        # Update game state
        game.board_state['last_move'] = {'row': row, 'col': col, 'player': player.value}
        game.board_state['move_count'] = game.board_state.get('move_count', 0) + 1
        
        # Mark the game instance as needing to be saved
        game.save()


class GoStateManager(BaseStateManager):
    """State manager for Go games."""
    
    def initialize_board(self, game: Game) -> Dict[str, Any]:
        """Initialize the board state for a new Go game."""
        size = game.ruleset.board_size
        board = [[None for _ in range(size)] for _ in range(size)]
        
        return {
            'board': board,
            'last_move': None,
            'move_count': 0,
            'consecutive_passes': 0,
            'captured_stones': {'black': 0, 'white': 0},
            'board_history': [],  # For ko rule detection
            'game_over': False,
            'winner': None
        }
    
    def update_board_state(self, game: Game, row: int, col: int, player: Player) -> None:
        """Update the Go board state after a move."""
        # Handle pass moves
        if row == -1 and col == -1:
            game.board_state['consecutive_passes'] += 1
            game.board_state['last_move'] = {'pass': True, 'player': player.value}
            
            # Check if game ends (two consecutive passes)
            if game.board_state['consecutive_passes'] >= 2:
                game.board_state['game_over'] = True
        else:
            # Regular stone placement
            game.board_state['board'][row][col] = player.value
            game.board_state['consecutive_passes'] = 0  # Reset pass counter
            game.board_state['last_move'] = {'row': row, 'col': col, 'player': player.value}
            
            # Store board state for ko rule (simplified)
            board_copy = self.get_board_copy(game.board_state['board'])
            game.board_state['board_history'].append(board_copy)
            
            # Keep only recent history (last 10 moves should be sufficient for ko rule)
            if len(game.board_state['board_history']) > 10:
                game.board_state['board_history'].pop(0)
        
        # Update move count
        game.board_state['move_count'] = game.board_state.get('move_count', 0) + 1
        
        # Save the game instance
        game.save()
    
    def check_captures(self, game: Game, row: int, col: int, player: Player) -> int:
        """
        Check for captured stones after a move.
        
        Returns the number of stones captured.
        This is a simplified implementation.
        """
        # This would implement the capture detection logic
        # For now, returning 0 as a placeholder
        return 0


class ChessStateManager(BaseStateManager):
    """
    State manager for Chess games.
    
    This is a placeholder showing how a new game type could be added.
    """
    
    def initialize_board(self, game: Game) -> Dict[str, Any]:
        """Initialize the board state for a new Chess game."""
        # Chess would have a more complex initial board state
        # with pieces in their starting positions
        
        initial_board = [
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'],  # Black pieces
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],  # Black pawns
            [None] * 8,  # Empty row
            [None] * 8,  # Empty row
            [None] * 8,  # Empty row
            [None] * 8,  # Empty row
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],  # White pawns
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],  # White pieces
        ]
        
        return {
            'board': initial_board,
            'last_move': None,
            'move_count': 0,
            'castling_rights': {
                'white_kingside': True,
                'white_queenside': True,
                'black_kingside': True,
                'black_queenside': True
            },
            'en_passant_target': None,
            'fifty_move_counter': 0,
            'check_status': None,
            'game_over': False,
            'winner': None
        }
    
    def update_board_state(self, game: Game, row: int, col: int, player: Player) -> None:
        """Update the Chess board state after a move."""
        # Chess move updates would be much more complex
        # involving piece movement, capture, special moves, etc.
        raise NotImplementedError("Chess state management not yet implemented")


class StateManagerFactory:
    """Factory for creating state managers."""
    
    _managers = {
        'GOMOKU': GomokuStateManager,
        'GO': GoStateManager,
        'CHESS': ChessStateManager  # Placeholder for future implementation
    }
    
    @classmethod
    def get_manager(cls, game_type: str) -> BaseStateManager:
        """Get the appropriate state manager for a game type."""
        if game_type not in cls._managers:
            raise ValueError(f"No state manager available for game type: {game_type}")
        
        return cls._managers[game_type]()
    
    @classmethod
    def register_manager(cls, game_type: str, manager_class: type) -> None:
        """Register a state manager for a new game type."""
        if not issubclass(manager_class, BaseStateManager):
            raise TypeError("Manager must inherit from BaseStateManager")
        
        cls._managers[game_type] = manager_class