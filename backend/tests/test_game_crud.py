"""
Tests for game CRUD operations via API endpoints.
"""

import uuid
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from games.models import Game, RuleSet, GameStatus, Player
from tests.factories import UserFactory, GameFactory, RuleSetFactory

User = get_user_model()


class GameCRUDTests(APITestCase):
    """Test game CRUD operations."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        # Create test users
        self.user1 = UserFactory(username='player1', email='p1@test.com')
        self.user2 = UserFactory(username='player2', email='p2@test.com')
        self.user3 = UserFactory(username='player3', email='p3@test.com')
        
        # Create tokens
        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)
        
        # Create ruleset
        self.ruleset = RuleSetFactory()
        
        # URLs
        self.games_url = reverse('game-list')
    
    def authenticate_user1(self):
        """Authenticate as user1."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
    
    def authenticate_user2(self):
        """Authenticate as user2."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token2.key}')
    
    def test_create_game_success(self):
        """Test successful game creation."""
        self.authenticate_user1()
        
        data = {
            'black_player_id': self.user1.id,
            'white_player_id': self.user2.id,
            'ruleset_id': self.ruleset.id
        }
        
        response = self.client.post(self.games_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['status'], GameStatus.WAITING)
        
        # Verify game was created in database
        game_id = response.data['id']
        game = Game.objects.get(id=game_id)
        self.assertEqual(game.black_player, self.user1)
        self.assertEqual(game.white_player, self.user2)
        self.assertEqual(game.ruleset, self.ruleset)
    
    def test_create_game_same_players_error(self):
        """Test creating game with same player as black and white."""
        self.authenticate_user1()
        
        data = {
            'black_player_id': self.user1.id,
            'white_player_id': self.user1.id,  # Same player
            'ruleset_id': self.ruleset.id
        }
        
        response = self.client.post(self.games_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_create_game_invalid_ruleset(self):
        """Test creating game with invalid ruleset."""
        self.authenticate_user1()
        
        data = {
            'black_player_id': self.user1.id,
            'white_player_id': self.user2.id,
            'ruleset_id': 99999  # Non-existent ruleset
        }
        
        response = self.client.post(self.games_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_create_game_missing_fields(self):
        """Test creating game with missing required fields."""
        self.authenticate_user1()
        
        data = {
            'black_player_id': self.user1.id,
            # Missing white_player_id and ruleset_id
        }
        
        response = self.client.post(self.games_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_create_game_unauthenticated(self):
        """Test creating game without authentication."""
        data = {
            'black_player_id': self.user1.id,
            'white_player_id': self.user2.id,
            'ruleset_id': self.ruleset.id
        }
        
        response = self.client.post(self.games_url, data, format='json')
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        self.assertIn('error', response.data)
    
    def test_list_games(self):
        """Test listing games."""
        self.authenticate_user1()
        
        # Create some games
        game1 = GameFactory(black_player=self.user1, white_player=self.user2)
        game2 = GameFactory(black_player=self.user2, white_player=self.user3)
        game3 = GameFactory(black_player=self.user1, white_player=self.user3)
        
        response = self.client.get(self.games_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        
        game_ids = [game['id'] for game in response.data['results']]
        self.assertIn(str(game1.id), game_ids)
        self.assertIn(str(game2.id), game_ids)
        self.assertIn(str(game3.id), game_ids)
    
    def test_retrieve_game(self):
        """Test retrieving a specific game."""
        self.authenticate_user1()
        
        game = GameFactory(black_player=self.user1, white_player=self.user2)
        game_url = reverse('game-detail', kwargs={'pk': game.id})
        
        response = self.client.get(game_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(game.id))
        self.assertEqual(response.data['black_player']['id'], self.user1.id)
        self.assertEqual(response.data['white_player']['id'], self.user2.id)
    
    def test_retrieve_nonexistent_game(self):
        """Test retrieving a non-existent game."""
        self.authenticate_user1()
        
        fake_id = uuid.uuid4()
        game_url = reverse('game-detail', kwargs={'pk': fake_id})
        
        response = self.client.get(game_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
    
    def test_update_game_not_allowed(self):
        """Test that PUT/PATCH updates are not allowed for games."""
        self.authenticate_user1()
        
        game = GameFactory(black_player=self.user1, white_player=self.user2)
        game_url = reverse('game-detail', kwargs={'pk': game.id})
        
        data = {
            'black_player_id': self.user3.id,  # Try to change player
        }
        
        # Try PUT
        response = self.client.put(game_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Try PATCH
        response = self.client.patch(game_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_delete_game_not_allowed(self):
        """Test that DELETE is not allowed for games."""
        self.authenticate_user1()
        
        game = GameFactory(black_player=self.user1, white_player=self.user2)
        game_url = reverse('game-detail', kwargs={'pk': game.id})
        
        response = self.client.delete(game_url)
        
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_game_serialization_includes_related_data(self):
        """Test that game serialization includes related player and ruleset data."""
        self.authenticate_user1()
        
        game = GameFactory(
            black_player=self.user1, 
            white_player=self.user2,
            ruleset=self.ruleset
        )
        game_url = reverse('game-detail', kwargs={'pk': game.id})
        
        response = self.client.get(game_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that related data is included
        self.assertIn('black_player', response.data)
        self.assertIn('white_player', response.data)
        self.assertIn('ruleset', response.data)
        
        # Check player data structure
        self.assertEqual(response.data['black_player']['username'], 'player1')
        self.assertEqual(response.data['white_player']['username'], 'player2')
        
        # Check ruleset data
        self.assertEqual(response.data['ruleset']['id'], self.ruleset.id)


class GameActionTests(APITestCase):
    """Test game action endpoints (start, move, resign)."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.user1 = UserFactory(username='player1')
        self.user2 = UserFactory(username='player2')
        
        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)
        
        self.game = GameFactory(black_player=self.user1, white_player=self.user2)
    
    def authenticate_user1(self):
        """Authenticate as user1."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
    
    def authenticate_user2(self):
        """Authenticate as user2."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token2.key}')
    
    def test_start_game_success(self):
        """Test starting a game successfully."""
        self.authenticate_user1()
        
        start_url = reverse('game-start', kwargs={'pk': self.game.id})
        response = self.client.post(start_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh game from database
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, GameStatus.ACTIVE)
        self.assertIsNotNone(self.game.started_at)
        self.assertEqual(self.game.current_player, Player.BLACK)
    
    def test_start_already_active_game(self):
        """Test starting an already active game."""
        self.authenticate_user1()
        
        # Start game first time
        self.game.start_game()
        
        start_url = reverse('game-start', kwargs={'pk': self.game.id})
        response = self.client.post(start_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_get_game_moves_empty(self):
        """Test getting moves from a game with no moves."""
        self.authenticate_user1()
        
        moves_url = reverse('game-moves', kwargs={'pk': self.game.id})
        response = self.client.get(moves_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
    
    def test_unauthenticated_game_actions(self):
        """Test that game actions require authentication."""
        start_url = reverse('game-start', kwargs={'pk': self.game.id})
        moves_url = reverse('game-moves', kwargs={'pk': self.game.id})
        
        # Test without authentication
        response = self.client.post(start_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        
        response = self.client.get(moves_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])