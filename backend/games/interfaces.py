"""
Game service interfaces and protocols.

This module defines the interfaces that all game services must implement,
providing type safety and clear contracts for different game types.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Protocol, runtime_checkable
from django.db import models

from .models import Game, GameMove


@runtime_checkable
class GameServiceInterface(Protocol):
    """
    Protocol defining the interface for game-specific services.
    
    This protocol ensures all game services implement required methods
    with consistent signatures, enabling type safety and polymorphism.
    """
    
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
        ...
    
    def make_move(self, game: Game, player_id: int, row: int, col: int) -> GameMove:
        """
        Make a move in the game.
        
        Args:
            game: The game instance
            player_id: ID of the player making the move
            row: Row coordinate (0-based) 
            col: Column coordinate (0-based)
            
        Returns:
            GameMove: The created move instance
            
        Raises:
            InvalidMoveError: If the move is invalid
        """
        ...
    
    def check_win(self, game: Game, last_row: int, last_col: int) -> bool:
        """
        Check if the last move resulted in a win.
        
        Args:
            game: The game instance
            last_row: Row of the last move
            last_col: Column of the last move
            
        Returns:
            bool: True if the move wins the game
        """
        ...
    
    def get_valid_moves(self, game: Game) -> List[Tuple[int, int]]:
        """
        Get all valid moves for the current player.
        
        Args:
            game: The game instance
            
        Returns:
            List of (row, col) tuples representing valid moves
        """
        ...
    
    def resign_game(self, game: Game, player_id: int) -> None:
        """
        Handle a player resigning from the game.
        
        Args:
            game: The game instance
            player_id: ID of the resigning player
        """
        ...
    
    def initialize_board(self, game: Game) -> dict:
        """
        Initialize the board state for a new game.
        
        Args:
            game: The game instance
            
        Returns:
            dict: Initial board state
        """
        ...


class BaseGameService(ABC):
    """
    Abstract base class for game-specific services.
    
    Provides common functionality shared across all game types
    while enforcing implementation of game-specific methods.
    """
    
    @abstractmethod
    def validate_move(self, game: Game, player_id: int, row: int, col: int) -> None:
        """Validate a move before it's made."""
        pass
    
    @abstractmethod 
    def make_move(self, game: Game, player_id: int, row: int, col: int) -> GameMove:
        """Make a move in the game."""
        pass
    
    @abstractmethod
    def check_win(self, game: Game, last_row: int, last_col: int) -> bool:
        """Check if the last move resulted in a win."""
        pass
    
    @abstractmethod
    def get_valid_moves(self, game: Game) -> List[Tuple[int, int]]:
        """Get all valid moves for the current player."""
        pass
    
    def resign_game(self, game: Game, player_id: int) -> None:
        """
        Handle a player resigning from the game.
        
        Default implementation suitable for most game types.
        """
        from .models import GameStatus, Player
        from users.models import User
        
        # Validate player
        try:
            user = User.objects.get(id=player_id)
        except User.DoesNotExist:
            from core.exceptions import PlayerError
            raise PlayerError(f"Player {player_id} does not exist")
        
        if user not in [game.black_player, game.white_player]:
            from core.exceptions import PlayerError
            raise PlayerError(f"Player {player_id} is not part of this game")
        
        # Set game as resigned
        game.status = GameStatus.FINISHED
        game.winner = game.white_player if user == game.black_player else game.black_player
        game.save()
    
    def initialize_board(self, game: Game) -> dict:
        """
        Initialize a standard empty board.
        
        Default implementation creates an empty board.
        Game-specific services can override for special initialization.
        """
        size = game.ruleset.board_size
        board = [[None for _ in range(size)] for _ in range(size)]
        
        return {
            'board': board,
            'last_move': None,
            'move_count': 0
        }


class GameServiceRegistry:
    """
    Registry for game service implementations.
    
    Allows dynamic registration of game services and provides
    a clean way to add new game types without modifying existing code.
    """
    
    _services: dict = {}
    
    @classmethod
    def register(cls, game_type: str, service_class: type) -> None:
        """
        Register a service implementation for a game type.
        
        Args:
            game_type: String identifier for the game type (e.g., 'GOMOKU', 'GO')
            service_class: Class implementing GameServiceInterface
        """
        if not isinstance(service_class(), GameServiceInterface):
            raise TypeError(f"Service {service_class} must implement GameServiceInterface")
        
        cls._services[game_type] = service_class
    
    @classmethod
    def get_service(cls, game_type: str) -> GameServiceInterface:
        """
        Get a service instance for the specified game type.
        
        Args:
            game_type: String identifier for the game type
            
        Returns:
            Service instance implementing GameServiceInterface
            
        Raises:
            ValueError: If no service is registered for the game type
        """
        if game_type not in cls._services:
            raise ValueError(f"No service registered for game type: {game_type}")
        
        return cls._services[game_type]()
    
    @classmethod
    def get_registered_types(cls) -> List[str]:
        """Get a list of all registered game types."""
        return list(cls._services.keys())