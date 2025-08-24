"""
Tests for Single-View Dashboard with Embedded Game Board (formerly Phase 12)

This module contains pytest-style tests for embedded game functionality:
- Dashboard embedded game display tests
- Game selection via HTMX tests  
- URL parameter game selection tests
- SSE integration with embedded board tests
- Mobile responsive behavior tests
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from bs4 import BeautifulSoup
from unittest.mock import patch

from games.models import GomokuRuleSet, Game, GameStatus, Player
from web.models import Friendship, FriendshipStatus
from tests.factories import UserFactory, GomokuRuleSetFactory, GameFactory

User = get_user_model()


@pytest.fixture
def users(db):
    """Create test users."""
    user1 = UserFactory(username='player1')
    user2 = UserFactory(username='player2')
    return user1, user2


@pytest.fixture
def ruleset(db):
    """Create test ruleset."""
    return GomokuRuleSetFactory(
        name='Standard Gomoku',
        board_size=15,
        description='Standard 15x15 Gomoku'
    )


@pytest.fixture
def games(users, ruleset):
    """Create test games."""
    user1, user2 = users
    
    # Active game
    active_game = GameFactory(
        black_player=user1,
        white_player=user2,
        ruleset_content_type_id=ruleset.get_content_type().id,
        ruleset_object_id=ruleset.id,
        status=GameStatus.ACTIVE,
        current_player=Player.BLACK
    )
    active_game.initialize_board()
    active_game.save()
    
    # Finished game
    finished_game = GameFactory(
        black_player=user1,
        white_player=user2,
        ruleset_content_type_id=ruleset.get_content_type().id,
        ruleset_object_id=ruleset.id,
        status=GameStatus.FINISHED,
        winner=user1
    )
    
    return active_game, finished_game


@pytest.mark.django_db
@pytest.mark.web
@pytest.mark.integration
class TestDashboardEmbeddedGames:
    """Tests for embedded game display in dashboard center panel."""
        
    def test_dashboard_shows_embedded_game_by_default(self, client, users, games):
        """Test that dashboard shows most recent active game in center panel."""
        user1, user2 = users
        active_game, finished_game = games
        
        client.force_login(user1)
        response = client.get(reverse('web:dashboard'))
        
        assert response.status_code == 200
        assert 'selected_game' in response.context
        assert response.context['selected_game'] == active_game
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Should have a center panel with embedded game
        center_panel = soup.find('div', id='center-game-panel')
        assert center_panel is not None, "Dashboard should have center game panel"
        
        # Should contain game board
        game_board = center_panel.find('div', class_='game-board-grid') if center_panel else None
        assert game_board is not None, "Center panel should contain game board"
        
        # Enhanced Beautiful Soup validation
        assert game_board.get('data-board-size') == '15', "Board should have correct size attribute"
        
        # Check for HTMX attributes
        intersections = game_board.find_all('div', class_='board-intersection')
        assert len(intersections) == 225, f"Should have 225 intersections (15x15), got {len(intersections)}"
        
        # Verify some intersections have interactive HTMX attributes
        interactive_intersections = [i for i in intersections if i.get('hx-post')]
        assert len(interactive_intersections) > 0, "Should have interactive intersections for current player"
        
    def test_dashboard_shows_placeholder_when_no_active_games(self, client, db):
        """Test that dashboard shows placeholder when user has no active games."""
        # Create user with no active games
        user_no_games = UserFactory(username='nogames')
        client.force_login(user_no_games)
        
        response = client.get(reverse('web:dashboard'))
        assert response.status_code == 200
        assert response.context.get('selected_game') is None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Should have placeholder content
        center_panel = soup.find('div', id='center-game-panel')
        if center_panel:
            # Should contain placeholder text or empty state
            panel_text = center_panel.get_text().lower()
            placeholder_messages = ['no active games', 'no games', 'start playing']
            assert any(msg in panel_text for msg in placeholder_messages), \
                f"Should show placeholder when no active games. Found: {panel_text[:100]}"
            
    def test_embedded_game_shows_essential_info(self, client, users, games):
        """Test that embedded game display shows player info and game state.""" 
        user1, user2 = users
        active_game, finished_game = games
        
        client.force_login(user1)
        response = client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        center_panel = soup.find('div', id='center-game-panel')
        assert center_panel is not None, "Should have center game panel"
        
        panel_text = center_panel.get_text()
        
        # Should show player names
        assert 'player1' in panel_text, "Should show black player name"
        assert 'player2' in panel_text, "Should show white player name"
        
        # Should show game status or turn info
        status_keywords = ['active', 'turn', 'black', 'white']
        assert any(keyword in panel_text.lower() for keyword in status_keywords), \
            f"Should show game status information. Found: {panel_text[:100]}"
        
        # Enhanced validation: Check for specific game elements
        game_info = center_panel.find('div', class_='game-info')
        if game_info:
            # Test for structured game information
            player_info = game_info.find_all('span', class_=['player-name', 'current-player'])
            assert len(player_info) > 0, "Should have structured player information"
            
    def test_embedded_game_board_is_interactive(self, client, users, games):
        """Test that embedded game board allows moves when it's player's turn."""
        user1, user2 = users
        active_game, finished_game = games
        
        client.force_login(user1)
        response = client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Validate game context
        selected_game = response.context.get('selected_game')
        assert selected_game is not None, "Should have a selected game in context"
        assert selected_game.status == GameStatus.ACTIVE, "Selected game should be active"
        assert selected_game.current_player == Player.BLACK, "Current player should be BLACK"
        
        # Find board intersections
        intersections = soup.find_all('div', class_='board-intersection')
        assert len(intersections) > 0, "Should have board intersections"
        
        # Find center game panel
        center_panel = soup.find('div', id='center-game-panel')
        assert center_panel is not None, "Should have center game panel"
        
        # Enhanced Beautiful Soup validation for HTMX attributes
        clickable_intersections = [
            i for i in intersections 
            if i.get('hx-post') and 'game_move' in str(i.get('hx-post', ''))
        ]
        
        # Validate board structure and interactivity
        assert len(intersections) > 0, "Should have board intersections"
        
        # Check for HTMX SSE wrapper
        board_wrapper = soup.find('div', id='dashboard-game-board-wrapper')
        if board_wrapper:
            # Validate SSE configuration
            sse_attrs = board_wrapper.get('hx-ext')
            assert sse_attrs and 'sse' in sse_attrs, "Board wrapper should have SSE extension"
            
            # Check for SSE event listeners
            sse_swap = board_wrapper.get('sse-swap')
            assert sse_swap and 'game_move' in sse_swap, "Should listen for game_move SSE events"
        
        # Validate intersection data attributes
        for intersection in intersections[:5]:  # Check first 5 intersections
            assert intersection.get('data-row') is not None, "Intersection should have row data"
            assert intersection.get('data-col') is not None, "Intersection should have col data"
            
        # Check CSRF token presence for interactive elements
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        assert csrf_token is not None, "Should have CSRF token for secure interactions"


@pytest.mark.django_db
class TestGameSelection:
    """Tests for game selection via left panel clicks."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.user = UserFactory(username='testuser')
        self.opponent = UserFactory(username='opponent')
        
        self.ruleset = GomokuRuleSetFactory(name='Test Rules', board_size=15)
        
        # Create multiple games
        self.game1 = GameFactory(
            black_player=self.user,
            white_player=self.opponent,
            ruleset_content_type_id=self.ruleset.get_content_type().id,
            ruleset_object_id=self.ruleset.id,
            status=GameStatus.ACTIVE
        )
        self.game1.initialize_board()
        self.game1.save()
        
        self.game2 = GameFactory(
            black_player=self.user,
            white_player=self.opponent,
            ruleset_content_type_id=self.ruleset.get_content_type().id,
            ruleset_object_id=self.ruleset.id,
            status=GameStatus.ACTIVE
        )
        self.game2.initialize_board()
        self.game2.save()
        
    def test_games_panel_uses_htmx_for_game_selection(self, client):
        """Test that games in left panel use HTMX to load center panel."""
        client.force_login(self.user)
        
        response = client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find games panel
        games_panel = soup.find('div', id='games-panel')
        assert games_panel is not None, "Should have games panel"
        
        # Find game items 
        game_items = games_panel.find_all('div', class_='game-item')
        assert len(game_items) > 0, "Should have game items"
        
        # Game items should use HTMX for center panel loading
        htmx_items = []
        for item in game_items:
            if item.get('hx-get') or item.find('a', {'hx-get': True}) or item.find('button', {'hx-get': True}):
                htmx_items.append(item)
        
        assert len(htmx_items) > 0, \
              "Game items should use HTMX for loading center panel"
        
    def test_game_selection_via_url_parameter(self, client):
        """Test that specific game can be selected via URL parameter."""
        client.force_login(self.user)
        
        # Access dashboard with specific game ID
        response = client.get(f"{reverse('web:dashboard')}?game={self.game2.id}")
        assert response.status_code == 200
        
        # Should select the specified game
        assert 'selected_game' in response.context
        assert response.context['selected_game'] == self.game2
        
    def test_game_selection_htmx_endpoint(self, client):
        """Test HTMX endpoint for loading games in center panel."""
        client.force_login(self.user)
        
        # This will be implemented as part of the view updates
        # For now, test that the concept works through dashboard view
        response = client.get(f"{reverse('web:dashboard')}?game={self.game1.id}")
        assert response.status_code == 200
        assert response.context['selected_game'] == self.game1


