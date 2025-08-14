"""
Tests for the user management API endpoints and functionality.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from users.models import EnhancedToken

from tests.factories import UserFactory

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for testing."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Test user for model tests."""
    return UserFactory(
        username='testuser_model',
        email='test@example.com',
        display_name='Test User'
    )


@pytest.mark.unit
@pytest.mark.django_db
class TestUserModel:
    """Test User model methods and properties."""
    
    def test_user_creation(self, test_user):
        """Test user creation with default values."""
        assert test_user.username == 'testuser_model'
        assert test_user.email == 'test@example.com'
        assert test_user.display_name == 'Test User'
        assert test_user.games_played == 0
        assert test_user.games_won == 0
        assert test_user.is_active is True
        assert test_user.is_staff is False
        assert test_user.is_superuser is False
    
    def test_user_string_representation(self, test_user):
        """Test user string representation."""
        str_repr = str(test_user)
        # Should return display_name if available, otherwise username
        assert str_repr == 'Test User'
    
    def test_update_game_stats_win(self, test_user):
        """Test updating game statistics for a win."""
        initial_played = test_user.games_played
        initial_won = test_user.games_won
        
        test_user.update_game_stats(won=True)
        
        assert test_user.games_played == initial_played + 1
        assert test_user.games_won == initial_won + 1
    
    def test_update_game_stats_loss(self, test_user):
        """Test updating game statistics for a loss."""
        initial_played = test_user.games_played
        initial_won = test_user.games_won
        
        test_user.update_game_stats(won=False)
        
        assert test_user.games_played == initial_played + 1
        assert test_user.games_won == initial_won
    
    def test_win_rate_no_games(self, test_user):
        """Test win rate calculation with no games played."""
        assert test_user.win_rate == 0.0
    
    def test_win_rate_with_games(self, test_user):
        """Test win rate calculation with games played."""
        test_user.games_played = 10
        test_user.games_won = 7
        test_user.save()
        
        # Win rate is returned as percentage (70.0%)
        assert test_user.win_rate == 70.0
    
    def test_email_blank_conversion(self, db):
        """Test that blank email is converted to None in save method."""
        user = User(username='testuser_blank_email', email='', display_name='Test User 2')
        
        # Call save to trigger the conversion
        user.save()
        
        # Empty string should be converted to None for proper unique constraint handling
        assert user.email is None
    
    def test_unique_email_constraint(self, db):
        """Test that multiple users can have None email."""
        user1 = User.objects.create_user(username='user_none_email_1', email='')
        user2 = User.objects.create_user(username='user_none_email_2', email='')
        
        # Both should have None email and not conflict
        assert user1.email is None
        assert user2.email is None


@pytest.fixture
def test_users_api(db):
    """Create test users for API tests."""
    user1 = UserFactory(username='user_api_1', email='user1@test.com')
    user2 = UserFactory(username='user_api_2', email='user2@test.com')
    admin_user = UserFactory(
        username='admin_api',
        email='admin@test.com',
        is_staff=True,
        is_superuser=True
    )
    return user1, user2, admin_user


@pytest.fixture
def test_tokens_api(test_users_api):
    """Create enhanced tokens for API test users."""
    user1, user2, admin_user = test_users_api
    user1_token = EnhancedToken.objects.create_for_device(user=user1)
    user2_token = EnhancedToken.objects.create_for_device(user=user2)
    admin_token = EnhancedToken.objects.create_for_device(user=admin_user)
    return user1_token, user2_token, admin_token


@pytest.fixture
def users_url():
    """Users list URL."""
    return reverse('user-list')


@pytest.fixture
def authenticated_client_user1(api_client, test_tokens_api):
    """API client authenticated as user1."""
    user1_token, _, _ = test_tokens_api
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {user1_token.key}')
    return api_client


@pytest.fixture
def authenticated_client_user2(api_client, test_tokens_api):
    """API client authenticated as user2."""
    _, user2_token, _ = test_tokens_api
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {user2_token.key}')
    return api_client


