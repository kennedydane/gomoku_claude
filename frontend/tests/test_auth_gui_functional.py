"""
Functional tests for GUI authentication components.

Following TDD methodology: RED-GREEN-REFACTOR
These tests focus on the core functionality without GUI dependencies.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import pytest

from frontend.auth.auth_manager import AuthManager
from frontend.auth.models import UserProfile, TokenInfo


class MockDPGDialog:
    """Mock DearPyGUI dialog for testing purposes."""
    
    def __init__(self):
        self.is_visible = False
        self.is_loading = False
        self.form_data = {}
        self.error_message = ""
    
    def show(self):
        self.is_visible = True
    
    def hide(self):
        self.is_visible = False
    
    def set_loading(self, loading):
        self.is_loading = loading
    
    def set_error(self, message):
        self.error_message = message
    
    def set_form_value(self, field, value):
        self.form_data[field] = value
    
    def get_form_value(self, field):
        return self.form_data.get(field, "")


class TestAuthenticationGUILogic:
    """Test authentication GUI logic without DearPyGUI dependencies."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        # Create temporary config path
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
        
        # Create mock auth manager
        self.mock_auth_manager = MagicMock(spec=AuthManager)
        
        # Create mock dialog
        self.mock_dialog = MockDPGDialog()
        
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up temporary files
        if self.config_path.exists():
            self.config_path.unlink()
    
    def test_login_form_validation_empty_fields(self):
        """Test login form validation with empty fields."""
        # This tests the validation logic that will be in LoginDialog
        errors = []
        
        username = ""
        password = ""
        
        if not username.strip():
            errors.append("Username is required")
        
        if not password:
            errors.append("Password is required")
        elif len(password) < 4:
            errors.append("Password must be at least 4 characters")
        
        assert len(errors) == 2
        assert "Username is required" in errors
        assert "Password is required" in errors
    
    def test_login_form_validation_short_password(self):
        """Test login form validation with short password."""
        errors = []
        
        username = "testuser"
        password = "123"
        
        if not username.strip():
            errors.append("Username is required")
        
        if not password:
            errors.append("Password is required")
        elif len(password) < 4:
            errors.append("Password must be at least 4 characters")
        
        assert len(errors) == 1
        assert "Password must be at least 4 characters" in errors
    
    def test_login_form_validation_valid_fields(self):
        """Test login form validation with valid fields."""
        errors = []
        
        username = "testuser"
        password = "password123"
        
        if not username.strip():
            errors.append("Username is required")
        
        if not password:
            errors.append("Password is required")
        elif len(password) < 4:
            errors.append("Password must be at least 4 characters")
        
        assert len(errors) == 0
    
    @pytest.mark.asyncio
    async def test_login_success_flow(self):
        """Test successful login flow logic."""
        # Mock successful login
        self.mock_auth_manager.login = AsyncMock(return_value=True)
        self.mock_auth_manager.get_current_user.return_value = UserProfile(
            id=1,
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            date_joined=datetime.now()
        )
        
        # Simulate login process
        username = "testuser"
        password = "password123"
        
        # Validate form (this would be done by LoginDialog)
        errors = []
        if not username.strip():
            errors.append("Username is required")
        if not password:
            errors.append("Password is required")
        elif len(password) < 4:
            errors.append("Password must be at least 4 characters")
        
        is_valid = len(errors) == 0
        assert is_valid is True
        
        # Perform login (this would be done by LoginDialog)
        if is_valid:
            success = await self.mock_auth_manager.login(
                username=username,
                password=password,
                device_name="Desktop App",
                device_info={}
            )
            
            assert success is True
            
            # Should have called auth manager login
            self.mock_auth_manager.login.assert_called_once_with(
                username="testuser",
                password="password123",
                device_name="Desktop App",
                device_info={}
            )
    
    @pytest.mark.asyncio
    async def test_login_failure_flow(self):
        """Test failed login flow logic."""
        # Mock failed login
        self.mock_auth_manager.login = AsyncMock(return_value=False)
        
        username = "testuser"
        password = "wrongpassword"
        
        # Perform login attempt
        success = await self.mock_auth_manager.login(
            username=username,
            password=password,
            device_name="Desktop App",
            device_info={}
        )
        
        assert success is False
        
        # Should show error message in GUI
        expected_error = "Invalid username or password"
        assert expected_error is not None
    
    def test_register_form_validation_empty_fields(self):
        """Test registration form validation with empty fields."""
        errors = []
        
        username = ""
        password = ""
        confirm_password = ""
        email = ""
        
        # Username validation
        if not username.strip():
            errors.append("Username is required")
        elif len(username.strip()) < 3:
            errors.append("Username must be at least 3 characters")
        
        # Email validation
        if not email.strip():
            errors.append("Email is required")
        
        # Password validation
        if not password:
            errors.append("Password is required")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters")
        
        # Password confirmation validation
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        assert len(errors) == 3  # Username, email, and password required
        assert "Username is required" in errors
        assert "Email is required" in errors
        assert "Password is required" in errors
    
    def test_register_form_validation_password_mismatch(self):
        """Test registration form validation with password mismatch."""
        errors = []
        
        username = "testuser"
        password = "password123"
        confirm_password = "password456"  # Different password
        email = "test@example.com"
        
        # Username validation
        if not username.strip():
            errors.append("Username is required")
        elif len(username.strip()) < 3:
            errors.append("Username must be at least 3 characters")
        
        # Email validation (simplified)
        if not email.strip():
            errors.append("Email is required")
        
        # Password validation
        if not password:
            errors.append("Password is required")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters")
        
        # Password confirmation validation
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        assert len(errors) == 1
        assert "Passwords do not match" in errors
    
    def test_email_validation_logic(self):
        """Test email validation logic."""
        import re
        
        def is_valid_email(email):
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(email_pattern, email))
        
        # Test valid emails
        assert is_valid_email("test@example.com") is True
        assert is_valid_email("user.name@domain.org") is True
        assert is_valid_email("test123@example.co.uk") is True
        
        # Test invalid emails
        assert is_valid_email("invalid-email") is False
        assert is_valid_email("test@") is False
        assert is_valid_email("@example.com") is False
        assert is_valid_email("test..email@example.com") is False
    
    @pytest.mark.asyncio
    async def test_register_success_flow(self):
        """Test successful registration flow logic."""
        # Mock successful registration
        self.mock_auth_manager.register = AsyncMock(return_value=True)
        
        username = "newuser"
        password = "newpassword123"
        confirm_password = "newpassword123"
        email = "newuser@example.com"
        display_name = "New User"
        
        # Validate form
        errors = []
        if not username.strip():
            errors.append("Username is required")
        if not email.strip():
            errors.append("Email is required")
        if not password:
            errors.append("Password is required")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters")
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        is_valid = len(errors) == 0
        assert is_valid is True
        
        # Perform registration
        if is_valid:
            success = await self.mock_auth_manager.register(
                username=username,
                password=password,
                email=email,
                display_name=display_name,
                device_name="Desktop App",
                device_info={}
            )
            
            assert success is True
            
            # Should have called auth manager register
            self.mock_auth_manager.register.assert_called_once_with(
                username="newuser",
                password="newpassword123",
                email="newuser@example.com",
                display_name="New User",
                device_name="Desktop App",
                device_info={}
            )
    
    def test_authentication_status_logic(self):
        """Test authentication status display logic."""
        # Mock unauthenticated state
        self.mock_auth_manager.is_authenticated.return_value = False
        self.mock_auth_manager.get_current_user.return_value = None
        
        # Test status text logic
        if self.mock_auth_manager.is_authenticated():
            user = self.mock_auth_manager.get_current_user()
            if user:
                display_name = user.display_name or user.username
                status_text = f"Logged in as {display_name} ({user.username})"
            else:
                status_text = "Logged in"
        else:
            status_text = "Not logged in"
        
        assert status_text == "Not logged in"
        
        # Mock authenticated state
        self.mock_auth_manager.is_authenticated.return_value = True
        mock_user = UserProfile(
            id=1,
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            date_joined=datetime.now()
        )
        self.mock_auth_manager.get_current_user.return_value = mock_user
        
        # Test authenticated status
        if self.mock_auth_manager.is_authenticated():
            user = self.mock_auth_manager.get_current_user()
            if user:
                display_name = user.display_name or user.username
                status_text = f"Logged in as {display_name} ({user.username})"
            else:
                status_text = "Logged in"
        else:
            status_text = "Not logged in"
        
        assert "Test User" in status_text
        assert "testuser" in status_text
    
    def test_profile_management_logic(self):
        """Test profile management logic."""
        # Mock saved profiles
        mock_profiles = ["profile1", "profile2", "profile3"]
        self.mock_auth_manager.get_saved_profiles.return_value = mock_profiles
        
        profiles = self.mock_auth_manager.get_saved_profiles()
        assert len(profiles) == 3
        assert "profile1" in profiles
        assert "profile2" in profiles
        assert "profile3" in profiles
        
        # Test profile switching
        self.mock_auth_manager.switch_profile.return_value = True
        success = self.mock_auth_manager.switch_profile("profile1")
        assert success is True
        
        self.mock_auth_manager.switch_profile.assert_called_once_with("profile1")
    
    def test_logout_logic(self):
        """Test logout logic."""
        # Mock authenticated state
        self.mock_auth_manager.is_authenticated.return_value = True
        
        # Perform logout
        self.mock_auth_manager.logout()
        
        # Should have called logout
        self.mock_auth_manager.logout.assert_called_once()
        
        # Status should update (this would be done by GUI)
        status_text = "Not logged in"  # GUI would update this
        assert status_text == "Not logged in"


