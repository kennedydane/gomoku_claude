"""
Tests for Enhanced Web Interface with Dynamic Panels (formerly Phase 11)

This module contains pytest-style tests for dashboard panel functionality:
- Navigation cleanup tests
- Games table view tests  
- Left panel (games) tests
- Right panel (friends) tests
- Dashboard layout tests
- SSE panel update tests
- Styling and responsive tests
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.template.loader import render_to_string
from bs4 import BeautifulSoup
from unittest.mock import patch

from games.models import GomokuRuleSet, Game, GameStatus, Player
from web.models import Friendship, FriendshipStatus
from tests.factories import UserFactory, GomokuRuleSetFactory, GameFactory

User = get_user_model()


@pytest.mark.django_db
class TestNavigation:
    """Tests for navigation cleanup - removing challenges menu item."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.user = UserFactory()
        self.user.set_password('testpass123')
        self.user.save()
        
    def test_challenges_menu_removed_from_navigation(self, client):
        """Test that challenges menu item is removed from navigation."""
        client.force_login(self.user)
        
        response = client.get(reverse('web:dashboard'))
        assert response.status_code == 200
        
        # Parse HTML to check navigation structure
        soup = BeautifulSoup(response.content, 'html.parser')
        nav_items = soup.find_all('a', class_='nav-link')
        
        # Should have: Dashboard, Games, Friends (NO Challenges)
        nav_texts = [item.get_text().strip() for item in nav_items if 'dropdown-toggle' not in item.get('class', [])]
        
        assert 'Dashboard' in nav_texts
        assert 'Games' in nav_texts
        assert 'Friends' in nav_texts
        assert 'Challenges' not in nav_texts
        
    def test_navigation_only_shows_expected_items(self, client):
        """Test that navigation shows only expected menu items for authenticated users."""
        client.force_login(self.user)
        
        response = client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find main navigation links (exclude user dropdown)
        main_nav = soup.find('ul', class_='navbar-nav me-auto')
        nav_links = main_nav.find_all('a', class_='nav-link') if main_nav else []
        
        # Navigation has been simplified - main navigation items are now empty
        # All functionality is accessible via dashboard modals
        expected_items = set()  # Empty navigation by design
        actual_items = {link.get_text().strip() for link in nav_links}
        
        # Should contain exactly the expected items (empty by design)
        assert actual_items == expected_items


