"""
Tests for frontend authentication manager.

Following TDD methodology: RED-GREEN-REFACTOR
These tests define the behavior we want from the authentication system.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import pytest
import httpx
from pydantic import BaseModel

from frontend.auth.auth_manager import AuthManager
from frontend.auth.exceptions import AuthError, TokenExpiredError
from frontend.auth.models import TokenInfo, UserProfile


class TestAuthManager:
    """Test AuthManager functionality."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        # Create temporary directory for config files
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "auth_config.json"
        
        # Initialize AuthManager with test configuration
        self.auth_manager = AuthManager(
            base_url="http://localhost:8001",
            config_file=str(self.config_path)
        )
        
        # Mock token data
        self.mock_token_response = {
            "token": "test_token_123",
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
            "device_name": "Test Device"
        }
        
        self.mock_user_data = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "display_name": "Test User",
            "date_joined": datetime.now().isoformat()
        }
    
    def teardown_method(self):
        """Clean up after each test."""
        # Clean up temporary files
        if self.config_path.exists():
            self.config_path.unlink()
    
    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test successful login flow."""
        # RED: This test will fail because AuthManager doesn't exist yet
        with patch.object(self.auth_manager, '_make_request') as mock_request:
            mock_request.return_value = {
                **self.mock_token_response,
                "user": self.mock_user_data
            }
            
            result = await self.auth_manager.login(
                username="testuser",
                password="testpass123",
                device_name="Test Device",
                device_info={"os": "Linux", "app": "Test"}
            )
            
            assert result is True
            assert self.auth_manager.is_authenticated()
            assert self.auth_manager.get_current_token() == "test_token_123"
            assert self.auth_manager.get_current_user().username == "testuser"
            
            # Should save credentials to config file
            mock_request.assert_called_once_with(
                "POST",
                "/api/v1/auth/token/",
                json={
                    "username": "testuser",
                    "password": "testpass123",
                    "device_name": "Test Device",
                    "device_info": {"os": "Linux", "app": "Test"}
                }
            )
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        with patch.object(self.auth_manager, '_make_request') as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Invalid credentials",
                request=MagicMock(),
                response=MagicMock(status_code=400)
            )
            
            result = await self.auth_manager.login(
                username="testuser",
                password="wrongpassword"
            )
            
            assert result is False
            assert not self.auth_manager.is_authenticated()
            assert self.auth_manager.get_current_token() is None
    
    @pytest.mark.asyncio
    async def test_register_success(self):
        """Test successful user registration."""
        register_user_data = {
            "id": 2,
            "username": "newuser",
            "email": "new@example.com",
            "display_name": "New User",
            "date_joined": datetime.now().isoformat()
        }
        
        with patch.object(self.auth_manager, '_make_request') as mock_request:
            mock_request.return_value = {
                **self.mock_token_response,
                "user": register_user_data
            }
            
            result = await self.auth_manager.register(
                username="newuser",
                email="new@example.com",
                password="newpass123",
                display_name="New User",
                device_name="Test Device"
            )
            
            assert result is True
            assert self.auth_manager.is_authenticated()
            assert self.auth_manager.get_current_user().username == "newuser"
    
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self):
        """Test registration with duplicate username."""
        with patch.object(self.auth_manager, '_make_request') as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Username already exists",
                request=MagicMock(),
                response=MagicMock(status_code=400)
            )
            
            result = await self.auth_manager.register(
                username="existing",
                password="pass123"
            )
            
            assert result is False
            assert not self.auth_manager.is_authenticated()
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        """Test successful token refresh."""
        # Set up existing authentication
        await self._setup_authenticated_state()
        
        new_token_response = {
            "token": "new_token_456",
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
            "device_name": "Test Device"
        }
        
        with patch.object(self.auth_manager, '_make_request') as mock_request:
            mock_request.return_value = new_token_response
            
            result = await self.auth_manager.refresh_token()
            
            assert result is True
            assert self.auth_manager.get_current_token() == "new_token_456"
            
            # Should include Authorization header
            mock_request.assert_called_once_with(
                "POST",
                "/api/v1/auth/token/refresh/",
                headers={"Authorization": "Token test_token_123"}
            )
    
    @pytest.mark.asyncio
    async def test_refresh_token_expired(self):
        """Test refresh with expired token."""
        await self._setup_authenticated_state()
        
        with patch.object(self.auth_manager, '_make_request') as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Token has expired",
                request=MagicMock(),
                response=MagicMock(status_code=401)
            )
            
            with pytest.raises(TokenExpiredError):
                await self.auth_manager.refresh_token()
            
            # Should clear authentication state
            assert not self.auth_manager.is_authenticated()
            assert self.auth_manager.get_current_token() is None
    
    @pytest.mark.asyncio
    async def test_auto_refresh_before_expiration(self):
        """Test automatic token refresh before expiration."""
        # Set up token that expires in 30 minutes
        token_info = TokenInfo(
            token="expiring_token",
            expires_at=datetime.now() + timedelta(minutes=30),
            device_name="Test Device"
        )
        
        self.auth_manager._current_token = token_info
        self.auth_manager._current_user = UserProfile(**self.mock_user_data)
        
        new_token_response = {
            "token": "refreshed_token",
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
            "device_name": "Test Device"
        }
        
        with patch.object(self.auth_manager, '_make_request') as mock_request:
            mock_request.return_value = new_token_response
            
            # Should automatically refresh token
            token = await self.auth_manager.get_valid_token()
            
            assert token == "refreshed_token"
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_logout(self):
        """Test logout functionality."""
        await self._setup_authenticated_state()
        
        self.auth_manager.logout()
        
        assert not self.auth_manager.is_authenticated()
        assert self.auth_manager.get_current_token() is None
        assert self.auth_manager.get_current_user() is None
    
    def test_save_and_load_credentials(self):
        """Test saving and loading credentials from config file."""
        # Save credentials
        user_profile = UserProfile(**self.mock_user_data)
        token_info = TokenInfo(
            token="test_token",
            expires_at=datetime.now() + timedelta(days=7),
            device_name="Test Device"
        )
        
        self.auth_manager.save_credentials(user_profile, token_info)
        
        assert self.config_path.exists()
        
        # Load credentials
        loaded_user, loaded_token = self.auth_manager.load_credentials()
        
        assert loaded_user.username == "testuser"
        assert loaded_token.token == "test_token"
        assert loaded_token.device_name == "Test Device"
    
    def test_load_credentials_no_file(self):
        """Test loading credentials when no config file exists."""
        user, token = self.auth_manager.load_credentials()
        
        assert user is None
        assert token is None
    
    def test_load_credentials_invalid_json(self):
        """Test loading credentials from invalid JSON file."""
        # Write invalid JSON
        self.config_path.write_text("invalid json content")
        
        user, token = self.auth_manager.load_credentials()
        
        assert user is None
        assert token is None
    
    def test_multiple_user_profiles(self):
        """Test managing multiple user profiles."""
        # Save first user
        user1 = UserProfile(
            id=1,
            username="user1",
            email="user1@example.com",
            display_name="User One",
            date_joined=datetime.now()
        )
        token1 = TokenInfo(
            token="token1",
            expires_at=datetime.now() + timedelta(days=7),
            device_name="Device 1"
        )
        
        self.auth_manager.save_profile("user1", user1, token1)
        
        # Save second user
        user2 = UserProfile(
            id=2,
            username="user2", 
            email="user2@example.com",
            display_name="User Two",
            date_joined=datetime.now()
        )
        token2 = TokenInfo(
            token="token2",
            expires_at=datetime.now() + timedelta(days=7),
            device_name="Device 2"
        )
        
        self.auth_manager.save_profile("user2", user2, token2)
        
        # Load profiles
        profiles = self.auth_manager.get_saved_profiles()
        
        assert len(profiles) == 2
        assert "user1" in profiles
        assert "user2" in profiles
        
        # Switch to profile
        success = self.auth_manager.switch_profile("user2")
        
        assert success is True
        assert self.auth_manager.is_authenticated()
        assert self.auth_manager.get_current_user().username == "user2"
    
    def test_token_expiration_check(self):
        """Test token expiration validation."""
        # Valid token
        valid_token = TokenInfo(
            token="valid_token",
            expires_at=datetime.now() + timedelta(hours=1),
            device_name="Test Device"
        )
        
        assert not self.auth_manager._is_token_expired(valid_token)
        
        # Expired token
        expired_token = TokenInfo(
            token="expired_token",
            expires_at=datetime.now() - timedelta(hours=1),
            device_name="Test Device"
        )
        
        assert self.auth_manager._is_token_expired(expired_token)
    
    def test_token_needs_refresh(self):
        """Test token refresh threshold check."""
        # Token expiring in 10 minutes (needs refresh)
        expiring_token = TokenInfo(
            token="expiring_token",
            expires_at=datetime.now() + timedelta(minutes=10),
            device_name="Test Device"
        )
        
        assert self.auth_manager._token_needs_refresh(expiring_token)
        
        # Token expiring in 2 hours (doesn't need refresh)
        fresh_token = TokenInfo(
            token="fresh_token",
            expires_at=datetime.now() + timedelta(hours=2),
            device_name="Test Device"
        )
        
        assert not self.auth_manager._token_needs_refresh(fresh_token)
    
    async def _setup_authenticated_state(self):
        """Helper method to set up authenticated state."""
        user_profile = UserProfile(**self.mock_user_data)
        token_info = TokenInfo(
            token="test_token_123",
            expires_at=datetime.now() + timedelta(days=7),
            device_name="Test Device"
        )
        
        self.auth_manager._current_user = user_profile
        self.auth_manager._current_token = token_info


class TestAuthManagerIntegration:
    """Integration tests for AuthManager with API client."""
    
    def setup_method(self):
        """Set up test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "auth_config.json"
        
        self.auth_manager = AuthManager(
            base_url="http://localhost:8001",
            config_file=str(self.config_path)
        )
    
    @pytest.mark.asyncio
    async def test_authenticated_request(self):
        """Test making authenticated requests."""
        # Set up authentication
        user_profile = UserProfile(
            id=1,
            username="testuser",
            email="test@example.com", 
            display_name="Test User",
            date_joined=datetime.now()
        )
        token_info = TokenInfo(
            token="valid_token",
            expires_at=datetime.now() + timedelta(days=7),
            device_name="Test Device"
        )
        
        self.auth_manager._current_user = user_profile
        self.auth_manager._current_token = token_info
        
        with patch.object(self.auth_manager, '_client') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"result": "success"}
            mock_client.request = AsyncMock(return_value=mock_response)
            
            result = await self.auth_manager.make_authenticated_request(
                "GET", "/api/v1/users/"
            )
            
            assert result == {"result": "success"}
            
            # Should include Authorization header
            mock_client.request.assert_called_once_with(
                "GET",
                "/api/v1/users/",
                headers={"Authorization": "Token valid_token"}
            )
    
    @pytest.mark.asyncio
    async def test_authenticated_request_with_refresh(self):
        """Test authenticated request that triggers token refresh."""
        # Set up token that needs refresh
        user_profile = UserProfile(
            id=1,
            username="testuser",
            email="test@example.com",
            display_name="Test User", 
            date_joined=datetime.now()
        )
        token_info = TokenInfo(
            token="expiring_token",
            expires_at=datetime.now() + timedelta(minutes=10),
            device_name="Test Device"
        )
        
        self.auth_manager._current_user = user_profile
        self.auth_manager._current_token = token_info
        
        new_token_response = {
            "token": "refreshed_token",
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
            "device_name": "Test Device"
        }
        
        with patch.object(self.auth_manager, '_client') as mock_client:
            # Mock refresh response first, then actual request response
            refresh_response = MagicMock()
            refresh_response.raise_for_status.return_value = None
            refresh_response.json.return_value = new_token_response
            
            request_response = MagicMock()
            request_response.raise_for_status.return_value = None
            request_response.json.return_value = {"result": "success"}
            
            # Set up async mock to return different responses for different calls
            mock_client.request = AsyncMock(side_effect=[refresh_response, request_response])
            
            result = await self.auth_manager.make_authenticated_request(
                "GET", "/api/v1/users/"
            )
            
            assert result == {"result": "success"} 
            
            # Should have made two requests: refresh first, then actual request
            assert mock_client.request.call_count == 2
            
            # First call should be refresh
            first_call = mock_client.request.call_args_list[0]
            assert first_call[0] == ("POST", "/api/v1/auth/token/refresh/")
            assert first_call[1]["headers"]["Authorization"] == "Token expiring_token"
            
            # Second call should be actual request with new token
            second_call = mock_client.request.call_args_list[1]
            assert second_call[0] == ("GET", "/api/v1/users/")
            assert second_call[1]["headers"]["Authorization"] == "Token refreshed_token"