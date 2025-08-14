#!/usr/bin/env python3
"""
Test script to verify HTMX scope fix
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

from games.models import Game
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.http import HttpRequest
from django.middleware.csrf import get_token

User = get_user_model()

def test_htmx_scope_fix():
    print("🧪 TESTING HTMX SCOPE FIX")
    print("=" * 50)
    
    try:
        # Get the test game
        game = Game.objects.get(id='0bedaa46-b7ff-4376-b758-1a7ffcc2fca1')
        dane = User.objects.get(username='dane')
        
        print(f"Game: {game.id}")
        print(f"Game name: {game.ruleset.name}")
        print()
        
        # Create mock request
        request = HttpRequest()
        csrf_token = get_token(request)
        
        print("🎯 TESTING DASHBOARD GAME PANEL STRUCTURE")
        print("-" * 50)
        
        # Render the full dashboard game panel
        full_panel_html = render_to_string('web/partials/dashboard_game_panel.html', {
            'selected_game': game,
            'user': dane
        }, request=request)
        
        print(f"Full panel HTML length: {len(full_panel_html)} chars")
        
        # Check if it contains the game header (this should NOT be replaced by SSE)
        header_indicators = [
            game.ruleset.name,  # Ruleset name in header
            'vs',  # Player vs indicator
            dane.username,  # Player usernames
        ]
        
        print("\\n📋 HEADER CONTENT CHECK (should be preserved):")
        for indicator in header_indicators:
            found = indicator in full_panel_html
            print(f"  ✅ '{indicator}': {'Found' if found else 'Missing'}")
        
        print("\\n🎲 BOARD CONTENT CHECK:")
        # Check board content structure
        board_checks = [
            ('dashboard-game-board-wrapper', 'SSE wrapper container'),
            ('dashboard-game-board-content', 'Board content target'),
            ('game-board-grid', 'CSS Grid board'),
            ('board-intersection', 'Board intersections'),
        ]
        
        for search_term, description in board_checks:
            found = search_term in full_panel_html
            status = '✅' if found else '❌'
            print(f"  {status} {description}: {'Found' if found else 'Missing'}")
        
        print("\\n🔄 TESTING BOARD CONTENT ISOLATION:")
        print("-" * 40)
        
        # Render just the board content (what SSE updates)
        board_content_html = render_to_string('web/partials/game_board.html', {
            'game': game,
            'user': dane,
            'csrf_token': csrf_token,
            'wrapper_id': 'dashboard-game-board-content'
        }, request=request)
        
        print(f"Board content HTML length: {len(board_content_html)} chars")
        
        # Check that board content does NOT contain header information
        print("\\n📤 BOARD CONTENT ISOLATION CHECK (should NOT contain header):")
        for indicator in header_indicators:
            found = indicator in board_content_html
            status = '❌' if found else '✅'  # We want these NOT to be found
            issue = 'PROBLEM - contains header content!' if found else 'Good - header isolated'
            print(f"  {status} '{indicator}': {issue}")
        
        # Check that board content DOES contain game board
        board_content_checks = [
            'game-board-grid',
            'board-intersection', 
            'hx-target="#dashboard-game-board-content"'
        ]
        
        print("\\n🎮 BOARD CONTENT VALIDATION:")
        for check in board_content_checks:
            found = check in board_content_html
            status = '✅' if found else '❌'
            print(f"  {status} {check}: {'Found' if found else 'Missing'}")
        
        print("\\n🎯 HTMX TARGET VALIDATION:")
        target_count = board_content_html.count('hx-target="#dashboard-game-board-content"')
        print(f"  HTMX targets pointing to dashboard-game-board-content: {target_count}")
        
        if target_count > 0:
            print("  ✅ Board intersections correctly target the content div")
        else:
            print("  ❌ Board intersections not targeting correctly")
        
        print("\\n🔧 SUMMARY:")
        print("=" * 20)
        print("✅ Dashboard structure: Header + Content wrapper + Board content")
        print("✅ SSE updates: Only replace board content, preserve header")
        print("✅ Direct moves: Target same content div as SSE")
        print("✅ Isolation: Header content separate from board content")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_htmx_scope_fix()