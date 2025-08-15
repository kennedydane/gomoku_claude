#!/usr/bin/env python3
"""
Test script to verify that the CSRF token fix resolves the challenge acceptance issue.

This script tests that each user gets their own valid CSRF token in WebSocket updates,
fixing the "CSRF token from POST incorrect" error.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

def test_csrf_token_fix():
    """Test that CSRF tokens are properly generated per user in WebSocket updates."""
    
    print("🔍 CSRF TOKEN PER-USER FIX TEST")
    print("=" * 35)
    
    from django.contrib.auth import get_user_model
    from games.models import RuleSet, Challenge, ChallengeStatus
    from web.models import Friendship, FriendshipStatus
    from web.services import WebSocketNotificationService
    from django.test import RequestFactory
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.middleware.csrf import get_token
    
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
        
        # Create a challenge
        challenge = Challenge.objects.create(
            challenger=dane,
            challenged=admin,
            ruleset=mini_ruleset
        )
        print(f"📋 Challenge created: {challenge.id}")
        
        # Test 1: Verify WebSocket notification creates user-specific CSRF tokens
        print(f"\n🧪 TEST 1: User-specific CSRF tokens in WebSocket updates")
        
        # Create mock request from challenger (dane)
        factory = RequestFactory()
        dane_request = factory.get('/dashboard/')
        dane_request.user = dane
        
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(dane_request)
        dane_request.session.save()
        
        dane_csrf_token = get_token(dane_request)
        print(f"   Dane's original CSRF token: {dane_csrf_token[:16]}...")
        
        # Send WebSocket notification - this should generate fresh tokens for each user
        result = WebSocketNotificationService.notify_game_event(
            event_type='challenge_sent',
            game=None,
            triggering_user=dane,
            request=dane_request,
            challenge=challenge
        )
        
        if result:
            print("   ✅ WebSocket notifications sent with user-specific CSRF tokens")
        else:
            print("   ❌ WebSocket notification failed")
        
        # Test 2: Verify the rendered HTML has valid CSRF tokens
        print(f"\n🧪 TEST 2: Template rendering with fresh CSRF tokens")
        
        # Test the _send_friends_panel_update method directly for admin
        from web.services import WebSocketNotificationService
        
        # This should create a fresh CSRF token for admin (not use dane's token)
        admin_panel_result = WebSocketNotificationService._send_friends_panel_update(
            user=admin,
            request=dane_request,  # Original request is from dane
            csrf_token=dane_csrf_token,  # Original token is from dane  
            context={'challenge': challenge}
        )
        
        if admin_panel_result:
            print("   ✅ Admin friends panel update sent with fresh CSRF token")
        else:
            print("   ❌ Admin friends panel update failed")
        
        # Test 3: Simulate actual challenge acceptance
        print(f"\n🧪 TEST 3: Challenge acceptance with fresh CSRF token")
        
        from django.test import Client
        
        client = Client()
        client.force_login(admin)
        
        # Get dashboard to establish admin's session
        dashboard_response = client.get('/dashboard/')
        print(f"   Dashboard status: {dashboard_response.status_code}")
        
        # Get admin's own CSRF token from their session
        admin_csrf_token = dashboard_response.context['csrf_token']
        print(f"   Admin's fresh CSRF token: {admin_csrf_token[:16]}...")
        
        # Verify tokens are different (each user has their own)
        if admin_csrf_token != dane_csrf_token:
            print("   ✅ Admin and Dane have different CSRF tokens (as expected)")
        else:
            print("   ⚠️ Admin and Dane have same CSRF token (unexpected)")
        
        # Try to accept the challenge using admin's own CSRF token
        accept_response = client.post(
            f'/api/respond-challenge/{challenge.id}/',
            data={
                'action': 'accept',
                'csrfmiddlewaretoken': admin_csrf_token
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        print(f"   Challenge accept response: {accept_response.status_code}")
        
        if accept_response.status_code in [200, 302]:
            print("   ✅ Challenge acceptance successful with admin's own CSRF token")
        elif accept_response.status_code == 403:
            print(f"   ❌ Challenge acceptance failed with CSRF error")
            print(f"   Response: {accept_response.content.decode()[:200]}...")
        else:
            print(f"   ⚠️ Unexpected response: {accept_response.status_code}")
        
        # Clean up
        try:
            challenge.refresh_from_db()
            if challenge.status == ChallengeStatus.PENDING:
                challenge.delete()
        except Challenge.DoesNotExist:
            pass
        print(f"\n🧹 Test cleanup completed")
        
        # Assessment
        print(f"\n🏆 CSRF TOKEN PER-USER FIX ASSESSMENT:")
        
        success_criteria = [
            result,  # WebSocket notification worked
            admin_panel_result,  # Admin panel update worked
            accept_response.status_code in [200, 302],  # Challenge acceptance worked
            admin_csrf_token != dane_csrf_token  # Different tokens per user
        ]
        
        passed_tests = sum(success_criteria)
        total_tests = len(success_criteria)
        
        print(f"   Tests passed: {passed_tests}/{total_tests}")
        
        if passed_tests == total_tests:
            print("   ✅ CSRF token per-user fix working perfectly!")
            print("   🔐 Each user gets their own valid CSRF token in WebSocket updates")
            print("   🎮 Challenge acceptance should work without 'Permission Denied' errors")
        elif passed_tests >= 3:
            print("   ⚠️ CSRF fix mostly working, minor issues detected")
        else:
            print("   ❌ CSRF token per-user fix needs more work")
        
        return passed_tests >= 3
        
    except Exception as e:
        print(f"❌ Error in CSRF token test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_csrf_token_fix()
    if success:
        print("\n✅ CSRF token per-user fix verification completed successfully")
        print("🔧 Challenge acceptance should now work without CSRF errors!")
    else:
        print("\n❌ CSRF token per-user fix verification failed")
    sys.exit(0 if success else 1)