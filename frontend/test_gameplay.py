#!/usr/bin/env python3
"""Test the complete gameplay through the API."""

import asyncio
import httpx
from time import sleep


async def test_gameplay():
    """Test creating a game and making moves."""
    
    async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
        print("=== Testing Gomoku Gameplay ===\n")
        
        # 1. Create a game
        print("1. Creating a new game...")
        response = await client.post(
            "/api/v1/games/",
            json={
                "black_player_id": 1,
                "white_player_id": 2,
                "ruleset_id": 1
            }
        )
        
        if response.status_code != 201:
            print(f"Failed to create game: {response.text}")
            return
            
        game = response.json()
        game_id = game["id"]
        print(f"   Game created: {game_id}")
        print(f"   Status: {game['status']}")
        
        # 2. Start the game
        print("\n2. Starting the game...")
        response = await client.put(f"/api/v1/games/{game_id}/start")
        
        if response.status_code != 200:
            print(f"Failed to start game: {response.text}")
            return
            
        game = response.json()
        print(f"   Game started! Status: {game['status']}")
        
        # 3. Make some moves to demonstrate gameplay
        print("\n3. Making moves...")
        moves = [
            (1, 7, 7, "Black"),   # Black move 1
            (2, 8, 7, "White"),   # White move 1
            (1, 7, 8, "Black"),   # Black move 2
            (2, 8, 8, "White"),   # White move 2
            (1, 7, 9, "Black"),   # Black move 3
            (2, 8, 9, "White"),   # White move 3
            (1, 7, 10, "Black"),  # Black move 4
            (2, 9, 9, "White"),   # White move 4
            (1, 7, 11, "Black"),  # Black move 5 - WINNING MOVE!
        ]
        
        for i, (player_id, row, col, color) in enumerate(moves):
            print(f"\n   Move {i+1}: {color} at ({row}, {col})")
            
            response = await client.post(
                f"/api/v1/games/{game_id}/moves/",
                json={"player_id": player_id, "row": row, "col": col}
            )
            
            if response.status_code != 201:
                print(f"   Failed: {response.json().get('detail', 'Unknown error')}")
                break
                
            move = response.json()
            
            if move.get("is_winning_move"):
                print(f"   🎉 {color} WINS! Game Over!")
                break
            else:
                print(f"   Success! Next turn: {'White' if color == 'Black' else 'Black'}")
        
        # 4. Get final game state
        print("\n4. Final game state:")
        response = await client.get(f"/api/v1/games/{game_id}")
        game = response.json()
        
        print(f"   Status: {game['status']}")
        print(f"   Move count: {game['move_count']}")
        if game.get("winner"):
            print(f"   Winner: {game['winner']['display_name']}")
        
        # Show the board
        print("\n5. Final board position:")
        board = game["board_state"]["board"]
        print("     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4")
        for row_idx, row in enumerate(board[:15]):
            row_str = f"  {row_idx:2} "
            for cell in row[:15]:
                if cell == "black":
                    row_str += "● "
                elif cell == "white":
                    row_str += "○ "
                else:
                    row_str += ". "
            print(row_str)
        
        print("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_gameplay())