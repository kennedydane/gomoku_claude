"""
Game board UI component for the Gomoku game.

This module handles the visual representation of the game board and user interactions.
"""

import asyncio
from typing import Optional, Tuple, List

import dearpygui.dearpygui as dpg
from loguru import logger

from ..client.api_client import APIClient
from ..game.game_state import GameState, GameStateData


class GameBoard:
    """Visual game board component using Dear PyGUI."""
    
    def __init__(self, api_client: APIClient, game_state: GameState, size: int = 15):
        """Initialize the game board.
        
        Args:
            api_client: API client for making moves
            game_state: Game state manager
            size: Board size (default: 15x15)
        """
        self.api_client = api_client
        self.game_state = game_state
        self.size = size
        
        # UI configuration
        self.cell_size = 30
        self.stone_radius = 12
        self.grid_color = (100, 100, 100)
        self.black_stone_color = (20, 20, 20)
        self.white_stone_color = (240, 240, 240)
        self.highlight_color = (255, 255, 100)
        
        # State
        self._last_move: Optional[Tuple[int, int]] = None
        
        # Register for game state updates
        self.game_state.add_observer(self._on_game_state_changed)
        
        logger.debug(f"Initialized game board ({size}x{size})")
    
    def create(self) -> None:
        """Create the game board UI."""
        logger.info("Creating game board UI")
        
        # Calculate board dimensions
        board_width = self.size * self.cell_size
        board_height = self.size * self.cell_size
        
        with dpg.child_window(label="Game Board", width=board_width + 20, height=board_height + 40):
            # Create drawing area
            with dpg.drawlist(width=board_width, height=board_height, tag="game_board_canvas"):
                self._draw_empty_board()
            
            # Add invisible buttons for click detection
            self._create_click_handlers()
    
    def _draw_empty_board(self) -> None:
        """Draw the empty game board grid."""
        # Clear existing drawings
        dpg.delete_item("game_board_canvas", children_only=True)
        
        # Draw grid lines
        for i in range(self.size + 1):
            # Vertical lines
            x = i * self.cell_size
            dpg.draw_line(
                parent="game_board_canvas",
                p1=(x, 0),
                p2=(x, self.size * self.cell_size),
                color=self.grid_color,
                thickness=1
            )
            
            # Horizontal lines
            y = i * self.cell_size
            dpg.draw_line(
                parent="game_board_canvas",
                p1=(0, y),
                p2=(self.size * self.cell_size, y),
                color=self.grid_color,
                thickness=1
            )
        
        # Draw star points (traditional Go board markers)
        if self.size == 15:
            star_points = [(3, 3), (3, 11), (11, 3), (11, 11), (7, 7)]
            for row, col in star_points:
                x = col * self.cell_size
                y = row * self.cell_size
                dpg.draw_circle(
                    parent="game_board_canvas",
                    center=(x, y),
                    radius=3,
                    color=self.grid_color,
                    fill=self.grid_color
                )
    
    def _create_click_handlers(self) -> None:
        """Create invisible button overlay for click detection."""
        # For now, we'll skip the complex click handlers
        # TODO: Implement click detection properly
        pass
    
    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Handle cell click.
        
        Args:
            row: Board row (0-based)
            col: Board column (0-based)
        """
        logger.debug(f"Cell clicked: ({row}, {col})")
        
        # Check if move is valid
        if not self.game_state.is_valid_move(row, col):
            logger.debug("Invalid move attempt")
            return
        
        # Make the move
        game_id = self.game_state.game_id
        local_player_color = self.game_state.data.local_player_color
        
        if not game_id or not local_player_color:
            logger.warning("Cannot make move: no game or local player")
            return
        
        # Get local player ID
        game_info = self.game_state.data.game_info
        if not game_info:
            return
        
        if local_player_color.value == "black":
            player_id = game_info.black_player_id
        else:
            player_id = game_info.white_player_id
        
        # Make the move asynchronously
        asyncio.run(self._make_move(game_id, player_id, row, col))
    
    async def _make_move(self, game_id: str, player_id: int, row: int, col: int) -> None:
        """Make a move via the API.
        
        Args:
            game_id: Game ID
            player_id: Player making the move
            row: Board row
            col: Board column
        """
        try:
            logger.info(f"Making move: ({row}, {col}) for player {player_id}")
            
            # Make the move
            move_info = await self.api_client.make_move(game_id, player_id, row, col)
            
            # Get updated game state
            game_info = await self.api_client.get_game(game_id)
            
            # Update local state
            self.game_state.update_game(game_info)
            self.game_state.add_move(move_info)
            
            # Store last move for highlighting
            self._last_move = (row, col)
            
            logger.info(f"Move completed: {move_info.move_number}")
            
        except Exception as e:
            logger.error(f"Failed to make move: {e}")
    
    def _on_game_state_changed(self, state_data: GameStateData) -> None:
        """Handle game state changes to update board display.
        
        Args:
            state_data: Updated game state data
        """
        self._redraw_board()
    
    def _redraw_board(self) -> None:
        """Redraw the entire board with current state."""
        # Clear and redraw base board
        self._draw_empty_board()
        
        # Draw stones
        board = self.game_state.board
        for row in range(self.size):
            for col in range(self.size):
                stone_color = board[row][col] if row < len(board) and col < len(board[row]) else None
                
                if stone_color:
                    self._draw_stone(row, col, stone_color)
        
        # Highlight last move
        if self._last_move and self.game_state.has_game:
            row, col = self._last_move
            self._highlight_position(row, col)
    
    def _draw_stone(self, row: int, col: int, color: str) -> None:
        """Draw a stone at the specified position.
        
        Args:
            row: Board row
            col: Board column  
            color: Stone color ('black' or 'white')
        """
        x = col * self.cell_size
        y = row * self.cell_size
        
        stone_color = self.black_stone_color if color == "black" else self.white_stone_color
        border_color = self.white_stone_color if color == "black" else self.black_stone_color
        
        # Draw stone with border
        dpg.draw_circle(
            parent="game_board_canvas",
            center=(x, y),
            radius=self.stone_radius,
            color=border_color,
            fill=stone_color,
            thickness=2
        )
    
    def _highlight_position(self, row: int, col: int) -> None:
        """Highlight a position (for last move).
        
        Args:
            row: Board row
            col: Board column
        """
        x = col * self.cell_size
        y = row * self.cell_size
        
        # Draw highlight ring
        dpg.draw_circle(
            parent="game_board_canvas",
            center=(x, y),
            radius=self.stone_radius + 4,
            color=self.highlight_color,
            thickness=2
        )
    
    def reset_board(self) -> None:
        """Reset the board to empty state."""
        logger.info("Resetting game board")
        self._last_move = None
        self._draw_empty_board()