"""
Tests for game move validation and gameplay mechanics.
"""

import pytest
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from users.models import EnhancedToken

from games.models import Game, GameMove, GameStatus, Player
from games.services import GameService
from tests.factories import UserFactory, GameFactory, RuleSetFactory

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for testing."""
    return APIClient()


@pytest.fixture
def game_users(db):
    """Create test users for game testing."""
    user1 = UserFactory(username='player1')  # Black player
    user2 = UserFactory(username='player2')  # White player
    user3 = UserFactory(username='spectator')  # Not in game
    return user1, user2, user3


@pytest.fixture
def user_tokens(game_users):
    """Create authentication tokens for users."""
    user1, user2, user3 = game_users
    return (
        EnhancedToken.objects.create_for_device(user=user1),
        EnhancedToken.objects.create_for_device(user=user2),
        EnhancedToken.objects.create_for_device(user=user3)
    )


@pytest.fixture
def active_game(game_users):
    """Create an active game for testing."""
    user1, user2, user3 = game_users
    game = GameFactory(
        black_player=user1,
        white_player=user2,
        status=GameStatus.WAITING
    )
    game.start_game()
    return game


@pytest.mark.api
@pytest.mark.unit
class TestMoveValidationAPI:
    """Test move validation via API endpoints."""
    
    def test_valid_first_move(self, api_client, game_users, user_tokens, active_game):
        """Test making a valid first move."""
        user1, user2, user3 = game_users
        token1, token2, token3 = user_tokens
        
        # Black goes first
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
        move_url = reverse('game-move', kwargs={'pk': active_game.id})
        
        data = {'row': 7, 'col': 7}  # Center of 15x15 board
        response = api_client.post(move_url, data, format='json')
        
        # Enhanced assertions with better error messages
        assert response.status_code == status.HTTP_200_OK, \
            f"Expected 200, got {response.status_code}: {response.data}"
        
        # Validate response structure
        required_fields = ['id', 'row', 'col', 'player_color', 'move_number']
        for field in required_fields:
            assert field in response.data, f"Response missing required field: {field}"
        
        # Validate response values
        assert response.data['row'] == 7, "Move row should be 7"
        assert response.data['col'] == 7, "Move col should be 7"
        assert response.data['player_color'] == Player.BLACK, "Player should be BLACK"
        assert response.data['move_number'] == 1, "Should be first move"
        
        # Verify game state updated correctly
        active_game.refresh_from_db()
        assert active_game.current_player == Player.WHITE, "Turn should switch to WHITE"
        assert active_game.move_count == 1, "Move count should be 1"
    
    def test_move_out_of_bounds_comprehensive(self, api_client, game_users, user_tokens, active_game):
        """Test comprehensive out of bounds validation."""
        user1, user2, user3 = game_users
        token1, token2, token3 = user_tokens
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
        move_url = reverse('game-move', kwargs={'pk': active_game.id})
        
        # Test various out-of-bounds positions
        invalid_positions = [
            ({'row': -1, 'col': 7}, "Negative row should be invalid"),
            ({'row': 7, 'col': -1}, "Negative col should be invalid"),
            ({'row': 15, 'col': 7}, "Row 15 should be invalid (0-14 valid)"),
            ({'row': 7, 'col': 15}, "Col 15 should be invalid (0-14 valid)"),
            ({'row': 100, 'col': 100}, "Way out of bounds should be invalid"),
        ]
        
        for invalid_data, error_msg in invalid_positions:
            response = api_client.post(move_url, invalid_data, format='json')
            assert response.status_code == status.HTTP_400_BAD_REQUEST, \
                f"{error_msg}. Got {response.status_code}: {response.data}"
            
            # Verify error response structure
            assert 'error' in response.data or any(field in response.data for field in ['row', 'col']), \
                f"Should have error details for invalid position {invalid_data}"
    
    def test_move_invalid_data_types_enhanced(self, api_client, game_users, user_tokens, active_game):
        """Test moves with invalid data types and enhanced validation."""
        user1, user2, user3 = game_users
        token1, token2, token3 = user_tokens
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
        move_url = reverse('game-move', kwargs={'pk': active_game.id})
        
        # Test various invalid data types
        invalid_data_tests = [
            ({'row': 'invalid', 'col': 7}, "String row should be rejected"),
            ({'row': 7, 'col': 'invalid'}, "String col should be rejected"),  
            ({'row': 7.5, 'col': 7}, "Float row should be rejected"),
            ({'row': None, 'col': 7}, "None row should be rejected"),
            ({'row': [], 'col': 7}, "List row should be rejected"),
            ({}, "Empty data should be rejected"),
            ({'row': 7}, "Missing col should be rejected"),
            ({'col': 7}, "Missing row should be rejected"),
        ]
        
        for invalid_data, error_msg in invalid_data_tests:
            response = api_client.post(move_url, invalid_data, format='json')
            assert response.status_code == status.HTTP_400_BAD_REQUEST, \
                f"{error_msg}. Got {response.status_code}: {response.data}"
    
    def test_valid_second_move(self):
        self.authenticate_user1()
        data = {'row': 7, 'col': 7}
        response = self.client.post(self.move_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # White makes second move
        self.authenticate_user2()
        data = {'row': 7, 'col': 8}
        response = self.client.post(self.move_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['player_color'], Player.WHITE)
        self.assertEqual(response.data['move_number'], 2)
        
        # Verify it's black's turn again
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_player, Player.BLACK)
    
    def test_move_out_of_turn(self, api_client, game_users, user_tokens, active_game):
        """Test making a move out of turn."""
        user1, user2, user3 = game_users
        token1, token2, token3 = user_tokens
        
        # White tries to go first (should be black's turn)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token2.key}')
        move_url = reverse('game-move', kwargs={'pk': active_game.id})
        
        data = {'row': 7, 'col': 7}
        response = api_client.post(move_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST, \
            f"Expected 400, got {response.status_code}: {response.data}"
        assert 'error' in response.data
        assert 'turn' in str(response.data).lower()
    
    def test_move_by_non_player(self, api_client, game_users, user_tokens, active_game):
        """Test move attempt by user not in the game."""
        user1, user2, user3 = game_users
        token1, token2, token3 = user_tokens
        
        # Spectator tries to make a move
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token3.key}')
        move_url = reverse('game-move', kwargs={'pk': active_game.id})
        
        data = {'row': 7, 'col': 7}
        response = api_client.post(move_url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'error' in response.data
        assert 'player' in str(response.data).lower()
    
    def test_move_out_of_bounds(self, api_client, game_users, user_tokens, active_game):
        """Test moves outside the board boundaries."""
        user1, user2, user3 = game_users
        token1, token2, token3 = user_tokens
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
        move_url = reverse('game-move', kwargs={'pk': active_game.id})
        
        invalid_positions = [
            {'row': -1, 'col': 7},    # Negative row
            {'row': 7, 'col': -1},    # Negative col
            {'row': 15, 'col': 7},    # Row too high (0-14 valid)
            {'row': 7, 'col': 15},    # Col too high (0-14 valid)
            {'row': 100, 'col': 100}, # Way out of bounds
        ]
        
        for data in invalid_positions:
            response = api_client.post(move_url, data, format='json')
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            # Check that there's an error in the response
            assert 'error' in response.data or len(response.data) > 0
    
    def test_move_on_occupied_position(self, api_client, game_users, user_tokens, active_game):
        """Test move on already occupied position."""
        user1, user2, user3 = game_users
        token1, token2, token3 = user_tokens
        move_url = reverse('game-move', kwargs={'pk': active_game.id})
        
        # Make first move as black
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
        data = {'row': 7, 'col': 7}
        response = api_client.post(move_url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        # Try to move on same position as white
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token2.key}')
        response = api_client.post(move_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        assert 'occupied' in str(response.data).lower()
    
    def test_move_invalid_data_types(self, api_client, game_users, user_tokens, active_game):
        """Test moves with invalid data types."""
        user1, user2, user3 = game_users
        token1, token2, token3 = user_tokens
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
        move_url = reverse('game-move', kwargs={'pk': active_game.id})
        
        invalid_data = [
            {'row': 'invalid', 'col': 7},      # String instead of int
            {'row': 7, 'col': 'invalid'},      # String instead of int
            {'row': 7.5, 'col': 7},            # Float instead of int
            {'row': None, 'col': 7},           # None value
            {'row': [], 'col': 7},             # List instead of int
        ]
        
        for data in invalid_data:
            response = api_client.post(move_url, data, format='json')
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            # Check that there's an error in the response (could be in 'error' or field-specific)
            assert 'error' in response.data or any(key != 'error' for key in response.data.keys())
    
    def test_move_missing_coordinates(self, api_client, game_users, user_tokens, active_game):
        """Test moves with missing coordinates."""
        user1, user2, user3 = game_users
        token1, token2, token3 = user_tokens
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
        move_url = reverse('game-move', kwargs={'pk': active_game.id})
        
        # Missing row
        data = {'col': 7}
        response = api_client.post(move_url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Missing col
        data = {'row': 7}
        response = api_client.post(move_url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Missing both
        data = {}
        response = api_client.post(move_url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_move_on_inactive_game(self, api_client, game_users, user_tokens):
        """Test making move on inactive game."""
        user1, user2, user3 = game_users
        token1, token2, token3 = user_tokens
        
        # Create inactive game
        inactive_game = GameFactory(
            black_player=user1,
            white_player=user2,
            status=GameStatus.WAITING  # Not active
        )
        move_url = reverse('game-move', kwargs={'pk': inactive_game.id})
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
        data = {'row': 7, 'col': 7}
        response = api_client.post(move_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
        # Check that the error mentions the game status issue
        assert 'waiting' in str(response.data).lower()
    
    def test_move_on_finished_game(self, api_client, game_users, user_tokens, active_game):
        """Test making move on finished game."""
        user1, user2, user3 = game_users
        token1, token2, token3 = user_tokens
        
        # Finish the game
        active_game.status = GameStatus.FINISHED
        active_game.winner = user1
        active_game.save()
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
        move_url = reverse('game-move', kwargs={'pk': active_game.id})
        data = {'row': 7, 'col': 7}
        response = api_client.post(move_url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_move_unauthenticated(self, api_client, active_game):
        """Test making move without authentication."""
        move_url = reverse('game-move', kwargs={'pk': active_game.id})
        data = {'row': 7, 'col': 7}
        response = api_client.post(move_url, data, format='json')
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        assert 'error' in response.data


@pytest.fixture
def sequence_users(db):
    """Create test users for sequence testing."""
    user1 = UserFactory(username='sequence_player1')  # Black
    user2 = UserFactory(username='sequence_player2')  # White
    return user1, user2


@pytest.fixture
def sequence_tokens(sequence_users):
    """Create authentication tokens for sequence users."""
    user1, user2 = sequence_users
    return (
        EnhancedToken.objects.create_for_device(user=user1),
        EnhancedToken.objects.create_for_device(user=user2)
    )


@pytest.fixture
def sequence_game(sequence_users):
    """Create an active game for sequence testing."""
    user1, user2 = sequence_users
    game = GameFactory(
        black_player=user1,
        white_player=user2,
        status=GameStatus.WAITING
    )
    game.start_game()
    return game


@pytest.mark.api
@pytest.mark.django_db
class TestMoveSequences:
    """Test sequences of moves and game progression."""
    
    def make_move(self, api_client, user_token, row, col, game):
        """Helper to make a move."""
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {user_token.key}')
        move_url = reverse('game-move', kwargs={'pk': game.id})
        data = {'row': row, 'col': col}
        return api_client.post(move_url, data, format='json')
    
    def test_alternating_moves(self, api_client, sequence_users, sequence_tokens, sequence_game):
        """Test that moves alternate between players correctly."""
        user1, user2 = sequence_users
        token1, token2 = sequence_tokens
        
        moves = [
            (token1, 7, 7),   # Black
            (token2, 7, 8),   # White
            (token1, 8, 7),   # Black
            (token2, 8, 8),   # White
            (token1, 9, 7),   # Black
        ]
        
        for i, (token, row, col) in enumerate(moves, 1):
            response = self.make_move(api_client, token, row, col, sequence_game)
            assert response.status_code == status.HTTP_200_OK
            assert response.data['move_number'] == i
        
        # Verify final game state
        sequence_game.refresh_from_db()
        assert sequence_game.move_count == 5
        assert sequence_game.current_player == Player.WHITE  # White's turn
    
    def test_move_count_tracking(self):
        """Test that move count is tracked correctly."""
        # Make several moves
        moves = [(7, 7), (7, 8), (8, 7), (8, 8)]
        
        for i, (row, col) in enumerate(moves):
            token = self.token1 if i % 2 == 0 else self.token2
            response = self.make_move(token, row, col)
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['move_number'], i + 1)
        
        # Check final count
        self.game.refresh_from_db()
        self.assertEqual(self.game.move_count, 4)
    
    def test_board_state_updates(self):
        """Test that board state is updated correctly after moves."""
        # Make some moves
        response = self.make_move(self.token1, 7, 7)  # Black at center
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.make_move(self.token2, 7, 8)  # White adjacent
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check board state
        self.game.refresh_from_db()
        board = self.game.board_state.get('board', [])
        
        self.assertIsNotNone(board)
        self.assertEqual(board[7][7], Player.BLACK)
        self.assertEqual(board[7][8], Player.WHITE)
        
        # Check empty positions are still None
        self.assertIsNone(board[0][0])
        self.assertIsNone(board[14][14])
    
    def test_cannot_repeat_same_move(self):
        """Test that the same player cannot make consecutive moves."""
        # Black makes first move
        response = self.make_move(self.token1, 7, 7)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Black tries to move again (should be white's turn)
        response = self.make_move(self.token1, 8, 8)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('turn', str(response.data).lower())


class WinDetectionTests(APITestCase):
    """Test win detection in move validation."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.user1 = UserFactory(username='win_player1')  # Black
        self.user2 = UserFactory(username='win_player2')  # White
        
        self.token1 = EnhancedToken.objects.create_for_device(user=self.user1)
        self.token2 = EnhancedToken.objects.create_for_device(user=self.user2)
        
        self.game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            status=GameStatus.WAITING
        )
        self.game.start_game()
        
        self.move_url = reverse('game-move', kwargs={'pk': self.game.id})
    
    def make_move(self, user_token, row, col):
        """Helper to make a move."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {user_token.key}')
        data = {'row': row, 'col': col}
        return self.client.post(self.move_url, data, format='json')
    
    def test_horizontal_win(self):
        """Test detecting horizontal win (5 in a row)."""
        # Set up a winning position for black (horizontal)
        moves = [
            (self.token1, 7, 5),   # Black
            (self.token2, 8, 5),   # White
            (self.token1, 7, 6),   # Black  
            (self.token2, 8, 6),   # White
            (self.token1, 7, 7),   # Black
            (self.token2, 8, 7),   # White
            (self.token1, 7, 8),   # Black
            (self.token2, 8, 8),   # White
            (self.token1, 7, 9),   # Black - winning move!
        ]
        
        for i, (token, row, col) in enumerate(moves[:-1]):
            response = self.make_move(token, row, col)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertFalse(response.data.get('is_winning_move', False))
        
        # Make winning move
        response = self.make_move(*moves[-1])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('is_winning_move', False))
        
        # Verify game is finished
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(self.game.winner, self.user1)
    
    def test_vertical_win(self):
        """Test detecting vertical win (5 in a column)."""
        # Set up a winning position for black (vertical)
        moves = [
            (self.token1, 5, 7),   # Black
            (self.token2, 5, 8),   # White
            (self.token1, 6, 7),   # Black  
            (self.token2, 6, 8),   # White
            (self.token1, 7, 7),   # Black
            (self.token2, 7, 8),   # White
            (self.token1, 8, 7),   # Black
            (self.token2, 8, 8),   # White
            (self.token1, 9, 7),   # Black - winning move!
        ]
        
        for i, (token, row, col) in enumerate(moves[:-1]):
            response = self.make_move(token, row, col)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertFalse(response.data.get('is_winning_move', False))
        
        # Make winning move
        response = self.make_move(*moves[-1])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('is_winning_move', False))
        
        # Verify game is finished
        self.game.refresh_from_db()
        self.assertEqual(self.game.status, GameStatus.FINISHED)
        self.assertEqual(self.game.winner, self.user1)
    
    def test_no_moves_after_win(self):
        """Test that no moves can be made after game is won."""
        # Create a simple horizontal win for black
        moves = [
            (self.token1, 7, 5),   
            (self.token2, 8, 5),   
            (self.token1, 7, 6),   
            (self.token2, 8, 6),   
            (self.token1, 7, 7),   
            (self.token2, 8, 7),   
            (self.token1, 7, 8),   
            (self.token2, 8, 8),   
            (self.token1, 7, 9),   # Winning move
        ]
        
        # Play out the game
        for token, row, col in moves:
            response = self.make_move(token, row, col)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Try to make another move
        response = self.make_move(self.token2, 9, 9)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)