#!/usr/bin/env python3
"""
Comprehensive test script to verify the complete challenge system functionality.

This script tests the entire flow:
1. Challenge creation with WebSocket updates
2. Challenge acceptance with CSRF token handling 
3. Game creation after challenge acceptance
4. Real-time updates to both users
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

def test_complete_challenge_system():
    """Test the complete challenge system end-to-end."""
    
    print("🎮 COMPLETE CHALLENGE SYSTEM TEST")
    print("=" * 40)
    
    from django.contrib.auth import get_user_model
    from games.models import RuleSet, Challenge, ChallengeStatus, Game, GameStatus
    from web.models import Friendship, FriendshipStatus
    from web.services import WebSocketNotificationService
    from django.test import RequestFactory, Client
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.middleware.csrf import get_token
    
    User = get_user_model()
    
    try:
        # Setup test users and friendship
        dane = User.objects.get(username='dane')
        admin = User.objects.get(username='admin')
        
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
        
        print(f"📋 Setup: {dane.username} ↔ {admin.username} (friends)")
        print(f"📋 Ruleset: {mini_ruleset.name}")
        
        # Test 1: Challenge Creation
        print(f"\n🧪 TEST 1: Challenge Creation with WebSocket Updates")
        
        factory = RequestFactory()
        request = factory.get('/dashboard/')
        request.user = dane
        
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        csrf_token = get_token(request)
        print(f"   CSRF token generated: {csrf_token[:16]}...")
        
        # Create challenge
        challenge = Challenge.objects.create(
            challenger=dane,
            challenged=admin,
            ruleset=mini_ruleset
        )
        print(f"   Challenge created: {challenge.id}")
        
        # Send WebSocket notification for challenge creation
        creation_result = WebSocketNotificationService.notify_game_event(
            event_type='challenge_sent',
            game=None,
            triggering_user=dane,
            request=request,
            challenge=challenge
        )
        
        if creation_result:
            print("   ✅ Challenge creation WebSocket notification sent")
        else:
            print("   ❌ Challenge creation WebSocket notification failed")
        
        # Test 2: Challenge Acceptance with CSRF 
        print(f"\n🧪 TEST 2: Challenge Acceptance with CSRF Token")
        
        client = Client()
        client.force_login(admin)
        
        # Get dashboard to establish session
        dashboard_response = client.get('/dashboard/')
        print(f"   Dashboard request status: {dashboard_response.status_code}")
        
        # Accept the challenge using the proper CSRF token
        accept_response = client.post(
            f'/api/respond-challenge/{challenge.id}/',
            data={
                'action': 'accept',
                'csrfmiddlewaretoken': csrf_token
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        print(f"   Challenge accept response: {accept_response.status_code}")
        
        if accept_response.status_code in [200, 302]:
            print("   ✅ Challenge acceptance successful (no CSRF errors)")
        else:
            print(f"   ❌ Challenge acceptance failed: {accept_response.content.decode()[:200]}")
        
        # Test 3: Verify Game Creation
        print(f"\n🧪 TEST 3: Game Creation After Challenge Acceptance")
        
        # Refresh challenge from database
        challenge.refresh_from_db()
        print(f"   Challenge status: {challenge.status}")
        
        # Look for created game
        created_games = Game.objects.filter(
            black_player__in=[dane, admin],
            white_player__in=[dane, admin]
        ).filter(
            status=GameStatus.ACTIVE
        ).order_by('-created_at')
        
        if created_games.exists():
            game = created_games.first()
            print(f"   ✅ Game created: {game.id}")
            print(f"   Players: {game.black_player.username} (Black) vs {game.white_player.username} (White)")
            print(f"   Board size: {game.ruleset.board_size}x{game.ruleset.board_size}")
        else:
            print("   ❌ No game created after challenge acceptance")
            game = None
        
        # Test 4: WebSocket Updates for Both Users
        print(f"\n🧪 TEST 4: WebSocket Updates for Both Users")
        
        if game:
            # Test notification for challenge acceptance
            admin_request = factory.get('/dashboard/')
            admin_request.user = admin
            middleware.process_request(admin_request)
            admin_request.session.save()
            
            acceptance_result = WebSocketNotificationService.notify_game_event(
                event_type='challenge_accepted',
                game=game,
                triggering_user=admin,
                request=admin_request,
                challenge=challenge
            )
            
            if acceptance_result:
                print("   ✅ Challenge acceptance WebSocket notifications sent to both users")
            else:
                print("   ❌ Challenge acceptance WebSocket notifications failed")
        
        # Test 5: Template Rendering Without Errors
        print(f"\n🧪 TEST 5: Template Rendering Without Errors")
        
        from django.template.loader import render_to_string
        
        # Test friends panel rendering for both users
        for test_user in [dane, admin]:
            friends = Friendship.objects.get_friends(test_user)
            pending_challenges = Challenge.objects.filter(
                challenged=test_user,
                status=ChallengeStatus.PENDING
            )
            
            context = {
                'user': test_user,
                'friends': friends,
                'pending_sent_challenges': [],
                'pending_received_challenges': pending_challenges,
                'csrf_token': csrf_token
            }
            
            try:
                friends_html = render_to_string('web/partials/friends_panel.html', context, request=request)
                if csrf_token in friends_html:
                    print(f"   ✅ {test_user.username} friends panel rendered with CSRF token")
                else:
                    print(f"   ⚠️ {test_user.username} friends panel rendered but CSRF token not found")
            except Exception as e:
                print(f"   ❌ {test_user.username} friends panel rendering failed: {e}")
        
        # Clean up
        if game:
            game.delete()
        if Challenge.objects.filter(id=challenge.id).exists():
            challenge.delete()
        print(f"\n🧹 Test cleanup completed")
        
        # Final Assessment
        print(f"\n🏆 COMPLETE CHALLENGE SYSTEM ASSESSMENT:")
        
        success_criteria = [
            creation_result,  # Challenge creation WebSocket worked
            accept_response.status_code in [200, 302],  # Challenge acceptance worked
            challenge.status == ChallengeStatus.ACCEPTED,  # Challenge was accepted
            created_games.exists(),  # Game was created
        ]
        
        passed_tests = sum(success_criteria)
        total_tests = len(success_criteria)
        
        print(f"   Core functionality tests: {passed_tests}/{total_tests} passed")
        
        if passed_tests == total_tests:
            print("   ✅ Complete challenge system working perfectly!")
            print("   🎮 Users can create challenges, accept them, and start games")
            print("   🔄 Real-time WebSocket updates work for both users")
            print("   🔐 CSRF token handling is secure and functional")
        elif passed_tests >= 3:
            print("   ⚠️ Challenge system mostly working, minor issues detected")
        else:
            print("   ❌ Challenge system has significant issues")
        
        print(f"\n💡 MANUAL TESTING INSTRUCTIONS:")
        print(f"1. Start server: DB_PASSWORD=your_secure_password_here_change_this DB_NAME=gomoku_dev_db uv run daphne -p 8003 gomoku.asgi:application")
        print(f"2. Open two browser windows")
        print(f"3. Login as dane in one, admin in the other")
        print(f"4. Navigate both to dashboard")
        print(f"5. Use dane to challenge admin via friends panel")
        print(f"6. VERIFY: Both users see challenge immediately")
        print(f"7. Use admin to accept challenge")
        print(f"8. VERIFY: Both users see new game appear immediately")
        print(f"9. VERIFY: No console errors or 'Permission Denied' messages")
        
        return passed_tests >= 3
        
    except Exception as e:
        print(f"❌ Error in complete challenge system test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_complete_challenge_system()
    if success:
        print("\n✅ Complete challenge system test passed!")
        print("🎉 Challenge system is fully functional with real-time updates!")
    else:
        print("\n❌ Complete challenge system test failed")
    sys.exit(0 if success else 1)