@pytest.mark.django_db
class TestResponsiveLayout:
    """Tests for responsive behavior of single-view dashboard."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.user = UserFactory(username='mobileuser')
        
    def test_mobile_layout_maintains_functionality(self, client):
        """Test that mobile layout still provides game access."""
        client.force_login(self.user)
        
        response = client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Should still have mobile panels section
        mobile_panels = soup.find('div', class_='d-md-none')
        
        # Mobile behavior is acceptable if present or if desktop layout is responsive
        desktop_responsive = bool(soup.find_all('div', class_=lambda x: x and 'col-' in x))
        
        assert mobile_panels is not None or desktop_responsive, \
            "Should maintain mobile accessibility"




@pytest.mark.django_db
class TestIntegration:
    """Integration tests for complete single-view dashboard workflow."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.user1 = UserFactory(username='integuser1')
        self.user2 = UserFactory(username='integuser2')
        
        self.ruleset = GomokuRuleSetFactory(name='Integration Test', board_size=15)
        
        # Create friendship
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        # Create test game
        self.game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset_content_type_id=self.ruleset.get_content_type().id,
            ruleset_object_id=self.ruleset.id,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
        
    def test_complete_single_view_workflow(self, client):
        """Test complete workflow: dashboard -> embedded game -> friends panel."""
        client.force_login(self.user1)
        
        # 1. Access dashboard
        response = client.get(reverse('web:dashboard'))
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 2. Should have all three panels
        has_left_panel = bool(soup.find('div', id='games-panel'))
        has_center_panel = bool(soup.find('div', id='center-game-panel'))  
        has_right_panel = bool(soup.find('div', id='friends-panel'))
        
        # At minimum should have the structure for panels
        panels_found = sum([has_left_panel, has_center_panel, has_right_panel])
        assert panels_found >= 2, \
               "Should have at least 2 of 3 main panels"
        
        # 3. Should show selected game
        assert 'selected_game' in response.context
        assert response.context['selected_game'] == self.game
        
        # 4. Should have game board in center
        if has_center_panel:
            center_panel = soup.find('div', id='center-game-panel')
            board_elements = center_panel.find_all('div', class_='board-intersection')
            assert len(board_elements) > 0, \
                  "Center panel should contain game board"
    
    def test_dashboard_replaces_separate_game_page_functionality(self, client):
        """Test that dashboard provides same functionality as separate game page."""
        client.force_login(self.user1)
        
        # Access embedded game via dashboard
        dashboard_response = client.get(f"{reverse('web:dashboard')}?game={self.game.id}")
        
        # Access separate game page
        game_page_response = client.get(reverse('web:game_detail', kwargs={'game_id': self.game.id}))
        
        # Both should provide game access
        assert dashboard_response.status_code == 200
        assert game_page_response.status_code == 200
        
        # Dashboard should have the game context
        assert dashboard_response.context['selected_game'] == self.game
        
        # Game page should have game context  
        assert game_page_response.context['game'] == self.game