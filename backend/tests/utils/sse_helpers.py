"""
Utilities for testing Server-Sent Events (SSE) with Selenium.
"""
import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException, WebDriverException


class SSEEventWatcher:
    """Helper class to monitor and verify SSE events in browser."""
    
    def __init__(self, driver: WebDriver, timeout: int = 10):
        self.driver = driver
        self.timeout = timeout
        self.events = []
        
    def start_monitoring(self, event_types: list = None):
        """Start monitoring SSE events by injecting JavaScript."""
        if event_types is None:
            event_types = ['game_move']
            
        # Inject JavaScript to capture SSE events
        js_code = f"""
        window.sseEvents = [];
        window.sseConnected = false;
        window.sseLastError = null;
        
        // Find existing SSE connection or wait for it
        function findSSEConnection() {{
            const sseElement = document.querySelector('[hx-ext*="sse"]');
            if (sseElement) {{
                console.log('Found SSE element:', sseElement);
                
                // Hook into HTMX SSE events
                document.body.addEventListener('htmx:sseConnect', function(event) {{
                    console.log('SSE Connected:', event.detail);
                    window.sseConnected = true;
                }});
                
                document.body.addEventListener('htmx:sseError', function(event) {{
                    console.error('SSE Error:', event.detail);
                    window.sseLastError = event.detail;
                }});
                
                document.body.addEventListener('htmx:sseClose', function(event) {{
                    console.log('SSE Closed:', event.detail);
                    window.sseConnected = false;
                }});
                
                // Monitor specific SSE messages
                {chr(10).join([f'''
                document.body.addEventListener('htmx:sseMessage:{event_type}', function(event) {{
                    console.log('SSE Event {event_type}:', event.detail);
                    window.sseEvents.push({{
                        type: '{event_type}',
                        data: event.detail.data,
                        timestamp: new Date().toISOString()
                    }});
                }});''' for event_type in event_types])}
                
                return true;
            }}
            return false;
        }}
        
        // Try to find SSE connection immediately or wait for it
        if (!findSSEConnection()) {{
            // Wait for DOM changes
            const observer = new MutationObserver(function(mutations) {{
                if (findSSEConnection()) {{
                    observer.disconnect();
                }}
            }});
            observer.observe(document.body, {{ childList: true, subtree: true }});
        }}
        
        return true;
        """
        
        try:
            result = self.driver.execute_script(js_code)
            print(f"SSE monitoring started: {result}")
            return True
        except WebDriverException as e:
            print(f"Failed to start SSE monitoring: {e}")
            return False
    
    def wait_for_connection(self, timeout: int = None) -> bool:
        """Wait for SSE connection to be established."""
        timeout = timeout or self.timeout
        
        def check_connection():
            try:
                return self.driver.execute_script("return window.sseConnected === true;")
            except WebDriverException:
                return False
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if check_connection():
                print("SSE connection established")
                return True
            time.sleep(0.1)
        
        # Check for errors
        try:
            error = self.driver.execute_script("return window.sseLastError;")
            if error:
                print(f"SSE connection failed with error: {error}")
        except WebDriverException:
            pass
            
        print(f"SSE connection timeout after {timeout}s")
        return False
    
    def wait_for_event(self, event_type: str = 'game_move', timeout: int = None) -> dict:
        """Wait for a specific SSE event and return its data."""
        timeout = timeout or self.timeout
        
        def get_events():
            try:
                events = self.driver.execute_script("return window.sseEvents || [];")
                return [e for e in events if e.get('type') == event_type]
            except WebDriverException:
                return []
        
        initial_count = len(get_events())
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            events = get_events()
            if len(events) > initial_count:
                new_event = events[-1]  # Get the latest event
                print(f"Received SSE event: {new_event}")
                return new_event
            time.sleep(0.1)
        
        raise TimeoutException(f"No {event_type} event received within {timeout}s")
    
    def get_all_events(self) -> list:
        """Get all captured SSE events."""
        try:
            return self.driver.execute_script("return window.sseEvents || [];")
        except WebDriverException:
            return []
    
    def clear_events(self):
        """Clear the events buffer."""
        try:
            self.driver.execute_script("window.sseEvents = [];")
        except WebDriverException:
            pass


class GameBoardHelper:
    """Helper class for interacting with the Gomoku game board."""
    
    def __init__(self, driver: WebDriver):
        self.driver = driver
        
    def wait_for_board(self, timeout: int = 10) -> bool:
        """Wait for the game board to be loaded."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, "game-board-grid"))
            )
            return True
        except TimeoutException:
            return False
    
    def get_board_size(self) -> int:
        """Get the board size from the grid element."""
        try:
            board_element = self.driver.find_element(By.CLASS_NAME, "game-board-grid")
            return int(board_element.get_attribute("data-board-size"))
        except:
            return 15  # Default size
    
    def click_intersection(self, row: int, col: int, timeout: int = 10) -> bool:
        """Click on a board intersection."""
        try:
            # Find the intersection element by data attributes
            intersection = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    f'.board-intersection[data-row="{row}"][data-col="{col}"]'
                ))
            )
            intersection.click()
            return True
        except TimeoutException:
            print(f"Failed to click intersection ({row}, {col}) - timeout")
            return False
        except Exception as e:
            print(f"Failed to click intersection ({row}, {col}) - {e}")
            return False
    
    def get_intersection_state(self, row: int, col: int) -> str:
        """Get the state of a board intersection (empty, black, white)."""
        try:
            intersection = self.driver.find_element(
                By.CSS_SELECTOR,
                f'.board-intersection[data-row="{row}"][data-col="{col}"]'
            )
            
            # Check for stone elements inside
            black_stones = intersection.find_elements(By.CLASS_NAME, "stone-black")
            white_stones = intersection.find_elements(By.CLASS_NAME, "stone-white")
            
            if black_stones:
                return "black"
            elif white_stones:
                return "white"
            else:
                return "empty"
        except:
            return "unknown"
    
    def get_board_state(self) -> list:
        """Get the complete board state as a 2D array."""
        board_size = self.get_board_size()
        board = []
        
        for row in range(board_size):
            board_row = []
            for col in range(board_size):
                state = self.get_intersection_state(row, col)
                board_row.append(state)
            board.append(board_row)
            
        return board
    
    def wait_for_move_completion(self, timeout: int = 10) -> bool:
        """Wait for a move to complete (loading indicator disappears)."""
        try:
            # Wait for loading indicator to appear and then disappear
            WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.ID, "board-loading"))
            )
        except TimeoutException:
            pass  # Loading might be too fast to catch
        
        try:
            # Wait for loading indicator to disappear
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located((By.ID, "board-loading"))
            )
            return True
        except TimeoutException:
            return False


def wait_for_page_load(driver: WebDriver, timeout: int = 10) -> bool:
    """Wait for page to be fully loaded."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        return True
    except TimeoutException:
        return False


def login_user(driver: WebDriver, live_server_url: str, username: str, password: str) -> bool:
    """Log in a user via the web interface."""
    try:
        # Navigate to login page
        driver.get(f"{live_server_url}/login/")
        wait_for_page_load(driver)
        
        # Fill in login form
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        password_field = driver.find_element(By.NAME, "password")
        submit_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        
        username_field.send_keys(username)
        password_field.send_keys(password)
        submit_button.click()
        
        # Wait for redirect to dashboard
        WebDriverWait(driver, 10).until(
            EC.url_contains("/dashboard/")
        )
        return True
    except Exception as e:
        print(f"Login failed for {username}: {e}")
        return False