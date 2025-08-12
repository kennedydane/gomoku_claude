"""
Game state management for the Gomoku frontend.

This module manages the local game state, synchronizing with the backend API.
"""

from typing import Optional, List, Callable, Any
from enum import Enum
from dataclasses import dataclass

from loguru import logger

from ..client.api_client import GameInfo, MoveInfo, UserInfo, RuleSetInfo


class GameStatus(Enum):
    """Game status enumeration."""
    WAITING = "waiting"
    ACTIVE = "active"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class Player(Enum):
    """Player color enumeration."""
    BLACK = "black"
    WHITE = "white"


@dataclass
class GameStateData:
    """Data class for game state information."""
    game_info: Optional[GameInfo] = None
    moves: List[MoveInfo] = None
    current_player_user: Optional[UserInfo] = None
    is_local_player_turn: bool = False
    local_player_color: Optional[Player] = None
    
    def __post_init__(self):
        if self.moves is None:
            self.moves = []


class GameState:
    """Manages the local game state and synchronization with backend."""
    
    def __init__(self):
        """Initialize game state."""
        self._data = GameStateData()
        self._observers: List[Callable[[GameStateData], None]] = []
        
        logger.debug("Initialized game state manager")
    
    def add_observer(self, callback: Callable[[GameStateData], None]) -> None:
        """Add an observer for game state changes.
        
        Args:
            callback: Function to call when state changes
        """
        self._observers.append(callback)
        logger.debug("Added game state observer")
    
    def remove_observer(self, callback: Callable[[GameStateData], None]) -> None:
        """Remove a game state observer.
        
        Args:
            callback: Function to remove from observers
        """
        if callback in self._observers:
            self._observers.remove(callback)
            logger.debug("Removed game state observer")
    
    def _notify_observers(self) -> None:
        """Notify all observers of state changes."""
        for observer in self._observers:
            try:
                observer(self._data)
            except Exception as e:
                logger.error(f"Error in game state observer: {e}")
    
    @property
    def data(self) -> GameStateData:
        """Get current game state data."""
        return self._data
    
    @property
    def has_game(self) -> bool:
        """Check if there's an active game."""
        return self._data.game_info is not None
    
    @property
    def game_id(self) -> Optional[str]:
        """Get current game ID."""
        return self._data.game_info.id if self._data.game_info else None
    
    @property
    def board_size(self) -> int:
        """Get the board size."""
        if self._data.game_info and self._data.game_info.board_state:
            return self._data.game_info.board_state.size
        return 15  # Default size
    
    @property
    def board(self) -> List[List[Optional[str]]]:
        """Get the current board state."""
        if self._data.game_info and self._data.game_info.board_state:
            return self._data.game_info.board_state.board
        # Return empty board
        size = self.board_size
        return [[None for _ in range(size)] for _ in range(size)]
    
    @property
    def current_player(self) -> Optional[Player]:
        """Get the current player color."""
        if self._data.game_info:
            try:
                return Player(self._data.game_info.current_player)
            except ValueError:
                logger.warning(f"Invalid current player value: {self._data.game_info.current_player}")
        return None
    
    @property
    def game_status(self) -> Optional[GameStatus]:
        """Get the current game status."""
        if self._data.game_info:
            try:
                return GameStatus(self._data.game_info.status)
            except ValueError:
                logger.warning(f"Invalid game status value: {self._data.game_info.status}")
        return None
    
    @property
    def is_game_over(self) -> bool:
        """Check if the game is over."""
        return self._data.game_info.is_game_over if self._data.game_info else False
    
    @property
    def winner_name(self) -> Optional[str]:
        """Get the winner's display name."""
        if self._data.game_info and self._data.game_info.winner:
            return self._data.game_info.winner.display_name
        return None
    
    def set_local_player(self, user_id: int, player_color: Player) -> None:
        """Set which player is controlled locally.
        
        Args:
            user_id: ID of the local user
            player_color: Color the local player is playing
        """
        self._data.local_player_color = player_color
        self._update_turn_status()
        
        logger.info(f"Set local player: {user_id} playing {player_color.value}")
        self._notify_observers()
    
    def update_game(self, game_info: GameInfo) -> None:
        """Update the game information.
        
        Args:
            game_info: New game information from backend
        """
        old_move_count = self._data.game_info.move_count if self._data.game_info else 0
        new_move_count = game_info.move_count
        
        self._data.game_info = game_info
        self._update_turn_status()
        
        if new_move_count > old_move_count:
            logger.info(f"Game updated: move count {old_move_count} -> {new_move_count}")
        
        self._notify_observers()
    
    def update_moves(self, moves: List[MoveInfo]) -> None:
        """Update the move history.
        
        Args:
            moves: List of moves from backend
        """
        old_count = len(self._data.moves)
        self._data.moves = moves
        
        if len(moves) != old_count:
            logger.debug(f"Updated moves: {old_count} -> {len(moves)}")
            self._notify_observers()
    
    def add_move(self, move: MoveInfo) -> None:
        """Add a new move to the history.
        
        Args:
            move: New move to add
        """
        self._data.moves.append(move)
        logger.info(f"Added move {move.move_number}: ({move.row}, {move.col}) by {move.player_color}")
        self._notify_observers()
    
    def clear_game(self) -> None:
        """Clear the current game state."""
        logger.info("Clearing game state")
        self._data = GameStateData()
        self._notify_observers()
    
    def _update_turn_status(self) -> None:
        """Update whether it's the local player's turn."""
        if (self._data.game_info and 
            self._data.local_player_color and 
            not self.is_game_over):
            
            current_player = self.current_player
            self._data.is_local_player_turn = (current_player == self._data.local_player_color)
        else:
            self._data.is_local_player_turn = False
    
    def get_position_state(self, row: int, col: int) -> Optional[str]:
        """Get the state of a specific board position.
        
        Args:
            row: Board row (0-based)
            col: Board column (0-based)
            
        Returns:
            'black', 'white', or None for empty
        """
        board = self.board
        if 0 <= row < len(board) and 0 <= col < len(board[row]):
            return board[row][col]
        return None
    
    def is_valid_move(self, row: int, col: int) -> bool:
        """Check if a move is valid at the given position.
        
        Args:
            row: Board row (0-based)
            col: Board column (0-based)
            
        Returns:
            True if the move is valid
        """
        # Check bounds
        if not (0 <= row < self.board_size and 0 <= col < self.board_size):
            return False
        
        # Check if position is empty
        if self.get_position_state(row, col) is not None:
            return False
        
        # Check if game is active and it's local player's turn
        if self.game_status != GameStatus.ACTIVE:
            return False
            
        if not self._data.is_local_player_turn:
            return False
        
        return True