@pytest.fixture
def authenticated_client_admin(api_client, test_tokens_api):
    """API client authenticated as admin."""
    _, _, admin_token = test_tokens_api
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
    return api_client


@pytest.mark.api
@pytest.mark.django_db
class TestUserAPI:
    """Test User API endpoints."""
    
    def test_list_users(self, authenticated_client_user1, test_users_api, users_url):
        """Test listing users."""
        user1, user2, admin_user = test_users_api
        
        response = authenticated_client_user1.get(users_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        
        # Check that users are included
        usernames = [user['username'] for user in response.data['results']]
        assert 'user_api_1' in usernames
        assert 'user_api_2' in usernames
        assert 'admin_api' in usernames
    
    def test_list_users_unauthenticated(self, api_client, users_url):
        """Test listing users without authentication."""
        response = api_client.get(users_url)
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        assert 'error' in response.data
    
    def test_retrieve_user(self, authenticated_client_user1, test_users_api):
        """Test retrieving a specific user."""
        user1, user2, admin_user = test_users_api
        
        user_url = reverse('user-detail', kwargs={'pk': user2.id})
        response = authenticated_client_user1.get(user_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == user2.id
        assert response.data['username'] == 'user_api_2'
        assert response.data['display_name'] == user2.display_name
    
    def test_retrieve_own_profile(self, authenticated_client_user1, test_users_api):
        """Test retrieving own user profile."""
        user1, user2, admin_user = test_users_api
        
        user_url = reverse('user-detail', kwargs={'pk': user1.id})
        response = authenticated_client_user1.get(user_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == user1.id
        assert response.data['username'] == 'user_api_1'
    
    def test_retrieve_nonexistent_user(self, authenticated_client_user1):
        """Test retrieving a non-existent user."""
        user_url = reverse('user-detail', kwargs={'pk': 99999})
        response = authenticated_client_user1.get(user_url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
    
    def test_create_user(self, authenticated_client_user1, users_url):
        """Test creating a new user."""
        data = {
            'username': 'newuser_api',
            'email': 'newuser@test.com',
            'password': 'securepassword123',
            'display_name': 'New User'
        }
        
        response = authenticated_client_user1.post(users_url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        assert response.data['username'] == 'newuser_api'
        assert response.data['display_name'] == 'New User'
        
        # Verify user was created in database
        user = User.objects.get(username='newuser_api')
        assert user.email == 'newuser@test.com'
        assert user.check_password('securepassword123')
    
    def test_create_user_missing_fields(self, authenticated_client_user1, users_url):
        """Test creating user with missing required fields."""
        data = {
            'email': 'incomplete@test.com',
            # Missing username and password
        }
        
        response = authenticated_client_user1.post(users_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_create_user_duplicate_username(self, api_client, test_users_api, users_url):
        """Test creating user with duplicate username."""
        user1, user2, admin_user = test_users_api
        
        data = {
            'username': 'user_api_1',  # Already exists
            'email': 'different@test.com',
            'password': 'securepassword123',
            'display_name': 'Different User'
        }
        
        response = api_client.post(users_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_create_user_duplicate_email(self, api_client, test_users_api, users_url):
        """Test creating user with duplicate email."""
        user1, user2, admin_user = test_users_api
        
        data = {
            'username': 'newuser_dup_email',
            'email': 'user1@test.com',  # Already exists
            'password': 'securepassword123',
            'display_name': 'Another User'
        }
        
        response = api_client.post(users_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_create_user_blank_email(self, authenticated_client_user1, users_url):
        """Test creating user with blank email (should be allowed)."""
        data = {
            'username': 'noemailuser_api',
            'email': '',
            'password': 'securepassword123',
            'display_name': 'No Email User'
        }
        
        response = authenticated_client_user1.post(users_url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify user was created with None email
        user = User.objects.get(username='noemailuser_api')
        assert user.email is None
    
    def test_update_user_own_profile(self, authenticated_client_user1, test_users_api):
        """Test updating own user profile."""
        user1, user2, admin_user = test_users_api
        
        user_url = reverse('user-detail', kwargs={'pk': user1.id})
        data = {
            'display_name': 'Updated Display Name'
        }
        
        response = authenticated_client_user1.patch(user_url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['display_name'] == 'Updated Display Name'
        
        # Verify update in database
        user1.refresh_from_db()
        assert user1.display_name == 'Updated Display Name'
    
    def test_update_other_user_profile_allowed(self, authenticated_client_user1, test_users_api):
        """Test updating another user's profile (currently allowed)."""
        user1, user2, admin_user = test_users_api
        
        user_url = reverse('user-detail', kwargs={'pk': user2.id})
        data = {
            'display_name': 'Updated Display Name'
        }
        
        response = authenticated_client_user1.patch(user_url, data, format='json')
        
        # Currently no permissions restriction
        assert response.status_code == status.HTTP_200_OK
        assert response.data['display_name'] == 'Updated Display Name'
    
    def test_update_user_username_allowed(self, authenticated_client_user1, test_users_api):
        """Test that username can be updated (currently not readonly)."""
        user1, user2, admin_user = test_users_api
        
        user_url = reverse('user-detail', kwargs={'pk': user1.id})
        data = {
            'username': 'newusername_api'
        }
        
        response = authenticated_client_user1.patch(user_url, data, format='json')
        
        # Username can be updated in current implementation
        user1.refresh_from_db()
        assert user1.username == 'newusername_api'
    
    def test_delete_user_soft_delete(self, authenticated_client_user1, test_users_api):
        """Test that deleting users performs soft delete."""
        user1, user2, admin_user = test_users_api
        
        user_url = reverse('user-detail', kwargs={'pk': user1.id})
        response = authenticated_client_user1.delete(user_url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify user is soft-deleted (is_active = False)
        user1.refresh_from_db()
        assert user1.is_active is False
    
    def test_get_user_stats(self, authenticated_client_user1, test_users_api):
        """Test getting user statistics."""
        user1, user2, admin_user = test_users_api
        
        # Update user stats
        user1.games_played = 10
        user1.games_won = 7
        user1.save()
        
        user_url = reverse('user-detail', kwargs={'pk': user1.id})
        response = authenticated_client_user1.get(user_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['games_played'] == 10
        assert response.data['games_won'] == 7
        assert response.data['win_rate'] == 70.0  # Percentage format


@pytest.fixture
def auth_test_user(db):
    """Test user for authentication tests."""
    user = UserFactory(username='testuser_auth', email='test@example.com')
    user.set_password('testpassword123')
    user.save()
    return user


@pytest.fixture
def token_url():
    """Token authentication URL."""
    return reverse('api_token_auth')


@pytest.mark.api
@pytest.mark.django_db
class TestAuthenticationAPI:
    """Test authentication API endpoints."""
    
    def test_get_token_success(self, api_client, auth_test_user, token_url):
        """Test successful token authentication."""
        data = {
            'username': 'testuser_auth',
            'password': 'testpassword123'
        }
        
        response = api_client.post(token_url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data
        assert response.data['token'] is not None
    
    def test_get_token_invalid_credentials(self, api_client, auth_test_user, token_url):
        """Test token authentication with invalid credentials."""
        data = {
            'username': 'testuser_auth',
            'password': 'wrongpassword'
        }
        
        response = api_client.post(token_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_get_token_missing_username(self, api_client, auth_test_user, token_url):
        """Test token authentication with missing username."""
        data = {
            'password': 'testpassword123'
        }
        
        response = api_client.post(token_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_get_token_missing_password(self, api_client, auth_test_user, token_url):
        """Test token authentication with missing password."""
        data = {
            'username': 'testuser_auth'
        }
        
        response = api_client.post(token_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_get_token_inactive_user(self, api_client, auth_test_user, token_url):
        """Test token authentication with inactive user."""
        auth_test_user.is_active = False
        auth_test_user.save()
        
        data = {
            'username': 'testuser_auth',
            'password': 'testpassword123'
        }
        
        response = api_client.post(token_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_token_authentication_in_api(self, api_client, auth_test_user, token_url):
        """Test using token for API authentication."""
        # Create an EnhancedToken directly for reliable authentication
        enhanced_token = EnhancedToken.objects.create_for_device(user=auth_test_user)
        
        # Use token for API request
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {enhanced_token.key}')
        users_url = reverse('user-list')
        response = api_client.get(users_url)
        
        # Should be successful (not 401/403)
        assert response.status_code == status.HTTP_200_OK
    
    def test_invalid_token_authentication(self, api_client):
        """Test API request with invalid token."""
        api_client.credentials(HTTP_AUTHORIZATION='Token invalidtoken123')
        users_url = reverse('user-list')
        response = api_client.get(users_url)
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        assert 'error' in response.data


@pytest.fixture
def permission_test_users(db):
    """Create test users for permission tests."""
    regular_user = UserFactory(username='regular_perm', email='regular@test.com')
    staff_user = UserFactory(
        username='staff_perm',
        email='staff@test.com',
        is_staff=True
    )
    admin_user = UserFactory(
        username='admin_perm',
        email='admin@test.com',
        is_staff=True,
        is_superuser=True
    )
    return regular_user, staff_user, admin_user


@pytest.fixture
def permission_test_tokens(permission_test_users):
    """Create enhanced tokens for permission test users."""
    regular_user, staff_user, admin_user = permission_test_users
    regular_token = EnhancedToken.objects.create_for_device(user=regular_user)
    staff_token = EnhancedToken.objects.create_for_device(user=staff_user)
    admin_token = EnhancedToken.objects.create_for_device(user=admin_user)
    return regular_token, staff_token, admin_token


@pytest.mark.api
@pytest.mark.django_db
class TestUserPermissions:
    """Test user permission and authorization scenarios."""
    
    def test_regular_user_can_view_own_profile(self, api_client, permission_test_users, permission_test_tokens):
        """Test that regular users can view their own profile."""
        regular_user, staff_user, admin_user = permission_test_users
        regular_token, staff_token, admin_token = permission_test_tokens
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {regular_token.key}')
        
        user_url = reverse('user-detail', kwargs={'pk': regular_user.id})
        response = api_client.get(user_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'regular_perm'
    
    def test_regular_user_can_update_own_profile(self, api_client, permission_test_users, permission_test_tokens):
        """Test that regular users can update their own profile."""
        regular_user, staff_user, admin_user = permission_test_users
        regular_token, staff_token, admin_token = permission_test_tokens
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {regular_token.key}')
        
        user_url = reverse('user-detail', kwargs={'pk': regular_user.id})
        data = {'display_name': 'Updated Name'}
        response = api_client.patch(user_url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['display_name'] == 'Updated Name'
    
    def test_regular_user_can_update_other_profiles(self, api_client, permission_test_users, permission_test_tokens):
        """Test that regular users can update other profiles (no restrictions currently)."""
        regular_user, staff_user, admin_user = permission_test_users
        regular_token, staff_token, admin_token = permission_test_tokens
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {regular_token.key}')
        
        user_url = reverse('user-detail', kwargs={'pk': staff_user.id})
        data = {'display_name': 'Updated Name'}
        response = api_client.patch(user_url, data, format='json')
        
        # Currently no permission restrictions
        assert response.status_code == status.HTTP_200_OK
        assert response.data['display_name'] == 'Updated Name'
    
    def test_admin_user_has_full_access(self, api_client, permission_test_users, permission_test_tokens):
        """Test that admin users have full access."""
        regular_user, staff_user, admin_user = permission_test_users
        regular_token, staff_token, admin_token = permission_test_tokens
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        
        # Admin should be able to view all users
        users_url = reverse('user-list')
        response = api_client.get(users_url)
        assert response.status_code == status.HTTP_200_OK
        
        # Admin should be able to view other user's profile
        user_url = reverse('user-detail', kwargs={'pk': regular_user.id})
        response = api_client.get(user_url)
        assert response.status_code == status.HTTP_200_OK