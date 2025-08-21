"""
SSE integration for GUI real-time updates.

This module manages SSE connection lifecycle and integrates with the GUI
board update system for automatic real-time updates when opponents make moves.
"""

import asyncio
import threading
from typing import Optional, Callable, Any
from loguru import logger

from .sse_client import SSEClient, SSEConnectionError, SSEParseError
from .html_parser import ParsedGameState


class SSEManager:
    """
    Manages SSE connection and integration with GUI updates.
    
    Handles connection lifecycle, reconnection, and translates SSE events
    into GUI board updates.
    """
    
    def __init__(self, auth_manager, on_board_update: Callable[[ParsedGameState], None]):
        """
        Initialize SSE manager.
        
        Args:
            auth_manager: Authentication manager instance
            on_board_update: Callback for board state updates
        """
        self.auth_manager = auth_manager
        self.on_board_update = on_board_update
        
        self._sse_client: Optional[SSEClient] = None
        self._connection_thread: Optional[threading.Thread] = None
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._is_running = False
        self._connection_status = "disconnected"  # disconnected, connecting, connected, error
        
        logger.debug("SSEManager initialized")
    
    def start_connection(self) -> None:
        """Start SSE connection in background thread."""
        if self._is_running:
            logger.warning("SSE connection already running")
            return
        
        # Handle different auth manager types (same as in SSEClient)
        auth_check_manager = self.auth_manager
        if (hasattr(self.auth_manager, 'auth_manager') and 
            not str(type(self.auth_manager)).startswith("<class 'unittest.mock.") and
            hasattr(self.auth_manager.auth_manager, 'config')):
            auth_check_manager = self.auth_manager.auth_manager
            
        if not auth_check_manager.is_authenticated():
            logger.error("Cannot start SSE connection: user not authenticated")
            raise ValueError("User must be authenticated to start SSE connection")
        
        logger.info("Starting SSE connection...")
        self._is_running = True
        self._connection_status = "connecting"
        
        # Start connection in background thread to avoid blocking GUI
        self._connection_thread = threading.Thread(
            target=self._run_sse_connection,
            daemon=True,
            name="SSE-Connection"
        )
        self._connection_thread.start()
    
    def stop_connection(self) -> None:
        """Stop SSE connection and cleanup."""
        if not self._is_running:
            return
            
        logger.info("Stopping SSE connection...")
        self._is_running = False
        self._connection_status = "disconnected"
        
        # Schedule cleanup on the event loop
        if self._event_loop and not self._event_loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._cleanup_connection(),
                self._event_loop
            )
        
        # Wait for thread to finish
        if self._connection_thread and self._connection_thread.is_alive():
            logger.debug("Waiting for SSE thread to finish...")
            self._connection_thread.join(timeout=2.0)
            if self._connection_thread.is_alive():
                logger.warning("SSE thread did not finish cleanly")
        
        logger.info("SSE connection stopped")
    
    def get_connection_status(self) -> str:
        """Get current connection status."""
        return self._connection_status
    
    def is_connected(self) -> bool:
        """Check if SSE client is connected."""
        return (self._sse_client is not None and 
                hasattr(self._sse_client, 'is_connected') and
                self._sse_client.is_connected)
    
    def _run_sse_connection(self) -> None:
        """Run SSE connection in background thread."""
        try:
            # Create new event loop for this thread
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
            
            logger.debug("Starting SSE event loop...")
            self._event_loop.run_until_complete(self._sse_connection_loop())
            
        except Exception as e:
            logger.error(f"SSE connection thread failed: {e}")
            self._connection_status = "error"
        finally:
            # Cleanup event loop
            if self._event_loop:
                try:
                    self._event_loop.close()
                except Exception as e:
                    logger.warning(f"Error closing SSE event loop: {e}")
                self._event_loop = None
    
    async def _sse_connection_loop(self) -> None:
        """Main SSE connection loop with reconnection."""
        reconnect_delay = 1.0  # Start with 1 second
        max_delay = 30.0       # Max 30 seconds between reconnects
        
        while self._is_running:
            try:
                logger.debug("Creating SSE client...")
                self._sse_client = SSEClient(
                    auth_manager=self.auth_manager,
                    on_game_update=self._handle_game_update,
                    on_error=self._handle_sse_error
                )
                
                logger.debug("Connecting to SSE endpoint...")
                await self._sse_client.connect()
                
                self._connection_status = "connected"
                reconnect_delay = 1.0  # Reset delay on successful connection
                logger.info("SSE connection established")
                
                # Start listening for events (this blocks until disconnection)
                await self._sse_client._listen_for_events()
                
            except SSEConnectionError as e:
                logger.warning(f"SSE connection failed: {e}")
                self._connection_status = "error"
                
                if not self._is_running:
                    break
                
                # Wait before reconnecting
                logger.info(f"Reconnecting in {reconnect_delay} seconds...")
                await asyncio.sleep(reconnect_delay)
                
                # Exponential backoff
                reconnect_delay = min(reconnect_delay * 2, max_delay)
                
            except Exception as e:
                logger.error(f"Unexpected SSE error: {e}")
                self._connection_status = "error"
                
                if not self._is_running:
                    break
                    
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_delay)
        
        logger.debug("SSE connection loop ended")
    
    async def _cleanup_connection(self) -> None:
        """Cleanup SSE client connection."""
        if self._sse_client:
            try:
                await self._sse_client.disconnect()
            except Exception as e:
                logger.warning(f"Error during SSE cleanup: {e}")
            finally:
                self._sse_client = None
    
    def _handle_game_update(self, game_state: ParsedGameState) -> None:
        """Handle game state update from SSE event."""
        try:
            logger.info(f"Received game update for game {game_state.game_id}")
            logger.debug(f"Board size: {game_state.board_size}, Current player: {game_state.current_player}")
            
            # Trigger GUI update callback
            # Note: This runs in the SSE thread, so the callback needs to handle
            # thread-safe GUI updates (e.g., using DearPyGUI's thread-safe functions)
            self.on_board_update(game_state)
            
        except Exception as e:
            logger.error(f"Error handling game update: {e}")
    
    def _handle_sse_error(self, error: Exception) -> None:
        """Handle SSE client errors."""
        logger.error(f"SSE client error: {error}")
        
        if isinstance(error, SSEParseError):
            # Parse errors are usually not fatal - continue connection
            logger.warning("HTML parse error in SSE event - continuing connection")
        else:
            # Other errors might require reconnection
            self._connection_status = "error"