"""
Tests for GUI authentication components.

Following TDD methodology: RED-GREEN-REFACTOR
These tests define the behavior for GUI authentication dialogs and components.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import pytest

# Mock DearPyGUI to avoid segmentation faults in testing
with patch.dict('sys.modules', {'dearpygui.dearpygui': MagicMock()}):
    from frontend.ui.auth_dialogs import LoginDialog, RegisterDialog, AuthenticationManager
    from frontend.auth.auth_manager import AuthManager
    from frontend.auth.models import UserProfile, TokenInfo


class TestLoginDialog:
    """Test LoginDialog functionality."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        # Create temporary config path
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
        
        # Create mock auth manager
        self.mock_auth_manager = MagicMock(spec=AuthManager)
        
        # Mock DearPyGUI functions
        self.dpg_mock = MagicMock()
        
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up temporary files
        if self.config_path.exists():
            self.config_path.unlink()
    
    @patch('frontend.ui.auth_dialogs.dpg')
    def test_login_dialog_creation(self, mock_dpg):
        """Test LoginDialog can be created and displayed."""
        # RED: This will fail because LoginDialog doesn't exist yet
        dialog = LoginDialog(self.mock_auth_manager)
        
        assert dialog is not None
        assert dialog.auth_manager == self.mock_auth_manager
        assert dialog.is_visible is False
    
    def test_login_dialog_show_hide(self):
        """Test showing and hiding the login dialog."""
        dialog = LoginDialog(self.mock_auth_manager)
        
        # Initially hidden
        assert dialog.is_visible is False
        
        # Show dialog
        dialog.show()
        assert dialog.is_visible is True
        
        # Hide dialog
        dialog.hide()
        assert dialog.is_visible is False
    
    def test_login_form_validation_empty_fields(self):
        """Test form validation with empty fields."""
        dialog = LoginDialog(self.mock_auth_manager)
        dialog.show()
        
        # Test with empty username and password
        is_valid = dialog.validate_form("", "")
        assert is_valid is False
        assert "Username is required" in dialog.get_error_message()
        assert "Password is required" in dialog.get_error_message()
    
    def test_login_form_validation_short_password(self):
        """Test form validation with short password."""
        dialog = LoginDialog(self.mock_auth_manager)
        dialog.show()
        
        # Test with valid username but short password
        is_valid = dialog.validate_form("testuser", "123")
        assert is_valid is False
        assert "Password must be at least 4 characters" in dialog.get_error_message()
    
    def test_login_form_validation_valid_fields(self):
        """Test form validation with valid fields."""
        dialog = LoginDialog(self.mock_auth_manager)
        dialog.show()
        
        # Test with valid username and password
        is_valid = dialog.validate_form("testuser", "password123")
        assert is_valid is True
        assert dialog.get_error_message() == ""
    
    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test successful login flow."""
        dialog = LoginDialog(self.mock_auth_manager)
        dialog.show()
        
        # Mock successful login
        self.mock_auth_manager.login = AsyncMock(return_value=True)
        self.mock_auth_manager.get_current_user.return_value = UserProfile(
            id=1,
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            date_joined=datetime.now()
        )
        
        # Set form values
        dialog.set_username("testuser")
        dialog.set_password("password123")
        dialog.set_remember_me(True)
        
        # Perform login
        success = await dialog.perform_login()
        
        assert success is True
        assert dialog.is_loading is False
        assert dialog.get_error_message() == ""
        
        # Should have called auth manager login
        self.mock_auth_manager.login.assert_called_once_with(
            username="testuser",
            password="password123",
            device_name="Desktop App",
            device_info={}
        )
    
    @pytest.mark.asyncio
    async def test_login_failure(self):
        """Test failed login flow."""
        dialog = LoginDialog(self.mock_auth_manager)
        dialog.show()
        
        # Mock failed login
        self.mock_auth_manager.login = AsyncMock(return_value=False)
        
        # Set form values
        dialog.set_username("testuser")
        dialog.set_password("wrongpassword")
        
        # Perform login
        success = await dialog.perform_login()
        
        assert success is False
        assert dialog.is_loading is False
        assert "Invalid username or password" in dialog.get_error_message()
    
    @pytest.mark.asyncio
    async def test_login_network_error(self):
        """Test login with network error."""
        dialog = LoginDialog(self.mock_auth_manager)
        dialog.show()
        
        # Mock network error
        from frontend.auth.exceptions import AuthError
        self.mock_auth_manager.login = AsyncMock(side_effect=AuthError("Network error"))
        
        # Set form values
        dialog.set_username("testuser")
        dialog.set_password("password123")
        
        # Perform login
        success = await dialog.perform_login()
        
        assert success is False
        assert "Network error" in dialog.get_error_message()
    
    def test_login_dialog_remember_me_functionality(self):
        """Test remember me checkbox functionality."""
        dialog = LoginDialog(self.mock_auth_manager)
        dialog.show()
        
        # Initially unchecked
        assert dialog.get_remember_me() is False
        
        # Check remember me
        dialog.set_remember_me(True)
        assert dialog.get_remember_me() is True
        
        # Uncheck remember me
        dialog.set_remember_me(False)
        assert dialog.get_remember_me() is False
    
    def test_password_visibility_toggle(self):
        """Test password visibility toggle functionality."""
        dialog = LoginDialog(self.mock_auth_manager)
        dialog.show()
        
        # Initially password is hidden
        assert dialog.is_password_visible() is False
        
        # Toggle password visibility
        dialog.toggle_password_visibility()
        assert dialog.is_password_visible() is True
        
        # Toggle back
        dialog.toggle_password_visibility()
        assert dialog.is_password_visible() is False
    
    def test_loading_state_management(self):
        """Test loading state during authentication."""
        dialog = LoginDialog(self.mock_auth_manager)
        dialog.show()
        
        # Initially not loading
        assert dialog.is_loading is False
        
        # Set loading state
        dialog.set_loading(True)
        assert dialog.is_loading is True
        
        # Should disable form controls during loading
        assert dialog.is_form_enabled() is False
        
        # Clear loading state
        dialog.set_loading(False)
        assert dialog.is_loading is False
        assert dialog.is_form_enabled() is True


class TestRegisterDialog:
    """Test RegisterDialog functionality."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        # Create mock auth manager
        self.mock_auth_manager = MagicMock(spec=AuthManager)
        
        # Initialize DearPyGui context for testing
        if not dpg.is_dearpygui_running():
            dpg.create_context()
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up DearPyGui context
        if dpg.is_dearpygui_running():
            try:
                dpg.destroy_context()
            except:
                pass
    
    def test_register_dialog_creation(self):
        """Test RegisterDialog can be created."""
        # RED: This will fail because RegisterDialog doesn't exist yet
        dialog = RegisterDialog(self.mock_auth_manager)
        
        assert dialog is not None
        assert dialog.auth_manager == self.mock_auth_manager
        assert dialog.is_visible is False
    
    def test_register_form_validation_empty_fields(self):
        """Test registration form validation with empty fields."""
        dialog = RegisterDialog(self.mock_auth_manager)
        dialog.show()
        
        # Test with all empty fields
        is_valid = dialog.validate_form("", "", "", "")
        assert is_valid is False
        
        errors = dialog.get_error_message()
        assert "Username is required" in errors
        assert "Password is required" in errors
        assert "Email is required" in errors
    
    def test_register_form_validation_password_mismatch(self):
        """Test registration form validation with password mismatch."""
        dialog = RegisterDialog(self.mock_auth_manager)
        dialog.show()
        
        # Test with mismatched passwords
        is_valid = dialog.validate_form("testuser", "password123", "password456", "test@example.com")
        assert is_valid is False
        assert "Passwords do not match" in dialog.get_error_message()
    
    def test_register_form_validation_invalid_email(self):
        """Test registration form validation with invalid email."""
        dialog = RegisterDialog(self.mock_auth_manager)
        dialog.show()
        
        # Test with invalid email
        is_valid = dialog.validate_form("testuser", "password123", "password123", "invalid-email")
        assert is_valid is False
        assert "Invalid email address" in dialog.get_error_message()
    
    def test_register_form_validation_weak_password(self):
        """Test registration form validation with weak password."""
        dialog = RegisterDialog(self.mock_auth_manager)
        dialog.show()
        
        # Test with weak password
        is_valid = dialog.validate_form("testuser", "123", "123", "test@example.com")
        assert is_valid is False
        assert "Password must be at least 8 characters" in dialog.get_error_message()
    
    @pytest.mark.asyncio
    async def test_register_success(self):
        """Test successful registration flow."""
        dialog = RegisterDialog(self.mock_auth_manager)
        dialog.show()
        
        # Mock successful registration
        self.mock_auth_manager.register = AsyncMock(return_value=True)
        
        # Set form values
        dialog.set_username("newuser")
        dialog.set_password("newpassword123")
        dialog.set_confirm_password("newpassword123")
        dialog.set_email("newuser@example.com")
        dialog.set_display_name("New User")
        
        # Perform registration
        success = await dialog.perform_registration()
        
        assert success is True
        assert dialog.is_loading is False
        assert dialog.get_error_message() == ""
        
        # Should have called auth manager register
        self.mock_auth_manager.register.assert_called_once_with(
            username="newuser",
            password="newpassword123",
            email="newuser@example.com",
            display_name="New User",
            device_name="Desktop App",
            device_info={}
        )
    
    @pytest.mark.asyncio
    async def test_register_failure_username_exists(self):
        """Test registration failure with existing username."""
        dialog = RegisterDialog(self.mock_auth_manager)
        dialog.show()
        
        # Mock registration failure
        self.mock_auth_manager.register = AsyncMock(return_value=False)
        
        # Set form values
        dialog.set_username("existinguser")
        dialog.set_password("password123")
        dialog.set_confirm_password("password123")
        dialog.set_email("existing@example.com")
        
        # Perform registration
        success = await dialog.perform_registration()
        
        assert success is False
        assert "Registration failed" in dialog.get_error_message()


