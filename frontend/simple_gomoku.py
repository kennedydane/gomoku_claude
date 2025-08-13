#!/usr/bin/env python3
"""Simplified Gomoku GUI that works."""

import asyncio
import httpx
import dearpygui.dearpygui as dpg
from typing import Optional, List
from loguru import logger
import sys

# Configure loguru for debug output
logger.remove()
logger.add(sys.stdout, level="DEBUG", format="{time} | {level} | {message}")
logger.add("gomoku_debug.log", level="DEBUG", rotation="10 MB")

# Game board state
board_state = [[None for _ in range(15)] for _ in range(15)]
current_player = "black"
game_id: Optional[str] = None
black_player_id = 1
white_player_id = 2
auth_token: Optional[str] = None

logger.info("Gomoku GUI initialized")
logger.debug(f"Player IDs - Black: {black_player_id}, White: {white_player_id}")

def draw_board():
    """Draw the game board."""
    logger.debug("Redrawing board")
    dpg.delete_item("board_drawing", children_only=True)
    
    # Draw grid (15x15 board = 14 spaces between lines)
    for i in range(15):
        # Vertical lines
        dpg.draw_line((i * 30 + 15, 15), (i * 30 + 15, 435), 
                     color=(100, 100, 100), parent="board_drawing")
        # Horizontal lines
        dpg.draw_line((15, i * 30 + 15), (435, i * 30 + 15), 
                     color=(100, 100, 100), parent="board_drawing")
    
    # Draw stones at intersections
    for row in range(15):
        for col in range(15):
            if board_state[row][col]:
                color = (20, 20, 20) if board_state[row][col] == "black" else (240, 240, 240)
                dpg.draw_circle((col * 30 + 15, row * 30 + 15), 12, 
                              color=color, fill=color, parent="board_drawing")

