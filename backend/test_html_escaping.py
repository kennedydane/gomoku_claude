#!/usr/bin/env python3
"""
Test script to check HTML escaping in SSE data.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.http import HttpRequest
from games.models import Game

def test_html_escaping():
    print("🧪 Testing HTML Escaping in SSE Data")
    print("=" * 50)
    
    # Get our test game
    game = Game.objects.get(id='f3581b53-b495-433a-9f9c-6cd27d3fc8dd')
    print(f"🎮 Game: {game.id} ({game.ruleset.name})")
    
    # Create a mock request for CSRF token
    request = HttpRequest()
    csrf_token = 'test-csrf-token'
    
    # Test the current rendering method
    board_html = render_to_string('web/partials/game_board.html', {
        'game': game,
        'csrf_token': csrf_token
    }, request=request).strip()
    
    board_html = str(mark_safe(board_html))
    
    print(f"\n📄 Rendered HTML length: {len(board_html)} characters")
    
    # Look for the specific escaping issue mentioned in conversation
    print("\n🔍 Checking for escaping patterns:")
    
    # The issue was: <div class=\"game-board- instead of <div class="game-board-
    escaped_pattern = 'class=\\"game-board-'
    normal_pattern = 'class="game-board-'
    
    has_escaped = escaped_pattern in board_html
    has_normal = normal_pattern in board_html
    
    print(f"❌ Has escaped quotes (class=\\\"): {has_escaped}")
    print(f"✅ Has normal quotes (class=\"): {has_normal}")
    
    # Find the actual game-board class
    import re
    matches = re.findall(r'class="[^"]*game-board[^"]*"', board_html)
    if matches:
        print(f"\n🎯 Found game-board class: {matches[0]}")
    
    # Show snippet around game-board-grid
    snippet_start = board_html.find('game-board-grid')
    if snippet_start != -1:
        start = max(0, snippet_start - 30)
        end = min(len(board_html), snippet_start + 80)
        print(f"\n📋 Snippet: {repr(board_html[start:end])}")
    
    # Test what would be sent via SSE
    board_html_sse = board_html.replace('\n\n', ' ').replace('\r\n\r\n', ' ').strip()
    print(f"\n📡 SSE-processed length: {len(board_html_sse)} characters")
    
    # Check if this would render correctly in browser
    print(f"\n🎯 Assessment:")
    if has_normal and not has_escaped:
        print("✅ SUCCESS: HTML should render correctly in browser")
    elif has_escaped:
        print("❌ PROBLEM: HTML has escaped quotes that will render as text")
    else:
        print("⚠️  UNKNOWN: No game-board class found")

if __name__ == '__main__':
    test_html_escaping()