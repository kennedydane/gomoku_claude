"""
Authentication dialogs for the Gomoku frontend GUI.

This module provides DearPyGUI-based dialogs for user authentication including
login, registration, and profile management interfaces.
"""

import asyncio
import re
from typing import Optional, List, Callable, Dict, Any
from pathlib import Path

import dearpygui.dearpygui as dpg
from loguru import logger

from frontend.auth.auth_manager import AuthManager
from frontend.auth.exceptions import AuthError, TokenExpiredError
from frontend.auth.models import UserProfile


class LoginDialog:
    """DearPyGUI-based login dialog with form validation and error handling."""
    
    def __init__(self, auth_manager: AuthManager):
        """
        Initialize the login dialog.
        
        Args:
            auth_manager: AuthManager instance for authentication operations
        """
        self.auth_manager = auth_manager
        self._is_visible = False
        self._is_loading = False
        self._error_message = ""
        self._remember_me = False
        self._password_visible = False
        self._on_success_callback: Optional[Callable] = None
        self._on_cancel_callback: Optional[Callable] = None
        
        # DearPyGui tags with unique identifiers
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        self._dialog_tag = f"login_dialog_{unique_id}"
        self._username_tag = f"login_username_{unique_id}"
        self._password_tag = f"login_password_{unique_id}"
        self._remember_me_tag = f"login_remember_me_{unique_id}"
        self._error_text_tag = f"login_error_text_{unique_id}"
        self._login_button_tag = f"login_button_{unique_id}"
        self._loading_text_tag = f"login_loading_text_{unique_id}"
        self._password_toggle_tag = f"login_password_toggle_{unique_id}"
        
        self._create_dialog()
        
        logger.debug("LoginDialog initialized")
    
    def _create_dialog(self) -> None:
        """Create the login dialog UI components."""
        with dpg.window(
            label="Login",
            tag=self._dialog_tag,
            modal=True,
            show=False,
            width=400,
            height=300,
            no_resize=True
        ):
            dpg.add_text("Login to Gomoku")
            dpg.add_separator()
            
            # Username field
            dpg.add_text("Username:")
            dpg.add_input_text(
                tag=self._username_tag,
                width=-1,
                hint="Enter your username",
                callback=self._on_form_change
            )
            
            # Password field with toggle
            dpg.add_text("Password:")
            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    tag=self._password_tag,
                    width=-50,
                    hint="Enter your password",
                    password=True,
                    callback=self._on_form_change
                )
                dpg.add_button(
                    label="👁",
                    tag=self._password_toggle_tag,
                    width=40,
                    callback=self._toggle_password_visibility
                )
            
            # Remember me checkbox
            dpg.add_checkbox(
                label="Remember me",
                tag=self._remember_me_tag,
                default_value=False
            )
            
            dpg.add_separator()
            
            # Error message display
            dpg.add_text(
                "",
                tag=self._error_text_tag,
                color=(255, 100, 100),  # Red color for errors
                wrap=380
            )
            
            # Loading indicator
            dpg.add_text(
                "Logging in...",
                tag=self._loading_text_tag,
                show=False,
                color=(100, 150, 255)  # Blue color for loading
            )
            
            # Action buttons
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Login",
                    tag=self._login_button_tag,
                    callback=self._on_login_clicked,
                    width=100
                )
                dpg.add_button(
                    label="Cancel",
                    callback=self._on_cancel_clicked,
                    width=100
                )
                dpg.add_button(
                    label="Register",
                    callback=self._on_register_clicked,
                    width=100
                )
    
    @property
    def is_visible(self) -> bool:
        """Check if the dialog is currently visible."""
        return self._is_visible
    
    @property
    def is_loading(self) -> bool:
        """Check if the dialog is in loading state."""
        return self._is_loading
    
    def show(self, on_success: Optional[Callable] = None, on_cancel: Optional[Callable] = None) -> None:
        """
        Show the login dialog.
        
        Args:
            on_success: Callback to call on successful login
            on_cancel: Callback to call when dialog is cancelled
        """
        self._on_success_callback = on_success
        self._on_cancel_callback = on_cancel
        self._error_message = ""
        self._is_visible = True
        
        dpg.configure_item(self._dialog_tag, show=True)
        dpg.focus_item(self._username_tag)
        
        logger.debug("LoginDialog shown")
    
    def hide(self) -> None:
        """Hide the login dialog."""
        self._is_visible = False
        dpg.configure_item(self._dialog_tag, show=False)
        logger.debug("LoginDialog hidden")
    
    def validate_form(self, username: str, password: str) -> bool:
        """
        Validate the login form inputs.
        
        Args:
            username: Username to validate
            password: Password to validate
            
        Returns:
            True if form is valid, False otherwise
        """
        errors = []
        
        if not username.strip():
            errors.append("Username is required")
        
        if not password:
            errors.append("Password is required")
        elif len(password) < 4:
            errors.append("Password must be at least 4 characters")
        
        self._error_message = "; ".join(errors)
        self._update_error_display()
        
        return len(errors) == 0
    
    def get_error_message(self) -> str:
        """Get the current error message."""
        return self._error_message
    
    def set_username(self, username: str) -> None:
        """Set the username field value."""
        dpg.set_value(self._username_tag, username)
    
    def set_password(self, password: str) -> None:
        """Set the password field value."""
        dpg.set_value(self._password_tag, password)
    
    def set_remember_me(self, remember: bool) -> None:
        """Set the remember me checkbox value."""
        self._remember_me = remember
        dpg.set_value(self._remember_me_tag, remember)
    
    def get_remember_me(self) -> bool:
        """Get the remember me checkbox value."""
        return dpg.get_value(self._remember_me_tag)
    
    def is_password_visible(self) -> bool:
        """Check if password is currently visible."""
        return self._password_visible
    
    def toggle_password_visibility(self) -> None:
        """Toggle password field visibility."""
        self._password_visible = not self._password_visible
        dpg.configure_item(self._password_tag, password=not self._password_visible)
        
        # Update button text
        button_text = "🙈" if self._password_visible else "👁"
        dpg.configure_item(self._password_toggle_tag, label=button_text)
    
    def set_loading(self, loading: bool) -> None:
        """
        Set the loading state of the dialog.
        
        Args:
            loading: True to show loading state, False to hide
        """
        self._is_loading = loading
        
        # Show/hide loading indicator
        dpg.configure_item(self._loading_text_tag, show=loading)
        
        # Enable/disable form controls
        dpg.configure_item(self._username_tag, enabled=not loading)
        dpg.configure_item(self._password_tag, enabled=not loading)
        dpg.configure_item(self._remember_me_tag, enabled=not loading)
        dpg.configure_item(self._login_button_tag, enabled=not loading)
        dpg.configure_item(self._password_toggle_tag, enabled=not loading)
    
    def is_form_enabled(self) -> bool:
        """Check if form controls are enabled."""
        return not self._is_loading
    
    async def perform_login(self) -> bool:
        """
        Perform the login operation.
        
        Returns:
            True if login successful, False otherwise
        """
        username = dpg.get_value(self._username_tag).strip()
        password = dpg.get_value(self._password_tag)
        
        # Validate form
        if not self.validate_form(username, password):
            return False
        
        # Set loading state
        self.set_loading(True)
        self._error_message = ""
        self._update_error_display()
        
        try:
            # Attempt login
            success = await self.auth_manager.login(
                username=username,
                password=password,
                device_name="Desktop App",
                device_info={}
            )
            
            if success:
                logger.info(f"Login successful for user: {username}")
                self.set_loading(False)
                return True
            else:
                self._error_message = "Invalid username or password"
                logger.warning(f"Login failed for user: {username}")
                
        except AuthError as e:
            self._error_message = str(e)
            logger.error(f"Login error for user {username}: {e}")
        except Exception as e:
            self._error_message = "An unexpected error occurred"
            logger.error(f"Unexpected login error for user {username}: {e}")
        
        self.set_loading(False)
        self._update_error_display()
        return False
    
    def _update_error_display(self) -> None:
        """Update the error message display."""
        dpg.set_value(self._error_text_tag, self._error_message)
        dpg.configure_item(self._error_text_tag, show=bool(self._error_message))
    
    def _on_form_change(self) -> None:
        """Handle form field changes."""
        # Clear error message when user starts typing
        if self._error_message:
            self._error_message = ""
            self._update_error_display()
    
    def _on_login_clicked(self) -> None:
        """Handle login button click."""
        async def login_task():
            success = await self.perform_login()
            if success:
                self.hide()
                if self._on_success_callback:
                    self._on_success_callback()
        
        # Run async login using asyncio.run for new event loop
        try:
            loop = asyncio.get_running_loop()
            # If there's already a loop, schedule the task
            loop.create_task(login_task())
        except RuntimeError:
            # No event loop running, create a new one
            import threading
            def run_login():
                try:
                    asyncio.run(login_task())
                except Exception as e:
                    # Handle any threading/event loop cleanup issues
                    from loguru import logger
                    logger.error(f"Error in login thread: {e}")
            
            threading.Thread(target=run_login, daemon=True).start()
    
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        self.hide()
        if self._on_cancel_callback:
            self._on_cancel_callback()
    
    def _on_register_clicked(self) -> None:
        """Handle register button click."""
        # This will be handled by the parent AuthenticationManager
        self.hide()
    
    def _toggle_password_visibility(self) -> None:
        """Handle password visibility toggle button click."""
        self.toggle_password_visibility()


