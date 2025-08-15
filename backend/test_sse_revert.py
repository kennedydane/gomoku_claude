#!/usr/bin/env python3
"""
Test that SSE revert was successful and real-time functionality is restored.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

def test_sse_revert():
    print("🔄 Testing SSE Revert - Real-time Functionality Restored")
    print("=" * 60)
    
    # Test 1: Check that JavaScript is removed from base template
    print("\n🚫 Checking JavaScript removal...")
    base_path = Path(__file__).parent / 'templates' / 'base.html'
    if base_path.exists():
        content = base_path.read_text()
        
        js_removed = [
            ('sse-manager.js', 'sse-manager.js' not in content),
            ('htmx-sse-integration.js', 'htmx-sse-integration.js' not in content),
            ('data-user-id', 'data-user-id' not in content),
        ]
        
        for item, removed in js_removed:
            print(f"  {'✅' if removed else '❌'} {item}: {'Removed' if removed else 'Still present'}")
        
        all_js_removed = all(removed for _, removed in js_removed)
    else:
        print("  ❌ base.html not found")
        all_js_removed = False
    
    # Test 2: Check that HTMX SSE attributes are restored
    print("\n🔌 Checking HTMX SSE restoration...")
    
    template_checks = []
    templates_to_check = [
        ('dashboard.html', 'templates/web/dashboard.html'),
        ('game_detail.html', 'templates/web/game_detail.html'),
        ('dashboard_game_panel.html', 'templates/web/partials/dashboard_game_panel.html')
    ]
    
    for template_name, template_path in templates_to_check:
        full_path = Path(__file__).parent / template_path
        if full_path.exists():
            content = full_path.read_text()
            
            has_hx_ext = 'hx-ext="sse"' in content
            has_sse_connect = 'sse-connect="/api/v1/events/?channel=user-' in content
            has_sse_swap = 'sse-swap=' in content
            
            restored = has_hx_ext and has_sse_connect and has_sse_swap
            print(f"  {'✅' if restored else '❌'} {template_name}: {'Restored' if restored else 'Missing SSE attributes'}")
            
            if not restored:
                print(f"    - hx-ext=\"sse\": {'✓' if has_hx_ext else '✗'}")
                print(f"    - sse-connect: {'✓' if has_sse_connect else '✗'}")
                print(f"    - sse-swap: {'✓' if has_sse_swap else '✗'}")
            
            template_checks.append(restored)
        else:
            print(f"  ❌ {template_name}: File not found")
            template_checks.append(False)
    
    # Test 3: Count SSE connections in dashboard (should be 4 again)
    print("\n📊 Checking SSE connection count...")
    dashboard_path = Path(__file__).parent / 'templates' / 'web' / 'dashboard.html'
    if dashboard_path.exists():
        content = dashboard_path.read_text()
        sse_connect_count = content.count('sse-connect=')
        expected_count = 3  # Left panel, center panel, friends panel
        print(f"  {'✅' if sse_connect_count == expected_count else '❌'} Dashboard SSE connections: {sse_connect_count} (expected: {expected_count})")
        connection_count_ok = sse_connect_count == expected_count
    else:
        print("  ❌ Dashboard template not found")
        connection_count_ok = False
    
    # Test 4: Verify embedded game board has SSE
    print("\n🎮 Checking embedded game board SSE...")
    game_panel_path = Path(__file__).parent / 'templates' / 'web' / 'partials' / 'dashboard_game_panel.html'
    if game_panel_path.exists():
        content = game_panel_path.read_text()
        has_embedded_sse = 'id="dashboard-game-board-wrapper"' in content and 'sse-connect=' in content
        print(f"  {'✅' if has_embedded_sse else '❌'} Embedded game board SSE: {'Restored' if has_embedded_sse else 'Missing'}")
    else:
        print("  ❌ Dashboard game panel template not found")
        has_embedded_sse = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Revert Test Summary:")
    
    all_tests = [
        all_js_removed,
        all(template_checks),
        connection_count_ok,
        has_embedded_sse
    ]
    
    passed = sum(all_tests)
    total = len(all_tests)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if all(all_tests):
        print("\n🎉 SSE Revert Successful!")
        print("✅ Real-time move updates should work again")
        print("✅ No JavaScript dependencies")
        print("✅ HTMX native SSE extension restored")
        print("⚠️  Multiple SSE connections restored (4 per user)")
        print("\n💡 The system is back to its original working state.")
    else:
        print("\n⚠️  Some revert steps failed. Manual review needed.")
    
    return all(all_tests)

if __name__ == '__main__':
    success = test_sse_revert()
    if success:
        print("\n🚀 Ready to test real-time moves!")
        print("   Start the server and test with two browser windows:")
        print("   1. Login as different users in each window")
        print("   2. Navigate to the same game")
        print("   3. Make a move in one window")
        print("   4. Verify the move appears in the other window")
    sys.exit(0 if success else 1)