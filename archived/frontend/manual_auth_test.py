#!/usr/bin/env python3
"""
Manual testing demo for GUI authentication components.

This script provides a simple GUI for manually testing the authentication
dialogs and functionality. Run this to test the authentication system.
"""

import asyncio
import sys
from pathlib import Path

import dearpygui.dearpygui as dpg
from loguru import logger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from frontend.ui.auth_dialogs import AuthenticationManager
from frontend.auth.auth_manager import AuthManager


class AuthTestApp:
    """Simple test application for authentication GUI components."""
    
    def __init__(self):
        """Initialize the test application."""
        # Initialize authentication manager with test config
        config_file = Path(__file__).parent / "test_auth_config.json"
        env_file = Path(__file__).parent / ".env"
        
        self.auth_gui = AuthenticationManager(
            config_file=str(config_file),
            env_file=str(env_file) if env_file.exists() else None
        )
        
        self._create_main_window()
        
        logger.info("AuthTestApp initialized")
    
    def _create_main_window(self):
        """Create the main test window."""
        with dpg.window(label="Authentication Test App", tag="main_window", width=600, height=400):
            dpg.add_text("Gomoku Authentication Test", color=(100, 150, 255))
            dpg.add_separator()
            
            # Status section
            dpg.add_text("Authentication Status:")
            dpg.add_text("Not logged in", tag="status_text", color=(255, 100, 100))
            dpg.add_separator()
            
            # Authentication controls
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Login",
                    callback=self._on_login_clicked,
                    width=100,
                    tag="login_button"
                )
                dpg.add_button(
                    label="Register",
                    callback=self._on_register_clicked,
                    width=100,
                    tag="register_button"
                )
                dpg.add_button(
                    label="Logout",
                    callback=self._on_logout_clicked,
                    width=100,
                    tag="logout_button",
                    enabled=False
                )
            
            dpg.add_separator()
            
            # Profile management
            dpg.add_text("Profile Management:")
            with dpg.group(horizontal=True):
                dpg.add_combo(
                    label="Profiles",
                    items=[],
                    tag="profile_combo",
                    width=200,
                    callback=self._on_profile_selected
                )
                dpg.add_button(
                    label="Refresh Profiles",
                    callback=self._refresh_profiles,
                    width=120
                )
            
            dpg.add_separator()
            
            # Current user info
            dpg.add_text("Current User Information:")
            dpg.add_text("Username: N/A", tag="user_username")
            dpg.add_text("Email: N/A", tag="user_email")
            dpg.add_text("Display Name: N/A", tag="user_display_name")
            
            dpg.add_separator()
            
            # Test API operations (these would normally require backend)
            dpg.add_text("Test Operations (requires backend):")
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Test API Call",
                    callback=self._test_api_call,
                    width=120,
                    enabled=False,
                    tag="test_api_button"
                )
                dpg.add_button(
                    label="Test Token Refresh",
                    callback=self._test_token_refresh,
                    width=120,
                    enabled=False,
                    tag="test_refresh_button"
                )
            
            dpg.add_separator()
            
            # Instructions
            dpg.add_text("Instructions:", color=(100, 255, 100))
            dpg.add_text("1. Click 'Register' to create a new account")
            dpg.add_text("2. Click 'Login' to login with existing credentials")
            dpg.add_text("3. Use 'Profiles' dropdown to switch between saved accounts")
            dpg.add_text("4. Click 'Logout' to clear authentication")
            dpg.add_text("5. Test operations require backend server on localhost:8001")
            
            # Update initial state
            self._update_ui_state()
    
    def _on_login_clicked(self):
        """Handle login button click."""
        logger.info("Login button clicked")
        self.auth_gui.show_login_dialog(on_success=self._on_auth_success)
    
    def _on_register_clicked(self):
        """Handle register button click."""
        logger.info("Register button clicked")
        self.auth_gui.show_register_dialog(on_success=self._on_auth_success)
    
    def _on_logout_clicked(self):
        """Handle logout button click."""
        logger.info("Logout button clicked")
        self.auth_gui.logout()
        self._update_ui_state()
    
    def _on_profile_selected(self, sender, app_data):
        """Handle profile selection."""
        if app_data:
            logger.info(f"Profile selected: {app_data}")
            success = self.auth_gui.switch_profile(app_data)
            if success:
                self._update_ui_state()
            else:
                dpg.set_value("status_text", f"Failed to switch to profile: {app_data}")
    
    def _refresh_profiles(self):
        """Refresh the profiles dropdown."""
        profiles = self.auth_gui.get_available_profiles()
        dpg.configure_item("profile_combo", items=profiles)
        logger.info(f"Refreshed profiles: {profiles}")
    
    def _test_api_call(self):
        """Test an authenticated API call."""
        try:
            # Simple synchronous test - just check if we have authentication
            if self.auth_gui.is_authenticated():
                user = self.auth_gui.get_current_user()
                token = self.auth_gui.auth_manager.get_current_token()
                
                if token:
                    dpg.set_value("status_text", f"API test: Token available (length: {len(token)})")
                    logger.info(f"API test successful - token length: {len(token)}")
                else:
                    dpg.set_value("status_text", "API test: No token available")
                    logger.warning("API test: No token available")
            else:
                dpg.set_value("status_text", "API test: Not authenticated")
                logger.warning("API test: Not authenticated")
        except Exception as e:
            dpg.set_value("status_text", f"API test error: {e}")
            logger.error(f"API test error: {e}")
    
    def _test_token_refresh(self):
        """Test token refresh functionality."""
        try:
            if self.auth_gui.is_authenticated():
                # For now, just show that we would refresh the token
                current_token = self.auth_gui.auth_manager.get_current_token()
                if current_token:
                    dpg.set_value("status_text", "Token refresh test: Ready to refresh (async operation disabled in demo)")
                    logger.info("Token refresh test: Current token exists, refresh would be possible")
                    # Note: Actual token refresh requires proper async context
                    # In a real application, this would be called from an async context
                else:
                    dpg.set_value("status_text", "Token refresh test: No token to refresh")
                    logger.warning("Token refresh test: No token available")
            else:
                dpg.set_value("status_text", "Cannot refresh: Not authenticated")
                logger.warning("Token refresh test: Not authenticated")
        except Exception as e:
            dpg.set_value("status_text", f"Refresh test error: {e}")
            logger.error(f"Token refresh test error: {e}")
    
    def _on_auth_success(self):
        """Handle successful authentication."""
        logger.info("Authentication successful")
        self._update_ui_state()
        self._refresh_profiles()
    
    def _update_ui_state(self):
        """Update the UI based on current authentication state."""
        is_authenticated = self.auth_gui.is_authenticated()
        user = self.auth_gui.get_current_user()
        
        # Update status text
        self.auth_gui.update_status()
        status = self.auth_gui.get_status_text()
        status_color = (100, 255, 100) if is_authenticated else (255, 100, 100)
        dpg.set_value("status_text", status)
        dpg.configure_item("status_text", color=status_color)
        
        # Update button states
        dpg.configure_item("login_button", enabled=not is_authenticated)
        dpg.configure_item("register_button", enabled=not is_authenticated)
        dpg.configure_item("logout_button", enabled=is_authenticated)
        dpg.configure_item("test_api_button", enabled=is_authenticated)
        dpg.configure_item("test_refresh_button", enabled=is_authenticated)
        
        # Update user information
        if user:
            dpg.set_value("user_username", f"Username: {user.username}")
            dpg.set_value("user_email", f"Email: {user.email or 'N/A'}")
            dpg.set_value("user_display_name", f"Display Name: {user.display_name or 'N/A'}")
        else:
            dpg.set_value("user_username", "Username: N/A")
            dpg.set_value("user_email", "Email: N/A")
            dpg.set_value("user_display_name", "Display Name: N/A")
        
        logger.debug(f"UI state updated: authenticated={is_authenticated}")
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.auth_gui.close()
        logger.info("AuthTestApp cleanup completed")


def main():
    """Main entry point for manual testing."""
    # Setup logging
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG",
        format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> - <level>{message}</level>"
    )
    
    logger.info("Starting authentication GUI manual test")
    
    # Initialize DearPyGUI
    dpg.create_context()
    dpg.create_viewport(title="Gomoku Authentication Test", width=800, height=600)
    dpg.setup_dearpygui()
    
    # Create test app
    app = AuthTestApp()
    
    # Set primary window
    dpg.set_primary_window("main_window", True)
    
    # Show viewport
    dpg.show_viewport()
    
    logger.info("GUI initialized, starting render loop")
    
    # Main render loop
    try:
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
    finally:
        # Cleanup
        asyncio.run(app.cleanup())
        dpg.destroy_context()
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    main()