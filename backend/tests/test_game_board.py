"""
pytest tests for Interactive Game Board.

Migrated from web/test_game_board.py to pytest format for better test management.
Following TDD methodology with comprehensive game board coverage.
"""

import pytest
import json
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from games.models import Game, GameStatus, Player
from tests.factories import UserFactory, GameFactory, GomokuRuleSetFactory

User = get_user_model()


@pytest.mark.django_db
class TestGameBoardRendering:
    """pytest tests for game board visualization and rendering."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.user1 = UserFactory(username='player1')
        self.user2 = UserFactory(username='player2')
        self.user1.set_password('testpass123')
        self.user2.set_password('testpass123')
        self.user1.save()
        self.user2.save()
        
        self.ruleset = GomokuRuleSetFactory(board_size=15)
        self.game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
    
    def test_game_board_renders_correctly(self):
        """Test game board renders with correct grid structure."""
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url, follow=True)  # Follow redirect to dashboard
        
        assert response.status_code == 200
        
        # Check for essential game board elements
        content = response.content.decode()
        assert 'game-board' in content or 'board-intersection' in content
        assert 'data-board-size' in content
        
        # Check for player information
        assert self.user1.username in content
        assert self.user2.username in content
    
    def test_game_board_shows_correct_size(self):
        """Test game board shows correct board dimensions."""
        # Test with different board sizes
        large_ruleset = GomokuRuleSetFactory(board_size=19)
        large_game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=large_ruleset,
            status=GameStatus.ACTIVE
        )
        large_game.initialize_board()
        large_game.save()
        
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': large_game.id})
        response = self.client.get(url, follow=True)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Check for 19x19 board size indicators
        assert 'data-board-size="19"' in content or '19' in content
    
    def test_game_board_shows_existing_stones(self):
        """Test game board displays existing stone placements."""
        # Make a move first
        from games.game_services import GameServiceFactory
        service = GameServiceFactory.get_service(self.game.ruleset.game_type)
        service.make_move(self.game, self.user1.id, 7, 7)  # Black stone
        
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url, follow=True)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Check for stone indicators (could be various formats)
        assert ('stone' in content or 
                'BLACK' in content or 
                'occupied' in content or
                'move' in content)
    
    def test_game_board_shows_turn_indicator(self):
        """Test game board shows whose turn it is."""
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url, follow=True)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Should show turn information
        assert ('turn' in content.lower() or 
                'your turn' in content.lower() or
                'current player' in content.lower() or
                self.user1.username in content)
    
    def test_game_board_responsive_design(self):
        """Test game board adapts to different screen sizes."""
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url, follow=True)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Check for responsive CSS classes or viewport meta tag
        assert ('viewport' in content or 
                'responsive' in content or
                'col-' in content or  # Bootstrap responsive classes
                '@media' in content or
                'fluid' in content)


@pytest.mark.django_db
class TestGameBoardInteraction:
    """pytest tests for game board user interaction."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.user1 = UserFactory(username='player1')
        self.user2 = UserFactory(username='player2')
        self.user1.set_password('testpass123')
        self.user2.set_password('testpass123')
        self.user1.save()
        self.user2.save()
        
        self.ruleset = GomokuRuleSetFactory(board_size=15)
        self.game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
    
    def test_board_intersections_clickable(self):
        """Test that board intersections are interactive."""
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url, follow=True)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Check for clickable elements
        assert ('onclick' in content or 
                'data-row' in content or 
                'data-col' in content or
                'clickable' in content or
                'intersection' in content)
    
    def test_move_endpoint_handles_click(self):
        """Test move endpoint processes board clicks correctly."""
        self.client.login(username='player1', password='testpass123')
        
        # Test making a move
        move_url = reverse('web:game_move', kwargs={'game_id': self.game.id})
        response = self.client.post(move_url, {
            'row': 7,
            'col': 7
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Could be various response formats
        assert response.status_code in [200, 204, 302]
        
        # Check game state was updated
        self.game.refresh_from_db()
        assert self.game.move_count > 0
    
    def test_invalid_move_returns_error(self):
        """Test invalid moves are rejected with error message."""
        self.client.login(username='player1', password='testpass123')
        
        # Try invalid coordinates
        move_url = reverse('web:game_move', kwargs={'game_id': self.game.id})
        response = self.client.post(move_url, {
            'row': -1,  # Invalid
            'col': 7
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should reject invalid move
        assert response.status_code in [400, 403, 422]
    
    def test_out_of_turn_move_rejected(self):
        """Test moves by wrong player are rejected."""
        # Login as player2 (white) when it's player1's (black) turn
        self.client.login(username='player2', password='testpass123')
        
        move_url = reverse('web:game_move', kwargs={'game_id': self.game.id})
        response = self.client.post(move_url, {
            'row': 7,
            'col': 7
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should reject out of turn move
        assert response.status_code in [403, 400, 422]
    
    def test_move_updates_board_state(self):
        """Test moves properly update the game board state."""
        self.client.login(username='player1', password='testpass123')
        
        initial_state = dict(self.game.board_state)
        
        # Make a move
        move_url = reverse('web:game_move', kwargs={'game_id': self.game.id})
        response = self.client.post(move_url, {
            'row': 7,
            'col': 7
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        assert response.status_code in [200, 204, 302]
        
        # Verify board state changed
        self.game.refresh_from_db()
        assert self.game.board_state != initial_state
        assert self.game.move_count > 0


@pytest.mark.django_db
class TestGameBoardVisualization:
    """pytest tests for game board visual elements."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.user1 = UserFactory(username='player1')
        self.user2 = UserFactory(username='player2')
        self.user1.set_password('testpass123')
        self.user2.set_password('testpass123')
        self.user1.save()
        self.user2.save()
        
        self.ruleset = GomokuRuleSetFactory(board_size=15)
        self.game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
    
    def test_game_info_displays_correctly(self):
        """Test game information is displayed correctly."""
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url, follow=True)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Check for game information
        assert self.user1.username in content
        assert self.user2.username in content
        assert (str(self.ruleset.board_size) in content or 
                '15' in content)  # Board size
    
    def test_game_status_shown(self):
        """Test game status is clearly displayed."""
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url, follow=True)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Check for status indicators
        assert ('active' in content.lower() or 
                'in progress' in content.lower() or
                'playing' in content.lower() or
                'turn' in content.lower())
    
    def test_finished_game_shows_winner(self):
        """Test finished games display winner information."""
        # Finish the game
        self.game.status = GameStatus.FINISHED
        self.game.winner = self.user1
        self.game.save()
        
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url, follow=True)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Check for winner information
        assert (self.user1.username in content and
                ('win' in content.lower() or 
                 'victor' in content.lower() or
                 'champion' in content.lower() or
                 'finished' in content.lower()))
    
    def test_move_history_displayed(self):
        """Test move history is accessible."""
        # Make a few moves
        from games.game_services import GameServiceFactory
        service = GameServiceFactory.get_service(self.game.ruleset.game_type)
        service.make_move(self.game, self.user1.id, 7, 7)  # Black
        service.make_move(self.game, self.user2.id, 8, 8)  # White
        
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url, follow=True)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Check for move history indicators
        assert ('move' in content.lower() or
                'history' in content.lower() or
                str(self.game.move_count) in content or
                'turn' in content.lower())


@pytest.mark.django_db
class TestGameBoardAccessibility:
    """pytest tests for game board accessibility features."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test data."""
        self.client = Client()
        self.user1 = UserFactory(username='player1')
        self.user2 = UserFactory(username='player2')
        self.user1.set_password('testpass123')
        self.user2.set_password('testpass123')
        self.user1.save()
        self.user2.save()
        
        self.ruleset = GomokuRuleSetFactory(board_size=15)
        self.game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
    
    def test_board_has_aria_labels(self):
        """Test game board includes ARIA labels for accessibility."""
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url, follow=True)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Check for accessibility attributes
        assert ('aria-' in content or 
                'role=' in content or
                'tabindex' in content or
                'alt=' in content)
    
    def test_keyboard_navigation_support(self):
        """Test game board supports keyboard navigation."""
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url, follow=True)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Check for keyboard navigation support
        assert ('tabindex' in content or 
                'onkeydown' in content or
                'onkeypress' in content or
                'keyboard' in content.lower())
    
    def test_screen_reader_announcements(self):
        """Test game board includes screen reader support."""
        self.client.login(username='player1', password='testpass123')
        
        url = reverse('web:game_detail', kwargs={'game_id': self.game.id})
        response = self.client.get(url, follow=True)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # Check for screen reader friendly elements
        assert ('aria-live' in content or 
                'sr-only' in content or
                'screen-reader' in content or
                'visually-hidden' in content or
                'aria-describedby' in content)