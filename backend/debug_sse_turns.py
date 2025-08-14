#!/usr/bin/env python3
"""
Debug script for SSE turn validation issue
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

from games.models import Game, Player
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.http import HttpRequest
from django.middleware.csrf import get_token

User = get_user_model()

def debug_sse_turn_context():
    print("🔍 DEBUGGING SSE TURN CONTEXT ISSUE")
    print("=" * 50)
    
    try:
        # Get the test game and users
        game = Game.objects.get(id='0bedaa46-b7ff-4376-b758-1a7ffcc2fca1')
        dane = User.objects.get(username='dane')
        admin = User.objects.get(username='admin')
        
        print(f"Game: {game.id}")
        print(f"Current Player: {game.current_player} ({game.get_current_player_user().username})")
        print()
        
        # Create a mock request for CSRF token
        request = HttpRequest()
        csrf_token = get_token(request)
        
        # Simulate dane making the first move
        print("🎮 STEP 1: Dane (BLACK) makes first move")
        print("-" * 40)
        
        # Render board for dane (current player)
        board_html_dane = render_to_string('web/partials/game_board.html', {
            'game': game,
            'user': dane,
            'csrf_token': csrf_token,
            'wrapper_id': 'dashboard-game-board-wrapper'
        }, request=request)
        
        # Check if dane's board has clickable intersections
        clickable_count_dane = board_html_dane.count('hx-post')
        print(f"Dane's board: {clickable_count_dane} clickable intersections")
        
        # Render board for admin (not current player)
        board_html_admin = render_to_string('web/partials/game_board.html', {
            'game': game,
            'user': admin,
            'csrf_token': csrf_token,
            'wrapper_id': 'dashboard-game-board-wrapper'
        }, request=request)
        
        clickable_count_admin = board_html_admin.count('hx-post')
        print(f"Admin's board: {clickable_count_admin} clickable intersections")
        print()
        
        # Simulate the turn change after dane's move
        print("🔄 STEP 2: After dane's move, turn changes to admin")
        print("-" * 50)
        
        # Change turn to WHITE (admin)
        game.current_player = Player.WHITE
        game.save()
        
        print(f"New Current Player: {game.current_player} ({game.get_current_player_user().username})")
        print()
        
        # Now simulate SSE update - render board for both users with new game state
        print("📡 STEP 3: SSE sends updated board to both users")
        print("-" * 50)
        
        # Render for dane (now not current player)
        board_html_dane_after = render_to_string('web/partials/game_board.html', {
            'game': game,
            'user': dane,
            'csrf_token': csrf_token,
            'wrapper_id': 'dashboard-game-board-wrapper'
        }, request=request)
        
        clickable_count_dane_after = board_html_dane_after.count('hx-post')
        print(f"Dane's board after SSE: {clickable_count_dane_after} clickable intersections")
        print(f"  - Should be 0 (not dane's turn anymore): {'✅' if clickable_count_dane_after == 0 else '❌'}")
        
        # Render for admin (now current player)  
        board_html_admin_after = render_to_string('web/partials/game_board.html', {
            'game': game,
            'user': admin,
            'csrf_token': csrf_token,
            'wrapper_id': 'dashboard-game-board-wrapper'
        }, request=request)
        
        clickable_count_admin_after = board_html_admin_after.count('hx-post')
        print(f"Admin's board after SSE: {clickable_count_admin_after} clickable intersections")
        print(f"  - Should be 64 (admin's turn now): {'✅' if clickable_count_admin_after == 64 else '❌'}")
        print()
        
        # Check if the issue is in the SSE event sending logic
        print("🔍 STEP 4: Check SSE context logic")
        print("-" * 40)
        
        # This is what happens in the game_move view for each player
        for notify_user in [dane, admin]:
            print(f"\\nSSE for {notify_user.username}:")
            print(f"  notify_user: {notify_user.username} (ID: {notify_user.id})")
            print(f"  game.get_current_player_user(): {game.get_current_player_user().username}")
            print(f"  notify_user == game.get_current_player_user(): {notify_user == game.get_current_player_user()}")
            
            # Render board with correct context
            sse_board_html = render_to_string('web/partials/game_board.html', {
                'game': game,
                'user': notify_user,  # This is the key - each user gets their own context
                'csrf_token': csrf_token,
                'wrapper_id': 'dashboard-game-board-wrapper'
            }, request=request)
            
            sse_clickable_count = sse_board_html.count('hx-post')
            expected_clickable = 64 if notify_user == game.get_current_player_user() else 0
            print(f"  SSE board clickable count: {sse_clickable_count} (expected: {expected_clickable})")
            status = '✅' if sse_clickable_count == expected_clickable else '❌'
            print(f"  Status: {status}")
        
        # Reset the game state
        game.current_player = Player.BLACK
        game.save()
        print(f"\\n🔄 Reset game to original state: {game.current_player}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_sse_turn_context()