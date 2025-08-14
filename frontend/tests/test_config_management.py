"""
Tests for configuration management with config.json and .env support.

Following TDD methodology: RED-GREEN-REFACTOR
These tests define the behavior for enhanced configuration management.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import pytest

from frontend.auth.config_manager import ConfigManager, ConfigurationError
from frontend.auth.models import UserProfile, TokenInfo


class TestConfigManager:
    """Test ConfigManager functionality."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        # Create temporary directory for config files
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "gomoku_config.json"
        self.env_path = Path(self.temp_dir) / ".env"
        
        # Initialize ConfigManager with test paths
        self.config_manager = ConfigManager(
            config_file=str(self.config_path),
            env_file=str(self.env_path)
        )
        
        # Mock data
        self.mock_user = UserProfile(
            id=1,
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            date_joined=datetime.now()
        )
        
        self.mock_token = TokenInfo(
            token="test_token_123",
            expires_at=datetime.now() + timedelta(days=7),
            device_name="Test Device"
        )
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up temporary files
        for file_path in [self.config_path, self.env_path]:
            if file_path.exists():
                file_path.unlink()
    
    def test_load_empty_config(self):
        """Test loading config when no files exist."""
        # RED: This will fail because ConfigManager doesn't exist yet
        config = self.config_manager.load_config()
        
        # Should return default config
        assert config is not None
        assert config.current_profile is None
        assert len(config.profiles) == 0
        assert config.base_url == "http://localhost:8001"  # default
        assert config.timeout == 30.0  # default
    
    def test_load_config_from_json(self):
        """Test loading config from JSON file."""
        # Create test config file
        test_config = {
            "base_url": "http://api.example.com",
            "timeout": 60.0,
            "current_profile": "user1",
            "profiles": {
                "user1": {
                    "user": {
                        "id": 1,
                        "username": "user1",
                        "email": "user1@example.com",
                        "display_name": "User One",
                        "date_joined": "2024-01-01T00:00:00"
                    },
                    "token": {
                        "token": "token1",
                        "expires_at": "2025-01-01T00:00:00",
                        "device_name": "Device 1"
                    }
                }
            },
            "default_device_info": {
                "platform": "Linux",
                "app": "Gomoku Desktop"
            }
        }
        
        self.config_path.write_text(json.dumps(test_config, indent=2))
        
        config = self.config_manager.load_config()
        
        assert config.base_url == "http://api.example.com"
        assert config.timeout == 60.0
        assert config.current_profile == "user1"
        assert len(config.profiles) == 1
        assert "user1" in config.profiles
    
    def test_load_config_from_env(self):
        """Test loading config from .env file."""
        # Create test .env file
        env_content = """
# Gomoku Configuration
GOMOKU_BASE_URL=http://env.example.com
GOMOKU_TIMEOUT=45.0
GOMOKU_DEFAULT_DEVICE_NAME=Desktop App
GOMOKU_LOG_LEVEL=DEBUG
GOMOKU_AUTO_REFRESH_TOKEN=true
"""
        self.env_path.write_text(env_content)
        
        config = self.config_manager.load_config()
        
        # Environment variables should override defaults
        assert config.base_url == "http://env.example.com"
        assert config.timeout == 45.0
        assert config.default_device_info["device_name"] == "Desktop App"
        assert config.log_level == "DEBUG"
        assert config.auto_refresh_token is True
    
    def test_env_overrides_json(self):
        """Test that environment variables override JSON config."""
        # Create JSON config
        json_config = {
            "base_url": "http://json.example.com",
            "timeout": 30.0
        }
        self.config_path.write_text(json.dumps(json_config))
        
        # Create .env with different values
        env_content = """
GOMOKU_BASE_URL=http://env.example.com
GOMOKU_TIMEOUT=60.0
"""
        self.env_path.write_text(env_content)
        
        config = self.config_manager.load_config()
        
        # Environment should win
        assert config.base_url == "http://env.example.com"
        assert config.timeout == 60.0
    
    def test_save_config(self):
        """Test saving configuration to JSON file."""
        config = self.config_manager.load_config()
        config.base_url = "http://saved.example.com"
        config.timeout = 120.0
        config.current_profile = "saved_user"
        
        # Save profile data
        self.config_manager.save_profile(
            "saved_user", 
            self.mock_user, 
            self.mock_token,
            config
        )
        
        self.config_manager.save_config(config)
        
        # Verify file was created and contains expected data
        assert self.config_path.exists()
        saved_data = json.loads(self.config_path.read_text())
        
        assert saved_data["base_url"] == "http://saved.example.com"
        assert saved_data["timeout"] == 120.0
        assert saved_data["current_profile"] == "saved_user"
        assert "saved_user" in saved_data["profiles"]
    
    def test_save_and_load_profile(self):
        """Test saving and loading user profiles."""
        config = self.config_manager.load_config()
        
        # Save profile
        self.config_manager.save_profile(
            "test_profile",
            self.mock_user,
            self.mock_token,
            config
        )
        
        # Load profile
        user, token = self.config_manager.load_profile("test_profile", config)
        
        assert user is not None
        assert token is not None
        assert user.username == "testuser"
        assert token.token == "test_token_123"
    
    def test_load_nonexistent_profile(self):
        """Test loading a profile that doesn't exist."""
        config = self.config_manager.load_config()
        
        user, token = self.config_manager.load_profile("nonexistent", config)
        
        assert user is None
        assert token is None
    
    def test_get_profile_names(self):
        """Test getting list of profile names."""
        config = self.config_manager.load_config()
        
        # Save multiple profiles
        for i in range(3):
            user = UserProfile(
                id=i+1,
                username=f"user{i+1}",
                email=f"user{i+1}@example.com",
                display_name=f"User {i+1}",
                date_joined=datetime.now()
            )
            token = TokenInfo(
                token=f"token{i+1}",
                expires_at=datetime.now() + timedelta(days=7),
                device_name=f"Device {i+1}"
            )
            
            self.config_manager.save_profile(f"profile{i+1}", user, token, config)
        
        profile_names = self.config_manager.get_profile_names(config)
        
        assert len(profile_names) == 3
        assert "profile1" in profile_names
        assert "profile2" in profile_names
        assert "profile3" in profile_names
    
    def test_delete_profile(self):
        """Test deleting a user profile."""
        config = self.config_manager.load_config()
        
        # Save profile
        self.config_manager.save_profile(
            "delete_me",
            self.mock_user,
            self.mock_token,
            config
        )
        
        # Verify it exists
        user, token = self.config_manager.load_profile("delete_me", config)
        assert user is not None
        
        # Delete it
        success = self.config_manager.delete_profile("delete_me", config)
        assert success is True
        
        # Verify it's gone
        user, token = self.config_manager.load_profile("delete_me", config)
        assert user is None
        assert token is None
    
    def test_delete_nonexistent_profile(self):
        """Test deleting a profile that doesn't exist."""
        config = self.config_manager.load_config()
        
        success = self.config_manager.delete_profile("nonexistent", config)
        assert success is False
    
    def test_invalid_json_fallback(self):
        """Test fallback behavior with invalid JSON."""
        # Write invalid JSON
        self.config_path.write_text("invalid json content")
        
        config = self.config_manager.load_config()
        
        # Should return default config
        assert config.base_url == "http://localhost:8001"
        assert config.current_profile is None
    
    def test_env_variable_types(self):
        """Test proper type conversion for environment variables."""
        env_content = """
GOMOKU_TIMEOUT=45.5
GOMOKU_AUTO_REFRESH_TOKEN=false
GOMOKU_MAX_RETRIES=3
"""
        self.env_path.write_text(env_content)
        
        config = self.config_manager.load_config()
        
        assert isinstance(config.timeout, float)
        assert config.timeout == 45.5
        assert isinstance(config.auto_refresh_token, bool)
        assert config.auto_refresh_token is False
        assert isinstance(config.max_retries, int)
        assert config.max_retries == 3
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Create invalid config (negative timeout)
        invalid_config = {
            "base_url": "",  # invalid URL
            "timeout": -10.0  # invalid timeout
        }
        self.config_path.write_text(json.dumps(invalid_config))
        
        with pytest.raises(ConfigurationError):
            self.config_manager.load_config(validate=True)
    
    def test_backup_and_restore(self):
        """Test backup and restore functionality."""
        # Save some config
        config = self.config_manager.load_config()
        config.base_url = "http://backup.example.com"
        self.config_manager.save_profile("backup_user", self.mock_user, self.mock_token, config)
        self.config_manager.save_config(config)
        
        # Create backup
        backup_path = self.config_manager.create_backup()
        assert backup_path.exists()
        
        # Modify config
        config.base_url = "http://modified.example.com"
        self.config_manager.save_config(config)
        
        # Restore backup
        success = self.config_manager.restore_backup(backup_path)
        assert success is True
        
        # Verify restoration
        restored_config = self.config_manager.load_config()
        assert restored_config.base_url == "http://backup.example.com"
        assert "backup_user" in restored_config.profiles


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager with AuthManager."""
    
    def setup_method(self):
        """Set up test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "gomoku_config.json"
        self.env_path = Path(self.temp_dir) / ".env"
    
    def test_auth_manager_uses_config_manager(self):
        """Test that AuthManager uses ConfigManager for configuration."""
        # This will test the integration once we implement it
        from frontend.auth.auth_manager import AuthManager
        
        # Create .env with custom config
        env_content = """
GOMOKU_BASE_URL=http://config-test.example.com
GOMOKU_TIMEOUT=75.0
"""
        self.env_path.write_text(env_content)
        
        # AuthManager should pick up the config
        auth_manager = AuthManager(
            config_file=str(self.config_path),
            env_file=str(self.env_path)
        )
        
        # Should use the configured base URL from env
        assert auth_manager.base_url == "http://config-test.example.com"
    
    def test_profile_switching_integration(self):
        """Test profile switching with ConfigManager."""
        from frontend.auth.auth_manager import AuthManager
        
        auth_manager = AuthManager(
            config_file=str(self.config_path),
            env_file=str(self.env_path)
        )
        
        # This should use the enhanced profile management
        profiles = auth_manager.get_saved_profiles()
        assert isinstance(profiles, list)