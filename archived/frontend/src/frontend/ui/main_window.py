"""
Main window for the Gomoku GUI application.

This module creates and manages the main application window with the game board,
controls, and status information.
"""

import asyncio
from typing import Optional, Dict, Any

import dearpygui.dearpygui as dpg
from loguru import logger

from ..client.api_client import APIClient, GameInfo, UserInfo
from ..game.game_state import GameState, GameStateData, GameStatus, Player
from .game_board import GameBoard


class MainWindow:
    """Main application window for the Gomoku game."""
    
    def __init__(self, api_client: APIClient, game_state: GameState):
        """Initialize the main window.
        
        Args:
            api_client: API client for backend communication
            game_state: Game state manager
        """
        self.api_client = api_client
        self.game_state = game_state
        self.game_board: Optional[GameBoard] = None
        
        # UI state
        self._server_connected = False
        self._users_cache: Dict[int, UserInfo] = {}
        self._pending_operations = False
        
        # Register for game state updates
        self.game_state.add_observer(self._on_game_state_changed)
        
        logger.debug("Initialized main window")
    
    def create(self) -> None:
        """Create the main window UI."""
        logger.info("Creating main window UI")
        
        with dpg.window(label="Gomoku Game", tag="main_window"):
            # Connection status
            with dpg.group(horizontal=True):
                dpg.add_text("Server Status:", color=(200, 200, 200))
                dpg.add_text("Disconnected", tag="connection_status", color=(255, 100, 100))
                dpg.add_button(label="Connect", tag="connect_button", callback=self._on_connect_clicked)
            
            dpg.add_separator()
            
            # Game controls
            with dpg.collapsing_header(label="Game Setup", default_open=True, tag="game_setup"):
                with dpg.group(horizontal=True):
                    dpg.add_text("Black Player:")
                    dpg.add_combo(label="##black_player", tag="black_player_combo", width=150)
                    dpg.add_text("White Player:")
                    dpg.add_combo(label="##white_player", tag="white_player_combo", width=150)
                
                with dpg.group(horizontal=True):
                    dpg.add_button(label="New Game", tag="new_game_button", 
                                 callback=self._on_new_game_clicked, enabled=False)
                    dpg.add_button(label="Start Game", tag="start_game_button",
                                 callback=self._on_start_game_clicked, enabled=False)
            
            dpg.add_separator()
            
            # Game status
            with dpg.group(horizontal=True):
                dpg.add_text("Game Status:", color=(200, 200, 200))
                dpg.add_text("No Game", tag="game_status", color=(150, 150, 150))
            
            with dpg.group(horizontal=True):
                dpg.add_text("Current Turn:", color=(200, 200, 200))
                dpg.add_text("N/A", tag="current_turn", color=(150, 150, 150))
            
            dpg.add_separator()
            
            # Game board
            self.game_board = GameBoard(
                api_client=self.api_client,
                game_state=self.game_state,
                size=15
            )
            self.game_board.create()
        
        # Set main window as primary
        dpg.set_primary_window("main_window", True)
        
        # Start connection check
        self._check_connection()
    
    def update(self) -> None:
        """Update the window state (called from main loop)."""
        # Handle any pending async operations
        pass
    
    def _check_connection(self) -> None:
        """Check server connection status."""
        async def check():
            try:
                connected = await self.api_client.health_check()
                self._server_connected = connected
                
                if connected:
                    dpg.set_value("connection_status", "Connected")
                    dpg.configure_item("connection_status", color=(100, 255, 100))
                    dpg.configure_item("connect_button", label="Refresh")
                    dpg.configure_item("new_game_button", enabled=True)
                    
                    # Load users
                    await self._load_users()
                else:
                    dpg.set_value("connection_status", "Disconnected")
                    dpg.configure_item("connection_status", color=(255, 100, 100))
                    dpg.configure_item("connect_button", label="Connect")
                    dpg.configure_item("new_game_button", enabled=False)
                    
            except Exception as e:
                logger.error(f"Connection check failed: {e}")
                self._server_connected = False
                dpg.set_value("connection_status", "Error")
                dpg.configure_item("connection_status", color=(255, 150, 50))
        
        # Run in background (Note: In a real app, we'd use proper async handling)
        try:
            asyncio.run(check())
        except Exception as e:
            logger.error(f"Failed to check connection: {e}")
    
    async def _load_users(self) -> None:
        """Load users from the backend."""
        try:
            users = await self.api_client.get_users()
            self._users_cache = {user.id: user for user in users}
            
            # Update combo boxes
            user_items = [f"{user.display_name} ({user.username})" for user in users]
            user_values = [user.id for user in users]
            
            dpg.configure_item("black_player_combo", items=user_items, user_data=user_values)
            dpg.configure_item("white_player_combo", items=user_items, user_data=user_values)
            
            # Select first two users by default if available
            if len(users) >= 2:
                dpg.set_value("black_player_combo", user_items[0])
                dpg.set_value("white_player_combo", user_items[1])
            
            logger.info(f"Loaded {len(users)} users")
            
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
    
    def _on_connect_clicked(self) -> None:
        """Handle connect button click."""
        logger.info("Checking server connection...")
        self._check_connection()
    
    def _on_new_game_clicked(self) -> None:
        """Handle new game button click."""
        if not self._server_connected:
            logger.warning("Cannot create game: not connected to server")
            return
        
        # Get selected players
        black_combo = dpg.get_value("black_player_combo")
        white_combo = dpg.get_value("white_player_combo")
        
        if not black_combo or not white_combo:
            logger.warning("Please select both players")
            return
        
        # Find user IDs
        black_users = dpg.get_item_user_data("black_player_combo")
        white_users = dpg.get_item_user_data("white_player_combo")
        
        if not black_users or not white_users:
            logger.error("User data not available")
            return
        
        try:
            black_idx = dpg.get_value("black_player_combo")
            white_idx = dpg.get_value("white_player_combo")
            
            # Find indices
            try:
                black_items = dpg.get_item_configuration("black_player_combo")["items"]
                white_items = dpg.get_item_configuration("white_player_combo")["items"]
                
                black_user_idx = black_items.index(black_combo)
                white_user_idx = white_items.index(white_combo)
            except (KeyError, ValueError) as e:
                logger.error(f"Failed to find user indices: {e}")
                return
            
            black_user_id = black_users[black_user_idx]
            white_user_id = white_users[white_user_idx]
            
            if black_user_id == white_user_id:
                logger.warning("Black and white players cannot be the same")
                return
            
            # Create the game
            asyncio.run(self._create_game(black_user_id, white_user_id))
            
        except Exception as e:
            logger.error(f"Failed to parse selected users: {e}")
    
    async def _create_game(self, black_player_id: int, white_player_id: int) -> None:
        """Create a new game.
        
        Args:
            black_player_id: ID of black player
            white_player_id: ID of white player
        """
        try:
            # Use default ruleset (assume ID 1 exists)
            ruleset_id = 1
            
            game_info = await self.api_client.create_game(
                black_player_id=black_player_id,
                white_player_id=white_player_id,
                ruleset_id=ruleset_id
            )
            
            # Update game state
            self.game_state.update_game(game_info)
            
            # Set local player (for demo, let's assume black player is local)
            self.game_state.set_local_player(black_player_id, Player.BLACK)
            
            logger.info(f"Created new game: {game_info.id}")
            
        except Exception as e:
            logger.error(f"Failed to create game: {e}")
    
    def _on_start_game_clicked(self) -> None:
        """Handle start game button click."""
        if not self.game_state.has_game:
            logger.warning("No game to start")
            return
        
        game_id = self.game_state.game_id
        if game_id:
            asyncio.run(self._start_game(game_id))
    
    async def _start_game(self, game_id: str) -> None:
        """Start the current game.
        
        Args:
            game_id: ID of game to start
        """
        try:
            game_info = await self.api_client.start_game(game_id)
            self.game_state.update_game(game_info)
            
            logger.info(f"Started game: {game_id}")
            
        except Exception as e:
            logger.error(f"Failed to start game: {e}")
    
    def _on_game_state_changed(self, state_data: GameStateData) -> None:
        """Handle game state changes.
        
        Args:
            state_data: Updated game state data
        """
        # Update game status display
        if state_data.game_info:
            status_text = state_data.game_info.status.title()
            if state_data.game_info.is_game_over and state_data.game_info.winner:
                status_text += f" - {state_data.game_info.winner.display_name} Wins!"
            
            dpg.set_value("game_status", status_text)
            
            # Update current turn
            if not state_data.game_info.is_game_over:
                current_player = state_data.game_info.current_player.title()
                if state_data.is_local_player_turn:
                    current_player += " (Your Turn)"
                dpg.set_value("current_turn", current_player)
                dpg.configure_item("current_turn", color=(100, 255, 100) if state_data.is_local_player_turn else (200, 200, 200))
            else:
                dpg.set_value("current_turn", "Game Over")
                dpg.configure_item("current_turn", color=(150, 150, 150))
            
            # Update button states
            can_start = state_data.game_info.can_start
            dpg.configure_item("start_game_button", enabled=can_start)
        else:
            dpg.set_value("game_status", "No Game")
            dpg.set_value("current_turn", "N/A")
            dpg.configure_item("start_game_button", enabled=False)