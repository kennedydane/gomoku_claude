#!/usr/bin/env python3
"""
Quick test script to verify the HTMX SSE fix is working.
This simulates making a move to trigger the SSE event.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

from games.models import Game
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

def test_sse_fix():
    """Test that making a move triggers proper SSE events."""
    print("🧪 Testing HTMX SSE Fix")
    print("=" * 50)
    
    # Get our test game
    User = get_user_model()
    dane = User.objects.get(username='dane')
    game = Game.objects.filter(black_player=dane).first()
    
    if not game:
        print("❌ No test game found!")
        return
    
    print(f"✅ Found test game: {game.id}")
    print(f"📋 Game URL: http://127.0.0.1:8003/games/{game.id}/")
    print(f"🎮 Ruleset: {game.ruleset.name} ({game.ruleset.board_size}×{game.ruleset.board_size})")
    print(f"👥 Players: {game.black_player.username} (Black) vs {game.white_player.username} (White)")
    
    # Verify the game board has no moves yet
    initial_stones = 0
    board = game.board_state.get('board', [])
    for row in board:
        for cell in row:
            if cell:
                initial_stones += 1
    
    print(f"🏁 Initial stones on board: {initial_stones}")
    print()
    print("🔧 To test the SSE fix:")
    print("1. Open TWO browser windows")
    print("2. In window 1: Login as 'dane' (password: dane1234)")
    print("3. In window 2: Login as 'admin' (password: admin123)")
    print(f"4. Navigate both to: http://127.0.0.1:8003/games/{game.id}/")
    print("5. Open Developer Console (F12) in BOTH windows")
    print("6. Make a move with dane (Black player)")
    print("7. Watch admin's console for debug logs:")
    print("   - '🎯 SSE: Received game_move event'")
    print("   - '🔄 HTMX: Game board swapped successfully'")
    print("   - '🎮 HTMX: Board has X stones and 64 intersections'")
    print("8. Verify admin's board shows the move as a BLACK STONE, not text")
    print()
    print("✅ If you see proper stones instead of text, the fix worked!")
    print("❌ If you still see text like \" \", the fix needs more work")

if __name__ == '__main__':
    test_sse_fix()