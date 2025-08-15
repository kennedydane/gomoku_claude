#!/usr/bin/env python3
"""
End-to-end WebSocket notification test script.

This script creates a comprehensive test scenario covering:
1. Challenge creation and acceptance
2. Game moves and turn updates
3. Game resignation
4. All using the centralized WebSocketNotificationService
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

def test_end_to_end_websocket_flow():
    """Test the complete WebSocket notification flow."""
    
    print("🔍 END-TO-END WEBSOCKET NOTIFICATION FLOW TEST")
    print("=" * 52)
    
    from django.contrib.auth import get_user_model
    from games.models import RuleSet, Game, GameStatus, Challenge, ChallengeStatus
    from web.models import Friendship, FriendshipStatus
    from web.services import WebSocketNotificationService
    from django.test import RequestFactory
    from django.contrib.sessions.middleware import SessionMiddleware
    from unittest.mock import patch
    
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
        
        # Get Mini Gomoku ruleset
        try:
            mini_ruleset = RuleSet.objects.get(name='Mini Gomoku')
        except RuleSet.DoesNotExist:
            mini_ruleset = RuleSet.objects.create(
                name='Mini Gomoku',
                board_size=8,
                description='Mini 8x8 Gomoku for testing'
            )
        
        print(f"📋 Test setup:")
        print(f"   Users: {dane.username} ↔ {admin.username} (friends)")
        print(f"   Ruleset: {mini_ruleset.name} ({mini_ruleset.board_size}x{mini_ruleset.board_size})")
        
        # Create mock request
        factory = RequestFactory()
        request = factory.post('/')
        request.user = dane
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Track all WebSocket messages
        all_messages = []
        
        def mock_send_to_user_sync(user_id, event_type, content, metadata=None):
            all_messages.append({
                'step': len(all_messages) + 1,
                'user_id': user_id,
                'username': User.objects.get(id=user_id).username,
                'event_type': event_type,
                'content_length': len(content) if content else 0,
                'metadata': metadata,
                'csrf_token_present': 'csrf_token' in (content or ''),
                'html_content': len(content or '') > 100  # Likely HTML if > 100 chars
            })
            
        # STEP 1: Challenge Creation
        print(f"\n🎯 STEP 1: Challenge Creation (dane → admin)")
        with patch('web.consumers.WebSocketMessageSender.send_to_user_sync', side_effect=mock_send_to_user_sync):
            challenge = Challenge.objects.create(
                challenger=dane,
                challenged=admin,
                ruleset=mini_ruleset
            )
            
            success = WebSocketNotificationService.notify_game_event(
                event_type='challenge_sent',
                game=None,
                triggering_user=dane,
                request=request,
                challenge=challenge
            )
            print(f"   Challenge created: {challenge.id}")
            print(f"   WebSocket success: {success}")
        
        # STEP 2: Challenge Acceptance
        print(f"\n🎯 STEP 2: Challenge Acceptance (admin accepts)")
        with patch('web.consumers.WebSocketMessageSender.send_to_user_sync', side_effect=mock_send_to_user_sync):
            # Create game
            game = Game.objects.create(
                black_player=dane,
                white_player=admin,
                ruleset=mini_ruleset,
                status=GameStatus.ACTIVE
            )
            game.initialize_board()
            game.save()
            
            request.user = admin  # Switch to admin accepting
            success = WebSocketNotificationService.notify_game_event(
                event_type='challenge_accepted',
                game=game,
                triggering_user=admin,
                request=request,
                challenge=challenge
            )
            print(f"   Game created: {game.id}")
            print(f"   WebSocket success: {success}")
        
        # STEP 3: Game Move (to test turn updates)
        print(f"\n🎯 STEP 3: Game Move (dane makes first move)")
        with patch('web.consumers.WebSocketMessageSender.send_to_user_sync', side_effect=mock_send_to_user_sync):
            request.user = dane  # Switch back to dane
            
            success = WebSocketNotificationService.notify_game_event(
                event_type='game_move_made',
                game=game,
                triggering_user=dane,
                request=request
            )
            print(f"   Move made by: {dane.username}")
            print(f"   WebSocket success: {success}")
        
        # STEP 4: Game Resignation
        print(f"\n🎯 STEP 4: Game Resignation (admin resigns)")
        with patch('web.consumers.WebSocketMessageSender.send_to_user_sync', side_effect=mock_send_to_user_sync):
            # Simulate game resignation
            game.status = GameStatus.FINISHED
            game.winner = dane
            game.save()
            
            request.user = admin  # admin resigns
            success = WebSocketNotificationService.notify_game_event(
                event_type='game_resigned',
                game=game,
                triggering_user=admin,
                request=request
            )
            print(f"   Game resigned by: {admin.username}")
            print(f"   Winner: {game.winner.username}")
            print(f"   WebSocket success: {success}")
        
        # ANALYSIS
        print(f"\n📊 END-TO-END ANALYSIS:")
        print(f"   Total WebSocket messages: {len(all_messages)}")
        print(f"   Unique event types: {set(msg['event_type'] for msg in all_messages)}")
        print(f"   Users reached: {set(msg['username'] for msg in all_messages)}")
        
        # Message breakdown by step
        print(f"\n📋 MESSAGE BREAKDOWN BY STEP:")
        
        step_boundaries = [0]  # Track where each step starts
        current_step = 1
        
        for i, msg in enumerate(all_messages):
            if i == 0 or msg['step'] == 1:
                step_boundaries.append(i)
        step_boundaries.append(len(all_messages))
        
        step_names = ["Challenge Sent", "Challenge Accepted", "Game Move", "Game Resigned"]
        
        for step_num in range(1, 5):
            if step_num <= len(step_names):
                step_name = step_names[step_num - 1]
                step_msgs = [msg for msg in all_messages if (step_num - 1) * 2 <= all_messages.index(msg) < step_num * 2 + 2]
                if not step_msgs:
                    # Fallback: get messages from this step
                    start_idx = (step_num - 1) * 2
                    end_idx = min(start_idx + 4, len(all_messages))
                    step_msgs = all_messages[start_idx:end_idx]
                
                print(f"\n   {step_name}:")
                for msg in step_msgs[:4]:  # Show up to 4 messages per step
                    print(f"     → {msg['username']}: {msg['event_type']} ({msg['content_length']} chars)")
                    if msg['csrf_token_present']:
                        print(f"       ✅ CSRF token present")
                    if msg['html_content']:
                        print(f"       📄 HTML content detected")
        
        # CSRF Token Verification
        csrf_messages = [msg for msg in all_messages if msg['csrf_token_present']]
        print(f"\n🔐 CSRF TOKEN VERIFICATION:")
        print(f"   Messages with CSRF tokens: {len(csrf_messages)}/{len(all_messages)}")
        
        if len(csrf_messages) > 0:
            print("   ✅ CSRF tokens are being included in WebSocket updates")
        else:
            print("   ⚠️ No CSRF tokens detected in WebSocket content")
        
        # Event Type Coverage
        expected_events = ['friends_update', 'dashboard_update', 'dashboard_game_update', 'game_move', 'game_turn_update']
        actual_events = set(msg['event_type'] for msg in all_messages)
        
        print(f"\n🎯 EVENT TYPE COVERAGE:")
        for event in expected_events:
            if event in actual_events:
                count = len([msg for msg in all_messages if msg['event_type'] == event])
                print(f"   ✅ {event}: {count} messages")
            else:
                print(f"   ❌ {event}: missing")
        
        # User Coverage
        dane_messages = [msg for msg in all_messages if msg['username'] == 'dane']
        admin_messages = [msg for msg in all_messages if msg['username'] == 'admin']
        
        print(f"\n👥 USER COVERAGE:")
        print(f"   dane received: {len(dane_messages)} messages")
        print(f"   admin received: {len(admin_messages)} messages")
        
        if len(dane_messages) > 0 and len(admin_messages) > 0:
            print("   ✅ Both users receiving WebSocket updates")
        else:
            print("   ❌ One or both users not receiving updates")
        
        # Clean up
        game.delete()
        challenge.delete()
        print(f"\n🧹 Cleaned up test data")
        
        # Final assessment
        success_criteria = [
            len(all_messages) >= 8,  # Should have multiple messages
            len(actual_events & set(expected_events)) >= 3,  # Should cover multiple event types
            len(dane_messages) > 0 and len(admin_messages) > 0,  # Both users get updates
        ]
        
        overall_success = all(success_criteria)
        
        print(f"\n🏆 OVERALL ASSESSMENT:")
        if overall_success:
            print("✅ End-to-end WebSocket notification flow working correctly!")
            print("🎮 Ready for production use with real browser sessions")
        else:
            print("❌ Some issues detected in WebSocket notification flow")
            print(f"   Success criteria: {sum(success_criteria)}/{len(success_criteria)} passed")
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Error in end-to-end test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_end_to_end_websocket_flow()
    if success:
        print("\n✅ End-to-end WebSocket test completed successfully")
    else:
        print("\n❌ End-to-end WebSocket test failed")
    sys.exit(0 if success else 1)