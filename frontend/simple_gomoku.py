#!/usr/bin/env python3
"""Simplified Gomoku GUI that works."""

import asyncio
import httpx
import dearpygui.dearpygui as dpg
from typing import Optional, List

# Game board state
board_state = [[None for _ in range(15)] for _ in range(15)]
current_player = "black"
game_id: Optional[str] = None
black_player_id = 1
white_player_id = 2

def draw_board():
    """Draw the game board."""
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
    for row in range(15):
        for col in range(15):
            if board_state[row][col]:
                color = (20, 20, 20) if board_state[row][col] == "black" else (240, 240, 240)
                dpg.draw_circle((col * 30, row * 30), 12, 
                              color=color, fill=color, parent="board_drawing")

def cell_clicked(sender, app_data, user_data):
    """Handle cell click."""
    global current_player, game_id
    row, col = user_data
    
    if board_state[row][col] is not None:
        dpg.set_value("status_text", f"Position ({row}, {col}) is occupied!")
        return
    
    if not game_id:
        dpg.set_value("status_text", "Please create a game first!")
        return
    
    # Make the move via API
    player_id = black_player_id if current_player == "black" else white_player_id
    
    async def make_move():
        global current_player
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"http://localhost:8001/api/v1/games/{game_id}/moves/",
                    json={"player_id": player_id, "row": row, "col": col}
                )
                
                if response.status_code == 201:
                    move = response.json()
                    board_state[row][col] = current_player
                    
                    # Switch players
                    current_player = "white" if current_player == "black" else "black"
                    
                    if move.get("is_winning_move"):
                        winner_color = move['player_color'].lower()
                        dpg.set_value("status_text", f"{winner_color.title()} wins!")
                    else:
                        dpg.set_value("status_text", f"Move made at ({row}, {col}). {current_player.title()}'s turn.")
                    
                    draw_board()
                else:
                    error = response.json().get("detail", "Unknown error")
                    dpg.set_value("status_text", f"Error: {error}")
                    
            except Exception as e:
                dpg.set_value("status_text", f"Error: {e}")
    
    asyncio.run(make_move())

def create_new_game():
    """Create a new game."""
    global game_id, board_state, current_player
    
    async def create():
        global game_id, board_state, current_player
        async with httpx.AsyncClient() as client:
            try:
                # Create game
                response = await client.post(
                    "http://localhost:8001/api/v1/games/",
                    json={
                        "black_player_id": black_player_id,
                        "white_player_id": white_player_id,
                        "ruleset_id": 1
                    }
                )
                
                if response.status_code == 201:
                    game_data = response.json()
                    game_id = game_data["id"]
                    
                    # Start the game
                    response = await client.put(
                        f"http://localhost:8001/api/v1/games/{game_id}/start"
                    )
                    
                    if response.status_code == 200:
                        board_state = [[None for _ in range(15)] for _ in range(15)]
                        current_player = "black"
                        draw_board()
                        dpg.set_value("status_text", f"New game started! Game ID: {game_id[:8]}... Black's turn.")
                    else:
                        dpg.set_value("status_text", "Failed to start game")
                else:
                    dpg.set_value("status_text", "Failed to create game")
                    
            except Exception as e:
                dpg.set_value("status_text", f"Error creating game: {e}")
    
    asyncio.run(create())

# Create GUI
dpg.create_context()

with dpg.window(label="Simple Gomoku", tag="main_window"):
    dpg.add_text("Simple Gomoku Game")
    dpg.add_separator()
    
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
        mouse_pos = dpg.get_mouse_pos(local=False)
        board_pos = dpg.get_item_pos("board_drawing")
        
        # Calculate relative position
        rel_x = mouse_pos[0] - board_pos[0]
        rel_y = mouse_pos[1] - board_pos[1]
        
        # Convert to grid coordinates
        col = round(rel_x / 30)
        row = round(rel_y / 30)
        
        if 0 <= row < 15 and 0 <= col < 15:
            cell_clicked(None, None, (row, col))

# Initial board draw
draw_board()

dpg.create_viewport(title="Simple Gomoku", width=500, height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("main_window", True)

# Main loop
while dpg.is_dearpygui_running():
    dpg.render_dearpygui_frame()

dpg.destroy_context()