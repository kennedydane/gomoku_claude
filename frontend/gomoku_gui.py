#!/usr/bin/env python3
"""Gomoku GUI with comprehensive logging and authentication."""

import sys
import asyncio
import argparse
from typing import Optional
from pathlib import Path
import httpx
import dearpygui.dearpygui as dpg
from loguru import logger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from frontend.ui.auth_dialogs import AuthenticationManager
from frontend.client.api_client import APIClient
from frontend.game.game_management import (
    process_games_for_display,
    get_filter_display_name
)

# Game board state
board_state = [[None for _ in range(15)] for _ in range(15)]
current_player = "black"
game_id: Optional[str] = None
api_base_url = "http://localhost:8001"

# Authentication and API
auth_manager: Optional[AuthenticationManager] = None
api_client: Optional[APIClient] = None

# Game management state
user_games = []
games_window_open = False
games_filter = "all"  # "all", "active", "completed", "your_turn"


def on_login_success():
    """Handle successful login."""
    logger.info("User logged in successfully")
    update_ui_auth_state()

def on_logout():
    """Handle logout."""
    logger.info("User logged out")
    update_ui_auth_state()

def update_ui_auth_state():
    """Update UI based on authentication state."""
    if not auth_manager:
        return
    
    is_authenticated = auth_manager.is_authenticated()
    auth_manager.update_status()
    status = auth_manager.get_status_text()
    
    # Update authentication status display
    dpg.set_value("auth_status_text", status)
    
    # Update button states
    dpg.configure_item("login_button", enabled=not is_authenticated)
    dpg.configure_item("register_button", enabled=not is_authenticated)  
    dpg.configure_item("logout_button", enabled=is_authenticated)
    
    # Update game controls
    dpg.configure_item("new_game_button", enabled=is_authenticated)
    dpg.configure_item("my_games_button", enabled=is_authenticated)
    
    logger.debug(f"UI auth state updated: authenticated={is_authenticated}")
    
    # Refresh games list if authenticated and games window is open
    if is_authenticated and games_window_open:
        refresh_games_list()

def show_login():
    """Show login dialog."""
    if auth_manager:
        auth_manager.show_login_dialog(on_success=on_login_success)

def show_register():
    """Show registration dialog."""
    if auth_manager:
        auth_manager.show_register_dialog(on_success=on_login_success)

def logout():
    """Logout current user."""
    if auth_manager:
        auth_manager.logout()
        on_logout()

def show_my_games():
    """Show the My Games window."""
    global games_window_open
    
    if not auth_manager or not auth_manager.is_authenticated():
        dpg.set_value("status_text", "Please login first to view games")
        return
    
    if dpg.does_item_exist("my_games_window"):
        if games_window_open:
            # Window exists and is open, just refresh
            refresh_games_list()
            return
        else:
            # Window exists but is closed, show it
            dpg.show_item("my_games_window")
            games_window_open = True
            refresh_games_list()
            return
    
    # Create new games window
    games_window_open = True
    
    with dpg.window(label="My Games", tag="my_games_window", width=650, height=450, 
                   on_close=lambda: globals().update({'games_window_open': False})):
        dpg.add_text("Your Games", color=(100, 150, 255))
        dpg.add_separator()
        
        # Controls row
        with dpg.group(horizontal=True):
            dpg.add_button(label="Refresh", callback=refresh_games_list)
            dpg.add_button(label="New Game", callback=create_new_game)
            
            # Filter dropdown
            dpg.add_text("Filter:")
            dpg.add_combo(
                items=["All Games", "Active Games", "Your Turn", "Completed Games"],
                tag="games_filter_combo",
                default_value="All Games",
                callback=on_filter_changed,
                width=120
            )
        
        dpg.add_separator()
        
        # Games list container
        with dpg.child_window(tag="games_list_container", height=320):
            dpg.add_text("Loading games...", tag="games_loading_text")
    
    # Initial games load
    refresh_games_list()

