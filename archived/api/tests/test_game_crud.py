"""
Tests for game CRUD operations via API endpoints.
"""

import uuid
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from users.models import EnhancedToken

from games.models import Game, RuleSet, GameStatus, Player
from tests.factories import UserFactory, GameFactory, RuleSetFactory

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for testing."""
    return APIClient()


@pytest.fixture
def test_users(db):
    """Create test users for game CRUD tests."""
    user1 = UserFactory(username='game_crud_player1', email='gc_p1@test.com')
    user2 = UserFactory(username='game_crud_player2', email='gc_p2@test.com')
    user3 = UserFactory(username='game_crud_player3', email='gc_p3@test.com')
    return user1, user2, user3


@pytest.fixture
def test_tokens(test_users):
    """Create enhanced tokens for test users."""
    user1, user2, user3 = test_users
    token1 = EnhancedToken.objects.create_for_device(user=user1)
    token2 = EnhancedToken.objects.create_for_device(user=user2)
    return token1, token2


@pytest.fixture
def test_ruleset(db):
    """Create test ruleset."""
    return RuleSetFactory()


@pytest.fixture
def games_url():
    """Games list URL."""
    return reverse('game-list')


@pytest.fixture
def authenticated_client_user1(api_client, test_tokens):
    """API client authenticated as user1."""
    token1, _ = test_tokens
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
    return api_client


@pytest.fixture
def authenticated_client_user2(api_client, test_tokens):
    """API client authenticated as user2."""
    _, token2 = test_tokens
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token2.key}')
    return api_client


@pytest.mark.api
@pytest.mark.django_db
class TestGameCRUD:
    """Test game CRUD operations."""
    
    def test_create_game_success(self, authenticated_client_user1, test_users, test_ruleset, games_url):
        """Test successful game creation."""
        user1, user2, _ = test_users
        
        data = {
            'black_player_id': user1.id,
            'white_player_id': user2.id,
            'ruleset_id': test_ruleset.id
        }
        
        response = authenticated_client_user1.post(games_url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        assert response.data['status'] == GameStatus.WAITING
        
        # Verify game was created in database
        game_id = response.data['id']
        game = Game.objects.get(id=game_id)
        assert game.black_player == user1
        assert game.white_player == user2
        assert game.ruleset == test_ruleset
    
    def test_create_game_same_players_error(self, authenticated_client_user1, test_users, test_ruleset, games_url):
        """Test creating game with same player as black and white."""
        user1, _, _ = test_users
        
        data = {
            'black_player_id': user1.id,
            'white_player_id': user1.id,  # Same player
            'ruleset_id': test_ruleset.id
        }
        
        response = authenticated_client_user1.post(games_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_create_game_invalid_ruleset(self, authenticated_client_user1, test_users, games_url):
        """Test creating game with invalid ruleset."""
        user1, user2, _ = test_users
        
        data = {
            'black_player_id': user1.id,
            'white_player_id': user2.id,
            'ruleset_id': 99999  # Non-existent ruleset
        }
        
        response = authenticated_client_user1.post(games_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_create_game_missing_fields(self, authenticated_client_user1, test_users, games_url):
        """Test creating game with missing required fields."""
        user1, _, _ = test_users
        
        data = {
            'black_player_id': user1.id,
            # Missing white_player_id and ruleset_id
        }
        
        response = authenticated_client_user1.post(games_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_create_game_unauthenticated(self, api_client, test_users, test_ruleset, games_url):
        """Test creating game without authentication."""
        user1, user2, _ = test_users
        
        data = {
            'black_player_id': user1.id,
            'white_player_id': user2.id,
            'ruleset_id': test_ruleset.id
        }
        
        response = api_client.post(games_url, data, format='json')
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        assert 'error' in response.data
    
    def test_list_games(self, authenticated_client_user1, test_users, games_url):
        """Test listing games."""
        user1, user2, user3 = test_users
        
        # Create some games
        game1 = GameFactory(black_player=user1, white_player=user2)
        game2 = GameFactory(black_player=user2, white_player=user3)
        game3 = GameFactory(black_player=user1, white_player=user3)
        
        response = authenticated_client_user1.get(games_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        
        game_ids = [game['id'] for game in response.data['results']]
        assert str(game1.id) in game_ids
        assert str(game2.id) in game_ids
        assert str(game3.id) in game_ids
    
    def test_retrieve_game(self, authenticated_client_user1, test_users):
        """Test retrieving a specific game."""
        user1, user2, _ = test_users
        
        game = GameFactory(black_player=user1, white_player=user2)
        game_url = reverse('game-detail', kwargs={'pk': game.id})
        
        response = authenticated_client_user1.get(game_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(game.id)
        assert response.data['black_player']['id'] == user1.id
        assert response.data['white_player']['id'] == user2.id
    
    def test_retrieve_nonexistent_game(self, authenticated_client_user1):
        """Test retrieving a non-existent game."""
        fake_id = uuid.uuid4()
        game_url = reverse('game-detail', kwargs={'pk': fake_id})
        
        response = authenticated_client_user1.get(game_url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
    
    def test_update_game_not_allowed(self, authenticated_client_user1, test_users):
        """Test that PUT/PATCH updates are not allowed for games."""
        user1, user2, user3 = test_users
        
        game = GameFactory(black_player=user1, white_player=user2)
        game_url = reverse('game-detail', kwargs={'pk': game.id})
        
        data = {
            'black_player_id': user3.id,  # Try to change player
        }
        
        # Try PUT
        response = authenticated_client_user1.put(game_url, data, format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        
        # Try PATCH
        response = authenticated_client_user1.patch(game_url, data, format='json')
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    def test_delete_game_not_allowed(self, authenticated_client_user1, test_users):
        """Test that DELETE is not allowed for games."""
        user1, user2, _ = test_users
        
        game = GameFactory(black_player=user1, white_player=user2)
        game_url = reverse('game-detail', kwargs={'pk': game.id})
        
        response = authenticated_client_user1.delete(game_url)
        
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    def test_game_serialization_includes_related_data(self, authenticated_client_user1, test_users, test_ruleset):
        """Test that game serialization includes related player and ruleset data."""
        user1, user2, _ = test_users
        
        game = GameFactory(
            black_player=user1, 
            white_player=user2,
            ruleset=test_ruleset
        )
        game_url = reverse('game-detail', kwargs={'pk': game.id})
        
        response = authenticated_client_user1.get(game_url)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check that related data is included
        assert 'black_player' in response.data
        assert 'white_player' in response.data
        assert 'ruleset' in response.data
        
        # Check player data structure
        assert response.data['black_player']['username'] == 'game_crud_player1'
        assert response.data['white_player']['username'] == 'game_crud_player2'
        
        # Check ruleset data
        assert response.data['ruleset']['id'] == test_ruleset.id


@pytest.fixture
def action_test_users(db):
    """Create test users for game action tests."""
    user1 = UserFactory(username='action_player1')
    user2 = UserFactory(username='action_player2')
    return user1, user2


@pytest.fixture
def action_test_tokens(action_test_users):
    """Create enhanced tokens for action test users."""
    user1, user2 = action_test_users
    token1 = EnhancedToken.objects.create_for_device(user=user1)
    token2 = EnhancedToken.objects.create_for_device(user=user2)
    return token1, token2


@pytest.fixture
def action_test_game(action_test_users):
    """Create test game for action tests."""
    user1, user2 = action_test_users
    return GameFactory(black_player=user1, white_player=user2)


@pytest.fixture
def authenticated_action_client_user1(api_client, action_test_tokens):
    """API client authenticated as action test user1."""
    token1, _ = action_test_tokens
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
    return api_client


@pytest.fixture
def authenticated_action_client_user2(api_client, action_test_tokens):
    """API client authenticated as action test user2."""
    _, token2 = action_test_tokens
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token2.key}')
    return api_client


@pytest.mark.api
@pytest.mark.django_db
class TestGameActions:
    """Test game action endpoints (start, move, resign)."""
    
    def test_start_game_success(self, authenticated_action_client_user1, action_test_game):
        """Test starting a game successfully."""
        start_url = reverse('game-start', kwargs={'pk': action_test_game.id})
        response = authenticated_action_client_user1.post(start_url)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Refresh game from database
        action_test_game.refresh_from_db()
        assert action_test_game.status == GameStatus.ACTIVE
        assert action_test_game.started_at is not None
        assert action_test_game.current_player == Player.BLACK
    
    def test_start_already_active_game(self, authenticated_action_client_user1, action_test_game):
        """Test starting an already active game."""
        # Start game first time
        action_test_game.start_game()
        
        start_url = reverse('game-start', kwargs={'pk': action_test_game.id})
        response = authenticated_action_client_user1.post(start_url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_get_game_moves_empty(self, authenticated_action_client_user1, action_test_game):
        """Test getting moves from a game with no moves."""
        moves_url = reverse('game-moves', kwargs={'pk': action_test_game.id})
        response = authenticated_action_client_user1.get(moves_url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0
    
    def test_unauthenticated_game_actions(self, api_client, action_test_game):
        """Test that game actions require authentication."""
        start_url = reverse('game-start', kwargs={'pk': action_test_game.id})
        moves_url = reverse('game-moves', kwargs={'pk': action_test_game.id})
        
        # Test without authentication
        response = api_client.post(start_url)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        
        response = api_client.get(moves_url)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]