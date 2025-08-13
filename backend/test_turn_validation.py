#!/usr/bin/env python3
"""
Test script to verify turn validation in the web interface.
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

def test_turn_validation():
    print("🧪 Testing Turn Validation in Web Interface")
    print("=" * 50)
    
    User = get_user_model()
    
    # Get test users
    dane = User.objects.get(username='dane')
    admin = User.objects.get(username='admin')
    
    # Get Mini Gomoku ruleset
    mini_ruleset = RuleSet.objects.get(name='Mini Gomoku')
    
    # Create a test game
    game = Game.objects.create(
        black_player=dane,
        white_player=admin,
        ruleset=mini_ruleset,
        status=GameStatus.ACTIVE,
        current_player=Player.BLACK  # Dane's turn (BLACK)
    )
    game.initialize_board()
    game.save()
    
    print(f"✅ Created test game: {game.id}")
    print(f"🎮 Black player: {game.black_player.username} (dane)")
    print(f"🎮 White player: {game.white_player.username} (admin)")
    print(f"⏰ Current turn: {game.current_player} ({game.get_current_player_user().username})")
    
    # Test template rendering for both players
    request = HttpRequest()
    
    print(f"\n🔍 Testing template rendering:")
    
    # Test 1: Dane's perspective (should see clickable intersections)
    dane_html = render_to_string('web/partials/game_board.html', {
        'game': game,
        'user': dane,
        'csrf_token': 'test-token'
    }, request=request)
    
    dane_clickable_count = dane_html.count('hx-post=')
    print(f"🎯 Dane (BLACK, current turn): {dane_clickable_count} clickable intersections")
    
    # Test 2: Admin's perspective (should see NO clickable intersections)
    admin_html = render_to_string('web/partials/game_board.html', {
        'game': game,
        'user': admin,
        'csrf_token': 'test-token'
    }, request=request)
    
    admin_clickable_count = admin_html.count('hx-post=')
    print(f"⏸️  Admin (WHITE, not turn): {admin_clickable_count} clickable intersections")
    
    # Test 3: Switch turns and test again
    game.current_player = Player.WHITE
    game.save()
    print(f"\n🔄 Switched turn to: {game.current_player} ({game.get_current_player_user().username})")
    
    # Test 4: Dane's perspective after turn switch (should see NO clickable intersections)
    dane_html_after = render_to_string('web/partials/game_board.html', {
        'game': game,
        'user': dane,
        'csrf_token': 'test-token'
    }, request=request)
    
    dane_clickable_after = dane_html_after.count('hx-post=')
    print(f"⏸️  Dane (BLACK, not turn): {dane_clickable_after} clickable intersections")
    
    # Test 5: Admin's perspective after turn switch (should see clickable intersections)
    admin_html_after = render_to_string('web/partials/game_board.html', {
        'game': game,
        'user': admin,
        'csrf_token': 'test-token'
    }, request=request)
    
    admin_clickable_after = admin_html_after.count('hx-post=')
    print(f"🎯 Admin (WHITE, current turn): {admin_clickable_after} clickable intersections")
    
    # Verify results
    expected_intersections = game.ruleset.board_size ** 2  # All empty intersections
    
    print(f"\n📊 Results Summary:")
    print(f"Expected clickable intersections (for current player): {expected_intersections}")
    print(f"Expected clickable intersections (for other player): 0")
    
    success = (
        dane_clickable_count == expected_intersections and
        admin_clickable_count == 0 and
        dane_clickable_after == 0 and
        admin_clickable_after == expected_intersections
    )
    
    if success:
        print(f"\n✅ SUCCESS: Turn validation working correctly!")
        print(f"🎉 Only the current player sees clickable intersections")
        print(f"🚫 Other player cannot click to make moves")
    else:
        print(f"\n❌ FAILURE: Turn validation not working correctly")
        print(f"Expected pattern: current_player={expected_intersections}, other_player=0")
        
    # Clean up
    game.delete()
    print(f"\n🧹 Cleaned up test game")
    
    return success

if __name__ == '__main__':
    test_turn_validation()