def on_filter_changed(sender, app_data):
    """Handle filter dropdown change."""
    global games_filter
    
    # Map display names to filter values
    filter_map = {
        "All Games": "all",
        "Active Games": "active",
        "Your Turn": "your_turn",
        "Completed Games": "completed"
    }
    
    games_filter = filter_map.get(app_data, "all")
    logger.debug(f"Filter changed to: {games_filter}")
    
    # Update display with current games
    update_games_display()

def refresh_games_list():
    """Refresh the games list from the API."""
    if not auth_manager or not auth_manager.is_authenticated():
        return
    
    logger.info("Refreshing games list")
    
    async def fetch_games():
        global user_games
        
        if not api_client:
            logger.error("API client not initialized")
            return
        
        try:
            current_user = auth_manager.get_current_user()
            if not current_user:
                logger.error("No current user")
                return
            
            # Fetch games from API
            games_data = await api_client.get_games()
            
            # Store games - filtering is now done by the game management functions
            user_games = games_data
            
            logger.info(f"Fetched {len(user_games)} games for user {current_user.username}")
            
            # Update UI on main thread
            update_games_display()
            
        except Exception as e:
            logger.error(f"Error fetching games: {e}", exc_info=True)
            if dpg.does_item_exist("games_loading_text"):
                dpg.set_value("games_loading_text", f"Error loading games: {e}")
    
    # Use threading approach
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(fetch_games())
    except RuntimeError:
        import threading
        def run_fetch():
            try:
                asyncio.run(fetch_games())
            except Exception as e:
                logger.error(f"Error in fetch games thread: {e}")
        threading.Thread(target=run_fetch, daemon=True).start()

def update_games_display():
    """Update the games display in the UI."""
    if not dpg.does_item_exist("games_list_container"):
        return
    
    # Clear existing items
    dpg.delete_item("games_list_container", children_only=True)
    
    if not user_games:
        dpg.add_text("No games found", parent="games_list_container", color=(150, 150, 150))
        return
    
    current_user = auth_manager.get_current_user() if auth_manager else None
    if not current_user:
        dpg.add_text("No user information", parent="games_list_container", color=(255, 100, 100))
        return
    
    # Use the testable game management functions
    # Use username for matching since API returns usernames
    formatted_games = process_games_for_display(user_games, games_filter, current_user.username)
    
    if not formatted_games:
        filter_name = get_filter_display_name(games_filter)
        dpg.add_text(f"No {filter_name} found", parent="games_list_container", color=(150, 150, 150))
        return
    
    # Create UI elements for each formatted game
    for game_info in formatted_games:
        with dpg.group(parent="games_list_container"):
            # Main game info line
            with dpg.group(horizontal=True):
                dpg.add_text(f"Game {game_info['game_id_short']}", color=(200, 200, 255))
                dpg.add_text(f"({game_info['player_color']} vs {game_info['opponent_name']})", color=(180, 180, 180))
                dpg.add_text(game_info['status_text'], color=game_info['status_color'])
                
                # Action buttons for active games
                if game_info['full_game'].get('status') == 'ACTIVE':
                    dpg.add_button(
                        label="Load Game", 
                        callback=lambda s, a, u=game_info['full_game']: load_game(u),
                        user_data=game_info['full_game'],
                        width=80
                    )
                
            # Secondary info line
            info_parts = []
            if game_info['board_size'] and game_info['board_size'] != 15:
                info_parts.append(f"{game_info['board_size']}×{game_info['board_size']}")
            if game_info['date_str']:
                info_parts.append(game_info['date_str'])
            
            if info_parts:
                info_text = " • ".join(info_parts)
                dpg.add_text(f"  {info_text}", color=(120, 120, 120))
            
        dpg.add_separator(parent="games_list_container")

