#!/usr/bin/env python
"""
Create a superuser for Django admin.
"""
import os
import django
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create superuser if it doesn't exist
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@gomoku.com',
        password='admin123',
        display_name='Administrator'
    )
    print("Superuser created: admin / admin123")
else:
    print("Superuser already exists")