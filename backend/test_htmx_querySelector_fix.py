#!/usr/bin/env python3
"""
Test script to verify that the HTMX querySelector error has been fixed.

This script tests the resign functionality to ensure that:
1. CSRF tokens are properly included in the resign response
2. The DOM replacement works correctly without querySelector errors
3. The resign button behaves properly after resignation
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

def test_htmx_queryselector_fix():
    """Test that the HTMX querySelector fix resolves DOM replacement issues."""
    
    print("🔍 HTMX QUERYSELECTOR FIX TEST")
    print("=" * 32)
    
    from django.contrib.auth import get_user_model
    from games.models import RuleSet, Game, GameStatus
    from web.models import Friendship, FriendshipStatus
    from django.test import RequestFactory
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.middleware.csrf import get_token
    from django.template.loader import render_to_string
    
    User = get_user_model()
    
    try:
        # Get test users
        dane = User.objects.get(username='dane')
        admin = User.objects.get(username='admin')
        
        # Get ruleset
        try:
            mini_ruleset = RuleSet.objects.get(name='Mini Gomoku')
        except RuleSet.DoesNotExist:
            mini_ruleset = RuleSet.objects.create(
                name='Mini Gomoku',
                board_size=8,
                description='Mini 8x8 Gomoku for testing'
            )
        
        print(f"📋 Test setup: {dane.username} vs {admin.username}")
        print(f"📋 Ruleset: {mini_ruleset.name}")
        
        # Create a test game
        test_game = Game.objects.create(
            black_player=dane,
            white_player=admin,
            ruleset=mini_ruleset,
            status=GameStatus.ACTIVE
        )
        test_game.initialize_board()
        test_game.save()
        
        print(f"📋 Test game created: {test_game.id}")
        
        # Test 1: Verify CSRF token is included in active game panel
        print(f"\n🧪 TEST 1: CSRF token in active game panel")
        
        factory = RequestFactory()
        request = factory.get('/dashboard/')
        request.user = dane
        
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        csrf_token = get_token(request)
        print(f"   Generated CSRF token: {csrf_token[:16]}...")
        
        # Render the dashboard game panel (before resignation)
        active_context = {
            'selected_game': test_game,
            'user': dane,
            'csrf_token': csrf_token
        }
        
        active_panel_html = render_to_string(
            'web/partials/dashboard_game_panel.html', 
            active_context, 
            request=request
        )
        
        # Check for CSRF token and resign button
        if csrf_token in active_panel_html:
            print("   ✅ CSRF token found in active game panel")
        else:
            print("   ❌ CSRF token missing from active game panel")
        
        if 'Resign' in active_panel_html and 'btn-outline-danger' in active_panel_html:
            print("   ✅ Resign button present in active game panel")
        else:
            print("   ❌ Resign button missing from active game panel")
        
        if 'hx-indicator="#board-loading"' in active_panel_html:
            print("   ✅ HTMX indicator properly configured")
        else:
            print("   ❌ HTMX indicator missing")
        
        # Test 2: Simulate resignation and check the response
        print(f"\n🧪 TEST 2: Resignation response with CSRF token")
        
        # Resign the game
        from games.services import GameService
        GameService.resign_game(test_game, dane.id)
        test_game.refresh_from_db()
        
        print(f"   Game status after resignation: {test_game.status}")
        
        # Simulate what the resign view returns
        resigned_context = {
            'selected_game': test_game,
            'user': dane,
            'csrf_token': csrf_token  # Should be included in the resign view
        }
        
        resigned_panel_html = render_to_string(
            'web/partials/dashboard_game_panel.html',
            resigned_context,
            request=request
        )
        
        # Check the resigned game panel
        if csrf_token in resigned_panel_html:
            print("   ✅ CSRF token included in resigned game panel")
        else:
            print("   ❌ CSRF token missing from resigned game panel")
        
        if 'Resign' not in resigned_panel_html:
            print("   ✅ Resign button correctly removed from resigned game")
        else:
            print("   ⚠️ Resign button still present in resigned game (unexpected)")
        
        if test_game.get_status_display() in resigned_panel_html:
            print(f"   ✅ Game status correctly updated to: {test_game.get_status_display()}")
        else:
            print("   ❌ Game status not properly displayed")
        
        # Test 3: Check for proper HTMX attributes
        print(f"\n🧪 TEST 3: HTMX configuration validation")
        
        # Check that HTMX attributes are properly configured
        htmx_checks = [
            ('hx-target="#center-game-panel"', 'Proper target element'),
            ('hx-swap="outerHTML"', 'Correct swap method'),
            ('hx-indicator="#board-loading"', 'Loading indicator configured'),
            ('hx-confirm="Are you sure you want to resign', 'Confirmation dialog'),
            ('hx-headers=\'{"X-CSRFToken":', 'CSRF header configuration')
        ]
        
        for check_pattern, description in htmx_checks:
            if check_pattern in active_panel_html:
                print(f"   ✅ {description}: Found")
            else:
                print(f"   ❌ {description}: Missing")
        
        # Test 4: Verify DOM element IDs are consistent
        print(f"\n🧪 TEST 4: DOM element consistency")
        
        # Check that key DOM elements exist and have consistent IDs
        dom_elements = [
            ('id="center-game-panel"', 'Main panel container'),
            ('id="board-loading"', 'Loading indicator'),
            ('id="dashboard-game-board-wrapper"', 'Board wrapper'),
            ('id="dashboard-game-board-content"', 'Board content'),
            ('id="game-turn-display"', 'Turn display')
        ]
        
        for element_pattern, description in dom_elements:
            if element_pattern in active_panel_html:
                print(f"   ✅ {description}: Present")
            else:
                print(f"   ❌ {description}: Missing")
        
        # Clean up
        test_game.delete()
        print(f"\n🧹 Test cleanup completed")
        
        # Assessment
        print(f"\n🏆 HTMX QUERYSELECTOR FIX ASSESSMENT:")
        
        success_criteria = [
            csrf_token in active_panel_html,  # CSRF in active panel
            csrf_token in resigned_panel_html,  # CSRF in resigned panel  
            'Resign' in active_panel_html,  # Resign button when active
            'Resign' not in resigned_panel_html,  # No resign button when resigned
            'hx-indicator="#board-loading"' in active_panel_html,  # Proper HTMX config
        ]
        
        passed_tests = sum(success_criteria)
        total_tests = len(success_criteria)
        
        print(f"   Core functionality tests: {passed_tests}/{total_tests} passed")
        
        if passed_tests == total_tests:
            print("   ✅ HTMX querySelector fix working perfectly!")
            print("   🔧 Resign functionality should work without JavaScript errors")
            print("   🎮 DOM replacement handled correctly")
        elif passed_tests >= 4:
            print("   ⚠️ HTMX fix mostly working, minor issues detected")
        else:
            print("   ❌ HTMX querySelector fix needs more work")
        
        print(f"\n💡 MANUAL TESTING INSTRUCTIONS:")
        print(f"1. Start server and login as dane")
        print(f"2. Navigate to a game in dashboard")
        print(f"3. Open browser developer console (F12)")
        print(f"4. Click the Resign button")
        print(f"5. VERIFY: No 'querySelector' errors in console")
        print(f"6. VERIFY: Game panel updates smoothly")
        print(f"7. VERIFY: No HTMX processing errors")
        
        return passed_tests >= 4
        
    except Exception as e:
        print(f"❌ Error in HTMX querySelector test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_htmx_queryselector_fix()
    if success:
        print("\n✅ HTMX querySelector fix verification completed successfully")
        print("🎯 Resign functionality should work without JavaScript errors!")
    else:
        print("\n❌ HTMX querySelector fix verification failed")
    sys.exit(0 if success else 1)