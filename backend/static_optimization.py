"""
Static Asset Optimization Settings for Go Goban Go
Add this to your Django settings.py for production optimization
"""

import os
import json
from pathlib import Path

# Asset optimization settings
ASSET_OPTIMIZATION = {
    'ENABLED': os.getenv('USE_OPTIMIZED_ASSETS', 'False').lower() == 'true',
    'MANIFEST_PATH': 'static/dist/manifest.json',
    'DEBUG_BUILD': False,
}

def load_asset_manifest(base_dir):
    """Load asset manifest with integrity hashes"""
    try:
        manifest_path = Path(base_dir) / ASSET_OPTIMIZATION['MANIFEST_PATH']
        
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                return json.load(f)
        else:
            print(f"Warning: Asset manifest not found at {manifest_path}")
            return None
            
    except Exception as e:
        print(f"Error loading asset manifest: {e}")
        return None

def get_optimized_static_urls():
    """Get URLs for optimized static assets"""
    if not ASSET_OPTIMIZATION['ENABLED']:
        return {
            'js': ['js/app.js', 'js/sse-manager.js', 'js/htmx-sse-integration.js'],
            'css': ['css/style.css'],
            'critical_css': 'css/critical.css'
        }
    
    manifest = load_asset_manifest(BASE_DIR)
    
    if manifest:
        return {
            'js': [manifest['assets']['js']],
            'css': [manifest['assets']['css']], 
            'critical_css': manifest['assets']['critical'],
            'integrity': manifest['integrity'],
            'version': manifest['version']
        }
    else:
        # Fallback to non-optimized assets
        return get_optimized_static_urls.__defaults__[0]

# Add to your Django settings.py:

"""
# Import this file
from .static_optimization import ASSET_OPTIMIZATION, get_optimized_static_urls

# Add to settings
ASSET_OPTIMIZATION_CONFIG = ASSET_OPTIMIZATION

# Template context processor
TEMPLATES[0]['OPTIONS']['context_processors'].extend([
    'path.to.static_optimization.asset_context_processor',
])

def asset_context_processor(request):
    '''Add optimized asset URLs to template context'''
    return {
        'optimized_assets': get_optimized_static_urls(),
        'use_optimized_assets': ASSET_OPTIMIZATION['ENABLED'],
    }
"""

# Production static file settings
OPTIMIZED_STATICFILES_SETTINGS = {
    # Enable static file compression
    'STATICFILES_STORAGE': 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage',
    
    # Add compression middleware
    'MIDDLEWARE': [
        'django.middleware.gzip.GZipMiddleware',
        # ... other middleware
    ],
    
    # Static file serving with proper headers
    'STATIC_FILE_HEADERS': {
        '*.js': {
            'Content-Encoding': 'gzip',
            'Cache-Control': 'public, max-age=31536000',  # 1 year
        },
        '*.css': {
            'Content-Encoding': 'gzip', 
            'Cache-Control': 'public, max-age=31536000',  # 1 year
        },
        '*.woff2': {
            'Cache-Control': 'public, max-age=31536000',  # 1 year
        },
        'manifest.json': {
            'Cache-Control': 'public, max-age=86400',     # 1 day
        }
    }
}

# Performance monitoring
PERFORMANCE_MONITORING = {
    'TRACK_CORE_WEB_VITALS': True,
    'ENABLE_PERFORMANCE_LOGGING': True,
    'SLOW_QUERY_THRESHOLD': 100,  # ms
}

# Content Security Policy for optimized assets
CSP_SETTINGS = {
    'script-src': [
        "'self'",
        "'unsafe-inline'",  # For critical inline scripts
        "https://unpkg.com",
        "https://cdn.jsdelivr.net"
    ],
    'style-src': [
        "'self'",
        "'unsafe-inline'",  # For critical inline CSS
        "https://cdn.jsdelivr.net"
    ],
    'connect-src': [
        "'self'",
        "ws://localhost:*",  # For development WebSocket
        "wss://*"            # For production WebSocket
    ]
}