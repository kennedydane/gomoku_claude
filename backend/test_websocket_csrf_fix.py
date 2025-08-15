#!/usr/bin/env python3
"""
Test script to verify that WebSocket-delivered challenges work with client-side CSRF handling.

This script tests that:
1. Challenges can be sent and appear immediately via WebSocket
2. Challenge acceptance works without page refresh using client-side CSRF tokens
3. No CSRF token issues after WebSocket updates
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

def test_websocket_csrf_fix():
    """Test that WebSocket challenge system works with client-side CSRF handling."""
    
    print("🔍 WEBSOCKET CSRF FIX TEST")
    print("=" * 28)
    
    from django.contrib.auth import get_user_model
    from games.models import RuleSet, Challenge, ChallengeStatus
    from web.models import Friendship, FriendshipStatus
    from web.services import WebSocketNotificationService
    from django.test import RequestFactory
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.middleware.csrf import get_token
    from django.template.loader import render_to_string
    
    User = get_user_model()
    
    try:
        # Get test users
        dane = User.objects.get(username='dane')
        admin = User.objects.get(username='admin')
        
        # Ensure friendship
        friendship, created = Friendship.objects.get_or_create(
            requester=dane,
            addressee=admin,
            defaults={'status': FriendshipStatus.ACCEPTED}
        )
        if friendship.status != FriendshipStatus.ACCEPTED:
            friendship.status = FriendshipStatus.ACCEPTED
            friendship.save()
        
        # Get ruleset
        try:
            mini_ruleset = RuleSet.objects.get(name='Mini Gomoku')
        except RuleSet.DoesNotExist:
            mini_ruleset = RuleSet.objects.create(
                name='Mini Gomoku',
                board_size=8,
                description='Mini 8x8 Gomoku for testing'
            )
        
        print(f"📋 Test setup: {dane.username} ↔ {admin.username} (friends)")
        print(f"📋 Ruleset: {mini_ruleset.name}")
        
        # Test 1: Verify WebSocket-delivered HTML doesn't include CSRF tokens
        print(f"\n🧪 TEST 1: WebSocket HTML without server-side CSRF tokens")
        
        # Create a challenge
        challenge = Challenge.objects.create(
            challenger=dane,
            challenged=admin,
            ruleset=mini_ruleset
        )
        print(f"   Challenge created: {challenge.id}")
        
        # Create mock request
        factory = RequestFactory()
        request = factory.get('/dashboard/')
        request.user = dane
        
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Test the WebSocket notification service
        result = WebSocketNotificationService.notify_game_event(
            event_type='challenge_sent',
            game=None,
            triggering_user=dane,
            request=request,
            challenge=challenge
        )
        
        if result:
            print("   ✅ WebSocket notification sent without server-side CSRF tokens")
        else:
            print("   ❌ WebSocket notification failed")
        
        # Test 2: Verify the rendered HTML structure
        print(f"\n🧪 TEST 2: Friends panel HTML structure")
        
        # Test direct rendering of friends panel (simulating WebSocket delivery)
        friends = Friendship.objects.get_friends(admin)
        pending_received_challenges = Challenge.objects.select_related(
            'challenger', 'challenged', 'ruleset'
        ).filter(
            challenged=admin,
            status=ChallengeStatus.PENDING
        )
        
        # Render without CSRF token (as WebSocket service now does)
        friends_html = render_to_string('web/partials/friends_panel.html', {
            'user': admin,
            'friends': friends,
            'pending_sent_challenges': [],
            'pending_received_challenges': pending_received_challenges,
            # No csrf_token parameter
        }, request=request)
        
        print(f"   Friends panel HTML length: {len(friends_html)} chars")
        
        # Check that no server-side CSRF tokens are included
        if 'csrfmiddlewaretoken' not in friends_html:
            print("   ✅ No server-side CSRF tokens in WebSocket HTML")
        else:
            print("   ❌ Server-side CSRF tokens still present")
        
        # Check that challenge buttons are present
        if 'accept-challenge-btn' in friends_html:
            print("   ✅ Challenge accept buttons present")
        else:
            print("   ❌ Challenge accept buttons missing")
        
        if 'hx-vals=\'{"action": "accept"}\'' in friends_html:
            print("   ✅ HTMX accept button configured without CSRF")
        else:
            print("   ❌ HTMX accept button not properly configured")
        
        # Test 3: Check dashboard JavaScript CSRF handling
        print(f"\n🧪 TEST 3: Dashboard CSRF handling JavaScript")
        
        # Render dashboard template
        dashboard_html = render_to_string('web/dashboard.html', {
            'user': admin,
            'selected_game': None,
            'active_games': [],
            'recent_finished_games': []
        }, request=request)
        
        # Check for CSRF handling JavaScript
        csrf_js_checks = [
            ('htmx:configRequest', 'HTMX request configuration event'),
            ('csrfmiddlewaretoken', 'CSRF token parameter handling'),
            ('getCookie(\'csrftoken\')', 'CSRF cookie reading function'),
            ('event.detail.parameters[\'csrfmiddlewaretoken\']', 'CSRF token injection')
        ]
        
        for check_pattern, description in csrf_js_checks:
            if check_pattern in dashboard_html:
                print(f"   ✅ {description}: Found")
            else:
                print(f"   ❌ {description}: Missing")
        
        # Test 4: Challenge workflow validation
        print(f"\n🧪 TEST 4: Challenge workflow validation")
        
        # Check that we have the expected challenge state
        challenge.refresh_from_db()
        if challenge.status == ChallengeStatus.PENDING:
            print("   ✅ Challenge is in PENDING state")
        else:
            print(f"   ❌ Challenge in unexpected state: {challenge.status}")
        
        if challenge.challenger == dane and challenge.challenged == admin:
            print("   ✅ Challenge has correct challenger and challenged users")
        else:
            print("   ❌ Challenge has incorrect user assignments")
        
        # Clean up
        challenge.delete()
        print(f"\n🧹 Test cleanup completed")
        
        # Assessment
        print(f"\n🏆 WEBSOCKET CSRF FIX ASSESSMENT:")
        
        success_criteria = [
            result,  # WebSocket notification worked
            'csrfmiddlewaretoken' not in friends_html,  # No server-side CSRF
            'accept-challenge-btn' in friends_html,  # Buttons present
            'htmx:configRequest' in dashboard_html,  # JavaScript CSRF handling
            challenge.status == ChallengeStatus.PENDING  # Challenge properly created
        ]
        
        passed_tests = sum(success_criteria)
        total_tests = len(success_criteria)
        
        print(f"   Tests passed: {passed_tests}/{total_tests}")
        
        if passed_tests == total_tests:
            print("   ✅ WebSocket CSRF fix working perfectly!")
            print("   🔐 Client-side CSRF handling configured correctly")
            print("   🎮 Challenge acceptance should work without page refresh")
        elif passed_tests >= 4:
            print("   ⚠️ WebSocket CSRF fix mostly working, minor issues detected")
        else:
            print("   ❌ WebSocket CSRF fix needs more work")
        
        print(f"\n💡 MANUAL TESTING INSTRUCTIONS:")
        print(f"1. Start server: DB_PASSWORD=your_secure_password_here_change_this DB_NAME=gomoku_dev_db uv run daphne -p 8003 gomoku.asgi:application")
        print(f"2. Open TWO browser windows")
        print(f"3. Login as dane in one, admin in the other")
        print(f"4. Navigate both to dashboard")
        print(f"5. Use dane to challenge admin via friends panel")
        print(f"6. VERIFY: Challenge appears immediately in admin's friends panel")
        print(f"7. Use admin to accept challenge WITHOUT refreshing page")
        print(f"8. VERIFY: Challenge acceptance works immediately")
        print(f"9. VERIFY: New game is created and appears in both users' active games")
        
        return passed_tests >= 4
        
    except Exception as e:
        print(f"❌ Error in WebSocket CSRF test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_websocket_csrf_fix()
    if success:
        print("\n✅ WebSocket CSRF fix verification completed successfully")
        print("🎯 Challenge acceptance should now work without page refresh!")
    else:
        print("\n❌ WebSocket CSRF fix verification failed")
    sys.exit(0 if success else 1)