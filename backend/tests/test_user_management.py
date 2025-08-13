"""
Tests for the user management API endpoints and functionality.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from tests.factories import UserFactory

User = get_user_model()


class UserModelTests(TestCase):
    """Test User model methods and properties."""
    
    def setUp(self):
        """Set up test data."""
        self.user = UserFactory(
            username='testuser',
            email='test@example.com',
            display_name='Test User'
        )
    
    def test_user_creation(self):
        """Test user creation with default values."""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.display_name, 'Test User')
        self.assertEqual(self.user.games_played, 0)
        self.assertEqual(self.user.games_won, 0)
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
    
    def test_user_string_representation(self):
        """Test user string representation."""
        str_repr = str(self.user)
        # Should return display_name if available, otherwise username
        self.assertEqual(str_repr, 'Test User')
    
    def test_update_game_stats_win(self):
        """Test updating game statistics for a win."""
        initial_played = self.user.games_played
        initial_won = self.user.games_won
        
        self.user.update_game_stats(won=True)
        
        self.assertEqual(self.user.games_played, initial_played + 1)
        self.assertEqual(self.user.games_won, initial_won + 1)
    
    def test_update_game_stats_loss(self):
        """Test updating game statistics for a loss."""
        initial_played = self.user.games_played
        initial_won = self.user.games_won
        
        self.user.update_game_stats(won=False)
        
        self.assertEqual(self.user.games_played, initial_played + 1)
        self.assertEqual(self.user.games_won, initial_won)
    
    def test_win_rate_no_games(self):
        """Test win rate calculation with no games played."""
        self.assertEqual(self.user.win_rate, 0.0)
    
    def test_win_rate_with_games(self):
        """Test win rate calculation with games played."""
        self.user.games_played = 10
        self.user.games_won = 7
        self.user.save()
        
        # Win rate is returned as percentage (70.0%)
        self.assertEqual(self.user.win_rate, 70.0)
    
    def test_email_blank_conversion(self):
        """Test that blank email is converted to None in save method."""
        user = User(username='testuser2', email='', display_name='Test User 2')
        
        # Call save to trigger the conversion
        user.save()
        
        # Empty string should be converted to None for proper unique constraint handling
        self.assertIsNone(user.email)
    
    def test_unique_email_constraint(self):
        """Test that multiple users can have None email."""
        user1 = User.objects.create_user(username='user1', email='')
        user2 = User.objects.create_user(username='user2', email='')
        
        # Both should have None email and not conflict
        self.assertIsNone(user1.email)
        self.assertIsNone(user2.email)


class UserAPITests(APITestCase):
    """Test User API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create test users
        self.user1 = UserFactory(username='user1', email='user1@test.com')
        self.user2 = UserFactory(username='user2', email='user2@test.com')
        self.admin_user = UserFactory(
            username='admin',
            email='admin@test.com',
            is_staff=True,
            is_superuser=True
        )
        
        # Create tokens
        self.user1_token = Token.objects.create(user=self.user1)
        self.user2_token = Token.objects.create(user=self.user2)
        self.admin_token = Token.objects.create(user=self.admin_user)
        
        # URLs
        self.users_url = reverse('user-list')
    
    def authenticate_user1(self):
        """Authenticate as user1."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user1_token.key}')
    
    def authenticate_user2(self):
        """Authenticate as user2."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user2_token.key}')
    
    def authenticate_admin(self):
        """Authenticate as admin."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
    
    def test_list_users(self):
        """Test listing users."""
        self.authenticate_user1()
        
        response = self.client.get(self.users_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        
        # Check that users are included
        usernames = [user['username'] for user in response.data['results']]
        self.assertIn('user1', usernames)
        self.assertIn('user2', usernames)
        self.assertIn('admin', usernames)
    
    def test_list_users_unauthenticated(self):
        """Test listing users without authentication."""
        response = self.client.get(self.users_url)
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        self.assertIn('error', response.data)
    
    def test_retrieve_user(self):
        """Test retrieving a specific user."""
        self.authenticate_user1()
        
        user_url = reverse('user-detail', kwargs={'pk': self.user2.id})
        response = self.client.get(user_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.user2.id)
        self.assertEqual(response.data['username'], 'user2')
        self.assertEqual(response.data['display_name'], self.user2.display_name)
    
    def test_retrieve_own_profile(self):
        """Test retrieving own user profile."""
        self.authenticate_user1()
        
        user_url = reverse('user-detail', kwargs={'pk': self.user1.id})
        response = self.client.get(user_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.user1.id)
        self.assertEqual(response.data['username'], 'user1')
    
    def test_retrieve_nonexistent_user(self):
        """Test retrieving a non-existent user."""
        self.authenticate_user1()
        
        user_url = reverse('user-detail', kwargs={'pk': 99999})
        response = self.client.get(user_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
    
    def test_create_user(self):
        """Test creating a new user."""
        # User creation requires authentication
        self.authenticate_user1()
        
        data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'securepassword123',
            'display_name': 'New User'
        }
        
        response = self.client.post(self.users_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['username'], 'newuser')
        self.assertEqual(response.data['display_name'], 'New User')
        
        # Verify user was created in database
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@test.com')
        self.assertTrue(user.check_password('securepassword123'))
    
    def test_create_user_missing_fields(self):
        """Test creating user with missing required fields."""
        self.authenticate_user1()
        
        data = {
            'email': 'incomplete@test.com',
            # Missing username and password
        }
        
        response = self.client.post(self.users_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_create_user_duplicate_username(self):
        """Test creating user with duplicate username."""
        data = {
            'username': 'user1',  # Already exists
            'email': 'different@test.com',
            'password': 'securepassword123',
            'display_name': 'Different User'
        }
        
        response = self.client.post(self.users_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_create_user_duplicate_email(self):
        """Test creating user with duplicate email."""
        data = {
            'username': 'newuser2',
            'email': 'user1@test.com',  # Already exists
            'password': 'securepassword123',
            'display_name': 'Another User'
        }
        
        response = self.client.post(self.users_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_create_user_blank_email(self):
        """Test creating user with blank email (should be allowed)."""
        data = {
            'username': 'noemailuser',
            'email': '',
            'password': 'securepassword123',
            'display_name': 'No Email User'
        }
        
        response = self.client.post(self.users_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify user was created with None email
        user = User.objects.get(username='noemailuser')
        self.assertIsNone(user.email)
    
    def test_update_user_own_profile(self):
        """Test updating own user profile."""
        self.authenticate_user1()
        
        user_url = reverse('user-detail', kwargs={'pk': self.user1.id})
        data = {
            'display_name': 'Updated Display Name'
        }
        
        response = self.client.patch(user_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Updated Display Name')
        
        # Verify update in database
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.display_name, 'Updated Display Name')
    
    def test_update_other_user_profile_allowed(self):
        """Test updating another user's profile (currently allowed)."""
        self.authenticate_user1()
        
        user_url = reverse('user-detail', kwargs={'pk': self.user2.id})
        data = {
            'display_name': 'Updated Display Name'
        }
        
        response = self.client.patch(user_url, data, format='json')
        
        # Currently no permissions restriction
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Updated Display Name')
    
    def test_update_user_username_allowed(self):
        """Test that username can be updated (currently not readonly)."""
        self.authenticate_user1()
        
        user_url = reverse('user-detail', kwargs={'pk': self.user1.id})
        data = {
            'username': 'newusername'
        }
        
        response = self.client.patch(user_url, data, format='json')
        
        # Username can be updated in current implementation
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.username, 'newusername')
    
    def test_delete_user_soft_delete(self):
        """Test that deleting users performs soft delete."""
        self.authenticate_user1()
        
        user_url = reverse('user-detail', kwargs={'pk': self.user1.id})
        response = self.client.delete(user_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify user is soft-deleted (is_active = False)
        self.user1.refresh_from_db()
        self.assertFalse(self.user1.is_active)
    
    def test_get_user_stats(self):
        """Test getting user statistics."""
        self.authenticate_user1()
        
        # Update user stats
        self.user1.games_played = 10
        self.user1.games_won = 7
        self.user1.save()
        
        user_url = reverse('user-detail', kwargs={'pk': self.user1.id})
        response = self.client.get(user_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['games_played'], 10)
        self.assertEqual(response.data['games_won'], 7)
        self.assertEqual(response.data['win_rate'], 70.0)  # Percentage format


class AuthenticationAPITests(APITestCase):
    """Test authentication API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = UserFactory(username='testuser', email='test@example.com')
        self.user.set_password('testpassword123')
        self.user.save()
        
        self.token_url = reverse('api_token_auth')
    
    def test_get_token_success(self):
        """Test successful token authentication."""
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        
        response = self.client.post(self.token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIsNotNone(response.data['token'])
    
    def test_get_token_invalid_credentials(self):
        """Test token authentication with invalid credentials."""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_get_token_missing_username(self):
        """Test token authentication with missing username."""
        data = {
            'password': 'testpassword123'
        }
        
        response = self.client.post(self.token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_get_token_missing_password(self):
        """Test token authentication with missing password."""
        data = {
            'username': 'testuser'
        }
        
        response = self.client.post(self.token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_get_token_inactive_user(self):
        """Test token authentication with inactive user."""
        self.user.is_active = False
        self.user.save()
        
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        
        response = self.client.post(self.token_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_token_authentication_in_api(self):
        """Test using token for API authentication."""
        # First get a token
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        
        token_response = self.client.post(self.token_url, data, format='json')
        token = token_response.data['token']
        
        # Use token for API request
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        users_url = reverse('user-list')
        response = self.client.get(users_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_invalid_token_authentication(self):
        """Test API request with invalid token."""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalidtoken123')
        users_url = reverse('user-list')
        response = self.client.get(users_url)
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        self.assertIn('error', response.data)


class UserPermissionTests(APITestCase):
    """Test user permission and authorization scenarios."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.regular_user = UserFactory(username='regular', email='regular@test.com')
        self.staff_user = UserFactory(
            username='staff',
            email='staff@test.com',
            is_staff=True
        )
        self.admin_user = UserFactory(
            username='admin',
            email='admin@test.com',
            is_staff=True,
            is_superuser=True
        )
        
        self.regular_token = Token.objects.create(user=self.regular_user)
        self.staff_token = Token.objects.create(user=self.staff_user)
        self.admin_token = Token.objects.create(user=self.admin_user)
    
    def test_regular_user_can_view_own_profile(self):
        """Test that regular users can view their own profile."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.regular_token.key}')
        
        user_url = reverse('user-detail', kwargs={'pk': self.regular_user.id})
        response = self.client.get(user_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'regular')
    
    def test_regular_user_can_update_own_profile(self):
        """Test that regular users can update their own profile."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.regular_token.key}')
        
        user_url = reverse('user-detail', kwargs={'pk': self.regular_user.id})
        data = {'display_name': 'Updated Name'}
        response = self.client.patch(user_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Updated Name')
    
    def test_regular_user_can_update_other_profiles(self):
        """Test that regular users can update other profiles (no restrictions currently)."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.regular_token.key}')
        
        user_url = reverse('user-detail', kwargs={'pk': self.staff_user.id})
        data = {'display_name': 'Updated Name'}
        response = self.client.patch(user_url, data, format='json')
        
        # Currently no permission restrictions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['display_name'], 'Updated Name')
    
    def test_admin_user_has_full_access(self):
        """Test that admin users have full access."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        
        # Admin should be able to view all users
        users_url = reverse('user-list')
        response = self.client.get(users_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Admin should be able to view other user's profile
        user_url = reverse('user-detail', kwargs={'pk': self.regular_user.id})
        response = self.client.get(user_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)