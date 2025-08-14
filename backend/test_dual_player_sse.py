#!/usr/bin/env python3
"""
Test script to verify dual-player SSE fix
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

from games.models import Game, Player
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()

def test_dual_player_sse():
    print("🧪 TESTING DUAL-PLAYER SSE FIX")
    print("=" * 50)
    
    try:
        # Get the test game
        game = Game.objects.get(id='0bedaa46-b7ff-4376-b758-1a7ffcc2fca1')
        dane = User.objects.get(username='dane')
        admin = User.objects.get(username='admin')
        
        print(f"Game: {game.id}")
        print(f"Initial state: {game.current_player} ({game.get_current_player_user().username})")
        print()
        
        # Create client and login as dane (current player)
        client = Client()
        client.login(username='dane', password='dane1234')
        
        # Make a move as dane
        print("🎮 Making move as dane (BLACK player)")
        print("-" * 40)
        
        move_response = client.post(
            reverse('web:game_move', kwargs={'game_id': game.id}),
            {'row': 4, 'col': 4},  # Center move
            HTTP_HX_REQUEST='true'  # Simulate HTMX request
        )
        
        print(f"Move response status: {move_response.status_code}")
        
        if move_response.status_code == 200:
            print("✅ Move successful!")
            
            # Refresh game state
            game.refresh_from_db()
            print(f"New game state: {game.current_player} ({game.get_current_player_user().username})")
            
            # Test that it's now admin's turn
            if game.current_player == Player.WHITE and game.get_current_player_user() == admin:
                print("✅ Turn correctly switched to admin")
            else:
                print("❌ Turn switch failed")
                
            # Test making a move as admin
            print()
            print("🎮 Testing admin's turn after SSE update")
            print("-" * 40)
            
            # Login as admin
            admin_client = Client()
            admin_client.login(username='admin', password='admin123')
            
            # Try to make a move as admin
            admin_move_response = admin_client.post(
                reverse('web:game_move', kwargs={'game_id': game.id}),
                {'row': 3, 'col': 3},  # Adjacent move
                HTTP_HX_REQUEST='true'
            )
            
            print(f"Admin move response status: {admin_move_response.status_code}")
            
            if admin_move_response.status_code == 200:
                print("✅ Admin can make moves after SSE update!")
                
                # Check final game state
                game.refresh_from_db()
                print(f"Final game state: {game.current_player} ({game.get_current_player_user().username})")
                
                if game.current_player == Player.BLACK:
                    print("✅ Turn correctly switched back to dane")
                    print("🎉 DUAL-PLAYER SSE FIX IS WORKING!")
                else:
                    print("❌ Final turn switch failed")
            else:
                print("❌ Admin cannot make moves - SSE fix may not be working")
                print(f"Response content: {admin_move_response.content[:200]}")
        else:
            print(f"❌ Initial move failed: {move_response.status_code}")
            print(f"Response content: {move_response.content[:200]}")
            
        # Check the board state
        print()
        print("📋 FINAL BOARD STATE:")
        print(f"  Board has moves: {bool(game.board_state and any(any(row) for row in game.board_state.board))}")
        if game.board_state and game.board_state.board:
            move_count = sum(1 for row in game.board_state.board for cell in row if cell)
            print(f"  Total moves made: {move_count}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_dual_player_sse()