def load_game(game_data):
    """Load a specific game into the main board."""
    global game_id, board_state, current_player
    
    logger.info(f"Loading game {game_data['id']}")
    
    async def load():
        global game_id, board_state, current_player
        
        if not api_client:
            logger.error("API client not initialized")
            return
        
        try:
            # Get detailed game data including moves
            detailed_game = await api_client.get_game(game_data['id'])
            moves_data = await api_client.get_game_moves(game_data['id'])
            
            # Set global game state
            game_id = detailed_game.id
            board_size = detailed_game.board_state.size
            
            # Load board state directly from API response
            api_board = detailed_game.board_state.board
            board_state = []
            for row in api_board:
                board_row = []
                for cell in row:
                    if cell is None:
                        board_row.append(None)
                    else:
                        # Convert API format to GUI format
                        board_row.append(cell.lower())
                board_state.append(board_row)
            
            move_count = detailed_game.move_count
            
            # Set current player based on move count
            current_player = "black" if move_count % 2 == 0 else "white"
            
            # Update board display
            draw_board()
            
            # Update status
            current_user = auth_manager.get_current_user()
            user_color = "Black" if detailed_game.black_player_id == current_user.id else "White"
            
            msg = f"Loaded game {game_id[:8]}. You are {user_color}. {current_player.title()}'s turn."
            dpg.set_value("status_text", msg)
            logger.info(f"Game loaded successfully: {msg}")
            
            # Close games window
            if dpg.does_item_exist("my_games_window"):
                dpg.hide_item("my_games_window")
                globals()['games_window_open'] = False
            
        except Exception as e:
            msg = f"Error loading game: {e}"
            logger.error(f"Error loading game {game_data['id']}: {e}", exc_info=True)
            dpg.set_value("status_text", msg)
    
    # Use threading approach
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(load())
    except RuntimeError:
        import threading
        def run_load():
            try:
                asyncio.run(load())
            except Exception as e:
                logger.error(f"Error in load game thread: {e}")
        threading.Thread(target=run_load, daemon=True).start()

def setup_logging(debug: bool = False):
    """Configure loguru logging."""
    logger.remove()  # Remove default handler
    
    if debug:
        log_level = "DEBUG"
        log_format = "<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    else:
        log_level = "INFO"
        log_format = "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    
    logger.add(sys.stderr, level=log_level, format=log_format)
    logger.info(f"Logging initialized at {log_level} level")


def get_optimal_board_size():
    """Calculate optimal board size based on current window size."""
    if not dpg.does_item_exist("main_window"):
        return 450
    
    # Get window size
    window_width = dpg.get_item_width("main_window")
    window_height = dpg.get_item_height("main_window")
    
    # Reserve space for menus, text, and padding (about 200px total)
    available_width = max(window_width - 50, 300)  # Min 300px
    available_height = max(window_height - 200, 300)  # Min 300px for menus/text
    
    # Keep it square and reasonably sized
    optimal_size = min(available_width, available_height, 800)  # Max 800px
    return max(optimal_size, 300)  # Min 300px


def draw_board():
    """Draw the game board with cell-based rendering (like web app)."""
    logger.debug("Redrawing game board")
    dpg.delete_item("board_drawing", children_only=True)
    
    # Determine board size dynamically
    if not board_state:
        return
    
    current_board_size = len(board_state)
    
    # Calculate optimal board size based on window size
    board_pixel_size = get_optimal_board_size()
    cell_size = board_pixel_size / current_board_size
    
    # Update the drawlist size to match calculated size
    dpg.configure_item("board_drawing", width=board_pixel_size, height=board_pixel_size)
    
    # Draw cells (like web app - filled rectangles with borders)
    for row in range(current_board_size):
        for col in range(current_board_size):
            x1 = col * cell_size
            y1 = row * cell_size
            x2 = x1 + cell_size
            y2 = y1 + cell_size
            
            # Determine cell color based on content and position
            if board_state[row][col]:
                # Occupied cell - draw stone
                if board_state[row][col] == "black":
                    cell_color = (40, 40, 40)      # Dark for black stone
                    border_color = (60, 60, 60)
                else:  # white
                    cell_color = (220, 220, 220)   # Light for white stone  
                    border_color = (180, 180, 180)
            else:
                # Empty cell - alternating pattern like web app
                if (row + col) % 2 == 0:
                    cell_color = (240, 217, 181)   # Light wood color
                else:
                    cell_color = (238, 214, 175)   # Slightly darker wood
                border_color = (200, 170, 140)
            
            # Draw filled cell
            dpg.draw_rectangle((x1, y1), (x2, y2), 
                             color=border_color, fill=cell_color, 
                             parent="board_drawing")
            
            # Draw stone circle if occupied (for better visual clarity)
            if board_state[row][col]:
                center_x = x1 + cell_size / 2
                center_y = y1 + cell_size / 2
                stone_radius = min(cell_size * 0.35, 15)  # 35% of cell size, max 15px
                
                if board_state[row][col] == "black":
                    stone_color = (0, 0, 0)
                    stone_border = (40, 40, 40)
                else:
                    stone_color = (255, 255, 255)
                    stone_border = (200, 200, 200)
                    
                dpg.draw_circle((center_x, center_y), stone_radius,
                              color=stone_border, fill=stone_color, 
                              parent="board_drawing")
    
    # Count stones for logging
    stone_count = sum(1 for row in board_state for cell in row if cell)
    logger.debug(f"Board drawn: {current_board_size}x{current_board_size}, {stone_count} stones, {board_pixel_size:.0f}px ({cell_size:.1f}px/cell)")


