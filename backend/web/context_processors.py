"""
Template context processors for Go Goban Go
Provides optimized asset URLs and performance data to templates
"""

import json
import os
from pathlib import Path
from django.conf import settings
from django.core.cache import cache

def optimized_assets(request):
    """
    Add optimized asset URLs to template context
    """
    # Check if optimization is enabled
    use_optimized = getattr(settings, 'USE_OPTIMIZED_ASSETS', False) or os.getenv('USE_OPTIMIZED_ASSETS', 'False').lower() == 'true'
    
    if not use_optimized:
        return {
            'use_optimized_assets': False,
            'asset_urls': {
                'js': ['js/app.js', 'js/sse-manager.js', 'js/htmx-sse-integration.js'],
                'css': ['css/style.css'],
                'critical_css': 'css/critical.css'
            }
        }
    
    # Try to load from cache first
    cache_key = 'optimized_asset_manifest'
    manifest = cache.get(cache_key)
    
    if manifest is None:
        try:
            manifest_path = Path(settings.BASE_DIR) / 'static' / 'dist' / 'manifest.json'
            
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                    
                # Cache for 1 hour in development, 24 hours in production
                cache_timeout = 3600 if settings.DEBUG else 86400
                cache.set(cache_key, manifest, cache_timeout)
            else:
                manifest = None
                
        except Exception as e:
            print(f"Warning: Could not load asset manifest: {e}")
            manifest = None
    
    if manifest:
        asset_urls = {
            'js': [f"static/{manifest['assets']['js']}"],
            'css': [f"static/{manifest['assets']['css']}"],
            'critical_css': f"static/{manifest['assets']['critical']}",
            'integrity': manifest.get('integrity', {}),
            'version': manifest.get('version', ''),
            'build_date': manifest.get('buildDate', '')
        }
    else:
        # Fallback to non-optimized assets
        asset_urls = {
            'js': ['static/js/app.optimized.js', 'static/js/sse-manager.optimized.js', 'static/js/htmx-sse-integration.optimized.js'],
            'css': ['static/css/style.css'],
            'critical_css': 'static/css/critical.css'
        }
    
    return {
        'use_optimized_assets': use_optimized,
        'asset_urls': asset_urls,
        'asset_manifest': manifest
    }

def performance_context(request):
    """
    Add performance monitoring context
    """
    return {
        'performance_monitoring': {
            'enabled': getattr(settings, 'TRACK_CORE_WEB_VITALS', True),
            'debug': settings.DEBUG,
            'version': getattr(settings, 'APP_VERSION', '1.0.0')
        }
    }

def pwa_context(request):
    """
    Add Progressive Web App context
    """
    return {
        'pwa': {
            'manifest_url': '/static/manifest.json',
            'service_worker_url': '/static/js/sw.js',
            'theme_color': '#0d6efd',
            'app_name': 'Go Goban Go'
        }
    }