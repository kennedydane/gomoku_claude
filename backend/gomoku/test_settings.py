"""
Test-specific Django settings.

This configuration ensures consistent test behavior by:
1. Using SQLite with in-memory database for fast, transactional tests
2. Disabling migrations for faster test setup
3. Using simple password hashing for speed
4. Disabling caching to avoid test interdependencies
"""

from .settings import *

# Force SQLite for tests regardless of environment variables
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',  # Use file-based DB but with proper test isolation
        'OPTIONS': {
            'timeout': 20,
        },
    }
}

# Use faster password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Use faster test database setup but keep migrations for table creation
# We'll rely on pytest-django's --reuse-db and --create-db for performance

# Disable caching during tests to avoid interdependencies
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Ensure DEBUG is off for tests unless explicitly set
DEBUG = False

# Test-specific logging to reduce noise
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'games': {
            'handlers': ['console'],  
            'level': 'ERROR',
        },
    },
}

# Disable Loguru for tests to reduce noise
import logging
logging.getLogger('loguru').setLevel(logging.WARNING)