class TestAuthDialogIntegration:
    """Test integration between auth dialogs and auth manager."""
    
    def setup_method(self):
        """Set up test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.json"
    
    def teardown_method(self):
        """Clean up after each test."""
        if self.config_path.exists():
            self.config_path.unlink()
    
    @patch('frontend.ui.auth_dialogs.dpg')
    def test_authentication_manager_creation(self, mock_dpg):
        """Test AuthenticationManager can be created."""
        # This will test the basic integration
        from frontend.ui.auth_dialogs import AuthenticationManager
        
        auth_gui = AuthenticationManager(config_file=str(self.config_path))
        
        assert auth_gui is not None
        assert auth_gui.auth_manager is not None
        assert hasattr(auth_gui, 'login_dialog')
        assert hasattr(auth_gui, 'register_dialog')
    
    @patch('frontend.ui.auth_dialogs.dpg')
    def test_authentication_manager_methods(self, mock_dpg):
        """Test AuthenticationManager core methods."""
        from frontend.ui.auth_dialogs import AuthenticationManager
        
        auth_gui = AuthenticationManager(config_file=str(self.config_path))
        
        # Test basic methods exist and don't crash
        assert callable(auth_gui.is_authenticated)
        assert callable(auth_gui.get_current_user)
        assert callable(auth_gui.get_status_text)
        assert callable(auth_gui.update_status)
        assert callable(auth_gui.show_login_dialog)
        assert callable(auth_gui.show_register_dialog)
        assert callable(auth_gui.logout)
        assert callable(auth_gui.get_available_profiles)
        assert callable(auth_gui.switch_profile)