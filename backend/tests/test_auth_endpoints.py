"""
Tests for authentication endpoints and functionality.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from users.models import EnhancedToken

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for testing."""
    return APIClient()


@pytest.fixture
def auth_user(db):
    """Test user for authentication."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        display_name='Test User'
    )


@pytest.fixture
def token_url():
    """Token authentication URL."""
    return reverse('api_token_auth')


@pytest.mark.api
@pytest.mark.django_db
class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    def test_obtain_auth_token_success(self, api_client, auth_user, token_url):
        """Test successful token authentication."""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = api_client.post(token_url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data
        
        # Verify token is valid
        token = response.data['token']
        assert EnhancedToken.objects.filter(key=token).exists()
        
        # Verify token belongs to correct user
        db_token = EnhancedToken.objects.get(key=token)
        assert db_token.user == auth_user
    
    def test_obtain_auth_token_invalid_credentials(self, api_client, auth_user, token_url):
        """Test token authentication with invalid credentials."""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = api_client.post(token_url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_obtain_auth_token_missing_username(self, api_client, auth_user, token_url):
        """Test token authentication with missing username."""
        data = {
            'password': 'testpass123'
        }
        
        response = api_client.post(token_url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_obtain_auth_token_missing_password(self, api_client, auth_user, token_url):
        """Test token authentication with missing password."""
        data = {
            'username': 'testuser'
        }
        
        response = api_client.post(token_url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_obtain_auth_token_empty_credentials(self, api_client, token_url):
        """Test token authentication with empty credentials."""
        data = {}
        
        response = api_client.post(token_url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_obtain_auth_token_inactive_user(self, api_client, auth_user, token_url):
        """Test token authentication with inactive user."""
        # Deactivate user
        auth_user.is_active = False
        auth_user.save()
        
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = api_client.post(token_url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_token_authentication_in_api_calls(self, api_client, auth_user, token_url):
        """Test using token for authenticated API calls."""
        # Get token
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = api_client.post(token_url, data)
        token = response.data['token']
        
        # Test authenticated request
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        games_url = reverse('game-list')
        response = api_client.get(games_url)
        
        # Should be successful (not 401/403)
        assert response.status_code == status.HTTP_200_OK
    
    def test_invalid_token_authentication(self, api_client):
        """Test API call with invalid token."""
        # Use invalid token
        api_client.credentials(HTTP_AUTHORIZATION='Token invalidtoken123')
        games_url = reverse('game-list')
        response = api_client.get(games_url)
        
        # DRF returns 403 for invalid tokens, 401 for missing auth
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        assert 'error' in response.data
    
    def test_missing_token_authentication(self, api_client):
        """Test API call without token."""
        games_url = reverse('game-list')
        response = api_client.get(games_url)
        
        # DRF returns 403 when permission denied due to auth requirement
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        assert 'error' in response.data
    
    def test_malformed_authorization_header(self, api_client):
        """Test API call with malformed authorization header."""
        # Missing 'Token' prefix
        api_client.credentials(HTTP_AUTHORIZATION='Bearer sometoken')
        games_url = reverse('game-list')
        response = api_client.get(games_url)
        
        # DRF returns 403 when permission denied due to auth requirement
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        assert 'error' in response.data


@pytest.mark.api
@pytest.mark.django_db
class TestTokenManagement:
    """Test token management functionality."""
    
    def test_token_persistence(self, api_client, auth_user, token_url):
        """Test that token persists across requests."""
        # Get token first time
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response1 = api_client.post(token_url, data)
        token1 = response1.data['token']
        
        # Get token second time
        response2 = api_client.post(token_url, data)
        token2 = response2.data['token']
        
        # Should be the same token
        assert token1 == token2
    
    def test_token_uniqueness(self, api_client, auth_user, token_url, db):
        """Test that different users get different tokens."""
        # Create second user
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        # Get token for first user
        data1 = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response1 = api_client.post(token_url, data1)
        token1 = response1.data['token']
        
        # Get token for second user
        data2 = {
            'username': 'testuser2',
            'password': 'testpass123'
        }
        response2 = api_client.post(token_url, data2)
        token2 = response2.data['token']
        
        # Tokens should be different
        assert token1 != token2
    
    def test_case_sensitive_credentials(self, api_client, auth_user, token_url):
        """Test that credentials are case-sensitive."""
        data = {
            'username': 'TESTUSER',  # Wrong case
            'password': 'testpass123'
        }
        
        response = api_client.post(token_url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data