#!/usr/bin/env python3
"""
Verification script for resign CSRF token fix.

This script verifies that both resign button templates now include
proper CSRF token headers for HTMX requests.
"""

import os
import sys

def verify_csrf_fix():
    """Verify that CSRF token headers are properly added to resign buttons."""
    
    print("🔍 RESIGN CSRF TOKEN FIX VERIFICATION")
    print("=" * 42)
    
    templates_to_check = [
        ('/home/dane/dev/gomoku_claude/backend/templates/web/partials/dashboard_game_panel.html', 'Dashboard Game Panel'),
        ('/home/dane/dev/gomoku_claude/backend/templates/web/game_detail.html', 'Game Detail Page')
    ]
    
    all_good = True
    
    for template_path, template_name in templates_to_check:
        print(f"\n📋 Checking {template_name}...")
        
        try:
            with open(template_path, 'r') as f:
                content = f.read()
            
            # Check for resign button with proper CSRF headers
            checks = [
                ('hx-post="{% url \'web:game_resign\'', 'Uses web resign endpoint'),
                ('hx-headers=\'{"X-CSRFToken": "{{ csrf_token }}"}\'', 'Includes CSRF token header'),
                ('hx-confirm="Are you sure you want to resign', 'Has confirmation dialog'),
                ('/api/v1/games/', 'Should NOT use old API endpoint (absence check)')
            ]
            
            for search_term, description in checks:
                found = search_term in content
                
                if search_term.startswith('/api/v1/games/'):
                    # This is an absence check - we want this to be False
                    status = '✅' if not found else '❌'
                    result = 'Not found (good)' if not found else 'Found (bad - still using API)'
                    if found:
                        all_good = False
                else:
                    # Normal presence checks
                    status = '✅' if found else '❌'
                    result = 'Found' if found else 'Missing'
                    if not found:
                        all_good = False
                
                print(f"  {status} {description}: {result}")
                
        except Exception as e:
            print(f"  ❌ Error reading {template_name}: {e}")
            all_good = False
    
    print(f"\n📋 VERIFICATION SUMMARY:")
    print("=" * 25)
    
    if all_good:
        print("✅ All checks passed!")
        print("✅ Both resign buttons now use web endpoint with CSRF tokens")
        print("✅ No more API endpoint usage for resign functionality")
        print("✅ Proper hx-headers with X-CSRFToken included")
        
        print(f"\n🎯 EXPECTED BEHAVIOR:")
        print("- Resign button clicks should include CSRF token in headers")
        print("- No more 'CSRF token missing' errors in server logs")
        print("- No more 'Permission Denied' errors for users")
        print("- Both players should receive real-time WebSocket updates")
        
        print(f"\n🧪 TEST WITH:")
        print("1. Login to dashboard")
        print("2. Click any active game resign button") 
        print("3. Confirm resignation")
        print("4. Check browser console and server logs for errors")
        print("5. Verify game updates immediately for both players")
        
        return True
    else:
        print("❌ Some checks failed!")
        print("❌ Manual review of templates may be needed")
        return False

if __name__ == '__main__':
    success = verify_csrf_fix()
    sys.exit(0 if success else 1)