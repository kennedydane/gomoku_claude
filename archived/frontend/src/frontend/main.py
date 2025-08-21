"""
Main entry point for the Gomoku GUI application.

This module initializes and runs the Dear PyGUI-based Gomoku game client.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import dearpygui.dearpygui as dpg
from loguru import logger

from .ui.main_window import MainWindow
from .client.api_client import APIClient
from .game.game_state import GameState


class GomokuApp:
    """Main application class for the Gomoku GUI."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """Initialize the Gomoku application.
        
        Args:
            api_url: Base URL for the Gomoku API server
        """
        self.api_url = api_url
        self.api_client: Optional[APIClient] = None
        self.game_state: Optional[GameState] = None
        self.main_window: Optional[MainWindow] = None
        
        # Configure logging
        logger.remove()  # Remove default handler
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        
    def setup(self) -> None:
        """Set up the application components."""
        logger.info(f"Initializing Gomoku GUI application (API: {self.api_url})")
        
        # Initialize Dear PyGUI
        dpg.create_context()
        dpg.create_viewport(title="Gomoku Game", width=800, height=700)
        
        # Initialize application components
        self.api_client = APIClient(base_url=self.api_url)
        self.game_state = GameState()
        self.main_window = MainWindow(
            api_client=self.api_client,
            game_state=self.game_state
        )
        
        # Set up the main window
        self.main_window.create()
        
        logger.info("Application setup complete")
    
    def run(self) -> None:
        """Run the main application loop."""
        if not self.main_window:
            raise RuntimeError("Application not properly initialized. Call setup() first.")
            
        logger.info("Starting Gomoku GUI application")
        
        try:
            # Set up viewport and show
            dpg.setup_dearpygui()
            dpg.show_viewport()
            
            # Main render loop
            while dpg.is_dearpygui_running():
                # Handle any async operations
                self.main_window.update()
                dpg.render_dearpygui_frame()
                
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.error(f"Application error: {e}")
            raise
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Clean up application resources."""
        logger.info("Cleaning up application resources")
        
        if self.api_client:
            # Close any open HTTP connections
            try:
                asyncio.run(self.api_client.close())
            except Exception as e:
                logger.warning(f"Error closing API client: {e}")
        
        # Clean up Dear PyGUI
        dpg.destroy_context()
        logger.info("Application cleanup complete")


def main() -> None:
    """Main entry point for the application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gomoku GUI Game Client")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL for the Gomoku API server (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    # Create and run the application
    app = GomokuApp(api_url=args.api_url)
    try:
        app.setup()
        app.run()
    except Exception as e:
        logger.error(f"Failed to run application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()