class RegisterDialog:
    """DearPyGUI-based registration dialog with form validation."""
    
    def __init__(self, auth_manager: AuthManager):
        """
        Initialize the registration dialog.
        
        Args:
            auth_manager: AuthManager instance for authentication operations
        """
        self.auth_manager = auth_manager
        self._is_visible = False
        self._is_loading = False
        self._error_message = ""
        self._on_success_callback: Optional[Callable] = None
        self._on_cancel_callback: Optional[Callable] = None
        
        # DearPyGui tags with unique identifiers
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        self._dialog_tag = f"register_dialog_{unique_id}"
        self._username_tag = f"register_username_{unique_id}"
        self._password_tag = f"register_password_{unique_id}"
        self._confirm_password_tag = f"register_confirm_password_{unique_id}"
        self._email_tag = f"register_email_{unique_id}"
        self._display_name_tag = f"register_display_name_{unique_id}"
        self._error_text_tag = f"register_error_text_{unique_id}"
        self._register_button_tag = f"register_button_{unique_id}"
        self._loading_text_tag = f"register_loading_text_{unique_id}"
        
        self._create_dialog()
        
        logger.debug("RegisterDialog initialized")
    
    def _create_dialog(self) -> None:
        """Create the registration dialog UI components."""
        with dpg.window(
            label="Register New Account",
            tag=self._dialog_tag,
            modal=True,
            show=False,
            width=450,
            height=400,
            no_resize=True
        ):
            dpg.add_text("Create a new Gomoku account")
            dpg.add_separator()
            
            # Username field
            dpg.add_text("Username:")
            dpg.add_input_text(
                tag=self._username_tag,
                width=-1,
                hint="Choose a username",
                callback=self._on_form_change
            )
            
            # Email field
            dpg.add_text("Email:")
            dpg.add_input_text(
                tag=self._email_tag,
                width=-1,
                hint="Enter your email address",
                callback=self._on_form_change
            )
            
            # Display name field
            dpg.add_text("Display Name (optional):")
            dpg.add_input_text(
                tag=self._display_name_tag,
                width=-1,
                hint="Enter your display name",
                callback=self._on_form_change
            )
            
            # Password field
            dpg.add_text("Password:")
            dpg.add_input_text(
                tag=self._password_tag,
                width=-1,
                hint="Choose a secure password",
                password=True,
                callback=self._on_form_change
            )
            
            # Confirm password field
            dpg.add_text("Confirm Password:")
            dpg.add_input_text(
                tag=self._confirm_password_tag,
                width=-1,
                hint="Confirm your password",
                password=True,
                callback=self._on_form_change
            )
            
            dpg.add_separator()
            
            # Error message display
            dpg.add_text(
                "",
                tag=self._error_text_tag,
                color=(255, 100, 100),  # Red color for errors
                wrap=430
            )
            
            # Loading indicator
            dpg.add_text(
                "Creating account...",
                tag=self._loading_text_tag,
                show=False,
                color=(100, 150, 255)  # Blue color for loading
            )
            
            # Action buttons
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Create Account",
                    tag=self._register_button_tag,
                    callback=self._on_register_clicked,
                    width=120
                )
                dpg.add_button(
                    label="Cancel",
                    callback=self._on_cancel_clicked,
                    width=100
                )
                dpg.add_button(
                    label="Back to Login",
                    callback=self._on_login_clicked,
                    width=120
                )
    
    @property
    def is_visible(self) -> bool:
        """Check if the dialog is currently visible."""
        return self._is_visible
    
    @property
    def is_loading(self) -> bool:
        """Check if the dialog is in loading state."""
        return self._is_loading
    
    def show(self, on_success: Optional[Callable] = None, on_cancel: Optional[Callable] = None) -> None:
        """
        Show the registration dialog.
        
        Args:
            on_success: Callback to call on successful registration
            on_cancel: Callback to call when dialog is cancelled
        """
        self._on_success_callback = on_success
        self._on_cancel_callback = on_cancel
        self._error_message = ""
        self._is_visible = True
        
        dpg.configure_item(self._dialog_tag, show=True)
        dpg.focus_item(self._username_tag)
        
        logger.debug("RegisterDialog shown")
    
    def hide(self) -> None:
        """Hide the registration dialog."""
        self._is_visible = False
        dpg.configure_item(self._dialog_tag, show=False)
        logger.debug("RegisterDialog hidden")
    
    def validate_form(self, username: str, password: str, confirm_password: str, email: str) -> bool:
        """
        Validate the registration form inputs.
        
        Args:
            username: Username to validate
            password: Password to validate
            confirm_password: Password confirmation to validate
            email: Email to validate
            
        Returns:
            True if form is valid, False otherwise
        """
        errors = []
        
        # Username validation
        if not username.strip():
            errors.append("Username is required")
        elif len(username.strip()) < 3:
            errors.append("Username must be at least 3 characters")
        
        # Email validation
        if not email.strip():
            errors.append("Email is required")
        elif not self._is_valid_email(email):
            errors.append("Invalid email address")
        
        # Password validation
        if not password:
            errors.append("Password is required")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters")
        
        # Password confirmation validation
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        self._error_message = "; ".join(errors)
        self._update_error_display()
        
        return len(errors) == 0
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format using regex."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    def get_error_message(self) -> str:
        """Get the current error message."""
        return self._error_message
    
    def set_username(self, username: str) -> None:
        """Set the username field value."""
        dpg.set_value(self._username_tag, username)
    
    def set_password(self, password: str) -> None:
        """Set the password field value."""
        dpg.set_value(self._password_tag, password)
    
    def set_confirm_password(self, password: str) -> None:
        """Set the confirm password field value."""
        dpg.set_value(self._confirm_password_tag, password)
    
    def set_email(self, email: str) -> None:
        """Set the email field value."""
        dpg.set_value(self._email_tag, email)
    
    def set_display_name(self, display_name: str) -> None:
        """Set the display name field value."""
        dpg.set_value(self._display_name_tag, display_name)
    
    def set_loading(self, loading: bool) -> None:
        """
        Set the loading state of the dialog.
        
        Args:
            loading: True to show loading state, False to hide
        """
        self._is_loading = loading
        
        # Show/hide loading indicator
        dpg.configure_item(self._loading_text_tag, show=loading)
        
        # Enable/disable form controls
        dpg.configure_item(self._username_tag, enabled=not loading)
        dpg.configure_item(self._password_tag, enabled=not loading)
        dpg.configure_item(self._confirm_password_tag, enabled=not loading)
        dpg.configure_item(self._email_tag, enabled=not loading)
        dpg.configure_item(self._display_name_tag, enabled=not loading)
        dpg.configure_item(self._register_button_tag, enabled=not loading)
    
    async def perform_registration(self) -> bool:
        """
        Perform the registration operation.
        
        Returns:
            True if registration successful, False otherwise
        """
        username = dpg.get_value(self._username_tag).strip()
        password = dpg.get_value(self._password_tag)
        confirm_password = dpg.get_value(self._confirm_password_tag)
        email = dpg.get_value(self._email_tag).strip()
        display_name = dpg.get_value(self._display_name_tag).strip() or None
        
        # Validate form
        if not self.validate_form(username, password, confirm_password, email):
            return False
        
        # Set loading state
        self.set_loading(True)
        self._error_message = ""
        self._update_error_display()
        
        try:
            # Attempt registration
            success = await self.auth_manager.register(
                username=username,
                password=password,
                email=email,
                display_name=display_name,
                device_name="Desktop App",
                device_info={}
            )
            
            if success:
                logger.info(f"Registration successful for user: {username}")
                self.set_loading(False)
                return True
            else:
                self._error_message = "Registration failed. Username may already exist."
                logger.warning(f"Registration failed for user: {username}")
                
        except AuthError as e:
            self._error_message = str(e)
            logger.error(f"Registration error for user {username}: {e}")
        except Exception as e:
            self._error_message = "An unexpected error occurred"
            logger.error(f"Unexpected registration error for user {username}: {e}")
        
        self.set_loading(False)
        self._update_error_display()
        return False
    
    def _update_error_display(self) -> None:
        """Update the error message display."""
        dpg.set_value(self._error_text_tag, self._error_message)
        dpg.configure_item(self._error_text_tag, show=bool(self._error_message))
    
    def _on_form_change(self) -> None:
        """Handle form field changes."""
        # Clear error message when user starts typing
        if self._error_message:
            self._error_message = ""
            self._update_error_display()
    
    def _on_register_clicked(self) -> None:
        """Handle register button click."""
        async def register_task():
            success = await self.perform_registration()
            if success:
                self.hide()
                if self._on_success_callback:
                    self._on_success_callback()
        
        # Run async registration using asyncio.run for new event loop
        try:
            loop = asyncio.get_running_loop()
            # If there's already a loop, schedule the task
            loop.create_task(register_task())
        except RuntimeError:
            # No event loop running, create a new one
            import threading
            def run_register():
                try:
                    asyncio.run(register_task())
                except Exception as e:
                    # Handle any threading/event loop cleanup issues
                    from loguru import logger
                    logger.error(f"Error in register thread: {e}")
            
            threading.Thread(target=run_register, daemon=True).start()
    
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        self.hide()
        if self._on_cancel_callback:
            self._on_cancel_callback()
    
    def _on_login_clicked(self) -> None:
        """Handle back to login button click."""
        # This will be handled by the parent AuthenticationManager
        self.hide()