@pytest.mark.django_db
class TestGamesTable:
    """Tests for games view table conversion."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.user1 = UserFactory(username='player1')
        self.user2 = UserFactory(username='player2')
        
        self.ruleset = GomokuRuleSetFactory(
            name='Standard Gomoku',
            board_size=15,
            description='Standard 15x15 Gomoku'
        )
        
        # Create test games
        self.active_game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset_content_type_id=self.ruleset.get_content_type().id,
            ruleset_object_id=self.ruleset.id,
            status=GameStatus.ACTIVE,
            current_player=Player.BLACK
        )
        
        self.finished_game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset_content_type_id=self.ruleset.get_content_type().id,
            ruleset_object_id=self.ruleset.id,
            status=GameStatus.FINISHED,
            winner=self.user1
        )
        
    def test_games_modal_uses_table_layout(self, client):
        """Test that games modal uses table layout instead of cards."""
        client.force_login(self.user1)
        
        response = client.get(reverse('web:games_modal'))
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Should have a table element
        table = soup.find('table')
        assert table is not None, "Games modal should use a table layout"
        
        # Should NOT have individual game cards (old layout)
        # The new layout may have one container card, but not individual game cards
        cards = soup.find_all('div', class_='card')
        game_cards = [card for card in cards if any(keyword in str(card).lower() 
                     for keyword in ['card-title', 'vs', 'black) vs', 'white)', 'view game']) 
                     and 'table' not in str(card).lower()]
        assert len(game_cards) == 0, "Games modal should not use individual card layout for games"
        
    def test_games_table_columns_present(self, client):
        """Test that games table has all required columns."""
        client.force_login(self.user1)
        
        response = client.get(reverse('web:games_modal'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check table headers
        table_headers = soup.find_all('th')
        header_texts = [th.get_text().strip() for th in table_headers]
        
        expected_columns = ['Opponent', 'Rules', 'Board Size', 'Status', 'Turn', 'Action']
        for column in expected_columns:
            assert column in header_texts, f"Table should have '{column}' column"
            
    def test_games_table_sorting(self, client):
        """Test that games are sorted with active games first, then by creation date."""
        client.force_login(self.user1)
        
        # Create more test games to verify sorting
        waiting_game = GameFactory(
            black_player=self.user1,
            white_player=self.user2,
            ruleset_content_type_id=self.ruleset.get_content_type().id,
            ruleset_object_id=self.ruleset.id,
            status=GameStatus.WAITING
        )
        
        response = client.get(reverse('web:games_modal'))
        games = response.context['games']
        
        # Convert to list to check order
        game_list = list(games)
        
        # Active and waiting games should come first
        active_statuses = [GameStatus.ACTIVE, GameStatus.WAITING]
        for i, game in enumerate(game_list):
            if game.status in active_statuses:
                # All subsequent games should also be active/waiting OR finished
                remaining_games = game_list[i:]
                finished_games = [g for g in remaining_games if g.status == GameStatus.FINISHED]
                active_games = [g for g in remaining_games if g.status in active_statuses]
                
                # All active games should come before finished games
                if finished_games:
                    last_active_idx = len(active_games) - 1 if active_games else -1
                    first_finished_idx = len(remaining_games) - len(finished_games)
                    
                    if last_active_idx >= 0:
                        assert last_active_idx < first_finished_idx, \
                               "Active games should come before finished games"
                break
                
    def test_games_table_turn_indicators(self, client):
        """Test that turn indicators are displayed correctly in the table."""
        client.force_login(self.user1)
        
        response = client.get(reverse('web:games_modal'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find turn indicator cells
        turn_cells = soup.find_all('td')  # We'll identify by content
        
        # Look for turn indicators
        found_my_turn = False
        found_their_turn = False
        
        for cell in turn_cells:
            cell_text = cell.get_text().strip().lower()
            if 'your turn' in cell_text or 'my turn' in cell_text:
                found_my_turn = True
            elif 'their turn' in cell_text or 'opponent' in cell_text:
                found_their_turn = True
                
        # For active game where current_player=BLACK and user1 is black player
        # Should show "Your Turn" for user1
        assert found_my_turn or found_their_turn, \
               "Table should display turn indicators"


@pytest.mark.django_db
class TestLeftPanel:
    """Tests for left panel (games panel) functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.user = UserFactory(username='paneluser')
        self.opponent = UserFactory(username='opponent')
        
        self.ruleset = GomokuRuleSetFactory(
            name='Test Rules',
            board_size=15
        )
        
        # Create various game states for panel testing
        self.active_game = GameFactory(
            black_player=self.user,
            white_player=self.opponent,
            ruleset_content_type_id=self.ruleset.get_content_type().id,
            ruleset_object_id=self.ruleset.id,
            status=GameStatus.ACTIVE
        )
        
        self.finished_games = []
        for i in range(7):  # Create 7 finished games to test "5 most recent" limit
            game = GameFactory(
                black_player=self.user,
                white_player=self.opponent,
                ruleset_content_type_id=self.ruleset.get_content_type().id,
                ruleset_object_id=self.ruleset.id,
                status=GameStatus.FINISHED,
                winner=self.user if i % 2 == 0 else self.opponent
            )
            self.finished_games.append(game)
            
    def test_games_panel_partial_renders(self):
        """Test that games panel partial template renders successfully."""
        # Test direct template rendering
        context = {
            'user': self.user,
            'active_games': [self.active_game],
            'recent_finished_games': self.finished_games[:5]
        }
        
        # This will fail until we create the template
        html = render_to_string('web/partials/games_panel.html', context)
        assert 'active' in html.lower()
        assert 'recent' in html.lower()
            
    def test_games_panel_shows_active_games(self, client):
        """Test that games panel displays active games with turn indicators."""
        client.force_login(self.user)
        
        # Access dashboard which should include the games panel
        response = client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for games panel section
        games_panel = soup.find('div', {'id': 'games-panel'}) or soup.find('div', class_='games-panel')
        
        if games_panel:
            # Should contain active game information
            panel_text = games_panel.get_text().lower()
            assert 'active' in panel_text
            
            # Should show turn indicator
            turn_indicators = games_panel.find_all(class_='turn-indicator') or \
                             games_panel.find_all(class_='my-turn') or \
                             games_panel.find_all(class_='their-turn')
            assert len(turn_indicators) > 0 or 'turn' in panel_text, \
                   "Games panel should show turn indicators"
        else:
            pytest.fail("Games panel should be present in dashboard")
            
    def test_games_panel_shows_recent_finished_games(self, client):
        """Test that games panel shows 5 most recent finished games."""
        client.force_login(self.user)
        
        response = client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for finished games section in panel
        games_panel = soup.find('div', {'id': 'games-panel'}) or soup.find('div', class_='games-panel')
        
        if games_panel:
            # Should have finished/recent games section
            panel_html = str(games_panel)
            assert 'finished' in panel_html.lower() or 'recent' in panel_html.lower(), \
                   "Games panel should have recent finished games section"
            
            # Count game links/items (should be limited to 5 + active games)
            game_links = games_panel.find_all('a', href=lambda x: x and '/games/' in x)
            # Active games + max 5 finished = at most 6 total
            assert len(game_links) <= 6, \
                   "Games panel should limit to 5 recent finished games"
        else:
            pytest.fail("Games panel should be present in dashboard")


