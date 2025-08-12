#!/usr/bin/env python3
"""Test win detection in the backend."""

import asyncio
import httpx

async def test_win_detection():
    """Test if the backend properly detects wins."""
    
    async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
        print("=== Testing Win Detection ===\n")
        
        # 1. Create a game
        print("Creating game...")
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
        print(f"Game created: {game_id}")
        
        # 2. Start the game
        print("Starting game...")
        response = await client.put(f"/api/v1/games/{game_id}/start")
        
        if response.status_code != 200:
            print(f"Failed to start game: {response.text}")
            return
            
        # 3. Make moves to create a win for black (horizontal)
        print("\nMaking moves to test win detection...")
        moves = [
            (1, 7, 7),   # Black
            (2, 8, 7),   # White
            (1, 7, 8),   # Black
            (2, 8, 8),   # White
            (1, 7, 9),   # Black
            (2, 8, 9),   # White
            (1, 7, 10),  # Black
            (2, 9, 9),   # White
            (1, 7, 11),  # Black - SHOULD BE WINNING MOVE!
        ]
        
        for i, (player_id, row, col) in enumerate(moves):
            color = "Black" if player_id == 1 else "White"
            print(f"\nMove {i+1}: {color} at ({row}, {col})")
            
            response = await client.post(
                f"/api/v1/games/{game_id}/moves/",
                json={"player_id": player_id, "row": row, "col": col}
            )
            
            if response.status_code != 201:
                print(f"Failed: {response.json().get('detail', 'Unknown error')}")
                break
                
            move = response.json()
            print(f"Response: {move}")
            
            if move.get("is_winning_move"):
                print(f"\n🎉 WIN DETECTED! {color} wins!")
                print(f"Winning move details: {move}")
                break
            else:
                print(f"is_winning_move: {move.get('is_winning_move', 'NOT IN RESPONSE')}")
        
        # 4. Check final game state
        print("\n\nFinal game state:")
        response = await client.get(f"/api/v1/games/{game_id}")
        game = response.json()
        
        print(f"Status: {game['status']}")
        print(f"Winner: {game.get('winner')}")
        
        print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_win_detection())