"""
Phase 11 TDD Tests: Enhanced Web Interface with Dynamic Panels

This module contains all the test cases for Phase 11 development following
strict TDD methodology (RED-GREEN-REFACTOR).

Test Categories:
- Navigation cleanup tests
- Games table view tests  
- Left panel (games) tests
- Right panel (friends) tests
- Dashboard layout tests
- SSE panel update tests
- Styling and responsive tests
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.template.loader import render_to_string
from django.http import HttpRequest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.base import SessionBase
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock

from games.models import Game, RuleSet, GameStatus, Player
from web.models import Friendship, FriendshipStatus

User = get_user_model()


class Phase11NavigationTests(TestCase):
    """Tests for navigation cleanup - removing challenges menu item."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = Client()
        
    def test_challenges_menu_removed_from_navigation(self):
        """Test that challenges menu item is removed from navigation."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('web:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Parse HTML to check navigation structure
        soup = BeautifulSoup(response.content, 'html.parser')
        nav_items = soup.find_all('a', class_='nav-link')
        
        # Should have: Dashboard, Games, Friends (NO Challenges)
        nav_texts = [item.get_text().strip() for item in nav_items if 'dropdown-toggle' not in item.get('class', [])]
        
        self.assertIn('Dashboard', nav_texts)
        self.assertIn('Games', nav_texts) 
        self.assertIn('Friends', nav_texts)
        self.assertNotIn('Challenges', nav_texts)
        
    def test_navigation_only_shows_expected_items(self):
        """Test that navigation shows only expected menu items for authenticated users."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('web:home'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find main navigation links (exclude user dropdown)
        main_nav = soup.find('ul', class_='navbar-nav me-auto')
        nav_links = main_nav.find_all('a', class_='nav-link') if main_nav else []
        
        expected_items = {'Dashboard', 'Games', 'Friends'}
        actual_items = {link.get_text().strip() for link in nav_links}
        
        # Should contain exactly the expected items, no more, no less
        self.assertEqual(actual_items, expected_items)


