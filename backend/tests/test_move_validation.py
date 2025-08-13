"""
Tests for game move validation and gameplay mechanics.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from games.models import Game, GameMove, GameStatus, Player
from games.services import GameService
from tests.factories import UserFactory, GameFactory, RuleSetFactory

User = get_user_model()


class MoveValidationTests(APITestCase):
    """Test move validation via API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.user1 = UserFactory(username='player1')  # Black player
        self.user2 = UserFactory(username='player2')  # White player
        self.user3 = UserFactory(username='spectator')  # Not in game
        
        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)
        self.token3 = Token.objects.create(user=self.user3)
        
        self.game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            status=GameStatus.WAITING
        )
        self.game.start_game()
        
        self.move_url = reverse('game-move', kwargs={'pk': self.game.id})
    
    def authenticate_user1(self):
        """Authenticate as user1 (black player)."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token1.key}')
    
    def authenticate_user2(self):
        """Authenticate as user2 (white player)."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token2.key}')
    
    def authenticate_user3(self):
        """Authenticate as user3 (spectator)."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token3.key}')
    
    def test_valid_first_move(self):
        """Test making a valid first move."""
        self.authenticate_user1()  # Black goes first
        
        data = {'row': 7, 'col': 7}  # Center of 15x15 board
        response = self.client.post(self.move_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['row'], 7)
        self.assertEqual(response.data['col'], 7)
        self.assertEqual(response.data['player_color'], Player.BLACK)
        self.assertEqual(response.data['move_number'], 1)
        
        # Verify game state updated
        self.game.refresh_from_db()
        self.assertEqual(self.game.current_player, Player.WHITE)
        self.assertEqual(self.game.move_count, 1)
    
    def test_valid_second_move(self):
        """Test making a valid second move."""
        # Black makes first move
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
    
    def test_move_out_of_turn(self):
        """Test making a move out of turn."""
        self.authenticate_user2()  # White tries to go first
        
        data = {'row': 7, 'col': 7}
        response = self.client.post(self.move_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('turn', str(response.data).lower())
    
    def test_move_by_non_player(self):
        """Test move attempt by user not in the game."""
        self.authenticate_user3()  # Spectator
        
        data = {'row': 7, 'col': 7}
        response = self.client.post(self.move_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertIn('player', str(response.data).lower())
    
    def test_move_out_of_bounds(self):
        """Test moves outside the board boundaries."""
        self.authenticate_user1()
        
        invalid_positions = [
            {'row': -1, 'col': 7},    # Negative row
            {'row': 7, 'col': -1},    # Negative col
            {'row': 15, 'col': 7},    # Row too high (0-14 valid)
            {'row': 7, 'col': 15},    # Col too high (0-14 valid)
            {'row': 100, 'col': 100}, # Way out of bounds
        ]
        
        for data in invalid_positions:
            response = self.client.post(self.move_url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            # Check that there's an error in the response
            self.assertTrue('error' in response.data or len(response.data) > 0)
    
    def test_move_on_occupied_position(self):
        """Test move on already occupied position."""
        self.authenticate_user1()
        
        # Make first move
        data = {'row': 7, 'col': 7}
        response = self.client.post(self.move_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Try to move on same position
        self.authenticate_user2()
        response = self.client.post(self.move_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('occupied', str(response.data).lower())
    
    def test_move_invalid_data_types(self):
        """Test moves with invalid data types."""
        self.authenticate_user1()
        
        invalid_data = [
            {'row': 'invalid', 'col': 7},      # String instead of int
            {'row': 7, 'col': 'invalid'},      # String instead of int
            {'row': 7.5, 'col': 7},            # Float instead of int
            {'row': None, 'col': 7},           # None value
            {'row': [], 'col': 7},             # List instead of int
        ]
        
        for data in invalid_data:
            response = self.client.post(self.move_url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            # Check that there's an error in the response (could be in 'error' or field-specific)
            self.assertTrue('error' in response.data or any(key != 'error' for key in response.data.keys()))
    
    def test_move_missing_coordinates(self):
        """Test moves with missing coordinates."""
        self.authenticate_user1()
        
        # Missing row
        data = {'col': 7}
        response = self.client.post(self.move_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Missing col
        data = {'row': 7}
        response = self.client.post(self.move_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Missing both
        data = {}
        response = self.client.post(self.move_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_move_on_inactive_game(self):
        """Test making move on inactive game."""
        # Create inactive game
        inactive_game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            status=GameStatus.WAITING  # Not active
        )
        move_url = reverse('game-move', kwargs={'pk': inactive_game.id})
        
        self.authenticate_user1()
        data = {'row': 7, 'col': 7}
        response = self.client.post(move_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        # Check that the error mentions the game status issue
        self.assertIn('waiting', str(response.data).lower())
    
    def test_move_on_finished_game(self):
        """Test making move on finished game."""
        # Finish the game
        self.game.status = GameStatus.FINISHED
        self.game.winner = self.user1
        self.game.save()
        
        self.authenticate_user1()
        data = {'row': 7, 'col': 7}
        response = self.client.post(self.move_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_move_unauthenticated(self):
        """Test making move without authentication."""
        data = {'row': 7, 'col': 7}
        response = self.client.post(self.move_url, data, format='json')
        
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
        self.assertIn('error', response.data)


class MoveSequenceTests(APITestCase):
    """Test sequences of moves and game progression."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
        self.user1 = UserFactory(username='player1')  # Black
        self.user2 = UserFactory(username='player2')  # White
        
        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)
        
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
    
    def test_alternating_moves(self):
        """Test that moves alternate between players correctly."""
        moves = [
            (self.token1, 7, 7),   # Black
            (self.token2, 7, 8),   # White
            (self.token1, 8, 7),   # Black
            (self.token2, 8, 8),   # White
            (self.token1, 9, 7),   # Black
        ]
        
        for i, (token, row, col) in enumerate(moves, 1):
            response = self.make_move(token, row, col)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['move_number'], i)
        
        # Verify final game state
        self.game.refresh_from_db()
        self.assertEqual(self.game.move_count, 5)
        self.assertEqual(self.game.current_player, Player.WHITE)  # White's turn
    
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
        
        self.user1 = UserFactory(username='player1')  # Black
        self.user2 = UserFactory(username='player2')  # White
        
        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)
        
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