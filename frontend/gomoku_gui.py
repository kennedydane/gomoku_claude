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

# Game board state
board_state = [[None for _ in range(15)] for _ in range(15)]
current_player = "black"
game_id: Optional[str] = None
api_base_url = "http://localhost:8001"

# Authentication and API
auth_manager: Optional[AuthenticationManager] = None
api_client: Optional[APIClient] = None


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
    
    logger.debug(f"UI auth state updated: authenticated={is_authenticated}")

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


def draw_board():
    """Draw the game board."""
    logger.debug("Redrawing game board")
    dpg.delete_item("board_drawing", children_only=True)
    
    # Draw grid
    for i in range(16):
        # Vertical lines
        dpg.draw_line((i * 30, 0), (i * 30, 450), 
                     color=(100, 100, 100), parent="board_drawing")
        # Horizontal lines
        dpg.draw_line((0, i * 30), (450, i * 30), 
                     color=(100, 100, 100), parent="board_drawing")
    
    # Draw stones
    stone_count = 0
    for row in range(15):
        for col in range(15):
            if board_state[row][col]:
                stone_count += 1
                color = (20, 20, 20) if board_state[row][col] == "black" else (240, 240, 240)
                dpg.draw_circle((col * 30, row * 30), 12, 
                              color=color, fill=color, parent="board_drawing")
    
    logger.debug(f"Board drawn with {stone_count} stones")


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
            
            move = await api_client.post(f"/api/v1/games/{game_id}/moves/", json=payload)
            
            board_state[row][col] = current_player
            logger.info(f"Move successful: {current_player} at ({row}, {col})")
            
            # Switch players
            old_player = current_player
            current_player = "white" if current_player == "black" else "black"
            logger.debug(f"Switched turn from {old_player} to {current_player}")
            
            if move.get("is_winning_move"):
                winner_color = move['player_color'].lower()
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
            payload = {
                "black_player_id": current_user.id,
                "white_player_id": current_user.id,  # For now, single player against self
                "ruleset_id": 1
            }
            
            logger.debug(f"Creating game with payload: {payload}")
            
            game_data = await api_client.post("/api/v1/games/", json=payload)
            game_id = game_data["id"]
            logger.info(f"Game created successfully with ID: {game_id}")
            
            # Start the game
            start_response = await api_client.put(f"/api/v1/games/{game_id}/start")
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
        mouse_pos = dpg.get_mouse_pos(local=False)
        board_pos = dpg.get_item_pos("board_drawing")
        
        # Calculate relative position
        rel_x = mouse_pos[0] - board_pos[0]
        rel_y = mouse_pos[1] - board_pos[1]
        
        # Convert to grid coordinates
        col = round(rel_x / 30)
        row = round(rel_y / 30)
        
        logger.debug(f"Mouse click at screen ({mouse_pos[0]:.0f}, {mouse_pos[1]:.0f}), board ({rel_x:.0f}, {rel_y:.0f}), grid ({row}, {col})")
        
        if 0 <= row < 15 and 0 <= col < 15:
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
            dpg.add_button(label="Check Backend", callback=check_backend)
        
        dpg.add_text("Click on the board to make moves", color=(150, 150, 150))
        dpg.add_text("Status: Please login to play", tag="status_text")
        dpg.add_separator()
        
        # Game board
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