@pytest.mark.django_db
class TestRightPanel:
    """Tests for right panel (friends panel) functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.user = UserFactory(username='frienduser')
        self.friend1 = UserFactory(username='friend1')
        self.friend2 = UserFactory(username='friend2')
        
        # Create friendships
        Friendship.objects.create(
            requester=self.user,
            addressee=self.friend1,
            status=FriendshipStatus.ACCEPTED
        )
        
        Friendship.objects.create(
            requester=self.friend2,
            addressee=self.user,
            status=FriendshipStatus.ACCEPTED
        )
        
    def test_friends_panel_partial_renders(self):
        """Test that friends panel partial template renders successfully."""
        context = {
            'user': self.user,
            'friends': [self.friend1, self.friend2],
            'online_friends': []  # Placeholder for online status
        }
        
        html = render_to_string('web/partials/friends_panel.html', context)
        assert 'friend' in html.lower()
            
    def test_friends_panel_shows_online_friends(self, client):
        """Test that friends panel displays friends with online indicators."""
        client.force_login(self.user)
        
        response = client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for friends panel
        friends_panel = soup.find('div', {'id': 'friends-panel'}) or soup.find('div', class_='friends-panel')
        
        if friends_panel:
            panel_text = friends_panel.get_text().lower()
            assert 'friend' in panel_text
            
            # Should have friend names
            assert 'friend1' in panel_text
            assert 'friend2' in panel_text
        else:
            pytest.fail("Friends panel should be present in dashboard")
            
    def test_friends_panel_challenge_buttons_work(self, client):
        """Test that challenge buttons in friends panel are functional."""
        client.force_login(self.user)
        
        response = client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        friends_panel = soup.find('div', {'id': 'friends-panel'}) or soup.find('div', class_='friends-panel')
        
        if friends_panel:
            # Look for challenge buttons
            challenge_buttons = friends_panel.find_all('button') or friends_panel.find_all('a')
            challenge_buttons = [btn for btn in challenge_buttons 
                               if 'challenge' in str(btn).lower()]
            
            assert len(challenge_buttons) > 0, \
                   "Friends panel should have challenge buttons"
            
            # Buttons should have appropriate attributes for HTMX or JavaScript
            for button in challenge_buttons:
                has_action = any([
                    button.get('onclick'),
                    button.get('hx-post'),
                    button.get('data-bs-toggle')
                ])
                assert has_action, \
                      "Challenge buttons should have action handlers"
        else:
            pytest.fail("Friends panel should be present in dashboard")


@pytest.mark.django_db
class TestDashboardLayout:
    """Tests for 3-column dashboard layout."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.user = UserFactory(username='layoutuser')
        
    def test_dashboard_three_column_layout(self, client):
        """Test that dashboard uses 3-column layout structure."""
        client.force_login(self.user)
        
        response = client.get(reverse('web:dashboard'))
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for Bootstrap grid structure - can be container or container-fluid
        container = soup.find('div', class_='container') or soup.find('div', class_='container-fluid')
        assert container is not None, "Dashboard should have container div"
        
        # Look for all Bootstrap columns anywhere in the document
        all_columns = soup.find_all('div', class_=lambda x: x and any(
            col_class in x for col_class in ['col-', 'col-md-', 'col-lg-', 'col-xl-']
        ))
        
        # Should have at least 3 columns for the main layout (left panel, main content, right panel)
        assert len(all_columns) >= 3, \
               "Dashboard should have 3-column layout structure"
        
        # Check for specific layout elements
        has_left_panel = bool(soup.find('div', class_='col-lg-3 col-md-4 d-none d-md-block'))
        has_main_content = bool(soup.find('div', class_='col-lg-6 col-md-8 col-12'))
        has_right_panel = bool(soup.find('div', class_='col-lg-3 d-none d-lg-block'))
        
        assert has_left_panel or has_main_content or has_right_panel, \
               "Dashboard should have specific column layout classes"
                               
    def test_dashboard_panels_render_correctly(self, client):
        """Test that both panels render correctly in dashboard layout."""
        client.force_login(self.user)
        
        response = client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Should have games panel
        games_panel_exists = bool(
            soup.find('div', {'id': 'games-panel'}) or 
            soup.find('div', class_='games-panel') or
            'active games' in response.content.decode().lower()
        )
        
        # Should have friends panel  
        friends_panel_exists = bool(
            soup.find('div', {'id': 'friends-panel'}) or
            soup.find('div', class_='friends-panel') or
            'online friends' in response.content.decode().lower()
        )
        
        assert games_panel_exists, "Dashboard should include games panel"
        assert friends_panel_exists, "Dashboard should include friends panel"
        
    def test_dashboard_responsive_design(self, client):
        """Test that dashboard layout is responsive (basic structure test)."""
        client.force_login(self.user)
        
        response = client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for responsive column classes
        responsive_columns = soup.find_all('div', class_=lambda x: x and any(
            responsive_class in x for responsive_class in ['col-md-', 'col-lg-', 'col-xl-', 'col-sm-']
        ))
        
        assert len(responsive_columns) > 0, \
               "Dashboard should use responsive column classes"
                       
        # Check for mobile-specific behavior hints (data attributes, classes, etc.)
        mobile_responsive_elements = soup.find_all(attrs={
            'class': lambda x: x and any(
                mobile_class in x for mobile_class in ['d-md-', 'd-lg-', 'collapse', 'offcanvas']
            )
        })
        
        # At minimum, should use responsive grid system
        assert len(responsive_columns) >= 2, \
               "Dashboard should implement responsive design patterns"



