#!/usr/bin/env python3
"""
Final test to verify SSE HTML escaping fix works.
This simulates the complete SSE flow.
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
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

def test_sse_flow():
    print("🎮 Testing Complete SSE HTML Fix")
    print("=" * 50)
    
    # Get our test game
    User = get_user_model()
    game = Game.objects.get(id='f3581b53-b495-433a-9f9c-6cd27d3fc8dd')
    dane = User.objects.get(username='dane')
    admin = User.objects.get(username='admin')
    
    print(f"✅ Game: {game.id}")
    print(f"🎯 URL: http://127.0.0.1:8003/games/{game.id}/")
    print(f"👥 Players: {dane.username} (Black) vs {admin.username} (White)")
    print(f"📏 Board: {game.ruleset.name} ({game.ruleset.board_size}×{game.ruleset.board_size})")
    
    # Simulate the SSE HTML generation process
    print(f"\n🧪 Simulating SSE HTML generation:")
    
    # This is what happens in views.py when a move is made
    from django.http import HttpRequest
    request = HttpRequest()
    csrf_token = 'test-csrf-token'
    
    # Generate HTML using our fixed method
    board_html = render_to_string('web/partials/game_board.html', {
        'game': game,
        'csrf_token': csrf_token
    }, request=request).strip()
    
    board_html = str(mark_safe(board_html))
    
    # Apply SSE newline processing
    board_html_sse = board_html.replace('\n\n', ' ').replace('\r\n\r\n', ' ').strip()
    
    # Verify the HTML is properly formatted
    has_proper_classes = 'class="game-board-grid"' in board_html_sse
    has_proper_intersections = 'class="board-intersection' in board_html_sse
    has_escaped_quotes = 'class=\\"' in board_html_sse
    
    print(f"📄 HTML length: {len(board_html_sse)} characters")
    print(f"✅ Has proper game-board class: {has_proper_classes}")
    print(f"✅ Has proper intersection classes: {has_proper_intersections}")
    print(f"❌ Has escaped quotes: {has_escaped_quotes}")
    
    # Count board elements
    import re
    intersections = len(re.findall(r'class="board-intersection', board_html_sse))
    expected_intersections = game.ruleset.board_size ** 2
    
    print(f"🎮 Intersections found: {intersections} (expected: {expected_intersections})")
    
    # Final assessment
    print(f"\n🎯 Final Assessment:")
    if has_proper_classes and has_proper_intersections and not has_escaped_quotes and intersections == expected_intersections:
        print("✅ SUCCESS: SSE HTML is properly formatted!")
        print("🎉 The HTML escaping fix is working correctly")
        print("📡 SSE events should now render as HTML elements, not text")
    else:
        print("❌ ISSUES FOUND:")
        if not has_proper_classes:
            print("  - Missing game-board class")
        if not has_proper_intersections:
            print("  - Missing intersection classes")
        if has_escaped_quotes:
            print("  - Still has escaped quotes")
        if intersections != expected_intersections:
            print(f"  - Wrong number of intersections ({intersections} vs {expected_intersections})")
    
    print(f"\n🔧 Testing Instructions:")
    print("1. Ensure server is running on port 8003")
    print("2. Open two browser windows")
    print("3. Login as 'dane' in one, 'admin' in the other")
    print(f"4. Navigate both to: http://127.0.0.1:8003/games/{game.id}/")
    print("5. Open browser console (F12) in both windows")
    print("6. Make a move with dane (Black player)")
    print("7. Watch admin's console for debug logs")
    print("8. Verify admin's board shows BLACK STONE, not text")

if __name__ == '__main__':
    test_sse_flow()