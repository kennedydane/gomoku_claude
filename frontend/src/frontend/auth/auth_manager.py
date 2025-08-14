"""
Authentication Manager for frontend applications.

This module provides comprehensive authentication management including
token handling, user session management, and secure credential storage.
"""

import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

import httpx
from loguru import logger

from .models import TokenInfo, UserProfile, AuthConfig
from .exceptions import AuthError, TokenExpiredError, InvalidCredentialsError, RegistrationError, ConfigurationError


class AuthManager:
    """
    Manages authentication state and operations for frontend applications.
    
    Provides functionality for:
    - User login and registration
    - Token refresh and management
    - Credential persistence
    - Multiple user profile support
    """
    
    # Token refresh threshold (refresh if expires within this time)
    TOKEN_REFRESH_THRESHOLD = timedelta(hours=1)
    
    def __init__(self, base_url: str = "http://localhost:8001", config_file: Optional[str] = None):
        """
        Initialize the authentication manager.
        
        Args:
            base_url: Base URL of the authentication server
            config_file: Path to configuration file for credential storage
        """
        self.base_url = base_url.rstrip("/")
        self.config_file = Path(config_file) if config_file else Path.home() / ".gomoku" / "auth_config.json"
        
        # Authentication state
        self._current_user: Optional[UserProfile] = None
        self._current_token: Optional[TokenInfo] = None
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"Initialized AuthManager for {self.base_url}")
        logger.debug(f"Config file: {self.config_file}")
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client and clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("AuthManager HTTP client closed")
    
    # Authentication state methods
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        return (
            self._current_user is not None and 
            self._current_token is not None and 
            not self._is_token_expired(self._current_token)
        )
    
    def get_current_token(self) -> Optional[str]:
        """Get current authentication token."""
        if self._current_token and not self._is_token_expired(self._current_token):
            return self._current_token.token
        return None
    
    def get_current_user(self) -> Optional[UserProfile]:
        """Get current authenticated user."""
        return self._current_user
    
    # Authentication operations
    async def login(
        self, 
        username: str, 
        password: str,
        device_name: str = "",
        device_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Authenticate user with username and password.
        
        Args:
            username: User's username
            password: User's password
            device_name: Optional device identifier
            device_info: Optional device information
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            payload = {
                "username": username,
                "password": password,
                "device_name": device_name or "Desktop App",
                "device_info": device_info or {}
            }
            
            response_data = await self._make_request("POST", "/api/v1/auth/token/", json=payload)
            
            # Parse response
            user_data = response_data["user"]
            token_data = {
                "token": response_data["token"],
                "expires_at": datetime.fromisoformat(response_data["expires_at"].replace("Z", "+00:00")),
                "device_name": response_data.get("device_name", device_name)
            }
            
            # Set authentication state
            self._current_user = UserProfile(**user_data)
            self._current_token = TokenInfo(**token_data)
            
            # Save credentials
            self.save_credentials(self._current_user, self._current_token)
            
            logger.info(f"Login successful for user: {username}")
            return True
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (400, 401):
                logger.warning(f"Login failed for user {username}: Invalid credentials")
                return False
            else:
                logger.error(f"Login failed for user {username}: HTTP {e.response.status_code}")
                raise AuthError(f"Login failed: {e}")
        except Exception as e:
            logger.error(f"Login failed for user {username}: {e}")
            raise AuthError(f"Login failed: {e}")
    
    async def register(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None,
        device_name: str = "",
        device_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register new user account.
        
        Args:
            username: Desired username
            password: User's password
            email: Optional email address
            display_name: Optional display name
            device_name: Optional device identifier
            device_info: Optional device information
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            payload = {
                "username": username,
                "password": password,
                "device_name": device_name or "Desktop App",
                "device_info": device_info or {}
            }
            
            if email:
                payload["email"] = email
            if display_name:
                payload["display_name"] = display_name
            
            response_data = await self._make_request("POST", "/api/v1/auth/register/", json=payload)
            
            # Parse response
            user_data = response_data["user"]
            token_data = {
                "token": response_data["token"],
                "expires_at": datetime.fromisoformat(response_data["expires_at"].replace("Z", "+00:00")),
                "device_name": response_data.get("device_name", device_name)
            }
            
            # Set authentication state
            self._current_user = UserProfile(**user_data)
            self._current_token = TokenInfo(**token_data)
            
            # Save credentials
            self.save_credentials(self._current_user, self._current_token)
            
            logger.info(f"Registration successful for user: {username}")
            return True
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                logger.warning(f"Registration failed for user {username}: {e}")
                return False
            else:
                logger.error(f"Registration failed for user {username}: HTTP {e.response.status_code}")
                raise RegistrationError(f"Registration failed: {e}")
        except Exception as e:
            logger.error(f"Registration failed for user {username}: {e}")
            raise RegistrationError(f"Registration failed: {e}")
    
    async def refresh_token(self) -> bool:
        """
        Refresh current authentication token.
        
        Returns:
            True if refresh successful
            
        Raises:
            TokenExpiredError: If token cannot be refreshed
        """
        if not self._current_token:
            raise TokenExpiredError("No token to refresh")
        
        try:
            headers = {"Authorization": f"Token {self._current_token.token}"}
            response_data = await self._make_request(
                "POST", 
                "/api/v1/auth/token/refresh/", 
                headers=headers
            )
            
            # Update token info
            token_data = {
                "token": response_data["token"],
                "expires_at": datetime.fromisoformat(response_data["expires_at"].replace("Z", "+00:00")),
                "device_name": response_data.get("device_name", self._current_token.device_name),
                "device_info": getattr(self._current_token, 'device_info', {})
            }
            
            self._current_token = TokenInfo(**token_data)
            
            # Save updated credentials
            if self._current_user:
                self.save_credentials(self._current_user, self._current_token)
            
            logger.info("Token refresh successful")
            return True
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                logger.warning("Token refresh failed: Token expired")
                self.logout()
                raise TokenExpiredError("Token has expired and cannot be refreshed")
            else:
                logger.error(f"Token refresh failed: HTTP {e.response.status_code}")
                raise AuthError(f"Token refresh failed: {e}")
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise AuthError(f"Token refresh failed: {e}")
    
    async def get_valid_token(self) -> str:
        """
        Get a valid authentication token, refreshing if necessary.
        
        Returns:
            Valid authentication token
            
        Raises:
            TokenExpiredError: If token cannot be refreshed
        """
        if not self._current_token:
            raise TokenExpiredError("No authentication token available")
        
        # Check if token needs refresh
        if self._token_needs_refresh(self._current_token):
            await self.refresh_token()
        
        if not self._current_token:
            raise TokenExpiredError("Failed to obtain valid token")
        
        return self._current_token.token
    
    def logout(self) -> None:
        """Logout current user and clear authentication state."""
        self._current_user = None
        self._current_token = None
        logger.info("User logged out")
    
    # Configuration and credential management
    def save_credentials(self, user: UserProfile, token: TokenInfo) -> None:
        """
        Save user credentials to configuration file.
        
        Args:
            user: User profile information
            token: Token information
        """
        try:
            # Ensure config directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config_data = {
                "user": user.model_dump(mode='json'),
                "token": {
                    "token": token.token,
                    "expires_at": token.expires_at.isoformat(),
                    "device_name": token.device_name,
                    "device_info": getattr(token, 'device_info', {})
                }
            }
            
            with self.config_file.open('w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.debug(f"Credentials saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    def load_credentials(self) -> Tuple[Optional[UserProfile], Optional[TokenInfo]]:
        """
        Load user credentials from configuration file.
        
        Returns:
            Tuple of (user_profile, token_info) or (None, None) if not found
        """
        try:
            if not self.config_file.exists():
                return None, None
            
            with self.config_file.open('r') as f:
                config_data = json.load(f)
            
            # Parse user data
            user_data = config_data["user"]
            user_data["date_joined"] = datetime.fromisoformat(user_data["date_joined"])
            user = UserProfile(**user_data)
            
            # Parse token data
            token_data = config_data["token"]
            token_data["expires_at"] = datetime.fromisoformat(token_data["expires_at"])
            token = TokenInfo(**token_data)
            
            logger.debug("Credentials loaded from configuration")
            return user, token
            
        except Exception as e:
            logger.warning(f"Failed to load credentials: {e}")
            return None, None
    
    def save_profile(self, profile_name: str, user: UserProfile, token: TokenInfo) -> None:
        """
        Save a named user profile.
        
        Args:
            profile_name: Name for the profile
            user: User profile information
            token: Token information
        """
        try:
            # Load existing config
            config = self._load_config()
            
            # Save profile
            config.profiles[profile_name] = {
                "user": user.model_dump(mode='json'),
                "token": {
                    "token": token.token,
                    "expires_at": token.expires_at.isoformat(),
                    "device_name": token.device_name,
                    "device_info": getattr(token, 'device_info', {})
                }
            }
            
            self._save_config(config)
            logger.debug(f"Profile '{profile_name}' saved")
            
        except Exception as e:
            logger.error(f"Failed to save profile '{profile_name}': {e}")
    
    def get_saved_profiles(self) -> List[str]:
        """Get list of saved profile names."""
        try:
            config = self._load_config()
            return list(config.profiles.keys())
        except Exception as e:
            logger.error(f"Failed to get saved profiles: {e}")
            return []
    
    def switch_profile(self, profile_name: str) -> bool:
        """
        Switch to a saved user profile.
        
        Args:
            profile_name: Name of profile to switch to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self._load_config()
            
            if profile_name not in config.profiles:
                logger.warning(f"Profile '{profile_name}' not found")
                return False
            
            profile_data = config.profiles[profile_name]
            
            # Parse user data
            user_data = profile_data["user"]
            user_data["date_joined"] = datetime.fromisoformat(user_data["date_joined"])
            user = UserProfile(**user_data)
            
            # Parse token data
            token_data = profile_data["token"]
            token_data["expires_at"] = datetime.fromisoformat(token_data["expires_at"])
            token = TokenInfo(**token_data)
            
            # Check if token is still valid
            if self._is_token_expired(token):
                logger.warning(f"Token for profile '{profile_name}' has expired")
                return False
            
            # Set authentication state
            self._current_user = user
            self._current_token = token
            
            # Update current profile
            config.current_profile = profile_name
            self._save_config(config)
            
            logger.info(f"Switched to profile: {profile_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch to profile '{profile_name}': {e}")
            return False
    
    # Token validation methods
    def _is_token_expired(self, token: TokenInfo) -> bool:
        """Check if token has expired."""
        return datetime.now() >= token.expires_at
    
    def _token_needs_refresh(self, token: TokenInfo) -> bool:
        """Check if token needs refresh (expires within threshold)."""
        return datetime.now() + self.TOKEN_REFRESH_THRESHOLD >= token.expires_at
    
    # HTTP request methods
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to authentication server.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional arguments for httpx
            
        Returns:
            Response data as dictionary
        """
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError:
            # Re-raise HTTP errors for caller to handle
            raise
        except Exception as e:
            logger.error(f"Request failed {method} {endpoint}: {e}")
            raise AuthError(f"Request failed: {e}")
    
    async def make_authenticated_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make authenticated HTTP request, automatically handling token refresh.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional arguments for httpx
            
        Returns:
            Response data as dictionary
        """
        # Ensure we have a valid token
        token = await self.get_valid_token()
        
        # Add Authorization header
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Token {token}'
        kwargs['headers'] = headers
        
        return await self._make_request(method, endpoint, **kwargs)
    
    # Configuration file management
    def _load_config(self) -> AuthConfig:
        """Load authentication configuration."""
        try:
            if not self.config_file.exists():
                return AuthConfig()
            
            with self.config_file.open('r') as f:
                data = json.load(f)
            
            return AuthConfig(**data)
            
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            return AuthConfig()
    
    def _save_config(self, config: AuthConfig) -> None:
        """Save authentication configuration."""
        try:
            # Ensure config directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with self.config_file.open('w') as f:
                json.dump(config.model_dump(mode='json'), f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise ConfigurationError(f"Failed to save config: {e}")