def cell_clicked(sender, app_data, user_data):
    """Handle cell click."""
    global current_player, game_id
    row, col = user_data
    
    logger.info(f"Cell clicked at ({row}, {col})")
    logger.debug(f"Current game_id: {game_id}, current_player: {current_player}")
    
    if not auth_manager or not auth_manager.is_authenticated():
        msg = "Please login first to make moves"
        logger.warning(msg)
        dpg.set_value("status_text", msg)
        return
    
    if board_state[row][col] is not None:
        msg = f"Position ({row}, {col}) is occupied by {board_state[row][col]}!"
        logger.warning(msg)
        dpg.set_value("status_text", msg)
        return
    
    if not game_id:
        msg = "Please create a game first!"
        logger.warning(msg)
        dpg.set_value("status_text", msg)
        return
    
    current_user = auth_manager.get_current_user()
    if not current_user:
        msg = "No user information available"
        logger.error(msg)
        dpg.set_value("status_text", msg)
        return
    
    # Make the move via authenticated API
    player_id = current_user.id
    logger.debug(f"Making move for player_id {player_id} ({current_player})")
    
    async def make_move():
        global current_player
        logger.debug(f"Sending move request to API: game_id={game_id}, player_id={player_id}, position=({row},{col})")
        
        if not api_client:
            msg = "API client not initialized"
            logger.error(msg)
            dpg.set_value("status_text", msg)
            return
        
        try:
            payload = {"player_id": player_id, "row": row, "col": col}
            logger.debug(f"Move payload: {payload}")
            
            move = await api_client.make_move(game_id, player_id, row, col)
            
            board_state[row][col] = current_player
            logger.info(f"Move successful: {current_player} at ({row}, {col})")
            
            # Switch players
            old_player = current_player
            current_player = "white" if current_player == "black" else "black"
            logger.debug(f"Switched turn from {old_player} to {current_player}")
            
            if move.is_winning_move:
                winner_color = move.player_color.lower()
                msg = f"{winner_color.title()} wins!"
                logger.info(f"GAME OVER: {msg}")
                dpg.set_value("status_text", msg)
            else:
                msg = f"Move made at ({row}, {col}). {current_player.title()}'s turn."
                dpg.set_value("status_text", msg)
            
            draw_board()
            
        except Exception as e:
            msg = f"Error making move: {e}"
            logger.error(f"Unexpected error making move: {e}", exc_info=True)
            dpg.set_value("status_text", msg)
    
    # Use the threading approach like in the auth dialogs
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(make_move())
    except RuntimeError:
        import threading
        def run_move():
            try:
                asyncio.run(make_move())
            except Exception as e:
                logger.error(f"Error in make move thread: {e}")
        threading.Thread(target=run_move, daemon=True).start()


