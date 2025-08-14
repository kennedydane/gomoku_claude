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
from .config_manager import ConfigManager


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
    
    def __init__(
        self, 
        base_url: Optional[str] = None, 
        config_file: Optional[str] = None, 
        env_file: Optional[str] = None
    ):
        """
        Initialize the authentication manager.
        
        Args:
            base_url: Base URL of the authentication server (overrides config)
            config_file: Path to configuration file for credential storage
            env_file: Path to .env file for environment configuration
        """
        # Initialize configuration manager
        self.config_manager = ConfigManager(config_file=config_file, env_file=env_file)
        self.config = self.config_manager.load_config()
        
        # Use provided base_url or fall back to config
        self.base_url = (base_url or self.config.base_url).rstrip("/")
        
        # Legacy config file path for backward compatibility
        self.config_file = self.config_manager.config_file
        
        # Authentication state
        self._current_user: Optional[UserProfile] = None
        self._current_token: Optional[TokenInfo] = None
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"Initialized AuthManager for {self.base_url}")
        logger.debug(f"Config file: {self.config_file}")
        
        # Apply configuration settings
        self._apply_config_settings()
    
    def _apply_config_settings(self) -> None:
        """Apply configuration settings to the auth manager."""
        # Apply logging settings
        if self.config.log_level:
            logger.remove()  # Remove default handler
            logger.add(
                level=self.config.log_level,
                sink=lambda msg: print(msg, end="")  # Use print for console output
            )
        
        # Apply token refresh threshold if configured
        if hasattr(self.config, 'token_refresh_hours'):
            self.TOKEN_REFRESH_THRESHOLD = timedelta(hours=self.config.token_refresh_hours)
        
        logger.debug(f"Applied configuration settings: log_level={self.config.log_level}")
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.config.timeout
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
        if not self.config.save_credentials:
            logger.debug("Credential saving is disabled in configuration")
            return
            
        try:
            # Save as default profile and also update current session
            self.save_profile("default", user, token)
            
            # Update current profile to default if not set
            if not self.config.current_profile:
                self.config.current_profile = "default"
                self.config_manager.save_config(self.config)
            
            logger.debug("Credentials saved to configuration")
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    def load_credentials(self) -> Tuple[Optional[UserProfile], Optional[TokenInfo]]:
        """
        Load user credentials from configuration file.
        
        Returns:
            Tuple of (user_profile, token_info) or (None, None) if not found
        """
        try:
            # Reload config to get latest state
            self.config = self.config_manager.load_config()
            
            # Try to load current profile first
            if self.config.current_profile:
                user, token = self.config_manager.load_profile(self.config.current_profile, self.config)
                if user and token:
                    logger.debug(f"Credentials loaded from profile: {self.config.current_profile}")
                    return user, token
            
            # Fall back to default profile
            user, token = self.config_manager.load_profile("default", self.config)
            if user and token:
                logger.debug("Credentials loaded from default profile")
                return user, token
            
            logger.debug("No saved credentials found")
            return None, None
            
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
            # Reload config to get latest state
            self.config = self.config_manager.load_config()
            
            # Save profile using config manager
            self.config_manager.save_profile(profile_name, user, token, self.config)
            
            # Save updated config
            self.config_manager.save_config(self.config)
            
            logger.debug(f"Profile '{profile_name}' saved")
            
        except Exception as e:
            logger.error(f"Failed to save profile '{profile_name}': {e}")
    
    def get_saved_profiles(self) -> List[str]:
        """Get list of saved profile names."""
        try:
            # Reload config to get latest state
            self.config = self.config_manager.load_config()
            return self.config_manager.get_profile_names(self.config)
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
            # Reload config to get latest state
            self.config = self.config_manager.load_config()
            
            # Load profile using config manager
            user, token = self.config_manager.load_profile(profile_name, self.config)
            
            if user is None or token is None:
                logger.warning(f"Profile '{profile_name}' not found")
                return False
            
            # Check if token is still valid
            if self._is_token_expired(token):
                logger.warning(f"Token for profile '{profile_name}' has expired")
                return False
            
            # Set authentication state
            self._current_user = user
            self._current_token = token
            
            # Update current profile
            self.config.current_profile = profile_name
            self.config_manager.save_config(self.config)
            
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
    
