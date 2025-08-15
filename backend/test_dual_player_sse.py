#!/usr/bin/env python3
"""
Test script to verify dual-player WebSocket updates after resignation.

This script tests that both players receive proper WebSocket updates
when one player resigns from a game.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

def test_dual_player_resign_updates():
    """Test that resignation sends proper updates to both players."""
    
    print("🔍 DUAL PLAYER RESIGN WEBSOCKET TEST")
    print("=" * 42)
    
    from django.contrib.auth import get_user_model
    from games.models import Game, RuleSet, GameStatus
    from web.views import GameResignView
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
        
        # Create an active test game
        test_game = Game.objects.create(
            black_player=dane,
            white_player=admin,
            ruleset=mini_ruleset,
            status=GameStatus.ACTIVE
        )
        test_game.initialize_board()
        test_game.save()
        
        print(f"📋 Created active test game: {test_game.id}")
        print(f"   Black player: {dane.username}")
        print(f"   White player: {admin.username}")
        print(f"   Status: {test_game.status}")
        
        # Create a mock request for the resign view
        factory = RequestFactory()
        request = factory.post(f'/games/{test_game.id}/resign/')
        request.user = dane
        
        # Add session and messages middleware for Django compatibility
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Mock the WebSocket sender to capture messages
        sent_messages = []
        
        def mock_send_to_user_sync(user_id, message_type, content, metadata=None):
            sent_messages.append({
                'user_id': user_id,
                'message_type': message_type,
                'content_length': len(content) if content else 0,
                'metadata': metadata
            })
            print(f"   📤 WebSocket message sent to user {user_id}")
            print(f"      Type: {message_type}")
            print(f"      Content length: {len(content) if content else 0}")
            print(f"      Metadata: {metadata}")
        
        # Test the resign view with mocked WebSocket
        with patch('web.consumers.WebSocketMessageSender.send_to_user_sync', side_effect=mock_send_to_user_sync):
            print(f"\n🏃 Testing resignation via GameResignView...")
            
            # Create the view and process the request
            view = GameResignView()
            view.request = request
            response = view.post(request, test_game.id)
            
            print(f"   Response status code: {response.status_code}")
            
            # Check the game status after resignation
            test_game.refresh_from_db()
            print(f"   Game status after resign: {test_game.status}")
            print(f"   Winner: {test_game.winner.username if test_game.winner else 'None'}")
        
        print(f"\n📊 WEBSOCKET MESSAGES SENT:")
        print(f"   Total messages: {len(sent_messages)}")
        
        # Analyze the messages
        dashboard_updates = [msg for msg in sent_messages if msg['message_type'] == 'dashboard_update']
        game_updates = [msg for msg in sent_messages if msg['message_type'] == 'dashboard_game_update']
        
        print(f"   Dashboard updates: {len(dashboard_updates)}")
        print(f"   Game panel updates: {len(game_updates)}")
        
        # Check if both players got updates
        dane_updates = [msg for msg in sent_messages if msg['user_id'] == dane.id]
        admin_updates = [msg for msg in sent_messages if msg['user_id'] == admin.id]
        
        print(f"\n👥 PLAYER-SPECIFIC UPDATES:")
        print(f"   dane received: {len(dane_updates)} messages")
        print(f"   admin received: {len(admin_updates)} messages")
        
        for i, msg in enumerate(dane_updates):
            print(f"     dane[{i}]: {msg['message_type']} ({msg['content_length']} chars)")
        
        for i, msg in enumerate(admin_updates):
            print(f"     admin[{i}]: {msg['message_type']} ({msg['content_length']} chars)")
        
        # Verify expected behavior
        print(f"\n✅ VERIFICATION:")
        if test_game.status == GameStatus.FINISHED:
            print("✅ Game status correctly changed to FINISHED")
        else:
            print(f"❌ Game status incorrect: {test_game.status}")
        
        if len(dashboard_updates) >= 2:  # Both players should get dashboard updates
            print("✅ Dashboard updates sent to both players")
        else:
            print(f"❌ Insufficient dashboard updates: {len(dashboard_updates)}")
        
        if len(game_updates) >= 2:  # Both players should get game panel updates
            print("✅ Game panel updates sent to both players")
        else:
            print(f"❌ Insufficient game panel updates: {len(game_updates)}")
        
        if len(dane_updates) >= 1 and len(admin_updates) >= 1:
            print("✅ Both players received WebSocket messages")
        else:
            print(f"❌ Missing updates - dane: {len(dane_updates)}, admin: {len(admin_updates)}")
        
        # Clean up
        test_game.delete()
        print(f"\n🧹 Cleaned up test game")
        
        print(f"\n🎯 EXPECTED FRONTEND BEHAVIOR:")
        print("1. Both players' games panels should update immediately")
        print("2. Game should disappear from active games list")
        print("3. Game should appear in recent finished games list")
        print("4. Winner information should be displayed correctly")
        
        print(f"\n🧪 MANUAL VERIFICATION STEPS:")
        print("1. Open two browser windows with dane and admin logged in")
        print("2. Navigate both to an active game") 
        print("3. Open developer console in both windows")
        print("4. Have one player resign")
        print("5. Check console logs for WebSocket messages")
        print("6. Verify both games panels update without page refresh")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in dual player resign test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_dual_player_resign_updates()
    if success:
        print("\n✅ Dual player resign test completed successfully")
    else:
        print("\n❌ Dual player resign test failed")
    sys.exit(0 if success else 1)