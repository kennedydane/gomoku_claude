#!/usr/bin/env python
"""Test Ko rule performance after fixing duplicate Ko checks."""
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

from django.contrib.auth import get_user_model
from games.models import GoRuleSet, Game, GameStatus, Player
from games.game_services import GoGameService
from django.contrib.contenttypes.models import ContentType

User = get_user_model()

def test_ko_performance():
    """Test performance of moves with Ko rule detection."""
    print('🚀 TESTING KO RULE PERFORMANCE AFTER DUPLICATE CHECK FIX')
    print('='*60)
    
    # Create test users and game
    black_player = User.objects.create_user(
        username='perf_black',
        email='black@perf.com',
        password='testpass123'
    )
    white_player = User.objects.create_user(
        username='perf_white', 
        email='white@perf.com',
        password='testpass123'
    )
    
    ruleset = GoRuleSet.objects.create(
        name='Performance Test Go',
        board_size=9,
        description='Performance test ruleset'
    )
    
    content_type = ContentType.objects.get_for_model(GoRuleSet)
    game = Game.objects.create(
        black_player=black_player,
        white_player=white_player,
        ruleset_content_type=content_type,
        ruleset_object_id=ruleset.id,
        status=GameStatus.ACTIVE,
        current_player=Player.BLACK
    )
    game.initialize_board()
    game.save()
    
    service = GoGameService()
    
    # Test moves with timing
    moves = [
        (black_player.id, 3, 3),   # Move 1
        (white_player.id, 4, 4),   # Move 2
        (black_player.id, 3, 4),   # Move 3
        (white_player.id, 4, 3),   # Move 4
        (black_player.id, 5, 5),   # Move 5
        (white_player.id, 6, 6),   # Move 6
        (black_player.id, 5, 6),   # Move 7
        (white_player.id, 6, 5),   # Move 8
        (black_player.id, 7, 7),   # Move 9
        (white_player.id, 8, 8),   # Move 10
        (black_player.id, 7, 8),   # Move 11
        (white_player.id, 8, 7),   # Move 12
        (black_player.id, 2, 2),   # Move 13
        (white_player.id, 1, 1),   # Move 14
        (black_player.id, 2, 1),   # Move 15
        (white_player.id, 1, 2),   # Move 16
    ]
    
    total_time = 0
    move_times = []
    
    print('Making moves and measuring performance:')
    
    for i, (player_id, row, col) in enumerate(moves, start=1):
        start_time = time.time()
        
        try:
            move = service.make_move(game, player_id, row, col)
            end_time = time.time()
            
            move_time = (end_time - start_time) * 1000  # Convert to milliseconds
            total_time += move_time
            move_times.append(move_time)
            
            print(f'  Move {i:2d}: ({row},{col}) = {move_time:.2f}ms (cumulative: {total_time:.1f}ms)')
            
            if move_time > 100:  # Alert for slow moves
                print(f'    ⚠️  SLOW MOVE DETECTED: {move_time:.2f}ms')
                
        except Exception as e:
            end_time = time.time()
            move_time = (end_time - start_time) * 1000
            print(f'  Move {i:2d}: ({row},{col}) = FAILED after {move_time:.2f}ms - {e}')
    
    # Performance analysis
    print(f'\n📊 PERFORMANCE ANALYSIS:')
    print(f'   Total time: {total_time:.1f}ms')
    print(f'   Average per move: {total_time/len(move_times):.1f}ms')
    print(f'   Fastest move: {min(move_times):.1f}ms')
    print(f'   Slowest move: {max(move_times):.1f}ms')
    
    # Check for exponential slowdown
    first_half = move_times[:8]
    second_half = move_times[8:]
    
    if len(second_half) > 0:
        avg_first_half = sum(first_half) / len(first_half)
        avg_second_half = sum(second_half) / len(second_half)
        
        print(f'\n📈 EXPONENTIAL SLOWDOWN CHECK:')
        print(f'   First 8 moves average: {avg_first_half:.1f}ms')
        print(f'   Last {len(second_half)} moves average: {avg_second_half:.1f}ms')
        
        if avg_second_half > avg_first_half * 2:
            print('   ❌ EXPONENTIAL SLOWDOWN DETECTED!')
        else:
            print('   ✅ No exponential slowdown detected')
    
    # Performance verdict
    if max(move_times) < 50:  # All moves under 50ms
        print(f'\n🎉 PERFORMANCE: EXCELLENT - All moves under 50ms')
    elif max(move_times) < 100:
        print(f'\n✅ PERFORMANCE: GOOD - All moves under 100ms')
    elif max(move_times) < 500:
        print(f'\n⚠️ PERFORMANCE: ACCEPTABLE - Some moves over 100ms but under 500ms')
    else:
        print(f'\n❌ PERFORMANCE: POOR - Moves over 500ms detected')
    
    # Cleanup
    game.delete()
    ruleset.delete()
    black_player.delete()
    white_player.delete()

if __name__ == '__main__':
    test_ko_performance()