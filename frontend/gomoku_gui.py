#!/usr/bin/env python3
"""Gomoku GUI with comprehensive logging for debugging."""

import sys
import asyncio
import argparse
from typing import Optional
import httpx
import dearpygui.dearpygui as dpg
from loguru import logger

# Game board state
board_state = [[None for _ in range(15)] for _ in range(15)]
current_player = "black"
game_id: Optional[str] = None
black_player_id = 1
white_player_id = 2
api_base_url = "http://localhost:8001"


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
    
    # Make the move via API
    player_id = black_player_id if current_player == "black" else white_player_id
    logger.debug(f"Making move for player_id {player_id} ({current_player})")
    
    async def make_move():
        global current_player
        logger.debug(f"Sending move request to API: game_id={game_id}, player_id={player_id}, position=({row},{col})")
        
        async with httpx.AsyncClient() as client:
            try:
                url = f"{api_base_url}/api/v1/games/{game_id}/moves/"
                payload = {"player_id": player_id, "row": row, "col": col}
                
                logger.debug(f"POST {url}")
                logger.debug(f"Payload: {payload}")
                
                response = await client.post(url, json=payload)
                
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response body: {response.text}")
                
                if response.status_code == 201:
                    move = response.json()
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
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    msg = f"Error: {error_detail}"
                    logger.error(f"Move failed: {msg}")
                    logger.error(f"Full response: {response.text}")
                    dpg.set_value("status_text", msg)
                    
            except httpx.ConnectError as e:
                msg = f"Cannot connect to backend at {api_base_url}"
                logger.error(f"{msg}: {e}")
                dpg.set_value("status_text", msg)
            except Exception as e:
                msg = f"Error: {e}"
                logger.error(f"Unexpected error making move: {e}", exc_info=True)
                dpg.set_value("status_text", msg)
    
    asyncio.run(make_move())


def create_new_game():
    """Create a new game."""
    global game_id, board_state, current_player
    
    logger.info("Creating new game...")
    
    async def create():
        global game_id, board_state, current_player
        
        async with httpx.AsyncClient() as client:
            try:
                # First, check if backend is accessible
                logger.debug(f"Checking backend health at {api_base_url}")
                try:
                    health_response = await client.get(f"{api_base_url}/health")
                    logger.debug(f"Health check: {health_response.status_code}")
                except Exception as e:
                    logger.error(f"Backend health check failed: {e}")
                
                # Create game
                url = f"{api_base_url}/api/v1/games/"
                payload = {
                    "black_player_id": black_player_id,
                    "white_player_id": white_player_id,
                    "ruleset_id": 1
                }
                
                logger.debug(f"POST {url}")
                logger.debug(f"Payload: {payload}")
                
                response = await client.post(url, json=payload)
                
                logger.debug(f"Create game response status: {response.status_code}")
                logger.debug(f"Create game response body: {response.text}")
                
                if response.status_code == 201:
                    game_data = response.json()
                    game_id = game_data["id"]
                    logger.info(f"Game created successfully with ID: {game_id}")
                    
                    # Start the game
                    start_url = f"{api_base_url}/api/v1/games/{game_id}/start"
                    logger.debug(f"PUT {start_url}")
                    
                    response = await client.put(start_url)
                    
                    logger.debug(f"Start game response status: {response.status_code}")
                    logger.debug(f"Start game response body: {response.text}")
                    
                    if response.status_code == 200:
                        board_state = [[None for _ in range(15)] for _ in range(15)]
                        current_player = "black"
                        draw_board()
                        msg = f"New game started! Game ID: {game_id[:8]}... Black's turn."
                        logger.info(msg)
                        dpg.set_value("status_text", msg)
                    else:
                        error_detail = response.json().get("detail", "Unknown error")
                        msg = f"Failed to start game: {error_detail}"
                        logger.error(msg)
                        logger.error(f"Full response: {response.text}")
                        dpg.set_value("status_text", msg)
                else:
                    error_detail = response.json().get("detail", response.text)
                    msg = f"Failed to create game: {error_detail}"
                    logger.error(msg)
                    logger.error(f"Full response: {response.text}")
                    dpg.set_value("status_text", msg)
                    
            except httpx.ConnectError as e:
                msg = f"Cannot connect to backend at {api_base_url}"
                logger.error(f"{msg}: {e}")
                dpg.set_value("status_text", msg)
            except Exception as e:
                msg = f"Error creating game: {e}"
                logger.error(f"Unexpected error: {e}", exc_info=True)
                dpg.set_value("status_text", msg)
    
    asyncio.run(create())


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
    
    global api_base_url
    api_base_url = args.api_url
    
    # Setup logging
    setup_logging(args.debug)
    logger.info("Starting Gomoku GUI")
    logger.info(f"Backend API URL: {api_base_url}")
    
    # Create GUI
    dpg.create_context()
    
    with dpg.window(label="Gomoku Game", tag="main_window"):
        dpg.add_text("Gomoku Game with Logging")
        dpg.add_separator()
        
        with dpg.group(horizontal=True):
            dpg.add_button(label="New Game", callback=create_new_game)
            dpg.add_button(label="Check Backend", callback=check_backend)
        
        dpg.add_text("Click on the board to make moves", color=(150, 150, 150))
        dpg.add_text("Status: Ready", tag="status_text")
        dpg.add_separator()
        
        # Game board
        with dpg.drawlist(width=450, height=450, tag="board_drawing"):
            pass
        
        # Add click handlers
        with dpg.handler_registry():
            dpg.add_mouse_click_handler(callback=lambda s, a: handle_board_click())
    
    # Initial board draw
    draw_board()
    
    # Check backend on startup
    check_backend()
    
    dpg.create_viewport(title="Gomoku Game", width=500, height=600)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)
    
    logger.info("GUI initialized, entering main loop")
    
    # Main loop
    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()
    
    logger.info("GUI shutting down")
    dpg.destroy_context()


if __name__ == "__main__":
    main()