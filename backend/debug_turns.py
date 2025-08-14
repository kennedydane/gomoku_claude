#!/usr/bin/env python3
"""
Debug script for turn validation issue
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

from games.models import Game, Player
from django.contrib.auth import get_user_model

User = get_user_model()

def debug_turn_validation():
    print("🔍 DEBUGGING TURN VALIDATION ISSUE")
    print("=" * 50)
    
    try:
        # Get the test game
        game = Game.objects.get(id='0bedaa46-b7ff-4376-b758-1a7ffcc2fca1')
        dane = User.objects.get(username='dane')
        admin = User.objects.get(username='admin')
        
        print(f"Game ID: {game.id}")
        print(f"Status: {game.status}")
        print(f"Current Player (enum): {game.current_player}")
        print(f"Black Player: {game.black_player.username} (ID: {game.black_player.id})")
        print(f"White Player: {game.white_player.username} (ID: {game.white_player.id})")
        print()
        
        # Test get_current_player_user method
        current_user = game.get_current_player_user()
        print(f"get_current_player_user(): {current_user.username} (ID: {current_user.id})")
        print()
        
        # Test turn validation for both users
        dane_can_play = (dane == current_user)
        admin_can_play = (admin == current_user)
        
        print(f"Turn Validation Results:")
        print(f"  dane can play: {dane_can_play} (dane.id={dane.id} == current_user.id={current_user.id})")
        print(f"  admin can play: {admin_can_play} (admin.id={admin.id} == current_user.id={current_user.id})")
        print()
        
        # Test the exact template condition
        print("Template Conditions:")
        print(f"  game.status == 'ACTIVE': {game.status == 'ACTIVE'}")
        print(f"  dane == game.get_current_player_user(): {dane == game.get_current_player_user()}")
        print(f"  admin == game.get_current_player_user(): {admin == game.get_current_player_user()}")
        print()
        
        # Show what happens after a move
        print("🎮 SIMULATING MOVE AND TURN CHANGE:")
        original_current_player = game.current_player
        print(f"  Original current player: {original_current_player}")
        
        # Simulate turn change (don't actually make a move, just change the turn)
        if game.current_player == Player.BLACK:
            game.current_player = Player.WHITE
            print(f"  Changed to: {game.current_player}")
        else:
            game.current_player = Player.BLACK  
            print(f"  Changed to: {game.current_player}")
            
        # Test again after turn change
        new_current_user = game.get_current_player_user()
        print(f"  New current user: {new_current_user.username}")
        
        dane_can_play_after = (dane == new_current_user)
        admin_can_play_after = (admin == new_current_user)
        print(f"  dane can play after: {dane_can_play_after}")
        print(f"  admin can play after: {admin_can_play_after}")
        
        # Restore original state
        game.current_player = original_current_player
        print(f"  Restored to: {game.current_player}")
        
        # Test if there are any issues with User object comparison
        print()
        print("🔍 USER OBJECT COMPARISON TEST:")
        dane_fresh = User.objects.get(username='dane')
        admin_fresh = User.objects.get(username='admin')
        
        print(f"  dane == dane_fresh: {dane == dane_fresh}")
        print(f"  admin == admin_fresh: {admin == admin_fresh}")
        print(f"  dane.id == dane_fresh.id: {dane.id == dane_fresh.id}")
        print(f"  admin.id == admin_fresh.id: {admin.id == admin_fresh.id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_turn_validation()