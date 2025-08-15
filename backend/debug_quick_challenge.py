"""
Debug script to see what the quick challenge modal is actually rendering.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from bs4 import BeautifulSoup
from web.models import Friendship, FriendshipStatus

User = get_user_model()

def debug_quick_challenge_modal():
    # Create test users if they don't exist
    dane, created = User.objects.get_or_create(
        username='dane',
        defaults={'email': 'dane@test.com'}
    )
    if created:
        dane.set_password('dane1234')
        dane.save()
    
    admin, created = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@test.com'}
    )
    if created:
        admin.set_password('admin123')
        admin.save()
    
    # Make them friends
    friendship, created = Friendship.objects.get_or_create(
        requester=dane,
        addressee=admin,
        defaults={'status': FriendshipStatus.ACCEPTED}
    )
    if friendship.status != FriendshipStatus.ACCEPTED:
        friendship.status = FriendshipStatus.ACCEPTED
        friendship.save()
    
    # Test the modal rendering
    client = Client()
    client.login(username='dane', password='dane1234')
    
    print("🔍 Testing Standard Quick Challenge Modal...")
    response = client.get(reverse('web:challenge_friend'), {'quick': 'standard'})
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all inputs
        inputs = soup.find_all('input')
        print(f"\n📋 All inputs found:")
        for i, inp in enumerate(inputs):
            input_type = inp.get('type', 'text')
            input_name = inp.get('name', 'no-name')
            input_value = inp.get('value', 'no-value')
            print(f"  {i+1}. Type: {input_type}, Name: {input_name}, Value: {input_value}")
        
        # Find all selects
        selects = soup.find_all('select')
        print(f"\n📋 All selects found: {len(selects)}")
        for i, sel in enumerate(selects):
            select_name = sel.get('name', 'no-name')
            options = sel.find_all('option')
            print(f"  {i+1}. Name: {select_name}, Options: {len(options)}")
            for j, opt in enumerate(options):
                opt_value = opt.get('value', 'no-value')
                opt_selected = 'selected' if opt.get('selected') else 'not-selected'
                print(f"     Option {j+1}: Value={opt_value}, {opt_selected}")
        
        # Show the full form content
        form = soup.find('form')
        if form:
            print(f"\n🔍 Full form HTML:")
            print(form.prettify())
    else:
        print(f"❌ Error: {response.content.decode()}")

if __name__ == '__main__':
    debug_quick_challenge_modal()