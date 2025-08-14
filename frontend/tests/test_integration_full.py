"""
Full integration test demonstrating the complete authentication system.

This test demonstrates how all components work together:
- ConfigManager for configuration management
- AuthManager for authentication operations  
- APIClient for authenticated API requests
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import pytest

from frontend.auth.auth_manager import AuthManager
from frontend.auth.config_manager import ConfigManager
from frontend.client.api_client import APIClient
from frontend.auth.models import UserProfile, TokenInfo


class TestFullIntegration:
    """Test complete system integration."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "gomoku_config.json"
        self.env_path = Path(self.temp_dir) / ".env"
        
        # Create .env file with custom settings
        env_content = """
GOMOKU_BASE_URL=http://test-server.example.com
GOMOKU_TIMEOUT=45.0
GOMOKU_LOG_LEVEL=DEBUG
GOMOKU_AUTO_REFRESH_TOKEN=true
GOMOKU_DEFAULT_DEVICE_NAME=Integration Test Device
"""
        self.env_path.write_text(env_content)
        
        # Mock server responses
        self.mock_login_response = {
            "token": "test_integration_token",
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
            "device_name": "Integration Test Device",
            "user": {
                "id": 123,
                "username": "integration_user",
                "email": "integration@example.com",
                "display_name": "Integration Test User",
                "date_joined": datetime.now().isoformat()
            }
        }
        
        self.mock_user_data = {
            "id": 456,
            "username": "api_user",
            "display_name": "API User"
        }
    
    def teardown_method(self):
        """Clean up test files."""
        for file_path in [self.config_path, self.env_path]:
            if file_path.exists():
                file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_complete_authentication_flow(self):
        """Test complete authentication flow with configuration."""
        
        # 1. Initialize AuthManager with custom config
        auth_manager = AuthManager(
            config_file=str(self.config_path),
            env_file=str(self.env_path)
        )
        
        # Verify environment configuration was loaded
        assert auth_manager.base_url == "http://test-server.example.com"
        assert auth_manager.config.timeout == 45.0
        assert auth_manager.config.log_level == "DEBUG"
        assert auth_manager.config.default_device_info.get("device_name") == "Integration Test Device"
        
        # 2. Initialize APIClient with AuthManager
        api_client = APIClient(
            base_url="http://test-server.example.com",
            auth_manager=auth_manager
        )
        
        # Initially not authenticated
        assert not api_client.is_authenticated
        assert api_client.current_user is None
        
        # 3. Mock successful login
        with patch.object(auth_manager, '_make_request') as mock_request:
            mock_request.return_value = self.mock_login_response
            
            # Login via API client
            success = await api_client.login("integration_user", "test_password")
            assert success is True
            
            # Verify authentication state
            assert api_client.is_authenticated
            assert api_client.current_user is not None
            assert api_client.current_user.username == "integration_user"
            
            # Verify credentials were saved to config
            assert self.config_path.exists()
            
        # 4. Test authenticated API request
        with patch.object(auth_manager, 'make_authenticated_request') as mock_auth_request:
            mock_auth_request.return_value = [self.mock_user_data]
            
            users = await api_client.get_users()
            assert len(users) == 1
            assert users[0].username == "api_user"
            
            # Verify it used authenticated request
            mock_auth_request.assert_called_once_with("GET", "/api/v1/users/")
        
        # 5. Test profile management
        profile_names = auth_manager.get_saved_profiles()
        assert "default" in profile_names
        
        # Switch to default profile should work
        assert auth_manager.switch_profile("default") is True
        assert auth_manager.is_authenticated()
        
        # 6. Test logout
        api_client.logout()
        assert not api_client.is_authenticated
        assert api_client.current_user is None
        
        # Close resources
        await api_client.close()
    
    @pytest.mark.asyncio 
    async def test_configuration_priority(self):
        """Test configuration priority: ENV > JSON > defaults."""
        
        # Create JSON config with different values
        json_config = {
            "base_url": "http://json-config.example.com",
            "timeout": 30.0,
            "log_level": "INFO"
        }
        self.config_path.write_text(json.dumps(json_config, indent=2))
        
        # ENV should override JSON
        auth_manager = AuthManager(
            config_file=str(self.config_path),
            env_file=str(self.env_path)
        )
        
        # Environment values should win
        assert auth_manager.base_url == "http://test-server.example.com"  # From ENV
        assert auth_manager.config.timeout == 45.0  # From ENV
        assert auth_manager.config.log_level == "DEBUG"  # From ENV
        
        # Close resources
        await auth_manager.close()
    
    @pytest.mark.asyncio
    async def test_profile_persistence(self):
        """Test that profiles persist across AuthManager instances."""
        
        # Create first AuthManager instance and save profile
        auth_manager1 = AuthManager(
            config_file=str(self.config_path),
            env_file=str(self.env_path)
        )
        
        # Mock login and save profile
        user = UserProfile(
            id=789,
            username="persistent_user",
            email="persistent@example.com",
            display_name="Persistent User",
            date_joined=datetime.now()
        )
        token = TokenInfo(
            token="persistent_token",
            expires_at=datetime.now() + timedelta(days=7),
            device_name="Persistent Device"
        )
        
        auth_manager1.save_profile("persistent_profile", user, token)
        await auth_manager1.close()
        
        # Create second AuthManager instance
        auth_manager2 = AuthManager(
            config_file=str(self.config_path),
            env_file=str(self.env_path)
        )
        
        # Verify profile persisted
        profiles = auth_manager2.get_saved_profiles()
        assert "persistent_profile" in profiles
        
        # Switch to the profile
        success = auth_manager2.switch_profile("persistent_profile")
        assert success is True
        assert auth_manager2.get_current_user().username == "persistent_user"
        
        await auth_manager2.close()
    
    def test_config_manager_backup_restore(self):
        """Test configuration backup and restore functionality."""
        
        # Create config manager without .env file for this test
        no_env_config_path = self.config_path.with_name("no_env_config.json")
        config_manager = ConfigManager(
            config_file=str(no_env_config_path),
            env_file=str(Path("/nonexistent/.env"))  # Non-existent env file
        )
        
        # Load and modify config
        config = config_manager.load_config()
        config.base_url = "http://backup-test.example.com"
        
        # Save a test profile
        user = UserProfile(
            id=999,
            username="backup_user",
            email="backup@example.com", 
            display_name="Backup User",
            date_joined=datetime.now()
        )
        token = TokenInfo(
            token="backup_token",
            expires_at=datetime.now() + timedelta(days=7),
            device_name="Backup Device"
        )
        
        config_manager.save_profile("backup_profile", user, token, config)
        config_manager.save_config(config)
        
        # Create backup
        backup_path = config_manager.create_backup()
        assert backup_path.exists()
        
        # Modify original config
        config.base_url = "http://modified.example.com"
        config_manager.delete_profile("backup_profile", config)
        config_manager.save_config(config)
        
        # Verify modification (without env override)
        modified_config = config_manager.load_config()
        assert modified_config.base_url == "http://modified.example.com"
        assert "backup_profile" not in modified_config.profiles
        
        # Restore backup
        success = config_manager.restore_backup(backup_path)
        assert success is True
        
        # Verify restoration
        restored_config = config_manager.load_config()
        assert restored_config.base_url == "http://backup-test.example.com"
        assert "backup_profile" in restored_config.profiles
        
        # Clean up
        no_env_config_path.unlink(missing_ok=True)
        backup_path.unlink(missing_ok=True)