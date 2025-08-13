#!/usr/bin/env python3
"""
Test script to verify SSE template rendering includes correct user context.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

from games.models import Game, RuleSet, GameStatus, Player
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.http import HttpRequest
from django.middleware.csrf import get_token

def test_sse_user_context():
    print("🧪 Testing SSE Template Rendering with User Context")
    print("=" * 60)
    
    User = get_user_model()
    
    # Get test users
    dane = User.objects.get(username='dane')
    admin = User.objects.get(username='admin')
    
    # Get Mini Gomoku ruleset
    mini_ruleset = RuleSet.objects.get(name='Mini Gomoku')
    
    # Create a test game - Dane's turn (BLACK)
    game = Game.objects.create(
        black_player=dane,
        white_player=admin,
        ruleset=mini_ruleset,
        status=GameStatus.ACTIVE,
        current_player=Player.BLACK  # Dane's turn
    )
    game.initialize_board()
    game.save()
    
    print(f"✅ Created test game: {str(game.id)[:8]}...")
    print(f"🎮 Black player: {game.black_player.username} (current turn)")
    print(f"🎮 White player: {game.white_player.username}")
    
    # Simulate the SSE rendering process when dane makes a move
    # This should render the board from admin's perspective
    request = HttpRequest()
    csrf_token = 'test-csrf-token'
    
    print(f"\n🔄 Simulating SSE rendering after dane's move:")
    print(f"📡 SSE will be sent to: {admin.username} (admin)")
    
    # After dane's move, it becomes admin's turn
    game.current_player = Player.WHITE
    game.save()
    
    # This is what happens in the SSE code
    notify_user = admin  # Admin will receive the SSE update
    
    board_html = render_to_string('web/partials/game_board.html', {
        'game': game,
        'user': notify_user,  # Admin's perspective
        'csrf_token': csrf_token
    }, request=request).strip()
    
    print(f"⏰ Turn switched to: {game.current_player} ({game.get_current_player_user().username})")
    
    # Count clickable intersections in the SSE-rendered HTML
    clickable_count = board_html.count('hx-post=')
    expected_count = game.ruleset.board_size ** 2  # All intersections (no moves made yet)
    
    print(f"\n📊 SSE Template Analysis:")
    print(f"🎯 Template rendered for user: {notify_user.username}")
    print(f"⏰ Current turn player: {game.get_current_player_user().username}")
    print(f"🔢 Clickable intersections found: {clickable_count}")
    print(f"🔢 Expected clickable intersections: {expected_count}")
    
    # Check if turn validation is working correctly
    user_is_current_player = notify_user == game.get_current_player_user()
    print(f"✅ User matches current player: {user_is_current_player}")
    
    # Verify the fix
    if user_is_current_player and clickable_count == expected_count:
        print(f"\n✅ SUCCESS: SSE template correctly renders clickable intersections!")
        print(f"🎉 Admin can now make moves after receiving SSE update")
        result = True
    elif not user_is_current_player and clickable_count == 0:
        print(f"\n✅ SUCCESS: SSE template correctly shows no clickable intersections")
        print(f"⏸️  User correctly cannot make moves when not their turn")
        result = True
    else:
        print(f"\n❌ FAILURE: SSE template rendering issue")
        print(f"Expected: {expected_count if user_is_current_player else 0} clickable intersections")
        print(f"Got: {clickable_count} clickable intersections")
        result = False
    
    # Test the opposite case - render from dane's perspective after turn switch
    print(f"\n🔄 Testing opposite case:")
    print(f"📡 Rendering board from dane's perspective (not his turn):")
    
    dane_board_html = render_to_string('web/partials/game_board.html', {
        'game': game,
        'user': dane,  # Dane's perspective 
        'csrf_token': csrf_token
    }, request=request).strip()
    
    dane_clickable_count = dane_board_html.count('hx-post=')
    print(f"🔢 Dane's clickable intersections: {dane_clickable_count} (should be 0)")
    
    if dane_clickable_count == 0:
        print(f"✅ SUCCESS: Dane correctly sees no clickable intersections")
    else:
        print(f"❌ FAILURE: Dane should not see clickable intersections")
        result = False
    
    # Clean up
    game.delete()
    print(f"\n🧹 Cleaned up test game")
    
    return result

if __name__ == '__main__':
    success = test_sse_user_context()
    if success:
        print(f"\n🎉 ALL TESTS PASSED: SSE turn validation fix is working!")
    else:
        print(f"\n❌ TESTS FAILED: SSE turn validation needs more work")