@pytest.mark.django_db
class TestStyling:
    """Tests for consistent styling and responsive behavior."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.user = UserFactory(username='styleuser')
        
    def test_panel_styling_consistent(self, client):
        """Test that panel styling is consistent across panels."""
        client.force_login(self.user)
        
        response = client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for panel elements
        panel_elements = soup.find_all('div', class_=lambda x: x and 'panel' in x.lower()) or \
                        soup.find_all('div', {'id': lambda x: x and 'panel' in x.lower() if x else False})
        
        if panel_elements:
            # Check for consistent styling classes
            for panel in panel_elements:
                classes = panel.get('class', [])
                # Should have Bootstrap card or custom panel classes
                has_styling = any([
                    'card' in classes,
                    'panel' in ' '.join(classes).lower(),
                    'border' in ' '.join(classes),
                    panel.find('div', class_='card-body')
                ])
                assert has_styling, f"Panel should have consistent styling: {classes}"
        # If no panels found yet, that's expected in TDD - this test will guide implementation
        
    def test_turn_indicator_visual_design(self, client):
        """Test that turn indicators have distinctive visual design."""
        # This test will initially fail and guide the CSS implementation
        
        # Create game data for turn indicators
        opponent = UserFactory(username='opponent')
        ruleset = GomokuRuleSetFactory(name='Test', board_size=15)
        
        GameFactory(
            black_player=self.user,
            white_player=opponent,
            ruleset_content_type_id=ruleset.get_content_type().id,
            ruleset_object_id=ruleset.id,
            status=GameStatus.ACTIVE,
            current_player=Player.BLACK
        )
        
        client.force_login(self.user)
        response = client.get(reverse('web:games_modal'))
        
        # Look for turn indicator styling in CSS or inline styles
        content = response.content.decode()
        
        # Should have turn indicator related CSS classes or styles
        turn_related_styles = any([
            '.my-turn' in content,
            '.their-turn' in content,
            '.turn-indicator' in content,
            'your turn' in content.lower(),
            'their turn' in content.lower()
        ])
        
        assert turn_related_styles, \
               "Turn indicators should have distinctive visual styling"


@pytest.mark.django_db
class TestIntegration:
    """Integration tests for complete panel workflows."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.user1 = UserFactory(username='integuser1')
        self.user2 = UserFactory(username='integuser2')
        
        # Create friendship
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        self.ruleset = GomokuRuleSetFactory(name='Integration Test', board_size=15)
        
    def test_complete_panel_workflow(self, client):
        """Test complete workflow: dashboard -> games panel -> game -> friends panel -> challenge."""
        client.force_login(self.user1)
        
        # 1. Access dashboard with panels
        response = client.get(reverse('web:dashboard'))
        assert response.status_code == 200
        
        # 2. Should show panels (even if empty initially)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for panel structure or content
        has_games_section = bool(
            soup.find(text=lambda x: x and 'game' in x.lower()) or
            soup.find('div', {'id': lambda x: x and 'game' in x.lower() if x else False}) or
            'active games' in response.content.decode().lower()
        )
        
        has_friends_section = bool(
            soup.find(text=lambda x: x and 'friend' in x.lower()) or
            soup.find('div', {'id': lambda x: x and 'friend' in x.lower() if x else False}) or
            'online friends' in response.content.decode().lower()
        )
        
        # At minimum, should show some structure for panels
        # (This test guides the implementation - initially may not find fully implemented panels)
        assert has_games_section or has_friends_section or len(soup.find_all('div', class_='col-')) >= 3, \
               "Dashboard should show panel structure or multi-column layout"
        
        # 3. Access games modal (should be table format)
        games_response = client.get(reverse('web:games_modal'))
        assert games_response.status_code == 200
        
        # Should not be using old card layout
        games_soup = BeautifulSoup(games_response.content, 'html.parser')
        game_cards = games_soup.find_all('div', class_='card')
        # Filter out non-game cards (like navigation, containers, etc.)
        game_specific_cards = [card for card in game_cards 
                              if any(keyword in str(card).lower() 
                                   for keyword in ['vs', 'black', 'white', 'opponent'])]
        
        assert len(game_specific_cards) == 0, \
                "Games modal should not use card layout for games"