class AuthenticationManager:
    """Main GUI component for managing authentication dialogs and state."""
    
    def __init__(self, config_file: Optional[str] = None, env_file: Optional[str] = None):
        """
        Initialize the authentication manager.
        
        Args:
            config_file: Path to configuration file
            env_file: Path to environment file
        """
        self.auth_manager = AuthManager(config_file=config_file, env_file=env_file)
        self.login_dialog = LoginDialog(self.auth_manager)
        self.register_dialog = RegisterDialog(self.auth_manager)
        
        self._is_loading = False
        self._status_text = "Not logged in"
        
        # Set up dialog callbacks
        self.login_dialog._on_register_clicked = self.show_register_dialog
        self.register_dialog._on_login_clicked = self.show_login_dialog
        
        logger.info("AuthenticationManager initialized")
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return self.auth_manager.is_authenticated()
    
    def get_current_user(self) -> Optional[UserProfile]:
        """Get current authenticated user."""
        return self.auth_manager.get_current_user()
    
    def get_status_text(self) -> str:
        """Get authentication status text for display."""
        return self._status_text
    
    def update_status(self) -> None:
        """Update authentication status text."""
        if self.is_authenticated():
            user = self.get_current_user()
            if user:
                display_name = user.display_name or user.username
                self._status_text = f"Logged in as {display_name} ({user.username})"
            else:
                self._status_text = "Logged in"
        else:
            self._status_text = "Not logged in"
    
    def show_login_dialog(self, on_success: Optional[Callable] = None) -> None:
        """
        Show the login dialog.
        
        Args:
            on_success: Callback to call on successful login
        """
        self.register_dialog.hide()  # Hide other dialogs
        self.login_dialog.show(
            on_success=lambda: self._on_auth_success(on_success),
            on_cancel=None
        )
    
    def show_register_dialog(self, on_success: Optional[Callable] = None) -> None:
        """
        Show the registration dialog.
        
        Args:
            on_success: Callback to call on successful registration
        """
        self.login_dialog.hide()  # Hide other dialogs
        self.register_dialog.show(
            on_success=lambda: self._on_auth_success(on_success),
            on_cancel=None
        )
    
    def logout(self) -> None:
        """Logout the current user."""
        self.auth_manager.logout()
        self.update_status()
        logger.info("User logged out")
    
    def get_available_profiles(self) -> List[str]:
        """Get list of available user profiles."""
        return self.auth_manager.get_saved_profiles()
    
    def switch_profile(self, profile_name: str) -> bool:
        """
        Switch to a different user profile.
        
        Args:
            profile_name: Name of profile to switch to
            
        Returns:
            True if successful, False otherwise
        """
        success = self.auth_manager.switch_profile(profile_name)
        if success:
            self.update_status()
            logger.info(f"Switched to profile: {profile_name}")
        return success
    
    def set_loading(self, loading: bool) -> None:
        """Set global loading state."""
        self._is_loading = loading
    
    @property
    def is_loading(self) -> bool:
        """Check if authentication operations are in progress."""
        return self._is_loading
    
    def are_controls_enabled(self) -> bool:
        """Check if authentication controls should be enabled."""
        return not self._is_loading
    
    async def close(self) -> None:
        """Close the authentication manager and cleanup resources."""
        await self.auth_manager.close()
        logger.debug("AuthenticationManager closed")
    
    def _on_auth_success(self, callback: Optional[Callable]) -> None:
        """Handle successful authentication."""
        self.update_status()
        if callback:
            callback()