def create_new_game():
    """Create a new game."""
    global game_id, board_state, current_player
    
    if not auth_manager or not auth_manager.is_authenticated():
        msg = "Please login first to create a game"
        logger.warning(msg)
        dpg.set_value("status_text", msg)
        return
    
    current_user = auth_manager.get_current_user()
    if not current_user:
        msg = "No user information available"
        logger.error(msg)
        dpg.set_value("status_text", msg)
        return
    
    logger.info(f"Creating new game for user: {current_user.username}")
    
    async def create():
        global game_id, board_state, current_player
        
        if not api_client:
            msg = "API client not initialized"
            logger.error(msg)
            dpg.set_value("status_text", msg)
            return
        
        try:
            # Create game using authenticated API client
            logger.debug(f"Creating game for user {current_user.id}")
            
            game_data = await api_client.create_game(
                black_player_id=current_user.id,
                white_player_id=current_user.id,  # For now, single player against self  
                ruleset_id=1
            )
            game_id = game_data.id
            logger.info(f"Game created successfully with ID: {game_id}")
            
            # Start the game
            start_response = await api_client.start_game(game_id)
            logger.debug(f"Game started: {start_response}")
            
            # Reset board state
            board_state = [[None for _ in range(15)] for _ in range(15)]
            current_player = "black"
            draw_board()
            
            msg = f"New game started! Game ID: {game_id[:8]}... Black's turn."
            logger.info(msg)
            dpg.set_value("status_text", msg)
            
        except Exception as e:
            msg = f"Error creating game: {e}"
            logger.error(f"Unexpected error: {e}", exc_info=True)
            dpg.set_value("status_text", msg)
    
    # Use the threading approach like in the auth dialogs
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(create())
    except RuntimeError:
        import threading
        def run_create():
            try:
                asyncio.run(create())
            except Exception as e:
                logger.error(f"Error in create game thread: {e}")
        threading.Thread(target=run_create, daemon=True).start()


def check_backend():
    """Check if backend is running and get server info."""
    logger.info("Checking backend connection...")
    
    async def check():
        async with httpx.AsyncClient() as client:
            try:
                # Check root endpoint
                response = await client.get(f"{api_base_url}/")
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Backend connected: {data.get('message', 'Unknown')}")
                    logger.debug(f"Backend info: {data}")
                    
                    # Check if we have users
                    users_response = await client.get(f"{api_base_url}/api/v1/users/")
                    if users_response.status_code == 200:
                        users = users_response.json()
                        logger.info(f"Found {len(users)} users in database")
                        for user in users:
                            logger.debug(f"User: {user}")
                    else:
                        logger.warning(f"Could not fetch users: {users_response.status_code}")
                        logger.debug(f"Users response: {users_response.text}")
                    
                    # Check rulesets
                    rules_response = await client.get(f"{api_base_url}/api/v1/rulesets/")
                    if rules_response.status_code == 200:
                        rulesets = rules_response.json()
                        logger.info(f"Found {len(rulesets)} rulesets in database")
                        for ruleset in rulesets:
                            logger.debug(f"Ruleset: {ruleset}")
                    else:
                        logger.warning(f"Could not fetch rulesets: {rules_response.status_code}")
                        logger.debug(f"Rulesets response: {rules_response.text}")
                    
                    dpg.set_value("status_text", "Backend connected! Ready to play.")
                else:
                    logger.error(f"Backend returned status {response.status_code}")
                    dpg.set_value("status_text", f"Backend error: {response.status_code}")
                    
            except httpx.ConnectError as e:
                msg = f"Cannot connect to backend at {api_base_url}"
                logger.error(f"{msg}: {e}")
                dpg.set_value("status_text", msg)
            except Exception as e:
                logger.error(f"Unexpected error checking backend: {e}", exc_info=True)
                dpg.set_value("status_text", f"Error: {e}")
    
    asyncio.run(check())