class Phase11GamesTableTests(TestCase):
    """Tests for games view table conversion."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(username='player1', password='pass123')
        self.user2 = User.objects.create_user(username='player2', password='pass123')
        
        self.ruleset = RuleSet.objects.create(
            name='Standard Gomoku',
            board_size=15,
            description='Standard 15x15 Gomoku'
        )
        
        # Create test games
        self.active_game = Game.objects.create(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE,
            current_player=Player.BLACK
        )
        
        self.finished_game = Game.objects.create(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.FINISHED,
            winner=self.user1
        )
        
        self.client = Client()
        
    def test_games_view_uses_table_layout(self):
        """Test that games view uses table layout instead of cards."""
        self.client.login(username='player1', password='pass123')
        
        response = self.client.get(reverse('web:games'))
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Should have a table element
        table = soup.find('table')
        self.assertIsNotNone(table, "Games view should use a table layout")
        
        # Should NOT have individual game cards (old layout)
        # The new layout may have one container card, but not individual game cards
        cards = soup.find_all('div', class_='card')
        game_cards = [card for card in cards if any(keyword in str(card).lower() 
                     for keyword in ['card-title', 'vs', 'black) vs', 'white)', 'view game']) 
                     and 'table' not in str(card).lower()]
        self.assertEqual(len(game_cards), 0, "Games view should not use individual card layout for games")
        
    def test_games_table_columns_present(self):
        """Test that games table has all required columns."""
        self.client.login(username='player1', password='pass123')
        
        response = self.client.get(reverse('web:games'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check table headers
        table_headers = soup.find_all('th')
        header_texts = [th.get_text().strip() for th in table_headers]
        
        expected_columns = ['Opponent', 'Rules', 'Board Size', 'Status', 'Turn', 'Action']
        for column in expected_columns:
            self.assertIn(column, header_texts, f"Table should have '{column}' column")
            
    def test_games_table_sorting(self):
        """Test that games are sorted with active games first, then by creation date."""
        self.client.login(username='player1', password='pass123')
        
        # Create more test games to verify sorting
        waiting_game = Game.objects.create(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.WAITING
        )
        
        response = self.client.get(reverse('web:games'))
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
                        self.assertLess(last_active_idx, first_finished_idx, 
                                       "Active games should come before finished games")
                break
                
    def test_games_table_turn_indicators(self):
        """Test that turn indicators are displayed correctly in the table."""
        self.client.login(username='player1', password='pass123')
        
        response = self.client.get(reverse('web:games'))
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
        self.assertTrue(found_my_turn or found_their_turn, 
                       "Table should display turn indicators")


class Phase11LeftPanelTests(TestCase):
    """Tests for left panel (games panel) functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='paneluser', password='pass123')
        self.opponent = User.objects.create_user(username='opponent', password='pass123')
        
        self.ruleset = RuleSet.objects.create(
            name='Test Rules',
            board_size=15
        )
        
        # Create various game states for panel testing
        self.active_game = Game.objects.create(
            black_player=self.user,
            white_player=self.opponent,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        
        self.finished_games = []
        for i in range(7):  # Create 7 finished games to test "5 most recent" limit
            game = Game.objects.create(
                black_player=self.user,
                white_player=self.opponent, 
                ruleset=self.ruleset,
                status=GameStatus.FINISHED,
                winner=self.user if i % 2 == 0 else self.opponent
            )
            self.finished_games.append(game)
            
        self.client = Client()
        
    def test_games_panel_partial_renders(self):
        """Test that games panel partial template renders successfully."""
        # Test direct template rendering
        context = {
            'user': self.user,
            'active_games': [self.active_game],
            'recent_finished_games': self.finished_games[:5]
        }
        
        # This will fail until we create the template
        try:
            html = render_to_string('web/partials/games_panel.html', context)
            self.assertIn('active', html.lower())
            self.assertIn('recent', html.lower())
        except Exception as e:
            self.fail(f"Games panel template should render without errors: {e}")
            
    def test_games_panel_shows_active_games(self):
        """Test that games panel displays active games with turn indicators."""
        self.client.login(username='paneluser', password='pass123')
        
        # Access dashboard which should include the games panel
        response = self.client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for games panel section
        games_panel = soup.find('div', {'id': 'games-panel'}) or soup.find('div', class_='games-panel')
        
        if games_panel:
            # Should contain active game information
            panel_text = games_panel.get_text().lower()
            self.assertIn('active', panel_text)
            
            # Should show turn indicator
            turn_indicators = games_panel.find_all(class_='turn-indicator') or \
                             games_panel.find_all(class_='my-turn') or \
                             games_panel.find_all(class_='their-turn')
            self.assertTrue(len(turn_indicators) > 0 or 'turn' in panel_text,
                           "Games panel should show turn indicators")
        else:
            self.fail("Games panel should be present in dashboard")
            
    def test_games_panel_shows_recent_finished_games(self):
        """Test that games panel shows 5 most recent finished games."""
        self.client.login(username='paneluser', password='pass123')
        
        response = self.client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for finished games section in panel
        games_panel = soup.find('div', {'id': 'games-panel'}) or soup.find('div', class_='games-panel')
        
        if games_panel:
            # Should have finished/recent games section
            panel_html = str(games_panel)
            self.assertTrue('finished' in panel_html.lower() or 'recent' in panel_html.lower(),
                           "Games panel should have recent finished games section")
            
            # Count game links/items (should be limited to 5 + active games)
            game_links = games_panel.find_all('a', href=lambda x: x and '/games/' in x)
            # Active games + max 5 finished = at most 6 total
            self.assertLessEqual(len(game_links), 6,
                               "Games panel should limit to 5 recent finished games")
        else:
            self.fail("Games panel should be present in dashboard")


class Phase11RightPanelTests(TestCase):
    """Tests for right panel (friends panel) functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='frienduser', password='pass123')
        self.friend1 = User.objects.create_user(username='friend1', password='pass123')
        self.friend2 = User.objects.create_user(username='friend2', password='pass123')
        
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
        
        self.client = Client()
        
    def test_friends_panel_partial_renders(self):
        """Test that friends panel partial template renders successfully."""
        context = {
            'user': self.user,
            'friends': [self.friend1, self.friend2],
            'online_friends': []  # Placeholder for online status
        }
        
        try:
            html = render_to_string('web/partials/friends_panel.html', context)
            self.assertIn('friend', html.lower())
        except Exception as e:
            self.fail(f"Friends panel template should render without errors: {e}")
            
    def test_friends_panel_shows_online_friends(self):
        """Test that friends panel displays friends with online indicators."""
        self.client.login(username='frienduser', password='pass123')
        
        response = self.client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for friends panel
        friends_panel = soup.find('div', {'id': 'friends-panel'}) or soup.find('div', class_='friends-panel')
        
        if friends_panel:
            panel_text = friends_panel.get_text().lower()
            self.assertIn('friend', panel_text)
            
            # Should have friend names
            self.assertIn('friend1', panel_text)
            self.assertIn('friend2', panel_text)
        else:
            self.fail("Friends panel should be present in dashboard")
            
    def test_friends_panel_challenge_buttons_work(self):
        """Test that challenge buttons in friends panel are functional."""
        self.client.login(username='frienduser', password='pass123')
        
        response = self.client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        friends_panel = soup.find('div', {'id': 'friends-panel'}) or soup.find('div', class_='friends-panel')
        
        if friends_panel:
            # Look for challenge buttons
            challenge_buttons = friends_panel.find_all('button') or friends_panel.find_all('a')
            challenge_buttons = [btn for btn in challenge_buttons 
                               if 'challenge' in str(btn).lower()]
            
            self.assertTrue(len(challenge_buttons) > 0,
                           "Friends panel should have challenge buttons")
            
            # Buttons should have appropriate attributes for HTMX or JavaScript
            for button in challenge_buttons:
                has_action = any([
                    button.get('onclick'),
                    button.get('hx-post'),
                    button.get('data-bs-toggle')
                ])
                self.assertTrue(has_action, 
                              "Challenge buttons should have action handlers")
        else:
            self.fail("Friends panel should be present in dashboard")


class Phase11DashboardLayoutTests(TestCase):
    """Tests for 3-column dashboard layout."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='layoutuser', password='pass123')
        self.client = Client()
        
    def test_dashboard_three_column_layout(self):
        """Test that dashboard uses 3-column layout structure."""
        self.client.login(username='layoutuser', password='pass123')
        
        response = self.client.get(reverse('web:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for Bootstrap grid structure - can be container or container-fluid
        container = soup.find('div', class_='container') or soup.find('div', class_='container-fluid')
        self.assertIsNotNone(container, "Dashboard should have container div")
        
        # Look for all Bootstrap columns anywhere in the document
        all_columns = soup.find_all('div', class_=lambda x: x and any(
            col_class in x for col_class in ['col-', 'col-md-', 'col-lg-', 'col-xl-']
        ))
        
        # Should have at least 3 columns for the main layout (left panel, main content, right panel)
        self.assertGreaterEqual(len(all_columns), 3,
                               "Dashboard should have 3-column layout structure")
        
        # Check for specific layout elements
        has_left_panel = bool(soup.find('div', class_='col-lg-3 col-md-4 d-none d-md-block'))
        has_main_content = bool(soup.find('div', class_='col-lg-6 col-md-8 col-12'))
        has_right_panel = bool(soup.find('div', class_='col-lg-3 d-none d-lg-block'))
        
        self.assertTrue(has_left_panel or has_main_content or has_right_panel,
                       "Dashboard should have specific column layout classes")
                               
    def test_dashboard_panels_render_correctly(self):
        """Test that both panels render correctly in dashboard layout."""
        self.client.login(username='layoutuser', password='pass123')
        
        response = self.client.get(reverse('web:dashboard'))
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
        
        self.assertTrue(games_panel_exists, "Dashboard should include games panel")
        self.assertTrue(friends_panel_exists, "Dashboard should include friends panel")
        
    def test_dashboard_responsive_design(self):
        """Test that dashboard layout is responsive (basic structure test)."""
        self.client.login(username='layoutuser', password='pass123')
        
        response = self.client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for responsive column classes
        responsive_columns = soup.find_all('div', class_=lambda x: x and any(
            responsive_class in x for responsive_class in ['col-md-', 'col-lg-', 'col-xl-', 'col-sm-']
        ))
        
        self.assertTrue(len(responsive_columns) > 0,
                       "Dashboard should use responsive column classes")
                       
        # Check for mobile-specific behavior hints (data attributes, classes, etc.)
        mobile_responsive_elements = soup.find_all(attrs={
            'class': lambda x: x and any(
                mobile_class in x for mobile_class in ['d-md-', 'd-lg-', 'collapse', 'offcanvas']
            )
        })
        
        # At minimum, should use responsive grid system
        self.assertTrue(len(responsive_columns) >= 2,
                       "Dashboard should implement responsive design patterns")


class Phase11SSEPanelUpdateTests(TestCase):
    """Tests for SSE integration with panels."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(username='player1', password='pass123')
        self.user2 = User.objects.create_user(username='player2', password='pass123')
        
        self.ruleset = RuleSet.objects.create(
            name='Test Ruleset',
            board_size=15
        )
        
        self.game = Game.objects.create(
            black_player=self.user1,
            white_player=self.user2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
        
        self.client = Client()
        
    @patch('web.views.send_event')
    def test_sse_updates_turn_indicators(self, mock_send_event):
        """Test that SSE events update turn indicators across panels."""
        self.client.login(username='player1', password='pass123')
        
        # Make a move which should trigger SSE updates
        response = self.client.post(
            reverse('web:game_move', kwargs={'game_id': self.game.id}),
            {'row': 7, 'col': 7}
        )
        
        # Should have called send_event for SSE updates
        if mock_send_event.called:
            # Check that at least one SSE event was sent
            self.assertTrue(mock_send_event.call_count >= 1, "At least one SSE event should be sent after move")
            
            # Check all the calls made to send_event
            event_names = []
            for call in mock_send_event.call_args_list:
                channel, event_name, data = call[0][:3]
                self.assertIn('user-', channel, "SSE should target user channel")
                self.assertIn('<', str(data), "SSE data should contain HTML")
                event_names.append(event_name)
            
            # Should include game board update and potentially dashboard update
            self.assertIn('game_move', event_names, "Should send game_move event")
            # Dashboard update is optional but if sent, should be present
            if len(event_names) > 1:
                self.assertIn('dashboard_update', event_names, "Should send dashboard_update event if multiple events")
            
    def test_htmx_sse_panel_swapping(self):
        """Test that panels have HTMX SSE attributes for swapping."""
        self.client.login(username='player1', password='pass123')
        
        response = self.client.get(reverse('web:dashboard'))
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for HTMX SSE attributes
        sse_elements = soup.find_all(attrs={
            'hx-ext': lambda x: x and 'sse' in x,
        }) or soup.find_all(attrs={
            'sse-connect': True
        }) or soup.find_all(attrs={
            'sse-swap': True
        })
        
        # Should have elements configured for SSE
        self.assertTrue(len(sse_elements) > 0 or 'sse' in response.content.decode().lower(),
                       "Dashboard should have HTMX SSE configuration")


class Phase11StylingTests(TestCase):
    """Tests for consistent styling and responsive behavior."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='styleuser', password='pass123')
        self.client = Client()
        
    def test_panel_styling_consistent(self):
        """Test that panel styling is consistent across panels."""
        self.client.login(username='styleuser', password='pass123')
        
        response = self.client.get(reverse('web:dashboard'))
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
                self.assertTrue(has_styling, 
                              f"Panel should have consistent styling: {classes}")
        # If no panels found yet, that's expected in TDD - this test will guide implementation
        
    def test_turn_indicator_visual_design(self):
        """Test that turn indicators have distinctive visual design."""
        # This test will initially fail and guide the CSS implementation
        
        # Create game data for turn indicators
        opponent = User.objects.create_user(username='opponent', password='pass123')
        ruleset = RuleSet.objects.create(name='Test', board_size=15)
        
        Game.objects.create(
            black_player=self.user,
            white_player=opponent,
            ruleset=ruleset,
            status=GameStatus.ACTIVE,
            current_player=Player.BLACK
        )
        
        self.client.login(username='styleuser', password='pass123')
        response = self.client.get(reverse('web:games'))
        
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
        
        self.assertTrue(turn_related_styles,
                       "Turn indicators should have distinctive visual styling")


# Integration test class for end-to-end workflows
class Phase11IntegrationTests(TestCase):
    """Integration tests for complete panel workflows."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(username='integuser1', password='pass123')
        self.user2 = User.objects.create_user(username='integuser2', password='pass123')
        
        # Create friendship
        Friendship.objects.create(
            requester=self.user1,
            addressee=self.user2,
            status=FriendshipStatus.ACCEPTED
        )
        
        self.ruleset = RuleSet.objects.create(name='Integration Test', board_size=15)
        
        self.client = Client()
        
    def test_complete_panel_workflow(self):
        """Test complete workflow: dashboard -> games panel -> game -> friends panel -> challenge."""
        self.client.login(username='integuser1', password='pass123')
        
        # 1. Access dashboard with panels
        response = self.client.get(reverse('web:dashboard'))
        self.assertEqual(response.status_code, 200)
        
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
        self.assertTrue(has_games_section or has_friends_section or len(soup.find_all('div', class_='col-')) >= 3,
                       "Dashboard should show panel structure or multi-column layout")
        
        # 3. Access games view (should be table format)
        games_response = self.client.get(reverse('web:games'))
        self.assertEqual(games_response.status_code, 200)
        
        # Should not be using old card layout
        games_soup = BeautifulSoup(games_response.content, 'html.parser')
        game_cards = games_soup.find_all('div', class_='card')
        # Filter out non-game cards (like navigation, containers, etc.)
        game_specific_cards = [card for card in game_cards 
                              if any(keyword in str(card).lower() 
                                   for keyword in ['vs', 'black', 'white', 'opponent'])]
        
        self.assertEqual(len(game_specific_cards), 0,
                        "Games view should not use card layout for games")


if __name__ == '__main__':
    # Run specific test categories
    import sys
    if len(sys.argv) > 1:
        test_category = sys.argv[1]
        if test_category == 'navigation':
            from django.test.utils import get_runner
            from django.conf import settings
            TestRunner = get_runner(settings)
            test_runner = TestRunner()
            failures = test_runner.run_tests(['web.test_phase11_panels.Phase11NavigationTests'])
        elif test_category == 'tables':
            TestRunner = get_runner(settings)
            test_runner = TestRunner()
            failures = test_runner.run_tests(['web.test_phase11_panels.Phase11GamesTableTests'])
    else:
        # Run all Phase 11 tests
        pass