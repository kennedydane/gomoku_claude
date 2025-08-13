"""
TDD Tests for Interactive Game Board.

Following Red-Green-Refactor methodology:
1. RED: Write failing tests for interactive game board functionality
2. GREEN: Implement minimal code to pass tests
3. REFACTOR: Improve code quality while keeping tests green
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from games.models import Game, RuleSet, GameStatus, Player
from tests.factories import UserFactory, GameFactory, RuleSetFactory
import json

User = get_user_model()


class GameBoardRenderingTests(TestCase):
    """RED: Test game board visualization and rendering."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user1 = UserFactory(username='player1')
        self.user2 = UserFactory(username='player2')
        self.user1.set_password('testpass123')
        self.user2.set_password('testpass123')
        self.user1.save()
        self.user2.save()
        
        self.ruleset = RuleSetFactory(board_size=15)
        self.game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
    
    def test_game_board_renders_correctly(self):
        """RED: Test game board renders with correct grid structure."""
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'game-board-grid')
        self.assertContains(response, 'board-intersection')
        # Should have data-row and data-col attributes for coordinates
        content = response.content.decode()
        import re
        row_matches = re.findall(r'data-row="(\d+)"', content)
        col_matches = re.findall(r'data-col="(\d+)"', content) 
        # Should have 15 rows (0-14) and 15 cols (0-14) = 225 total intersections
        self.assertEqual(len(row_matches), 225)
        self.assertEqual(len(col_matches), 225)
    
    def test_game_board_shows_correct_size(self):
        """RED: Test board renders with correct size based on ruleset."""
        self.client.login(username='player1', password='testpass123')
        
        # Test 19x19 board
        large_ruleset = RuleSetFactory(board_size=19)
        large_game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=large_ruleset,
            status=GameStatus.ACTIVE
        )
        large_game.initialize_board()
        large_game.save()
        
        url = reverse('web:game_detail', kwargs={'game_id': large_game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should have 19x19 = 361 intersections
        content = response.content.decode()
        import re
        row_matches = re.findall(r'data-row="(\d+)"', content)
        # Should have 19x19 = 361 total intersections
        self.assertEqual(len(row_matches), 361)
        self.assertContains(response, 'data-board-size="19"')
    
    def test_game_board_shows_existing_stones(self):
        """RED: Test board displays previously placed stones correctly."""
        # Place some stones on the board
        self.game.board_state['board'][7][7] = 'black'
        self.game.board_state['board'][7][8] = 'white' 
        self.game.board_state['board'][8][7] = 'black'
        self.game.save()
        
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should show black stones
        self.assertContains(response, 'stone-black')
        # Should show white stones  
        self.assertContains(response, 'stone-white')
        # Count stones within board intersections only
        content = response.content.decode()
        import re
        # Look for stone divs inside board intersections
        black_stones_in_board = len(re.findall(r'board-intersection[^>]*>.*?<div class="stone-black">', content, re.DOTALL))
        white_stones_in_board = len(re.findall(r'board-intersection[^>]*>.*?<div class="stone-white">', content, re.DOTALL))
        self.assertEqual(black_stones_in_board, 2)
        self.assertEqual(white_stones_in_board, 1)
    
    def test_game_board_shows_turn_indicator(self):
        """RED: Test board shows whose turn it is."""
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'current-turn')
        # Black goes first by default
        self.assertContains(response, 'player1')
        self.assertContains(response, 'turn')
    
    def test_game_board_responsive_design(self):
        """RED: Test board has responsive CSS classes."""
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should have responsive CSS classes
        self.assertContains(response, 'game-board-container')
        self.assertContains(response, 'board-responsive')


class GameBoardInteractionTests(TestCase):
    """RED: Test game board click interactions and move making."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user1 = UserFactory(username='player1')
        self.user2 = UserFactory(username='player2') 
        self.user1.set_password('testpass123')
        self.user2.set_password('testpass123')
        self.user1.save()
        self.user2.save()
        
        self.ruleset = RuleSetFactory(board_size=15)
        self.game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
    
    def test_board_intersections_clickable(self):
        """RED: Test board intersections have click handlers."""
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Intersections should have click attributes
        self.assertContains(response, 'data-row=')
        self.assertContains(response, 'data-col=')
        self.assertContains(response, 'onclick=')
    
    def test_move_endpoint_handles_click(self):
        """RED: Test clicking intersection makes move via AJAX."""
        self.client.login(username='player1', password='testpass123')
        
        # Make move via AJAX call
        url = reverse('web:game_move', kwargs={'game_id': self.game.id})
        response = self.client.post(url, {
            'row': 7,
            'col': 7
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should return JSON response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Check response contains game state
        data = response.json()
        self.assertIn('success', data)
        self.assertIn('board_state', data)
        self.assertIn('current_player', data)
    
    def test_invalid_move_returns_error(self):
        """RED: Test invalid moves return proper error responses."""
        self.client.login(username='player1', password='testpass123')
        
        # Try to make move on occupied space
        self.game.board_state['board'][7][7] = 'black'
        self.game.save()
        
        url = reverse('web:game_move', kwargs={'game_id': self.game.id})
        response = self.client.post(url, {
            'row': 7,
            'col': 7
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('occupied', data['error'].lower())
    
    def test_out_of_turn_move_rejected(self):
        """RED: Test moves by wrong player are rejected."""
        self.client.login(username='player2', password='testpass123')  # White player
        
        # Game starts with black's turn
        url = reverse('web:game_move', kwargs={'game_id': self.game.id})
        response = self.client.post(url, {
            'row': 7,
            'col': 7
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('turn', data['error'].lower())
    
    def test_move_updates_board_state(self):
        """RED: Test successful move updates game board state."""
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_move', kwargs={'game_id': self.game.id})
        response = self.client.post(url, {
            'row': 7,
            'col': 7
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        
        # Reload game and check board state
        self.game.refresh_from_db()
        self.assertEqual(self.game.board_state['board'][7][7], 'BLACK')
        self.assertEqual(self.game.current_player, Player.WHITE)


class GameBoardVisualizationTests(TestCase):
    """RED: Test visual feedback and game state display."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user1 = UserFactory(username='player1')
        self.user2 = UserFactory(username='player2')
        self.user1.set_password('testpass123')
        self.user2.set_password('testpass123')
        self.user1.save()
        self.user2.save()
        
        self.ruleset = RuleSetFactory(board_size=15)
        self.game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
    
    def test_game_info_displays_correctly(self):
        """RED: Test game information panel shows player names and status."""
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'game-info')
        self.assertContains(response, 'player1')
        self.assertContains(response, 'player2')
        self.assertContains(response, 'Black')
        self.assertContains(response, 'White')
    
    def test_game_status_shown(self):
        """RED: Test current game status is displayed."""
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'game-status')
        self.assertContains(response, 'Active')
    
    def test_finished_game_shows_winner(self):
        """RED: Test finished games display winner information."""
        self.game.status = GameStatus.FINISHED
        self.game.winner = self.user1
        self.game.save()
        
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'game-winner')
        self.assertContains(response, 'player1')
        self.assertContains(response, 'wins')
    
    def test_move_history_displayed(self):
        """RED: Test move history is shown."""
        # Add some moves to the game
        self.game.board_state['board'][7][7] = 'black'
        self.game.board_state['board'][7][8] = 'white'
        self.game.save()
        
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'move-history')
        # Should show move numbers and coordinates
        self.assertContains(response, '(7,7)')
        self.assertContains(response, '(7,8)')


