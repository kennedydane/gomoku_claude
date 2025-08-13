"""
Cross-browser testing for SSE functionality and real-time features.
"""
import pytest
import time
from django.contrib.auth import get_user_model
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from games.models import Game, RuleSet, GameStatus
from .utils.sse_helpers import SSEEventWatcher, GameBoardHelper, login_user, wait_for_page_load


User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestCrossBrowserSSECompatibility:
    """Test SSE functionality across Chrome and Firefox browsers."""
    
    def setup_method(self):
        """Set up test data for each test."""
        self.player1 = User.objects.create_user(
            username='crossbrowser1', 
            password='testpass123'
        )
        self.player2 = User.objects.create_user(
            username='crossbrowser2', 
            password='testpass123'
        )
        
        self.ruleset = RuleSet.objects.create(
            name='Cross-Browser Test Gomoku',
            description='Standard 15x15 Gomoku for cross-browser testing',
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
    
    def test_chrome_firefox_sse_interoperability(self, chrome_driver, firefox_driver, live_server):
        """Test SSE communication between Chrome and Firefox browsers."""
        live_server_url = live_server.url
        
        # Player 1 uses Chrome, Player 2 uses Firefox
        assert login_user(chrome_driver, live_server_url, 'crossbrowser1', 'testpass123')
        assert login_user(firefox_driver, live_server_url, 'crossbrowser2', 'testpass123')
        
        game_url = f"{live_server_url}/games/{self.game.id}/"
        chrome_driver.get(game_url)
        firefox_driver.get(game_url)
        
        # Initialize helpers for both browsers
        chrome_board = GameBoardHelper(chrome_driver)
        firefox_board = GameBoardHelper(firefox_driver)
        chrome_sse = SSEEventWatcher(chrome_driver)
        firefox_sse = SSEEventWatcher(firefox_driver)
        
        # Wait for boards to load
        assert chrome_board.wait_for_board(timeout=10)
        assert firefox_board.wait_for_board(timeout=10)
        
        # Set up SSE monitoring
        assert chrome_sse.start_monitoring(['game_move'])
        assert firefox_sse.start_monitoring(['game_move'])
        assert chrome_sse.wait_for_connection(timeout=15)
        assert firefox_sse.wait_for_connection(timeout=15)
        
        # Chrome player makes a move
        assert chrome_board.click_intersection(8, 8)
        assert chrome_board.wait_for_move_completion()
        
        # Firefox player should receive SSE event
        event = firefox_sse.wait_for_event('game_move', timeout=10)
        assert event is not None
        time.sleep(1)  # Allow DOM update
        
        # Verify move appears on Firefox
        chrome_state = chrome_board.get_intersection_state(8, 8)
        firefox_state = firefox_board.get_intersection_state(8, 8)
        assert chrome_state == firefox_state
        assert firefox_state in ['black', 'white']
        
        # Now Firefox player makes a move
        firefox_sse.clear_events()
        chrome_sse.clear_events()
        
        assert firefox_board.click_intersection(9, 9)
        assert firefox_board.wait_for_move_completion()
        
        # Chrome player should receive SSE event
        event = chrome_sse.wait_for_event('game_move', timeout=10)
        assert event is not None
        time.sleep(1)  # Allow DOM update
        
        # Verify move appears on Chrome
        chrome_state = chrome_board.get_intersection_state(9, 9)
        firefox_state = firefox_board.get_intersection_state(9, 9)
        assert chrome_state == firefox_state
        assert chrome_state in ['black', 'white']
    
    @pytest.mark.parametrize("browser_type", ["chrome", "firefox"])
    def test_sse_event_format_consistency(self, browser_type, chrome_driver, firefox_driver, live_server):
        """Test that SSE event format is consistent across browsers."""
        # Select the appropriate driver based on parameter
        driver = chrome_driver if browser_type == "chrome" else firefox_driver
        other_driver = firefox_driver if browser_type == "chrome" else chrome_driver
        
        live_server_url = live_server.url
        
        # Log in both users on different browsers
        assert login_user(driver, live_server_url, 'crossbrowser1', 'testpass123')
        assert login_user(other_driver, live_server_url, 'crossbrowser2', 'testpass123')
        
        game_url = f"{live_server_url}/games/{self.game.id}/"
        driver.get(game_url)
        other_driver.get(game_url)
        
        # Set up helpers
        board_helper = GameBoardHelper(driver)
        other_board_helper = GameBoardHelper(other_driver)
        sse_watcher = SSEEventWatcher(other_driver)  # Other browser watches for events
        
        assert board_helper.wait_for_board(timeout=10)
        assert other_board_helper.wait_for_board(timeout=10)
        assert sse_watcher.start_monitoring(['game_move'])
        assert sse_watcher.wait_for_connection(timeout=15)
        
        # Make a move and capture the SSE event
        assert board_helper.click_intersection(5, 5)
        assert board_helper.wait_for_move_completion()
        
        event = sse_watcher.wait_for_event('game_move', timeout=10)
        assert event is not None
        
        # Verify event structure
        assert 'type' in event
        assert 'data' in event
        assert 'timestamp' in event
        assert event['type'] == 'game_move'
        
        # Verify data contains HTML
        html_data = event['data']
        assert isinstance(html_data, str)
        assert len(html_data) > 100  # Should contain substantial HTML
        assert 'game-board-container' in html_data
        assert 'board-intersection' in html_data
        
        print(f"SSE event format test passed for {browser_type}")
        print(f"Event data length: {len(html_data)} characters")
    
    def test_sse_reconnection_behavior_cross_browser(self, chrome_driver, firefox_driver, live_server):
        """Test SSE reconnection behavior across different browsers."""
        live_server_url = live_server.url
        
        # Setup both browsers
        assert login_user(chrome_driver, live_server_url, 'crossbrowser1', 'testpass123')
        assert login_user(firefox_driver, live_server_url, 'crossbrowser2', 'testpass123')
        
        game_url = f"{live_server_url}/games/{self.game.id}/"
        chrome_driver.get(game_url)
        firefox_driver.get(game_url)
        
        # Initialize helpers
        chrome_board = GameBoardHelper(chrome_driver)
        firefox_board = GameBoardHelper(firefox_driver)
        chrome_sse = SSEEventWatcher(chrome_driver)
        firefox_sse = SSEEventWatcher(firefox_driver)
        
        assert chrome_board.wait_for_board(timeout=10)
        assert firefox_board.wait_for_board(timeout=10)
        assert chrome_sse.start_monitoring(['game_move'])
        assert firefox_sse.start_monitoring(['game_move'])
        assert chrome_sse.wait_for_connection(timeout=15)
        assert firefox_sse.wait_for_connection(timeout=15)
        
        # Test initial communication
        assert chrome_board.click_intersection(3, 3)
        event = firefox_sse.wait_for_event('game_move', timeout=5)
        assert event is not None
        
        # Simulate reconnection by refreshing Firefox
        firefox_driver.refresh()
        wait_for_page_load(firefox_driver)
        
        # Re-initialize Firefox helpers
        firefox_board = GameBoardHelper(firefox_driver)
        firefox_sse = SSEEventWatcher(firefox_driver)
        
        assert firefox_board.wait_for_board(timeout=10)
        assert firefox_sse.start_monitoring(['game_move'])
        assert firefox_sse.wait_for_connection(timeout=15)
        
        # Test communication after reconnection
        firefox_sse.clear_events()
        assert chrome_board.click_intersection(4, 4)
        event = firefox_sse.wait_for_event('game_move', timeout=10)
        assert event is not None
        
        print("Cross-browser SSE reconnection test passed")
    
    def test_browser_specific_sse_limits(self, chrome_driver, firefox_driver, live_server):
        """Test browser-specific SSE connection limits."""
        live_server_url = live_server.url
        
        # Test with Chrome
        self._test_sse_connection_limit(chrome_driver, live_server_url, "Chrome")
        
        # Test with Firefox  
        self._test_sse_connection_limit(firefox_driver, live_server_url, "Firefox")
    
    def _test_sse_connection_limit(self, driver, live_server_url, browser_name):
        """Helper method to test SSE connection limits for a specific browser."""
        assert login_user(driver, live_server_url, 'crossbrowser1', 'testpass123')
        
        game_url = f"{live_server_url}/games/{self.game.id}/"
        driver.get(game_url)
        
        # Get initial tab handle
        initial_tab = driver.current_window_handle
        tabs = [initial_tab]
        
        # Set up SSE on initial tab
        board_helper = GameBoardHelper(driver)
        sse_watcher = SSEEventWatcher(driver)
        
        assert board_helper.wait_for_board(timeout=10)
        assert sse_watcher.start_monitoring(['game_move'])
        initial_connection = sse_watcher.wait_for_connection(timeout=15)
        assert initial_connection
        
        print(f"{browser_name}: Initial SSE connection established")
        
        # Try to open additional tabs and establish SSE connections
        connections_established = 1
        max_tabs_to_test = 8  # Test up to 8 tabs (typical browser limit is 6)
        
        for i in range(2, max_tabs_to_test + 1):
            try:
                # Open new tab
                driver.execute_script("window.open();")
                new_tabs = driver.window_handles
                new_tab = [tab for tab in new_tabs if tab not in tabs][0]
                tabs.append(new_tab)
                
                # Switch to new tab and try to establish SSE
                driver.switch_to.window(new_tab)
                driver.get(game_url)
                
                tab_board_helper = GameBoardHelper(driver)
                tab_sse_watcher = SSEEventWatcher(driver)
                
                if tab_board_helper.wait_for_board(timeout=5):
                    if tab_sse_watcher.start_monitoring(['game_move']):
                        if tab_sse_watcher.wait_for_connection(timeout=5):
                            connections_established += 1
                            print(f"{browser_name}: Tab {i} SSE connection established")
                        else:
                            print(f"{browser_name}: Tab {i} SSE connection failed (likely hit limit)")
                            break
                    else:
                        print(f"{browser_name}: Tab {i} SSE monitoring failed")
                        break
                else:
                    print(f"{browser_name}: Tab {i} board loading failed")
                    break
                    
            except Exception as e:
                print(f"{browser_name}: Tab {i} failed with error: {e}")
                break
        
        print(f"{browser_name}: Total SSE connections established: {connections_established}")
        
        # Clean up - close all additional tabs
        for tab in tabs[1:]:  # Keep the first tab
            try:
                driver.switch_to.window(tab)
                driver.close()
            except:
                pass
        
        # Switch back to initial tab
        driver.switch_to.window(initial_tab)
        
        return connections_established
    
    @pytest.mark.parametrize("browser_pair", [("chrome", "firefox"), ("firefox", "chrome")])
    def test_bidirectional_sse_communication(self, browser_pair, chrome_driver, firefox_driver, live_server):
        """Test bidirectional SSE communication between different browsers."""
        browser1_type, browser2_type = browser_pair
        driver1 = chrome_driver if browser1_type == "chrome" else firefox_driver
        driver2 = firefox_driver if browser2_type == "firefox" else chrome_driver
        
        live_server_url = live_server.url
        
        # Setup both browsers
        assert login_user(driver1, live_server_url, 'crossbrowser1', 'testpass123')
        assert login_user(driver2, live_server_url, 'crossbrowser2', 'testpass123')
        
        game_url = f"{live_server_url}/games/{self.game.id}/"
        driver1.get(game_url)
        driver2.get(game_url)
        
        # Initialize helpers
        board1 = GameBoardHelper(driver1)
        board2 = GameBoardHelper(driver2)
        sse1 = SSEEventWatcher(driver1)
        sse2 = SSEEventWatcher(driver2)
        
        assert board1.wait_for_board(timeout=10)
        assert board2.wait_for_board(timeout=10)
        assert sse1.start_monitoring(['game_move'])
        assert sse2.start_monitoring(['game_move'])
        assert sse1.wait_for_connection(timeout=15)
        assert sse2.wait_for_connection(timeout=15)
        
        # Test communication in both directions
        moves = [
            (6, 6, board1, sse2, f"{browser1_type} → {browser2_type}"),
            (6, 7, board2, sse1, f"{browser2_type} → {browser1_type}"),
            (7, 6, board1, sse2, f"{browser1_type} → {browser2_type}"),
            (7, 7, board2, sse1, f"{browser2_type} → {browser1_type}"),
        ]
        
        for row, col, mover_board, watcher_sse, description in moves:
            watcher_sse.clear_events()
            
            # Make move
            assert mover_board.click_intersection(row, col)
            assert mover_board.wait_for_move_completion()
            
            # Wait for SSE event
            event = watcher_sse.wait_for_event('game_move', timeout=10)
            assert event is not None, f"Failed to receive SSE event for {description}"
            
            time.sleep(0.5)  # Allow DOM update
            
            # Verify move appears on both boards
            state1 = board1.get_intersection_state(row, col)
            state2 = board2.get_intersection_state(row, col)
            assert state1 == state2, f"Board state mismatch for {description}"
            assert state1 in ['black', 'white'], f"Invalid board state for {description}"
            
            print(f"✓ {description}: Move at ({row}, {col}) propagated successfully")
        
        print(f"Bidirectional SSE communication test passed for {browser1_type} ↔ {browser2_type}")