def handle_board_click():
    """Handle clicks on the board."""
    if dpg.is_item_hovered("board_drawing"):
        # Use drawing mouse position which is relative to the drawing area
        draw_mouse_pos = dpg.get_drawing_mouse_pos()
        rel_x = draw_mouse_pos[0]
        rel_y = draw_mouse_pos[1]
        
        # Determine current board size and cell size
        if not board_state:
            return
            
        current_board_size = len(board_state)
        board_pixel_size = get_optimal_board_size()
        cell_size = board_pixel_size / current_board_size
        
        # Convert to grid coordinates (cell-based, not intersection-based)
        col = int(rel_x // cell_size)
        row = int(rel_y // cell_size)
        
        logger.debug(f"Mouse click at drawing ({rel_x:.0f}, {rel_y:.0f}), cell size {cell_size:.1f}, grid ({row}, {col})")
        
        if 0 <= row < current_board_size and 0 <= col < current_board_size:
            cell_clicked(None, None, (row, col))
        else:
            logger.debug(f"Click outside board bounds: ({row}, {col})")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Gomoku GUI Game")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--api-url", default="http://localhost:8001", help="Backend API URL")
    args = parser.parse_args()
    
    global api_base_url, auth_manager, api_client
    api_base_url = args.api_url
    
    # Setup logging
    setup_logging(args.debug)
    logger.info("Starting Gomoku GUI with Authentication")
    logger.info(f"Backend API URL: {api_base_url}")
    
    # Create GUI first (required for authentication dialogs)
    logger.debug("Creating DearPyGUI context...")
    dpg.create_context()
    logger.debug("DearPyGUI context created successfully")
    
    # Initialize authentication system after DearPyGUI context is created
    try:
        logger.debug("Initializing AuthenticationManager...")
        auth_manager = AuthenticationManager(
            config_file=str(Path(__file__).parent / "gomoku_config.json"),
            env_file=str(Path(__file__).parent / ".env")
        )
        logger.debug("AuthenticationManager created, initializing APIClient...")
        api_client = APIClient(
            base_url=api_base_url,
            auth_manager=auth_manager.auth_manager
        )
        logger.info("Authentication system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize authentication: {e}", exc_info=True)
        auth_manager = None
        api_client = None
    
    with dpg.window(label="Gomoku Game", tag="main_window"):
        dpg.add_text("Gomoku Game with Authentication", color=(100, 150, 255))
        dpg.add_separator()
        
        # Authentication section
        dpg.add_text("Authentication:")
        dpg.add_text("Not logged in", tag="auth_status_text", color=(255, 100, 100))
        
        with dpg.group(horizontal=True):
            dpg.add_button(label="Login", tag="login_button", callback=show_login, width=80)
            dpg.add_button(label="Register", tag="register_button", callback=show_register, width=80)
            dpg.add_button(label="Logout", tag="logout_button", callback=logout, width=80, enabled=False)
        
        dpg.add_separator()
        
        # Game controls
        dpg.add_text("Game Controls:")
        with dpg.group(horizontal=True):
            dpg.add_button(label="New Game", tag="new_game_button", callback=create_new_game, enabled=False)
            dpg.add_button(label="My Games", tag="my_games_button", callback=show_my_games, enabled=False)
            dpg.add_button(label="Check Backend", callback=check_backend)
        
        dpg.add_text("Click on the board to make moves", color=(150, 150, 150))
        dpg.add_text("Status: Please login to play", tag="status_text")
        dpg.add_separator()
        
        # Game board - will be resized dynamically
        with dpg.drawlist(width=450, height=450, tag="board_drawing"):
            pass
        
        # Add click handlers
        with dpg.handler_registry():
            dpg.add_mouse_click_handler(callback=lambda s, a: handle_board_click())
    
    # Initial board draw
    draw_board()
    
    # Update UI to reflect initial auth state
    update_ui_auth_state()
    
    # Check backend on startup
    check_backend()
    
    logger.debug("Creating viewport...")
    dpg.create_viewport(title="Gomoku Game with Authentication", width=500, height=700)
    logger.debug("Setting up DearPyGUI...")
    dpg.setup_dearpygui()
    logger.debug("Showing viewport...")
    dpg.show_viewport()
    logger.debug("Setting primary window...")
    dpg.set_primary_window("main_window", True)
    
    logger.info("GUI initialized, entering main loop")
    
    # Main loop
    try:
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
    finally:
        # Cleanup authentication system
        if auth_manager:
            try:
                asyncio.run(auth_manager.close())
            except RuntimeError as e:
                if "event loop" in str(e).lower():
                    logger.debug("Skipping auth manager cleanup - event loop already closed")
                else:
                    logger.error(f"Error closing auth manager: {e}")
            except Exception as e:
                logger.error(f"Error closing auth manager: {e}")
        
        logger.info("GUI shutting down")
        dpg.destroy_context()


if __name__ == "__main__":
    main()