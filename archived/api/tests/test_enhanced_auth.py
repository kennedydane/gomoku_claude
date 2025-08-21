"""
Tests for enhanced authentication functionality.

Following TDD methodology: RED-GREEN-REFACTOR
These tests define the behavior we want from the enhanced token system.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch

User = get_user_model()


class EnhancedTokenModelTests(TestCase):
    """Test enhanced token model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            display_name='Test User'
        )
    
    def test_enhanced_token_creation_with_expiration(self):
        """Test creating enhanced token with automatic expiration."""
        # RED: This test will fail because EnhancedToken doesn't exist yet
        from users.models import EnhancedToken
        
        token = EnhancedToken.objects.create(user=self.user)
        
        # Should have expiration set automatically
        self.assertIsNotNone(token.expires_at)
        self.assertTrue(token.expires_at > timezone.now())
        
        # Should expire in reasonable time (default 7 days)
        expected_expiry = timezone.now() + timedelta(days=7)
        time_diff = abs((token.expires_at - expected_expiry).total_seconds())
        self.assertLess(time_diff, 60, "Expiration should be approximately 7 days from now")
    
    def test_enhanced_token_custom_expiration(self):
        """Test creating enhanced token with custom expiration."""
        from users.models import EnhancedToken
        
        custom_expiry = timezone.now() + timedelta(hours=1)
        token = EnhancedToken.objects.create(
            user=self.user,
            expires_at=custom_expiry
        )
        
        self.assertEqual(token.expires_at, custom_expiry)
    
    def test_enhanced_token_device_tracking(self):
        """Test device-specific token tracking."""
        from users.models import EnhancedToken
        
        token = EnhancedToken.objects.create(
            user=self.user,
            device_name='Desktop App',
            device_info={'os': 'Linux', 'app_version': '1.0.0'}
        )
        
        self.assertEqual(token.device_name, 'Desktop App')
        self.assertEqual(token.device_info['os'], 'Linux')
        self.assertEqual(token.device_info['app_version'], '1.0.0')
    
    def test_multiple_tokens_per_user(self):
        """Test that users can have multiple active tokens."""
        from users.models import EnhancedToken
        
        token1 = EnhancedToken.objects.create(
            user=self.user,
            device_name='Desktop'
        )
        token2 = EnhancedToken.objects.create(
            user=self.user,
            device_name='Mobile'
        )
        
        user_tokens = EnhancedToken.objects.filter(user=self.user)
        self.assertEqual(user_tokens.count(), 2)
        self.assertIn(token1, user_tokens)
        self.assertIn(token2, user_tokens)
    
    def test_token_expiration_validation(self):
        """Test token expiration validation."""
        from users.models import EnhancedToken
        
        # Create expired token
        expired_token = EnhancedToken.objects.create(
            user=self.user,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        self.assertTrue(expired_token.is_expired)
        
        # Create valid token
        valid_token = EnhancedToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        self.assertFalse(valid_token.is_expired)
    
    def test_token_last_used_tracking(self):
        """Test tracking when token was last used."""
        from users.models import EnhancedToken
        
        token = EnhancedToken.objects.create(user=self.user)
        self.assertIsNone(token.last_used)
        
        # Simulate token usage
        token.update_last_used()
        self.assertIsNotNone(token.last_used)
        
        # Should be recent
        time_diff = abs((timezone.now() - token.last_used).total_seconds())
        self.assertLess(time_diff, 5, "Last used should be very recent")
    
    def test_token_cleanup_expired(self):
        """Test cleanup of expired tokens."""
        from users.models import EnhancedToken
        
        # Create mix of expired and valid tokens
        expired_token1 = EnhancedToken.objects.create(
            user=self.user,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        expired_token2 = EnhancedToken.objects.create(
            user=self.user,
            expires_at=timezone.now() - timedelta(days=1)
        )
        valid_token = EnhancedToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        # Clean up expired tokens
        deleted_count = EnhancedToken.objects.cleanup_expired()
        
        self.assertEqual(deleted_count, 2)
        self.assertFalse(EnhancedToken.objects.filter(id=expired_token1.id).exists())
        self.assertFalse(EnhancedToken.objects.filter(id=expired_token2.id).exists())
        self.assertTrue(EnhancedToken.objects.filter(id=valid_token.id).exists())
    
    def test_token_string_representation(self):
        """Test token string representation."""
        from users.models import EnhancedToken
        
        token = EnhancedToken.objects.create(
            user=self.user,
            device_name='Test Device'
        )
        
        expected = f"Token for {self.user.username} (Test Device)"
        self.assertEqual(str(token), expected)
    
    def test_token_unique_key_generation(self):
        """Test that token keys are unique."""
        from users.models import EnhancedToken
        
        token1 = EnhancedToken.objects.create(user=self.user)
        token2 = EnhancedToken.objects.create(user=self.user)
        
        self.assertNotEqual(token1.key, token2.key)
        self.assertEqual(len(token1.key), 40)  # Standard token length
        self.assertEqual(len(token2.key), 40)


class EnhancedTokenManagerTests(TestCase):
    """Test enhanced token manager functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            display_name='Test User'
        )
    
    def test_create_token_for_device(self):
        """Test manager method to create device-specific tokens."""
        from users.models import EnhancedToken
        
        token = EnhancedToken.objects.create_for_device(
            user=self.user,
            device_name='Desktop App',
            device_info={'version': '1.0.0'}
        )
        
        self.assertEqual(token.user, self.user)
        self.assertEqual(token.device_name, 'Desktop App')
        self.assertEqual(token.device_info['version'], '1.0.0')
    
    def test_get_valid_tokens_for_user(self):
        """Test getting only valid (non-expired) tokens for a user."""
        from users.models import EnhancedToken
        
        # Create mix of expired and valid tokens
        EnhancedToken.objects.create(
            user=self.user,
            expires_at=timezone.now() - timedelta(hours=1)  # Expired
        )
        valid_token = EnhancedToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=1)  # Valid
        )
        
        valid_tokens = EnhancedToken.objects.get_valid_tokens_for_user(self.user)
        
        self.assertEqual(valid_tokens.count(), 1)
        self.assertEqual(valid_tokens.first(), valid_token)
    
    def test_revoke_all_tokens_for_user(self):
        """Test revoking all tokens for a user."""
        from users.models import EnhancedToken
        
        # Create multiple tokens
        token1 = EnhancedToken.objects.create(user=self.user)
        token2 = EnhancedToken.objects.create(user=self.user)
        
        # Revoke all
        revoked_count = EnhancedToken.objects.revoke_all_for_user(self.user)
        
        self.assertEqual(revoked_count, 2)
        self.assertFalse(EnhancedToken.objects.filter(user=self.user).exists())


class EnhancedTokenAuthenticationTests(APITestCase):
    """Test enhanced token authentication integration."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            display_name='Test User'
        )
    
    def test_authentication_with_enhanced_token(self):
        """Test API authentication using enhanced token."""
        from users.models import EnhancedToken
        
        token = EnhancedToken.objects.create(user=self.user)
        
        # Test authenticated request
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get('/api/v1/users/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_authentication_with_expired_token(self):
        """Test that expired tokens are rejected."""
        from users.models import EnhancedToken
        
        expired_token = EnhancedToken.objects.create(
            user=self.user,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        # Test with expired token
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {expired_token.key}')
        response = self.client.get('/api/v1/users/')
        
        # Either 401 (Unauthorized) or 403 (Forbidden) is acceptable for expired tokens
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_last_used_update_on_authentication(self):
        """Test that last_used is updated when token is used."""
        from users.models import EnhancedToken
        
        token = EnhancedToken.objects.create(user=self.user)
        self.assertIsNone(token.last_used)
        
        # Use token for authentication
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get('/api/v1/users/')
        
        # Reload token and check last_used was updated
        token.refresh_from_db()
        self.assertIsNotNone(token.last_used)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TokenRefreshEndpointTests(APITestCase):
    """Test token refresh endpoint functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            display_name='Test User'
        )
        self.refresh_url = '/api/v1/auth/token/refresh/'
    
    def test_refresh_valid_token(self):
        """Test refreshing a valid token."""
        from users.models import EnhancedToken
        
        # Create a token
        original_token = EnhancedToken.objects.create(user=self.user)
        
        # Request token refresh
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {original_token.key}')
        response = self.client.post(self.refresh_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        
        # New token should be different from original
        new_token_key = response.data['token']
        self.assertNotEqual(original_token.key, new_token_key)
        
        # New token should exist in database
        self.assertTrue(EnhancedToken.objects.filter(key=new_token_key).exists())
    
    def test_refresh_expired_token(self):
        """Test refreshing an expired token should fail."""
        from users.models import EnhancedToken
        
        expired_token = EnhancedToken.objects.create(
            user=self.user,
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {expired_token.key}')
        response = self.client.post(self.refresh_url)
        
        # Should fail with authentication error
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_refresh_invalid_token(self):
        """Test refreshing with invalid token should fail."""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalidtoken123')
        response = self.client.post(self.refresh_url)
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_refresh_no_token(self):
        """Test refresh without authentication should fail."""
        response = self.client.post(self.refresh_url)
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_refresh_creates_new_token(self):
        """Test that refresh creates a new token with extended expiration."""
        from users.models import EnhancedToken
        
        # Create token that will expire soon
        near_expiry = timezone.now() + timedelta(minutes=10)
        original_token = EnhancedToken.objects.create(
            user=self.user,
            expires_at=near_expiry
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {original_token.key}')
        response = self.client.post(self.refresh_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        new_token = EnhancedToken.objects.get(key=response.data['token'])
        
        # New token should have extended expiration
        self.assertTrue(new_token.expires_at > near_expiry)
        self.assertTrue(new_token.expires_at > timezone.now() + timedelta(days=6))  # Should be ~7 days
    
    def test_refresh_removes_old_token(self):
        """Test that refresh removes the old token."""
        from users.models import EnhancedToken
        
        original_token = EnhancedToken.objects.create(user=self.user)
        original_key = original_token.key
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {original_key}')
        response = self.client.post(self.refresh_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Original token should be deleted
        self.assertFalse(EnhancedToken.objects.filter(key=original_key).exists())
    
    def test_refresh_preserves_device_info(self):
        """Test that refresh preserves device information."""
        from users.models import EnhancedToken
        
        device_name = 'Desktop App'
        device_info = {'os': 'Linux', 'version': '1.0.0'}
        
        original_token = EnhancedToken.objects.create(
            user=self.user,
            device_name=device_name,
            device_info=device_info
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {original_token.key}')
        response = self.client.post(self.refresh_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        new_token = EnhancedToken.objects.get(key=response.data['token'])
        
        # Device info should be preserved
        self.assertEqual(new_token.device_name, device_name)
        self.assertEqual(new_token.device_info, device_info)


class EnhancedTokenObtainEndpointTests(APITestCase):
    """Test enhanced token obtain endpoint functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            display_name='Test User'
        )
        self.token_url = '/api/v1/auth/token/'
    
    def test_obtain_enhanced_token_success(self):
        """Test obtaining enhanced token with valid credentials."""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        
        # Token should be an EnhancedToken
        from users.models import EnhancedToken
        token_key = response.data['token']
        self.assertTrue(EnhancedToken.objects.filter(key=token_key).exists())
    
    def test_obtain_enhanced_token_with_device_info(self):
        """Test obtaining enhanced token with device information."""
        data = {
            'username': 'testuser',
            'password': 'testpass123',
            'device_name': 'Mobile App',
            'device_info': {'os': 'Android', 'version': '12'}
        }
        
        response = self.client.post(self.token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check device info was stored
        from users.models import EnhancedToken
        token = EnhancedToken.objects.get(key=response.data['token'])
        self.assertEqual(token.device_name, 'Mobile App')
        self.assertEqual(token.device_info['os'], 'Android')
    
    def test_obtain_token_invalid_credentials(self):
        """Test token obtain with invalid credentials."""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('token', response.data)


class UserRegistrationEndpointTests(APITestCase):
    """Test user registration endpoint functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.register_url = '/api/v1/auth/register/'
    
    def test_register_user_success(self):
        """Test successful user registration."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'testpass123',
            'display_name': 'New User'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'newuser')
        
        # User should exist in database
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.display_name, 'New User')
        
        # Token should be an EnhancedToken
        from users.models import EnhancedToken
        token_key = response.data['token']
        self.assertTrue(EnhancedToken.objects.filter(key=token_key).exists())
    
    def test_register_user_with_device_info(self):
        """Test user registration with device information."""
        data = {
            'username': 'mobileuser',
            'email': 'mobile@example.com',
            'password': 'testpass123',
            'display_name': 'Mobile User',
            'device_name': 'Mobile App',
            'device_info': {'os': 'iOS', 'version': '15.0'}
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check device info was stored with token
        from users.models import EnhancedToken
        token = EnhancedToken.objects.get(key=response.data['token'])
        self.assertEqual(token.device_name, 'Mobile App')
        self.assertEqual(token.device_info['os'], 'iOS')
    
    def test_register_user_duplicate_username(self):
        """Test registration with duplicate username should fail."""
        # Create existing user
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='testpass123'
        )
        
        data = {
            'username': 'existing',
            'email': 'different@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_user_duplicate_email(self):
        """Test registration with duplicate email should fail."""
        # Create existing user
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='testpass123'
        )
        
        data = {
            'username': 'different',
            'email': 'existing@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_user_missing_username(self):
        """Test registration without username should fail."""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_user_missing_password(self):
        """Test registration without password should fail."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_user_invalid_email(self):
        """Test registration with invalid email should fail."""
        data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_user_short_username(self):
        """Test registration with too short username should fail."""
        data = {
            'username': 'ab',  # Less than 3 characters
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_user_invalid_username_chars(self):
        """Test registration with invalid username characters should fail."""
        data = {
            'username': 'user@name',  # Contains invalid character @
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_user_optional_email(self):
        """Test registration without email should work."""
        data = {
            'username': 'noemailuser',
            'password': 'testpass123',
            'display_name': 'No Email User'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        user = User.objects.get(username='noemailuser')
        self.assertIsNone(user.email)
        self.assertEqual(user.display_name, 'No Email User')
    
    def test_register_user_optional_display_name(self):
        """Test registration without display_name should use username."""
        data = {
            'username': 'simpleuser',
            'email': 'simple@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        user = User.objects.get(username='simpleuser')
        self.assertEqual(user.display_name, '')  # Should be empty string, will fallback to username in __str__