class TestAuthenticationManager:
    """Test AuthenticationManager GUI component."""
    
    def setup_method(self):
        """Set up test data."""
        # Create temporary config path
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
        
        # Initialize DearPyGui context for testing
        if not dpg.is_dearpygui_running():
            dpg.create_context()
    
    def teardown_method(self):
        """Clean up after each test."""
        if self.config_path.exists():
            self.config_path.unlink()
        
        if dpg.is_dearpygui_running():
            try:
                dpg.destroy_context()
            except:
                pass
    
    def test_authentication_manager_creation(self):
        """Test AuthenticationManager can be created."""
        # RED: This will fail because AuthenticationManager doesn't exist yet
        auth_gui = AuthenticationManager(
            config_file=str(self.config_path)
        )
        
        assert auth_gui is not None
        assert auth_gui.auth_manager is not None
        assert auth_gui.login_dialog is not None
        assert auth_gui.register_dialog is not None
    
    def test_authentication_status_display(self):
        """Test authentication status display."""
        auth_gui = AuthenticationManager(config_file=str(self.config_path))
        
        # Initially not authenticated
        assert auth_gui.is_authenticated() is False
        assert "Not logged in" in auth_gui.get_status_text()
        
        # Mock authenticated state
        mock_user = UserProfile(
            id=1,
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            date_joined=datetime.now()
        )
        
        with patch.object(auth_gui.auth_manager, 'is_authenticated', return_value=True):
            with patch.object(auth_gui.auth_manager, 'get_current_user', return_value=mock_user):
                auth_gui.update_status()
                
                assert auth_gui.is_authenticated() is True
                assert "Test User" in auth_gui.get_status_text()
                assert "testuser" in auth_gui.get_status_text()
    
    def test_show_login_dialog(self):
        """Test showing login dialog."""
        auth_gui = AuthenticationManager(config_file=str(self.config_path))
        
        # Initially dialog should be hidden
        assert auth_gui.login_dialog.is_visible is False
        
        # Show login dialog
        auth_gui.show_login_dialog()
        
        assert auth_gui.login_dialog.is_visible is True
        
        # Hide other dialogs when showing login
        assert auth_gui.register_dialog.is_visible is False
    
    def test_show_register_dialog(self):
        """Test showing registration dialog."""
        auth_gui = AuthenticationManager(config_file=str(self.config_path))
        
        # Show register dialog
        auth_gui.show_register_dialog()
        
        assert auth_gui.register_dialog.is_visible is True
        
        # Hide other dialogs when showing register
        assert auth_gui.login_dialog.is_visible is False
    
    @pytest.mark.asyncio
    async def test_logout_functionality(self):
        """Test logout functionality."""
        auth_gui = AuthenticationManager(config_file=str(self.config_path))
        
        # Mock authenticated state
        with patch.object(auth_gui.auth_manager, 'is_authenticated', return_value=True):
            with patch.object(auth_gui.auth_manager, 'logout') as mock_logout:
                
                # Perform logout
                auth_gui.logout()
                
                # Should have called auth manager logout
                mock_logout.assert_called_once()
                
                # Status should update
                assert "Not logged in" in auth_gui.get_status_text()
    
    def test_profile_management_integration(self):
        """Test profile management integration."""
        auth_gui = AuthenticationManager(config_file=str(self.config_path))
        
        # Mock saved profiles
        mock_profiles = ["profile1", "profile2", "profile3"]
        with patch.object(auth_gui.auth_manager, 'get_saved_profiles', return_value=mock_profiles):
            
            profiles = auth_gui.get_available_profiles()
            assert len(profiles) == 3
            assert "profile1" in profiles
            assert "profile2" in profiles
            assert "profile3" in profiles
    
    @pytest.mark.asyncio
    async def test_switch_profile_functionality(self):
        """Test profile switching functionality."""
        auth_gui = AuthenticationManager(config_file=str(self.config_path))
        
        # Mock profile switching
        with patch.object(auth_gui.auth_manager, 'switch_profile') as mock_switch:
            mock_switch.return_value = True
            
            success = auth_gui.switch_profile("test_profile")
            
            assert success is True
            mock_switch.assert_called_once_with("test_profile")
    
    def test_gui_state_management(self):
        """Test GUI state management during operations."""
        auth_gui = AuthenticationManager(config_file=str(self.config_path))
        
        # Test loading state
        auth_gui.set_loading(True)
        assert auth_gui.is_loading is True
        
        # Controls should be disabled during loading
        assert auth_gui.are_controls_enabled() is False
        
        # Clear loading state
        auth_gui.set_loading(False)
        assert auth_gui.is_loading is False
        assert auth_gui.are_controls_enabled() is True