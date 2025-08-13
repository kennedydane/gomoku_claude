"""
Selenium tests for multiplayer Gomoku game with Server-Sent Events (SSE).
"""
import pytest
import time
from django.test import TransactionTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth import get_user_model
from games.models import Game, RuleSet, GameStatus
from .utils.sse_helpers import SSEEventWatcher, GameBoardHelper, login_user, wait_for_page_load


User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestMultiplayerGameFlow:
    """Test complete multiplayer game flow with real-time updates."""
    
    def setup_method(self):
        """Set up test data for each test."""
        # Create test users
        self.player1 = User.objects.create_user(
            username='player1', 
            password='testpass123'
        )
        self.player2 = User.objects.create_user(
            username='player2', 
            password='testpass123'
        )
        
        # Create a standard ruleset
        self.ruleset = RuleSet.objects.create(
            name='Test Gomoku',
            description='Standard 15x15 Gomoku for testing',
            board_size=15,
            allow_overlines=True
        )
        
        # Create a test game
        self.game = Game.objects.create(
            black_player=self.player1,
            white_player=self.player2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
    
    def test_two_player_login_and_navigation(self, dual_chrome_drivers, live_server):
        """Test that both players can log in and navigate to the game."""
        driver1, driver2 = dual_chrome_drivers
        live_server_url = live_server.url
        
        # Both players log in
        assert login_user(driver1, live_server_url, 'player1', 'testpass123')
        assert login_user(driver2, live_server_url, 'player2', 'testpass123')
        
        # Both players navigate to the game
        game_url = f"{live_server_url}/games/{self.game.id}/"
        
        driver1.get(game_url)
        driver2.get(game_url)
        
        # Verify both players can see the game board
        board_helper1 = GameBoardHelper(driver1)
        board_helper2 = GameBoardHelper(driver2)
        
        assert board_helper1.wait_for_board(timeout=10)
        assert board_helper2.wait_for_board(timeout=10)
        
        # Verify board size
        assert board_helper1.get_board_size() == 15
        assert board_helper2.get_board_size() == 15
    
    def test_sse_connection_establishment(self, dual_chrome_drivers, live_server):
        """Test that SSE connections are established properly for both players."""
        driver1, driver2 = dual_chrome_drivers
        live_server_url = live_server.url
        
        # Log in both players
        assert login_user(driver1, live_server_url, 'player1', 'testpass123')
        assert login_user(driver2, live_server_url, 'player2', 'testpass123')
        
        # Navigate to game
        game_url = f"{live_server_url}/games/{self.game.id}/"
        driver1.get(game_url)
        driver2.get(game_url)
        
        # Set up SSE monitoring
        sse_watcher1 = SSEEventWatcher(driver1)
        sse_watcher2 = SSEEventWatcher(driver2)
        
        assert sse_watcher1.start_monitoring(['game_move'])
        assert sse_watcher2.start_monitoring(['game_move'])
        
        # Wait for SSE connections to be established
        assert sse_watcher1.wait_for_connection(timeout=15)
        assert sse_watcher2.wait_for_connection(timeout=15)
    
    def test_real_time_move_propagation(self, dual_chrome_drivers, live_server):
        """Test that moves made by one player appear in real-time for the other player."""
        driver1, driver2 = dual_chrome_drivers
        live_server_url = live_server.url
        
        # Log in both players
        assert login_user(driver1, live_server_url, 'player1', 'testpass123')
        assert login_user(driver2, live_server_url, 'player2', 'testpass123')
        
        # Navigate to game
        game_url = f"{live_server_url}/games/{self.game.id}/"
        driver1.get(game_url)
        driver2.get(game_url)
        
        # Set up helpers
        board_helper1 = GameBoardHelper(driver1)
        board_helper2 = GameBoardHelper(driver2)
        sse_watcher2 = SSEEventWatcher(driver2)
        
        # Wait for boards to load
        assert board_helper1.wait_for_board(timeout=10)
        assert board_helper2.wait_for_board(timeout=10)
        
        # Set up SSE monitoring for player 2 (who will receive the update)
        assert sse_watcher2.start_monitoring(['game_move'])
        assert sse_watcher2.wait_for_connection(timeout=15)
        
        # Player 1 makes a move (black stone at center)
        row, col = 7, 7
        initial_state = board_helper2.get_intersection_state(row, col)
        assert initial_state == "empty"
        
        # Player 1 clicks the intersection
        assert board_helper1.click_intersection(row, col)
        assert board_helper1.wait_for_move_completion()
        
        # Wait for SSE event on player 2's browser
        event = sse_watcher2.wait_for_event('game_move', timeout=10)
        assert event is not None
        assert 'data' in event
        
        # Give a moment for the DOM to update
        time.sleep(1)
        
        # Verify the move appears on player 2's board
        updated_state = board_helper2.get_intersection_state(row, col)
        assert updated_state == "black"
    
    def test_alternating_moves_with_sse(self, dual_chrome_drivers, live_server):
        """Test alternating moves between players with SSE updates."""
        driver1, driver2 = dual_chrome_drivers
        live_server_url = live_server.url
        
        # Log in both players
        assert login_user(driver1, live_server_url, 'player1', 'testpass123')
        assert login_user(driver2, live_server_url, 'player2', 'testpass123')
        
        # Navigate to game
        game_url = f"{live_server_url}/games/{self.game.id}/"
        driver1.get(game_url)
        driver2.get(game_url)
        
        # Set up helpers
        board_helper1 = GameBoardHelper(driver1)
        board_helper2 = GameBoardHelper(driver2)
        sse_watcher1 = SSEEventWatcher(driver1)
        sse_watcher2 = SSEEventWatcher(driver2)
        
        # Wait for boards and SSE connections
        assert board_helper1.wait_for_board(timeout=10)
        assert board_helper2.wait_for_board(timeout=10)
        assert sse_watcher1.start_monitoring(['game_move'])
        assert sse_watcher2.start_monitoring(['game_move'])
        assert sse_watcher1.wait_for_connection(timeout=15)
        assert sse_watcher2.wait_for_connection(timeout=15)
        
        # Test sequence of moves
        moves = [
            (7, 7, 'player1', 'black'),    # Player 1 (black) moves first
            (7, 8, 'player2', 'white'),    # Player 2 (white) responds
            (8, 7, 'player1', 'black'),    # Player 1 continues
        ]
        
        for move_num, (row, col, player, expected_color) in enumerate(moves):
            if player == 'player1':
                mover_helper = board_helper1
                watcher_helper = sse_watcher2  # Player 2 watches for player 1's moves
            else:
                mover_helper = board_helper2
                watcher_helper = sse_watcher1  # Player 1 watches for player 2's moves
            
            # Clear previous events
            watcher_helper.clear_events()
            
            # Make the move
            assert mover_helper.click_intersection(row, col)
            assert mover_helper.wait_for_move_completion()
            
            # Wait for SSE event
            event = watcher_helper.wait_for_event('game_move', timeout=10)
            assert event is not None
            
            # Give DOM time to update
            time.sleep(1)
            
            # Verify move appears on both boards
            state1 = board_helper1.get_intersection_state(row, col)
            state2 = board_helper2.get_intersection_state(row, col)
            assert state1 == expected_color
            assert state2 == expected_color
    
    def test_board_state_synchronization(self, dual_chrome_drivers, live_server):
        """Test that complete board states remain synchronized."""
        driver1, driver2 = dual_chrome_drivers
        live_server_url = live_server.url
        
        # Log in both players
        assert login_user(driver1, live_server_url, 'player1', 'testpass123')
        assert login_user(driver2, live_server_url, 'player2', 'testpass123')
        
        # Navigate to game
        game_url = f"{live_server_url}/games/{self.game.id}/"
        driver1.get(game_url)
        driver2.get(game_url)
        
        # Set up helpers
        board_helper1 = GameBoardHelper(driver1)
        board_helper2 = GameBoardHelper(driver2)
        sse_watcher1 = SSEEventWatcher(driver1)
        sse_watcher2 = SSEEventWatcher(driver2)
        
        # Wait for initialization
        assert board_helper1.wait_for_board(timeout=10)
        assert board_helper2.wait_for_board(timeout=10)
        assert sse_watcher1.start_monitoring(['game_move'])
        assert sse_watcher2.start_monitoring(['game_move'])
        assert sse_watcher1.wait_for_connection(timeout=15)
        assert sse_watcher2.wait_for_connection(timeout=15)
        
        # Make several moves
        moves = [(7, 7), (7, 8), (8, 7), (8, 8)]
        current_player = 'player1'
        
        for row, col in moves:
            if current_player == 'player1':
                mover_helper = board_helper1
                watcher_helper = sse_watcher2
            else:
                mover_helper = board_helper2
                watcher_helper = sse_watcher1
            
            # Make move and wait for propagation
            assert mover_helper.click_intersection(row, col)
            assert mover_helper.wait_for_move_completion()
            watcher_helper.wait_for_event('game_move', timeout=10)
            time.sleep(1)  # Allow DOM update
            
            # Switch players
            current_player = 'player2' if current_player == 'player1' else 'player1'
        
        # Compare complete board states
        board_state1 = board_helper1.get_board_state()
        board_state2 = board_helper2.get_board_state()
        
        # Boards should be identical
        assert board_state1 == board_state2
        
        # Verify specific moves are present
        assert board_state1[7][7] in ['black', 'white']  # Should have a stone
        assert board_state1[7][8] in ['black', 'white']  # Should have a stone
        assert board_state1[8][7] in ['black', 'white']  # Should have a stone
        assert board_state1[8][8] in ['black', 'white']  # Should have a stone


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("browser_driver", ["chrome", "firefox"], indirect=True)
class TestCrossBrowserSSE:
    """Test SSE functionality across different browsers."""
    
    def setup_method(self):
        """Set up test data for each test."""
        self.user = User.objects.create_user(
            username='testuser', 
            password='testpass123'
        )
        
        self.ruleset = RuleSet.objects.create(
            name='Test Gomoku',
            description='Standard 15x15 Gomoku for testing',
            board_size=15,
            allow_overlines=True
        )
    
    def test_sse_connection_cross_browser(self, browser_driver, live_server):
        """Test SSE connection works across different browsers."""
        live_server_url = live_server.url
        
        # Log in user
        assert login_user(browser_driver, live_server_url, 'testuser', 'testpass123')
        
        # Create a game for this test
        other_user = User.objects.create_user(username='other', password='pass')
        game = Game.objects.create(
            black_player=self.user,
            white_player=other_user,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        game.save()
        
        # Navigate to game
        game_url = f"{live_server_url}/games/{game.id}/"
        browser_driver.get(game_url)
        
        # Test SSE connection
        sse_watcher = SSEEventWatcher(browser_driver)
        assert sse_watcher.start_monitoring(['game_move'])
        assert sse_watcher.wait_for_connection(timeout=15)
    
    def test_board_interaction_cross_browser(self, browser_driver, live_server):
        """Test board interaction works across different browsers."""
        live_server_url = live_server.url
        
        # Log in user
        assert login_user(browser_driver, live_server_url, 'testuser', 'testpass123')
        
        # Create a game
        other_user = User.objects.create_user(username='other', password='pass')
        game = Game.objects.create(
            black_player=self.user,
            white_player=other_user,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        game.initialize_board()
        game.save()
        
        # Navigate to game and interact with board
        game_url = f"{live_server_url}/games/{game.id}/"
        browser_driver.get(game_url)
        
        board_helper = GameBoardHelper(browser_driver)
        assert board_helper.wait_for_board(timeout=10)
        
        # Make a move
        assert board_helper.click_intersection(7, 7)
        assert board_helper.wait_for_move_completion()
        
        # Verify move was made
        state = board_helper.get_intersection_state(7, 7)
        assert state in ['black', 'white']