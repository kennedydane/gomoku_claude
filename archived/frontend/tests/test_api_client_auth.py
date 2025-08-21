"""
Tests for API client authentication integration.

Following TDD methodology: RED-GREEN-REFACTOR
These tests define the behavior for authenticated API client operations.
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

from frontend.client.api_client import APIClient, UserInfo, GameInfo, RuleSetInfo
from frontend.auth.auth_manager import AuthManager
from frontend.auth.exceptions import TokenExpiredError


class TestAPIClientAuthentication:
    """Test APIClient with authentication integration."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        # Create temporary directory for config files
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "auth_config.json"
        
        # Initialize APIClient with auth manager
        self.api_client = APIClient(
            base_url="http://localhost:8001",
            auth_manager=AuthManager(
                base_url="http://localhost:8001",
                config_file=str(self.config_path)
            )
        )
        
        # Mock user and token data
        self.mock_user_data = {
            "id": 1,
            "username": "testuser",
            "display_name": "Test User"
        }
        
        self.mock_game_data = {
            "id": "game123",
            "black_player_id": 1,
            "white_player_id": 2,
            "ruleset_id": 1,
            "status": "active",
            "current_player": "black",
            "board_state": {
                "board": [["" for _ in range(15)] for _ in range(15)],
                "size": 15
            },
            "winner_id": None,
            "move_count": 0,
            "started_at": None,
            "finished_at": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_game_over": False,
            "can_start": True,
            "black_player": self.mock_user_data,
            "white_player": {"id": 2, "username": "opponent", "display_name": "Opponent"},
            "winner": None,
            "ruleset": {"id": 1, "name": "Standard", "board_size": 15, "allow_overlines": True}
        }
    
    def teardown_method(self):
        """Clean up after each test."""
        if self.config_path.exists():
            self.config_path.unlink()
    
    @pytest.mark.asyncio
    async def test_api_client_with_auth_manager(self):
        """Test APIClient initialization with AuthManager."""
        # RED: This will fail because APIClient doesn't support auth_manager parameter yet
        assert self.api_client.auth_manager is not None
        assert isinstance(self.api_client.auth_manager, AuthManager)
    
    @pytest.mark.asyncio
    async def test_authenticated_get_users(self):
        """Test get_users with authentication."""
        # Set up authenticated state
        await self._setup_authenticated_state()
        
        with patch.object(self.api_client.auth_manager, 'make_authenticated_request') as mock_auth_request:
            mock_auth_request.return_value = [self.mock_user_data]
            
            users = await self.api_client.get_users()
            
            assert len(users) == 1
            assert users[0].username == "testuser"
            
            # Should use authenticated request
            mock_auth_request.assert_called_once_with("GET", "/api/v1/users/")
    
    @pytest.mark.asyncio
    async def test_authenticated_create_user(self):
        """Test create_user with authentication."""
        await self._setup_authenticated_state()
        
        with patch.object(self.api_client.auth_manager, 'make_authenticated_request') as mock_auth_request:
            mock_auth_request.return_value = self.mock_user_data
            
            user = await self.api_client.create_user(
                username="newuser",
                email="new@example.com",
                display_name="New User"
            )
            
            assert user.username == "testuser"
            
            # Should use authenticated request with payload
            mock_auth_request.assert_called_once_with(
                "POST", 
                "/api/v1/users/",
                json={
                    "username": "newuser",
                    "email": "new@example.com",
                    "display_name": "New User"
                }
            )
    
    @pytest.mark.asyncio
    async def test_authenticated_create_game(self):
        """Test create_game with authentication."""
        await self._setup_authenticated_state()
        
        with patch.object(self.api_client.auth_manager, 'make_authenticated_request') as mock_auth_request:
            mock_auth_request.return_value = self.mock_game_data
            
            game = await self.api_client.create_game(
                black_player_id=1,
                white_player_id=2,
                ruleset_id=1
            )
            
            assert game.id == "game123"
            assert game.black_player_id == 1
            
            # Should use authenticated request
            mock_auth_request.assert_called_once_with(
                "POST",
                "/api/v1/games/",
                json={
                    "black_player_id": 1,
                    "white_player_id": 2,
                    "ruleset_id": 1
                }
            )
    
    @pytest.mark.asyncio
    async def test_authenticated_make_move(self):
        """Test make_move with authentication."""
        await self._setup_authenticated_state()
        
        move_data = {
            "id": 1,
            "game_id": "game123",
            "player_id": 1,
            "move_number": 1,
            "row": 7,
            "col": 7,
            "player_color": "black",
            "is_winning_move": False,
            "created_at": datetime.now().isoformat()
        }
        
        with patch.object(self.api_client.auth_manager, 'make_authenticated_request') as mock_auth_request:
            mock_auth_request.return_value = move_data
            
            move = await self.api_client.make_move(
                game_id="game123",
                player_id=1,
                row=7,
                col=7
            )
            
            assert move.row == 7
            assert move.col == 7
            
            # Should use authenticated request
            mock_auth_request.assert_called_once_with(
                "POST",
                "/api/v1/games/game123/moves/",
                json={
                    "player_id": 1,
                    "row": 7,
                    "col": 7
                }
            )
    
    @pytest.mark.asyncio
    async def test_fallback_to_unauthenticated_requests(self):
        """Test fallback to unauthenticated requests when not authenticated."""
        # Don't set up authentication
        
        with patch.object(self.api_client, 'client') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = []
            mock_client.get = AsyncMock(return_value=mock_response)
            
            # Should fallback to unauthenticated request
            response = await self.api_client.get_rulesets()
            
            assert response == []
            
            # Should use regular client, not auth manager
            mock_client.get.assert_called_once_with("/api/v1/rulesets/")
    
    @pytest.mark.asyncio
    async def test_health_check_no_auth_required(self):
        """Test health check doesn't require authentication."""
        with patch.object(self.api_client, 'client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await self.api_client.health_check()
            
            assert result is True
            
            # Should use regular client for health check
            mock_client.get.assert_called_once_with("/")
    
    @pytest.mark.asyncio
    async def test_auto_token_refresh_on_401(self):
        """Test automatic token refresh when 401 error occurs."""
        await self._setup_authenticated_state()
        
        with patch.object(self.api_client.auth_manager, 'make_authenticated_request') as mock_auth_request:
            # First call returns 401, second call succeeds after refresh
            mock_auth_request.side_effect = [
                TokenExpiredError("Token expired"),
                [self.mock_user_data]
            ]
            
            with patch.object(self.api_client.auth_manager, 'refresh_token') as mock_refresh:
                mock_refresh.return_value = True
                
                users = await self.api_client.get_users()
                
                assert len(users) == 1
                assert users[0].username == "testuser"
                
                # Should have attempted refresh and retried
                mock_refresh.assert_called_once()
                assert mock_auth_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_login_integration(self):
        """Test login integration with API client."""
        with patch.object(self.api_client.auth_manager, 'login') as mock_login:
            mock_login.return_value = True
            
            result = await self.api_client.login(
                username="testuser",
                password="testpass"
            )
            
            assert result is True
            
            # Should call auth manager login
            mock_login.assert_called_once_with(
                username="testuser",
                password="testpass",
                device_name="Desktop App",
                device_info={}
            )
    
    @pytest.mark.asyncio
    async def test_register_integration(self):
        """Test user registration integration."""
        with patch.object(self.api_client.auth_manager, 'register') as mock_register:
            mock_register.return_value = True
            
            result = await self.api_client.register_user(
                username="newuser",
                password="newpass",
                email="new@example.com"
            )
            
            assert result is True
            
            # Should call auth manager register
            mock_register.assert_called_once_with(
                username="newuser",
                password="newpass",
                email="new@example.com",
                display_name=None,
                device_name="Desktop App",
                device_info={}
            )
    
    @pytest.mark.asyncio
    async def test_logout_integration(self):
        """Test logout integration."""
        await self._setup_authenticated_state()
        
        self.api_client.logout()
        
        # Should clear authentication state
        assert not self.api_client.auth_manager.is_authenticated()
    
    @pytest.mark.asyncio
    async def test_is_authenticated_property(self):
        """Test is_authenticated property."""
        # Initially not authenticated
        assert not self.api_client.is_authenticated
        
        # Set up authentication
        await self._setup_authenticated_state()
        
        assert self.api_client.is_authenticated
    
    @pytest.mark.asyncio
    async def test_current_user_property(self):
        """Test current_user property."""
        # Initially no user
        assert self.api_client.current_user is None
        
        # Set up authentication
        await self._setup_authenticated_state()
        
        assert self.api_client.current_user is not None
        assert self.api_client.current_user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_close_with_auth_manager(self):
        """Test closing API client also closes auth manager."""
        with patch.object(self.api_client.auth_manager, 'close') as mock_auth_close:
            with patch.object(self.api_client, '_client') as mock_client:
                mock_client.aclose = AsyncMock()
                
                await self.api_client.close()
                
                # Should close both client and auth manager
                mock_client.aclose.assert_called_once()
                mock_auth_close.assert_called_once()
    
    async def _setup_authenticated_state(self):
        """Helper method to set up authenticated state."""
        from frontend.auth.models import UserProfile, TokenInfo
        
        user_profile = UserProfile(
            id=1,
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            date_joined=datetime.now()
        )
        
        token_info = TokenInfo(
            token="test_token_123",
            expires_at=datetime.now() + timedelta(days=7),
            device_name="Test Device"
        )
        
        self.api_client.auth_manager._current_user = user_profile
        self.api_client.auth_manager._current_token = token_info


class TestAPIClientAuthErrorHandling:
    """Test error handling in authenticated API client operations."""
    
    def setup_method(self):
        """Set up test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "auth_config.json"
        
        self.api_client = APIClient(
            base_url="http://localhost:8001",
            auth_manager=AuthManager(
                base_url="http://localhost:8001",
                config_file=str(self.config_path)
            )
        )
    
    @pytest.mark.asyncio
    async def test_retry_on_token_expired_error(self):
        """Test retry logic when TokenExpiredError occurs."""
        await self._setup_authenticated_state()
        
        with patch.object(self.api_client.auth_manager, 'make_authenticated_request') as mock_auth_request:
            # First call fails with token expired, second succeeds
            mock_auth_request.side_effect = [
                TokenExpiredError("Token expired"),
                {"result": "success"}
            ]
            
            with patch.object(self.api_client.auth_manager, 'refresh_token') as mock_refresh:
                mock_refresh.return_value = True
                
                # Should retry after token refresh
                result = await self.api_client._make_authenticated_request("GET", "/test")
                
                assert result == {"result": "success"}
                mock_refresh.assert_called_once()
                assert mock_auth_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_on_other_errors(self):
        """Test no retry for non-token errors."""
        await self._setup_authenticated_state()
        
        with patch.object(self.api_client.auth_manager, 'make_authenticated_request') as mock_auth_request:
            mock_auth_request.side_effect = httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500)
            )
            
            with pytest.raises(httpx.HTTPStatusError):
                await self.api_client._make_authenticated_request("GET", "/test")
            
            # Should only try once
            assert mock_auth_request.call_count == 1
    
    async def _setup_authenticated_state(self):
        """Helper method to set up authenticated state."""
        from frontend.auth.models import UserProfile, TokenInfo
        
        user_profile = UserProfile(
            id=1,
            username="testuser",
            email="test@example.com",
            display_name="Test User",
            date_joined=datetime.now()
        )
        
        token_info = TokenInfo(
            token="test_token_123",
            expires_at=datetime.now() + timedelta(days=7),
            device_name="Test Device"
        )
        
        self.api_client.auth_manager._current_user = user_profile
        self.api_client.auth_manager._current_token = token_info