class GameBoardJavaScriptTests(TestCase):
    """RED: Test JavaScript functionality for board interactions."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user1 = UserFactory(username='player1')
        self.user2 = UserFactory(username='player2')
        self.user1.set_password('testpass123')
        self.user2.set_password('testpass123')
        self.user1.save()
        self.user2.save()
        
        self.ruleset = RuleSetFactory(board_size=15)
        self.game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
    
    def test_javascript_board_functions_included(self):
        """RED: Test JavaScript functions for board interaction are loaded."""
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should include JavaScript functions
        self.assertContains(response, 'makeMove')
        self.assertContains(response, 'updateBoard')
        self.assertContains(response, 'showMessage')
    
    def test_csrf_token_included_for_ajax(self):
        """RED: Test CSRF token is available for AJAX requests."""
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'csrfmiddlewaretoken')
    
    def test_game_id_available_to_javascript(self):
        """RED: Test game ID is available to JavaScript code."""
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Game ID should be in JavaScript variables
        self.assertContains(response, f'gameId = "{self.game.id}"')


class GameBoardAccessibilityTests(TestCase):
    """RED: Test accessibility features for game board."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user1 = UserFactory(username='player1')
        self.user2 = UserFactory(username='player2')
        self.user1.set_password('testpass123')
        self.user1.save()
        
        self.ruleset = RuleSetFactory(board_size=15)
        self.game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
    
    def test_board_has_aria_labels(self):
        """RED: Test board intersections have proper ARIA labels."""
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label=')
        self.assertContains(response, 'role="button"')
    
    def test_keyboard_navigation_support(self):
        """RED: Test board supports keyboard navigation."""
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tabindex=')
        self.assertContains(response, 'onkeydown=')
    
    def test_screen_reader_announcements(self):
        """RED: Test board has elements for screen reader announcements."""
        self.client.login(username='player1', password='testpass123')
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sr-only')
        self.assertContains(response, 'aria-live=')


# These tests will ALL FAIL initially - that's the RED phase!
# Next step: Implement minimal code to make them pass (GREEN phase)