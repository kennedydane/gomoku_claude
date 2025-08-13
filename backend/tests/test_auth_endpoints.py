"""
Tests for authentication endpoints and functionality.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

User = get_user_model()


class AuthEndpointTests(APITestCase):
    """Test authentication endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.token_url = reverse('api_token_auth')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            display_name='Test User'
        )
    
    def test_obtain_auth_token_success(self):
        """Test successful token authentication."""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.token_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        
        # Verify token is valid
        token = response.data['token']
        self.assertTrue(Token.objects.filter(key=token).exists())
        
        # Verify token belongs to correct user
        db_token = Token.objects.get(key=token)
        self.assertEqual(db_token.user, self.user)
    
    def test_obtain_auth_token_invalid_credentials(self):
        """Test token authentication with invalid credentials."""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.token_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_obtain_auth_token_missing_username(self):
        """Test token authentication with missing username."""
        data = {
            'password': 'testpass123'
        }
        
        response = self.client.post(self.token_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_obtain_auth_token_missing_password(self):
        """Test token authentication with missing password."""
        data = {
            'username': 'testuser'
        }
        
        response = self.client.post(self.token_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_obtain_auth_token_empty_credentials(self):
        """Test token authentication with empty credentials."""
        data = {}
        
        response = self.client.post(self.token_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_obtain_auth_token_inactive_user(self):
        """Test token authentication with inactive user."""
        # Deactivate user
        self.user.is_active = False
        self.user.save()
        
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.token_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_token_authentication_in_api_calls(self):
        """Test using token for authenticated API calls."""
        # Get token
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.token_url, data)
        token = response.data['token']
        
        # Test authenticated request
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        games_url = reverse('game-list')
        response = self.client.get(games_url)
        
        # Should be successful (not 401/403)
        self.assertIn(response.status_code, [status.HTTP_200_OK])
    
    def test_invalid_token_authentication(self):
        """Test API call with invalid token."""
        # Use invalid token
        self.client.credentials(HTTP_AUTHORIZATION='Token invalidtoken123')
        games_url = reverse('game-list')
        response = self.client.get(games_url)
        
        # DRF returns 403 for invalid tokens, 401 for missing auth
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        self.assertIn('error', response.data)
    
    def test_missing_token_authentication(self):
        """Test API call without token."""
        games_url = reverse('game-list')
        response = self.client.get(games_url)
        
        # DRF returns 403 when permission denied due to auth requirement
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        self.assertIn('error', response.data)
    
    def test_malformed_authorization_header(self):
        """Test API call with malformed authorization header."""
        # Missing 'Token' prefix
        self.client.credentials(HTTP_AUTHORIZATION='Bearer sometoken')
        games_url = reverse('game-list')
        response = self.client.get(games_url)
        
        # DRF returns 403 when permission denied due to auth requirement
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        self.assertIn('error', response.data)


class TokenManagementTests(APITestCase):
    """Test token management functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.token_url = reverse('api_token_auth')
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_token_persistence(self):
        """Test that token persists across requests."""
        # Get token first time
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response1 = self.client.post(self.token_url, data)
        token1 = response1.data['token']
        
        # Get token second time
        response2 = self.client.post(self.token_url, data)
        token2 = response2.data['token']
        
        # Should be the same token
        self.assertEqual(token1, token2)
    
    def test_token_uniqueness(self):
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
        response1 = self.client.post(self.token_url, data1)
        token1 = response1.data['token']
        
        # Get token for second user
        data2 = {
            'username': 'testuser2',
            'password': 'testpass123'
        }
        response2 = self.client.post(self.token_url, data2)
        token2 = response2.data['token']
        
        # Tokens should be different
        self.assertNotEqual(token1, token2)
    
    def test_case_sensitive_credentials(self):
        """Test that credentials are case-sensitive."""
        data = {
            'username': 'TESTUSER',  # Wrong case
            'password': 'testpass123'
        }
        
        response = self.client.post(self.token_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)