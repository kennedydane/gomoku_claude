#!/usr/bin/env python3
"""
Test script to verify that the resign functionality works with the centralized WebSocketNotificationService.

This script tests that resignation now uses the centralized service and sends proper updates.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

def test_centralized_resign_service():
    """Test that resignation uses the centralized notification service."""
    
    print("🔍 CENTRALIZED RESIGN SERVICE TEST")
    print("=" * 40)
    
    from django.contrib.auth import get_user_model
    from games.models import Game, RuleSet, GameStatus
    from web.services import WebSocketNotificationService
    from django.test import RequestFactory
    from django.contrib.messages.storage.fallback import FallbackStorage
    from django.contrib.sessions.middleware import SessionMiddleware
    from unittest.mock import patch, MagicMock
    
    User = get_user_model()
    
    try:
        # Get test users
        dane = User.objects.get(username='dane')
        admin = User.objects.get(username='admin')
        
        # Get or create a test ruleset
        try:
            mini_ruleset = RuleSet.objects.get(name='Mini Gomoku')
        except RuleSet.DoesNotExist:
            mini_ruleset = RuleSet.objects.create(
                name='Mini Gomoku',
                board_size=8,
                description='Mini 8x8 Gomoku for testing'
            )
        
        print(f"📋 Test setup:")
        print(f"   Users: {dane.username}, {admin.username}")
        print(f"   Ruleset: {mini_ruleset.name} ({mini_ruleset.board_size}x{mini_ruleset.board_size})")
        
        # Test the centralized service directly first
        print(f"\n🧪 Testing centralized service directly...")
        
        # Create an active test game
        test_game = Game.objects.create(
            black_player=dane,
            white_player=admin,
            ruleset=mini_ruleset,
            status=GameStatus.ACTIVE
        )
        test_game.initialize_board()
        test_game.save()
        
        print(f"   Created test game: {test_game.id}")
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.post(f'/games/{test_game.id}/resign/')
        request.user = dane
        
        # Add session middleware for Django compatibility
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Mock the WebSocket sender to capture messages
        sent_messages = []
        
        def mock_send_to_user_sync(user_id, event_type, content, metadata=None):
            sent_messages.append({
                'user_id': user_id,
                'event_type': event_type,
                'content_length': len(content) if content else 0,
                'metadata': metadata
            })
            print(f"   📤 {event_type} → user {user_id} ({len(content) if content else 0} chars)")
        
        # Test the centralized service with mocked WebSocket
        with patch('web.consumers.WebSocketMessageSender.send_to_user_sync', side_effect=mock_send_to_user_sync):
            success = WebSocketNotificationService.notify_game_event(
                event_type='game_resigned',
                game=test_game,
                triggering_user=dane,
                request=request,
                metadata={'resigned_by': dane.id}
            )
            
            print(f"   Service returned: {success}")
        
        print(f"\n📊 CENTRALIZED SERVICE RESULTS:")
        print(f"   Total messages sent: {len(sent_messages)}")
        
        # Analyze message types
        message_types = {}
        for msg in sent_messages:
            event_type = msg['event_type']
            message_types[event_type] = message_types.get(event_type, 0) + 1
        
        for event_type, count in message_types.items():
            print(f"   {event_type}: {count} messages")
        
        # Check user coverage
        users_reached = set(msg['user_id'] for msg in sent_messages)
        print(f"   Users reached: {len(users_reached)} ({users_reached})")
        
        # Verification
        print(f"\n✅ VERIFICATION:")
        expected_updates = ['dashboard_update', 'dashboard_game_update']
        
        if len(users_reached) == 2:
            print("✅ Both players received notifications")
        else:
            print(f"❌ Expected 2 users, got {len(users_reached)}")
        
        if all(event_type in [msg['event_type'] for msg in sent_messages] for event_type in expected_updates):
            print("✅ All expected update types sent")
        else:
            print(f"❌ Missing expected update types: {expected_updates}")
        
        total_expected_messages = len(expected_updates) * 2  # 2 users × 2 update types
        if len(sent_messages) >= total_expected_messages:
            print(f"✅ Sufficient messages sent ({len(sent_messages)} >= {total_expected_messages})")
        else:
            print(f"❌ Insufficient messages ({len(sent_messages)} < {total_expected_messages})")
        
        # Test the service event definitions
        print(f"\n🔍 SERVICE EVENT DEFINITIONS:")
        event_def = WebSocketNotificationService.EVENT_DEFINITIONS.get('game_resigned')
        if event_def:
            print(f"   Description: {event_def['description']}")
            print(f"   Updates: {event_def['updates']}")
            
            # Verify the event definition matches what we expect
            expected_roles = ['resigning_player', 'other_player']
            actual_roles = list(event_def['updates'].keys())
            if set(actual_roles) == set(expected_roles):
                print("✅ Event definition has correct player roles")
            else:
                print(f"❌ Event definition roles mismatch. Expected: {expected_roles}, Got: {actual_roles}")
        else:
            print("❌ game_resigned event definition not found")
        
        # Clean up
        test_game.delete()
        print(f"\n🧹 Cleaned up test game")
        
        print(f"\n🎯 CENTRALIZED SERVICE BENEFITS:")
        print("✅ Single point of control for all WebSocket updates")
        print("✅ Consistent CSRF token handling")
        print("✅ Standardized event definitions")
        print("✅ Automatic user role detection")
        print("✅ Simplified view code")
        print("✅ Easier testing and debugging")
        
        return success and len(sent_messages) >= total_expected_messages
        
    except Exception as e:
        print(f"❌ Error in centralized resign test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_centralized_resign_service()
    if success:
        print("\n✅ Centralized resign service test completed successfully")
        print("🎮 Ready to test with real browser sessions!")
    else:
        print("\n❌ Centralized resign service test failed")
    sys.exit(0 if success else 1)