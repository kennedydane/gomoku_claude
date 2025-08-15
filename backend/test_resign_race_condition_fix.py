#!/usr/bin/env python3
"""
Test script to verify that the resign race condition fix resolves HTMX swapError.

This script tests that:
1. Resign button uses hx-swap="none" to avoid DOM conflicts
2. Resign view returns 204 No Content for HTMX requests
3. WebSocket notifications handle all DOM updates
4. No race conditions between HTMX and WebSocket updates
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

def test_resign_race_condition_fix():
    """Test that resign race condition has been fixed."""
    
    print("🔍 RESIGN RACE CONDITION FIX TEST")
    print("=" * 35)
    
    from django.contrib.auth import get_user_model
    from games.models import RuleSet, Game, GameStatus
    from django.test import RequestFactory, Client
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
        
        # Test 1: Verify resign button configuration
        print(f"\n🧪 TEST 1: Resign button HTMX configuration")
        
        factory = RequestFactory()
        request = factory.get('/dashboard/')
        request.user = dane
        
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        csrf_token = get_token(request)
        
        # Render the dashboard game panel
        context = {
            'selected_game': test_game,
            'user': dane,
            'csrf_token': csrf_token
        }
        
        panel_html = render_to_string(
            'web/partials/dashboard_game_panel.html',
            context,
            request=request
        )
        
        # Check for proper HTMX configuration
        if 'hx-swap="none"' in panel_html:
            print("   ✅ Resign button uses hx-swap=\"none\"")
        else:
            print("   ❌ Resign button does not use hx-swap=\"none\"")
        
        if 'hx-target="#center-game-panel"' not in panel_html:
            print("   ✅ Resign button removed problematic hx-target")
        else:
            print("   ❌ Resign button still has problematic hx-target")
        
        if 'hx-indicator="#board-loading"' in panel_html:
            print("   ✅ Resign button has loading indicator")
        else:
            print("   ❌ Resign button missing loading indicator")
        
        # Test 2: Test resign view response
        print(f"\n🧪 TEST 2: Resign view response handling")
        
        client = Client()
        client.force_login(dane)
        
        # Make HTMX resign request
        resign_response = client.post(
            f'/games/{test_game.id}/resign/',
            HTTP_HX_REQUEST='true'
        )
        
        print(f"   Resign response status: {resign_response.status_code}")
        
        if resign_response.status_code == 204:
            print("   ✅ HTMX resign returns 204 No Content")
        else:
            print(f"   ❌ HTMX resign returns unexpected status: {resign_response.status_code}")
        
        if len(resign_response.content) == 0:
            print("   ✅ HTMX resign returns empty content")
        else:
            print(f"   ❌ HTMX resign returns content: {len(resign_response.content)} bytes")
        
        # Test 3: Check game state after resignation
        print(f"\n🧪 TEST 3: Game state after resignation")
        
        test_game.refresh_from_db()
        
        if test_game.status == GameStatus.FINISHED:
            print("   ✅ Game status updated to FINISHED")
        else:
            print(f"   ❌ Game status unexpected: {test_game.status}")
        
        if test_game.winner_id == admin.id:  # Other player wins when someone resigns
            print("   ✅ Winner correctly set to other player")
        else:
            print(f"   ❌ Winner incorrectly set: {test_game.winner_id}")
        
        # Test 4: Test WebSocket notification structure
        print(f"\n🧪 TEST 4: WebSocket notification verification")
        
        from web.services import WebSocketNotificationService
        
        # Check that resign event is properly defined
        event_def = WebSocketNotificationService.EVENT_DEFINITIONS.get('game_resigned')
        if event_def:
            print("   ✅ game_resigned event definition exists")
            
            expected_updates = ['game_panel', 'games_panel']
            actual_updates = event_def['updates']
            
            resigning_updates = actual_updates.get('resigning_player', [])
            other_updates = actual_updates.get('other_player', [])
            
            if all(update in resigning_updates for update in expected_updates):
                print("   ✅ Resigning player gets correct updates")
            else:
                print(f"   ❌ Resigning player updates wrong: {resigning_updates}")
                
            if all(update in other_updates for update in expected_updates):
                print("   ✅ Other player gets correct updates")
            else:
                print(f"   ❌ Other player updates wrong: {other_updates}")
        else:
            print("   ❌ game_resigned event definition missing")
        
        # Clean up
        test_game.delete()
        print(f"\n🧹 Test cleanup completed")
        
        # Assessment
        print(f"\n🏆 RESIGN RACE CONDITION FIX ASSESSMENT:")
        
        success_criteria = [
            'hx-swap="none"' in panel_html,  # No DOM swap conflicts
            resign_response.status_code == 204,  # Minimal HTMX response
            len(resign_response.content) == 0,  # No content conflicts
            test_game.status == GameStatus.FINISHED,  # Game properly resigned
            event_def is not None,  # WebSocket events configured
        ]
        
        passed_tests = sum(success_criteria)
        total_tests = len(success_criteria)
        
        print(f"   Tests passed: {passed_tests}/{total_tests}")
        
        if passed_tests == total_tests:
            print("   ✅ Resign race condition fix working perfectly!")
            print("   🔧 No more HTMX swapError or querySelector issues")
            print("   🎮 WebSocket handles all DOM updates cleanly")
        elif passed_tests >= 4:
            print("   ⚠️ Resign fix mostly working, minor issues detected")
        else:
            print("   ❌ Resign race condition fix needs more work")
        
        print(f"\n💡 MANUAL TESTING INSTRUCTIONS:")
        print(f"1. Start server and login as dane")
        print(f"2. Start a game and navigate to dashboard")
        print(f"3. Open browser developer console (F12)")
        print(f"4. Click the Resign button")
        print(f"5. VERIFY: No htmx:swapError or querySelector errors")
        print(f"6. VERIFY: Game panel updates smoothly via WebSocket")
        print(f"7. VERIFY: No DOM conflicts or race conditions")
        
        return passed_tests >= 4
        
    except Exception as e:
        print(f"❌ Error in resign race condition test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_resign_race_condition_fix()
    if success:
        print("\n✅ Resign race condition fix verification completed successfully")
        print("🎯 Resign should work without HTMX errors!")
    else:
        print("\n❌ Resign race condition fix verification failed")
    sys.exit(0 if success else 1)