def cell_clicked(sender, app_data, user_data):
    """Handle cell click."""
    global current_player, game_id, auth_token
    row, col = user_data
    
    logger.debug(f"Cell clicked at ({row}, {col})")
    logger.debug(f"Current player: {current_player}, Game ID: {game_id}")
    
    if board_state[row][col] is not None:
        logger.warning(f"Position ({row}, {col}) is already occupied!")
        dpg.set_value("status_text", f"Position ({row}, {col}) is occupied!")
        return
    
    if not game_id:
        logger.error("No active game - cannot make move")
        dpg.set_value("status_text", "Please create a game first!")
        return
        
    if not auth_token:
        logger.error("Not authenticated - cannot make move")
        dpg.set_value("status_text", "Please login first!")
        return
    
    # Make the move via API
    player_id = black_player_id if current_player == "black" else white_player_id
    
    async def make_move():
        global current_player
        logger.info(f"Making move: player={current_player}, position=({row}, {col}), game_id={game_id}")
        
        headers = {"Authorization": f"Token {auth_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                url = f"http://localhost:8001/api/v1/games/{game_id}/move/"
                payload = {"row": row, "col": col}
                logger.debug(f"POST {url} with payload: {payload}")
                logger.debug(f"Headers: {headers}")
                
                response = await client.post(url, json=payload, headers=headers)
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                
                response_text = response.text
                logger.debug(f"Response body: {response_text}")
                
                if response.status_code == 200:
                    move = response.json()
                    logger.info(f"Move successful: {move}")
                    board_state[row][col] = current_player
                    
                    # Switch players
                    current_player = "white" if current_player == "black" else "black"
                    logger.debug(f"Switched to player: {current_player}")
                    
                    if move.get("is_winning_move"):
                        winner_color = move['player_color'].lower()
                        logger.info(f"Game won by {winner_color}!")
                        dpg.set_value("status_text", f"{winner_color.title()} wins!")
                    else:
                        dpg.set_value("status_text", f"Move made at ({row}, {col}). {current_player.title()}'s turn.")
                    
                    draw_board()
                else:
                    logger.error(f"API error - Status: {response.status_code}")
                    try:
                        error_data = response.json()
                        logger.error(f"Error details: {error_data}")
                        error = error_data.get("detail", error_data.get("error", "Unknown error"))
                    except:
                        logger.error("Failed to parse error response as JSON")
                        error = f"HTTP {response.status_code}: {response_text[:200]}"
                    
                    dpg.set_value("status_text", f"Error: {error}")
                    
            except httpx.ConnectError as e:
                logger.error(f"Connection error: {e}")
                dpg.set_value("status_text", f"Connection Error: {e}")
            except httpx.TimeoutException as e:
                logger.error(f"Timeout error: {e}")
                dpg.set_value("status_text", f"Timeout Error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error: {type(e).__name__}: {e}")
                dpg.set_value("status_text", f"Error: {type(e).__name__}: {e}")
    
    asyncio.run(make_move())

def login_user():
    """Login user and get auth token."""
    global auth_token
    
    async def authenticate():
        global auth_token
        logger.info("Logging in user...")
        
        async with httpx.AsyncClient() as client:
            try:
                # For demo purposes, login as admin user
                auth_payload = {
                    "username": "admin",
                    "password": "admin123"
                }
                url = "http://localhost:8001/api/v1/auth/token/"
                logger.debug(f"Auth request to {url}")
                
                response = await client.post(url, json=auth_payload)
                logger.debug(f"Auth response status: {response.status_code}")
                
                if response.status_code == 200:
                    token_data = response.json()
                    auth_token = token_data["token"]
                    logger.info(f"Authentication successful, token: {auth_token[:10]}...")
                    dpg.set_value("status_text", "Login successful!")
                else:
                    error_data = response.json() if response.text else {"error": "Unknown error"}
                    logger.error(f"Authentication failed: {error_data}")
                    dpg.set_value("status_text", f"Login failed: {error_data.get('error', 'Unknown')}")
                    
            except Exception as e:
                logger.error(f"Login error: {e}")
                dpg.set_value("status_text", f"Login error: {e}")
    
    asyncio.run(authenticate())

def create_new_game():
    """Create a new game."""
    global game_id, board_state, current_player, auth_token
    
    if not auth_token:
        logger.warning("Not authenticated! Please login first.")
        dpg.set_value("status_text", "Not authenticated! Login first.")
        return
    
    async def create():
        global game_id, board_state, current_player
        logger.info("Creating new game...")
        
        headers = {"Authorization": f"Token {auth_token}"}
        
        async with httpx.AsyncClient() as client:
            try:
                # Create game
                create_payload = {
                    "black_player_id": black_player_id,
                    "white_player_id": white_player_id,
                    "ruleset_id": 1
                }
                logger.debug(f"Creating game with payload: {create_payload}")
                
                response = await client.post(
                    "http://localhost:8001/api/v1/games/",
                    json=create_payload,
                    headers=headers
                )
                
                logger.debug(f"Create game response status: {response.status_code}")
                logger.debug(f"Create game response: {response.text}")
                
                if response.status_code == 201:
                    game_data = response.json()
                    game_id = game_data["id"]
                    logger.info(f"Game created successfully with ID: {game_id}")
                    
                    # Start the game
                    start_url = f"http://localhost:8001/api/v1/games/{game_id}/start/"
                    logger.debug(f"Starting game at: {start_url}")
                    
                    response = await client.post(start_url, headers=headers)
                    logger.debug(f"Start game response status: {response.status_code}")
                    logger.debug(f"Start game response: {response.text}")
                    
                    if response.status_code == 200:
                        board_state = [[None for _ in range(15)] for _ in range(15)]
                        current_player = "black"
                        logger.info("Game started successfully")
                        draw_board()
                        dpg.set_value("status_text", f"New game started! Game ID: {game_id[:8]}... Black's turn.")
                    else:
                        logger.error(f"Failed to start game - Status: {response.status_code}")
                        try:
                            error_data = response.json()
                            logger.error(f"Start game error details: {error_data}")
                        except:
                            pass
                        dpg.set_value("status_text", f"Failed to start game (HTTP {response.status_code})")
                else:
                    logger.error(f"Failed to create game - Status: {response.status_code}")
                    try:
                        error_data = response.json()
                        logger.error(f"Create game error details: {error_data}")
                    except:
                        pass
                    dpg.set_value("status_text", f"Failed to create game (HTTP {response.status_code})")
                    
            except httpx.ConnectError as e:
                logger.error(f"Connection error during game creation: {e}")
                dpg.set_value("status_text", f"Connection error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during game creation: {type(e).__name__}: {e}")
                dpg.set_value("status_text", f"Error creating game: {type(e).__name__}: {e}")
    
    asyncio.run(create())

# Create GUI
dpg.create_context()

with dpg.window(label="Simple Gomoku", tag="main_window"):
    dpg.add_text("Simple Gomoku Game")
    dpg.add_separator()
    
    dpg.add_button(label="Login", callback=login_user)
    dpg.add_button(label="New Game", callback=create_new_game)
    dpg.add_text("Click on the board to make moves", color=(150, 150, 150))
    dpg.add_text("Status: Ready", tag="status_text")
    dpg.add_separator()
    
    # Game board
    with dpg.drawlist(width=450, height=450, tag="board_drawing"):
        pass
    
    # Add click handlers
    with dpg.handler_registry():
        dpg.add_mouse_click_handler(callback=lambda s, a: handle_board_click())

def handle_board_click():
    """Handle clicks on the board."""
    if dpg.is_item_hovered("board_drawing"):
        # Get drawing position relative to window
        draw_mouse_pos = dpg.get_drawing_mouse_pos()
        
        # Convert to grid coordinates (offset by 15 pixels for border)
        col = round((draw_mouse_pos[0] - 15) / 30)
        row = round((draw_mouse_pos[1] - 15) / 30)
        
        if 0 <= row < 15 and 0 <= col < 15:
            cell_clicked(None, None, (row, col))

# Initial board draw
draw_board()

dpg.create_viewport(title="Simple Gomoku", width=500, height=600)
dpg.setup_dearpygui()
logger.info("Starting Gomoku GUI application")
dpg.show_viewport()
dpg.set_primary_window("main_window", True)

logger.info("Entering main GUI loop")
# Main loop
while dpg.is_dearpygui_running():
    dpg.render_dearpygui_frame()

logger.info("GUI loop ended, cleaning up")
dpg.destroy_context()