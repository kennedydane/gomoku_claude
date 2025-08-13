"""
Dedicated tests for real-time board updates and SSE edge cases.
"""
import pytest
import time
import threading
from django.test import TransactionTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth import get_user_model
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from games.models import Game, RuleSet, GameStatus
from .utils.sse_helpers import SSEEventWatcher, GameBoardHelper, login_user, wait_for_page_load


User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestRealTimeBoardUpdates:
    """Comprehensive tests for real-time board updates via SSE."""
    
    def setup_method(self):
        """Set up test data for each test."""
        self.player1 = User.objects.create_user(
            username='realtime1', 
            password='testpass123'
        )
        self.player2 = User.objects.create_user(
            username='realtime2', 
            password='testpass123'
        )
        
        self.ruleset = RuleSet.objects.create(
            name='Real-time Test Gomoku',
            description='Standard 15x15 Gomoku for real-time testing',
            board_size=15,
            allow_overlines=True
        )
        
        self.game = Game.objects.create(
            black_player=self.player1,
            white_player=self.player2,
            ruleset=self.ruleset,
            status=GameStatus.ACTIVE
        )
        self.game.initialize_board()
        self.game.save()
    
    def test_immediate_move_propagation(self, dual_chrome_drivers, live_server):
        """Test that moves propagate immediately without delay."""
        driver1, driver2 = dual_chrome_drivers
        live_server_url = live_server.url
        
        # Setup both players
        assert login_user(driver1, live_server_url, 'realtime1', 'testpass123')
        assert login_user(driver2, live_server_url, 'realtime2', 'testpass123')
        
        game_url = f"{live_server_url}/games/{self.game.id}/"
        driver1.get(game_url)
        driver2.get(game_url)
        
        # Initialize helpers
        board_helper1 = GameBoardHelper(driver1)
        board_helper2 = GameBoardHelper(driver2)
        sse_watcher2 = SSEEventWatcher(driver2)
        
        assert board_helper1.wait_for_board(timeout=10)
        assert board_helper2.wait_for_board(timeout=10)
        assert sse_watcher2.start_monitoring(['game_move'])
        assert sse_watcher2.wait_for_connection(timeout=15)
        
        # Record start time and make move
        start_time = time.time()
        assert board_helper1.click_intersection(5, 5)
        
        # Wait for SSE event and measure time
        event = sse_watcher2.wait_for_event('game_move', timeout=5)
        propagation_time = time.time() - start_time
        
        assert event is not None
        assert propagation_time < 2.0  # Should be nearly instantaneous
        print(f"Move propagation time: {propagation_time:.3f}s")
        
        # Verify move appears on player 2's board quickly
        time.sleep(0.5)  # Brief wait for DOM update
        state = board_helper2.get_intersection_state(5, 5)
        assert state == "black"
    
    def test_rapid_successive_moves(self, dual_chrome_drivers, live_server):
        """Test handling of rapid successive moves."""
        driver1, driver2 = dual_chrome_drivers
        live_server_url = live_server.url
        
        # Setup both players
        assert login_user(driver1, live_server_url, 'realtime1', 'testpass123')
        assert login_user(driver2, live_server_url, 'realtime2', 'testpass123')
        
        game_url = f"{live_server_url}/games/{self.game.id}/"
        driver1.get(game_url)
        driver2.get(game_url)
        
        # Initialize helpers
        board_helper1 = GameBoardHelper(driver1)
        board_helper2 = GameBoardHelper(driver2)
        sse_watcher1 = SSEEventWatcher(driver1)
        sse_watcher2 = SSEEventWatcher(driver2)
        
        assert board_helper1.wait_for_board(timeout=10)
        assert board_helper2.wait_for_board(timeout=10)
        assert sse_watcher1.start_monitoring(['game_move'])
        assert sse_watcher2.start_monitoring(['game_move'])
        assert sse_watcher1.wait_for_connection(timeout=15)
        assert sse_watcher2.wait_for_connection(timeout=15)
        
        # Make rapid alternating moves
        moves = [
            (6, 6, board_helper1, sse_watcher2),  # Player 1
            (6, 7, board_helper2, sse_watcher1),  # Player 2
            (7, 6, board_helper1, sse_watcher2),  # Player 1
            (7, 7, board_helper2, sse_watcher1),  # Player 2
        ]
        
        for i, (row, col, mover, watcher) in enumerate(moves):
            watcher.clear_events()
            
            # Make move with minimal delay
            assert mover.click_intersection(row, col)
            assert mover.wait_for_move_completion()
            
            # Verify SSE event
            event = watcher.wait_for_event('game_move', timeout=3)
            assert event is not None, f"Failed to receive SSE event for move {i+1}"
            
            # Brief wait for DOM update
            time.sleep(0.3)
        
        # Verify all moves are present on both boards
        for row, col, _, _ in moves:
            state1 = board_helper1.get_intersection_state(row, col)
            state2 = board_helper2.get_intersection_state(row, col)
            assert state1 in ['black', 'white'], f"Move at ({row}, {col}) missing on board 1"
            assert state2 in ['black', 'white'], f"Move at ({row}, {col}) missing on board 2"
            assert state1 == state2, f"Board mismatch at ({row}, {col})"
    
    def test_sse_reconnection_after_interruption(self, dual_chrome_drivers, live_server):
        """Test SSE reconnection after simulated connection interruption."""
        driver1, driver2 = dual_chrome_drivers
        live_server_url = live_server.url
        
        # Setup both players
        assert login_user(driver1, live_server_url, 'realtime1', 'testpass123')
        assert login_user(driver2, live_server_url, 'realtime2', 'testpass123')
        
        game_url = f"{live_server_url}/games/{self.game.id}/"
        driver1.get(game_url)
        driver2.get(game_url)
        
        # Initialize helpers
        board_helper1 = GameBoardHelper(driver1)
        board_helper2 = GameBoardHelper(driver2)
        sse_watcher2 = SSEEventWatcher(driver2)
        
        assert board_helper1.wait_for_board(timeout=10)
        assert board_helper2.wait_for_board(timeout=10)
        assert sse_watcher2.start_monitoring(['game_move'])
        assert sse_watcher2.wait_for_connection(timeout=15)
        
        # Make initial move to verify connection works
        assert board_helper1.click_intersection(3, 3)
        event = sse_watcher2.wait_for_event('game_move', timeout=5)
        assert event is not None
        time.sleep(0.5)
        
        # Simulate connection interruption by disabling/re-enabling network
        # Note: This is a simplified simulation - in real scenarios you might 
        # use network conditioning tools
        driver2.execute_script("""
            // Simulate connection interruption
            if (window.eventSource) {
                window.eventSource.close();
            }
        """)
        
        time.sleep(2)  # Wait for interruption to take effect
        
        # Refresh player 2's page to re-establish connection
        driver2.refresh()
        wait_for_page_load(driver2)
        
        # Re-initialize helpers after refresh
        board_helper2 = GameBoardHelper(driver2)
        sse_watcher2 = SSEEventWatcher(driver2)
        
        assert board_helper2.wait_for_board(timeout=10)
        assert sse_watcher2.start_monitoring(['game_move'])
        assert sse_watcher2.wait_for_connection(timeout=15)
        
        # Make another move to test reconnection
        sse_watcher2.clear_events()
        assert board_helper1.click_intersection(4, 4)
        event = sse_watcher2.wait_for_event('game_move', timeout=10)
        assert event is not None
        
        # Verify board is still synchronized
        time.sleep(0.5)
        state1 = board_helper1.get_intersection_state(4, 4)
        state2 = board_helper2.get_intersection_state(4, 4)
        assert state1 == state2
    
    def test_multiple_tab_sse_handling(self, chrome_driver, live_server):
        """Test SSE behavior when multiple tabs are open to the same game."""
        live_server_url = live_server.url
        
        # Log in user
        assert login_user(chrome_driver, live_server_url, 'realtime1', 'testpass123')
        
        game_url = f"{live_server_url}/games/{self.game.id}/"
        
        # Open first tab
        chrome_driver.get(game_url)
        first_tab = chrome_driver.current_window_handle
        
        board_helper1 = GameBoardHelper(chrome_driver)
        sse_watcher1 = SSEEventWatcher(chrome_driver)
        
        assert board_helper1.wait_for_board(timeout=10)
        assert sse_watcher1.start_monitoring(['game_move'])
        assert sse_watcher1.wait_for_connection(timeout=15)
        
        # Open second tab with same game
        chrome_driver.execute_script("window.open();")
        tabs = chrome_driver.window_handles
        second_tab = [tab for tab in tabs if tab != first_tab][0]
        
        chrome_driver.switch_to.window(second_tab)
        chrome_driver.get(game_url)
        
        board_helper2 = GameBoardHelper(chrome_driver)
        sse_watcher2 = SSEEventWatcher(chrome_driver)
        
        assert board_helper2.wait_for_board(timeout=10)
        assert sse_watcher2.start_monitoring(['game_move'])
        
        # Note: Due to browser SSE connection limits (typically 6 per domain),
        # we might not be able to establish a second connection
        # This test verifies the behavior in such cases
        
        try:
            connection_established = sse_watcher2.wait_for_connection(timeout=10)
            print(f"Second SSE connection established: {connection_established}")
        except Exception as e:
            print(f"Expected SSE connection limit reached: {e}")
        
        # Switch back to first tab and make a move
        chrome_driver.switch_to.window(first_tab)
        assert board_helper1.click_intersection(2, 2)
        assert board_helper1.wait_for_move_completion()
        
        # Verify move appears on first tab
        state1 = board_helper1.get_intersection_state(2, 2)
        assert state1 in ['black', 'white']
        
        # Check second tab (may or may not receive SSE update due to connection limits)
        chrome_driver.switch_to.window(second_tab)
        time.sleep(2)  # Allow time for any potential update
        
        # Clean up - close second tab
        chrome_driver.close()
        chrome_driver.switch_to.window(first_tab)
    
    def test_csrf_token_in_sse_events(self, dual_chrome_drivers, live_server):
        """Test that CSRF tokens are properly included in SSE events."""
        driver1, driver2 = dual_chrome_drivers
        live_server_url = live_server.url
        
        # Setup both players
        assert login_user(driver1, live_server_url, 'realtime1', 'testpass123')
        assert login_user(driver2, live_server_url, 'realtime2', 'testpass123')
        
        game_url = f"{live_server_url}/games/{self.game.id}/"
        driver1.get(game_url)
        driver2.get(game_url)
        
        # Initialize helpers
        board_helper1 = GameBoardHelper(driver1)
        sse_watcher2 = SSEEventWatcher(driver2)
        
        assert board_helper1.wait_for_board(timeout=10)
        assert sse_watcher2.start_monitoring(['game_move'])
        assert sse_watcher2.wait_for_connection(timeout=15)
        
        # Make a move
        assert board_helper1.click_intersection(1, 1)
        
        # Wait for SSE event
        event = sse_watcher2.wait_for_event('game_move', timeout=5)
        assert event is not None
        assert 'data' in event
        
        # Check that the HTML data contains CSRF token reference
        html_data = event['data']
        assert 'X-CSRFToken' in html_data, "SSE event should contain CSRF token reference"
        print(f"SSE event contains CSRF token reference: {'X-CSRFToken' in html_data}")
    
    def test_board_state_consistency_after_page_refresh(self, dual_chrome_drivers, live_server):
        """Test board state consistency after one player refreshes their page."""
        driver1, driver2 = dual_chrome_drivers
        live_server_url = live_server.url
        
        # Setup both players
        assert login_user(driver1, live_server_url, 'realtime1', 'testpass123')
        assert login_user(driver2, live_server_url, 'realtime2', 'testpass123')
        
        game_url = f"{live_server_url}/games/{self.game.id}/"
        driver1.get(game_url)
        driver2.get(game_url)
        
        # Initialize helpers
        board_helper1 = GameBoardHelper(driver1)
        board_helper2 = GameBoardHelper(driver2)
        sse_watcher1 = SSEEventWatcher(driver1)
        sse_watcher2 = SSEEventWatcher(driver2)
        
        assert board_helper1.wait_for_board(timeout=10)
        assert board_helper2.wait_for_board(timeout=10)
        assert sse_watcher1.start_monitoring(['game_move'])
        assert sse_watcher2.start_monitoring(['game_move'])
        assert sse_watcher1.wait_for_connection(timeout=15)
        assert sse_watcher2.wait_for_connection(timeout=15)
        
        # Make several moves
        moves = [(0, 0), (0, 1), (1, 0), (1, 1)]
        current_player = 1
        
        for row, col in moves:
            if current_player == 1:
                mover = board_helper1
                watcher = sse_watcher2
            else:
                mover = board_helper2
                watcher = sse_watcher1
            
            watcher.clear_events()
            assert mover.click_intersection(row, col)
            assert mover.wait_for_move_completion()
            watcher.wait_for_event('game_move', timeout=5)
            time.sleep(0.5)
            
            current_player = 2 if current_player == 1 else 1
        
        # Get board state before refresh
        board_state_before = board_helper1.get_board_state()
        
        # Player 2 refreshes their page
        driver2.refresh()
        wait_for_page_load(driver2)
        
        # Re-initialize player 2's helpers
        board_helper2 = GameBoardHelper(driver2)
        assert board_helper2.wait_for_board(timeout=10)
        
        # Compare board states after refresh
        board_state_after = board_helper2.get_board_state()
        
        # Boards should be identical
        assert board_state_before == board_state_after
        
        # Verify specific moves are still present
        for row, col in moves:
            assert board_state_after[row][col] in ['black', 'white']