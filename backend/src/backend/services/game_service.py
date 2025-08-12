"""
Game Service for Gomoku business logic.

This module contains the GameService class which handles all game-related
business logic including move validation, win detection, and game state management.
Separates business logic from API routes for better architecture.
"""

from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from ..db.models import Game, GameMove, GameStatus, Player, User


class GameService:
    """
    Service class for Gomoku game business logic.
    
    Handles move validation, win detection, and game state management.
    """
    
    def __init__(self, db_session: AsyncSession):
        """Initialize the game service with database session."""
        self.db = db_session
    
    async def validate_move(
        self, 
        game: Game, 
        player_id: int, 
        row: int, 
        col: int
    ) -> None:
        """
        Validate a move before it's made.
        
        Args:
            game: The game instance
            player_id: ID of the player making the move
            row: Row coordinate (0-based)
            col: Column coordinate (0-based)
            
        Raises:
            ValueError: If the move is invalid
        """
        # Check if game is active
        if game.status != GameStatus.ACTIVE:
            raise ValueError("Game is not active")
        
        # Check if it's the correct player's turn
        expected_player_id = (
            game.black_player_id if game.current_player == Player.BLACK 
            else game.white_player_id
        )
        if player_id != expected_player_id:
            current_color = game.current_player.value
            raise ValueError(f"It's {current_color} player's turn")
        
        # Check board bounds
        board_size = game.board_state.get("size", 15)
        if row < 0 or row >= board_size or col < 0 or col >= board_size:
            raise ValueError(f"Move position ({row}, {col}) is out of bounds")
        
        # Check if position is already occupied
        board = game.board_state.get("board", [])
        if (row < len(board) and 
            col < len(board[row]) and 
            board[row][col] is not None):
            raise ValueError(f"Position ({row}, {col}) is already occupied")
    
    async def make_move(
        self,
        game: Game,
        player_id: int,
        row: int,
        col: int
    ) -> GameMove:
        """
        Make a move in the game.
        
        Args:
            game: The game instance
            player_id: ID of the player making the move
            row: Row coordinate (0-based)
            col: Column coordinate (0-based)
            
        Returns:
            GameMove: The created move
            
        Raises:
            ValueError: If the move is invalid
        """
        # Validate the move
        await self.validate_move(game, player_id, row, col)
        
        # Create the move
        move_number = game.move_count + 1
        player_color = game.current_player
        
        move = GameMove(
            game_id=game.id,
            player_id=player_id,
            move_number=move_number,
            row=row,
            col=col,
            player_color=player_color
        )
        
        # Update the board state
        game.board_state["board"][row][col] = player_color.value
        game.move_count += 1
        
        # Mark the board_state field as modified so SQLAlchemy knows to update it
        flag_modified(game, "board_state")
        
        # Check for win
        is_winning_move = self.check_win(game.board_state["board"], row, col, player_color.value)
        move.is_winning_move = is_winning_move
        
        if is_winning_move:
            game.status = GameStatus.FINISHED
            game.winner_id = player_id
            # Don't switch turns if game is won
        else:
            # Switch turns
            game.current_player = Player.WHITE if game.current_player == Player.BLACK else Player.BLACK
        
        # Save to database
        self.db.add(move)
        # Add the game to the session to ensure board state changes are persisted
        self.db.add(game)
        await self.db.commit()
        await self.db.refresh(move)
        # Don't refresh game as it would overwrite our in-memory board state changes
        
        return move
    
    def check_win(self, board: list, row: int, col: int, player_color: str) -> bool:
        """
        Check if the last move resulted in a win.
        
        Args:
            board: 2D board array
            row: Row of the last move
            col: Column of the last move
            player_color: Color of the player who made the move
            
        Returns:
            bool: True if this move wins the game
        """
        board_size = len(board)
        
        # Define the four directions: horizontal, vertical, diagonal-right, diagonal-left
        directions = [
            (0, 1),   # horizontal
            (1, 0),   # vertical
            (1, 1),   # diagonal-right (\)
            (1, -1),  # diagonal-left (/)
        ]
        
        for dr, dc in directions:
            count = 1  # Count the placed stone
            
            # Check in positive direction
            r, c = row + dr, col + dc
            while (0 <= r < board_size and 0 <= c < board_size and 
                   board[r][c] == player_color):
                count += 1
                r, c = r + dr, c + dc
            
            # Check in negative direction
            r, c = row - dr, col - dc
            while (0 <= r < board_size and 0 <= c < board_size and 
                   board[r][c] == player_color):
                count += 1
                r, c = r - dr, c - dc
            
            # Check if we have 5 in a row
            if count >= 5:
                return True
        
        return False
    
    async def get_game_status(self, game: Game) -> dict:
        """
        Get comprehensive game status information.
        
        Args:
            game: The game instance
            
        Returns:
            dict: Game status information
        """
        return {
            "id": game.id,
            "status": game.status.value,
            "current_player": game.current_player.value,
            "move_count": game.move_count,
            "is_game_over": game.is_game_over,
            "winner_id": game.winner_id,
            "board_state": game.board_state
        }