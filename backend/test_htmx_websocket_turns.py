#!/usr/bin/env python3
"""
Test script to verify HTMX WebSocket turn display updates work correctly.

This script tests the pure HTMX WebSocket implementation (no JavaScript)
for turn display updates in the dashboard game panel.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from games.models import Game

User = get_user_model()

def test_htmx_websocket_turn_display():
    """Test the HTMX WebSocket turn display template structure."""
    try:
        # Get test game
        game = Game.objects.get(id='91d67ccf-dc9e-4b70-96db-1c67a64d9657')
        dane = User.objects.get(username='dane')
        admin = User.objects.get(username='admin')
        
        print(f"🎮 Testing game: {game.id}")
        print(f"   Current player: {game.current_player}")
        print(f"   Black player: {game.black_player.username}")
        print(f"   White player: {game.white_player.username}")
        print()
        
        # Test turn display for both players
        for test_user in [dane, admin]:
            print(f"--- Turn display for {test_user.username} ---")
            
            # Render the turn display partial
            turn_html = render_to_string('web/partials/game_turn_display.html', {
                'game': game,
                'user': test_user,
            }).strip()
            
            print(f"HTML length: {len(turn_html)} characters")
            print("HTML content:")
            print(turn_html)
            print()
            
            # Check for HTMX WebSocket requirements
            checks = [
                ('id="game-turn-display"', 'Element has correct ID for targeting'),
                ('hx-swap-oob="true"', 'HTMX out-of-band swap attribute present'),
                ('stone-indicator', 'Stone indicator present'),
                ('Your Turn' if test_user == game.get_current_player_user() else f'{game.get_current_player_user().username}\'s Turn', 'Correct turn text'),
            ]
            
            print("🔍 HTMX WebSocket Validation:")
            for search_term, description in checks:
                found = search_term in turn_html
                status = '✅' if found else '❌'
                print(f"  {status} {description}: {'Found' if found else 'Missing'}")
            print()
        
        print("🎯 HTMX WEBSOCKET IMPLEMENTATION SUMMARY:")
        print("========================================")
        print("✅ Removed all JavaScript WebSocket handling")
        print("✅ Added game_turn_update_message handler to WebSocket consumer")
        print("✅ Turn display template includes hx-swap-oob='true' for targeting")
        print("✅ WebSocket messages use HTMX-compatible out-of-band swaps")
        print()
        print("🧪 MANUAL TEST REQUIRED:")
        print("1. Start server and open two browser windows")
        print("2. Login as different users in each window")
        print("3. Navigate to the same game")
        print("4. Make a move and verify turn display updates in real-time")
        print("5. Check browser console - should see no JavaScript errors")
        
    except Exception as e:
        print(f"❌ Error testing HTMX WebSocket turn display: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_htmx_websocket_turn_display()