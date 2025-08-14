"""
Configuration Manager for frontend applications.

This module provides comprehensive configuration management including
JSON config files, .env file support, and profile management.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List, Union

from loguru import logger
from pydantic import ValidationError

from .models import AuthConfig, UserProfile, TokenInfo
from .exceptions import ConfigurationError


class ConfigManager:
    """
    Manages application configuration from multiple sources.
    
    Provides functionality for:
    - Loading configuration from JSON files and environment variables
    - Environment variable override support with type conversion
    - User profile management
    - Configuration validation
    - Backup and restore functionality
    """
    
    # Environment variable prefix
    ENV_PREFIX = "GOMOKU_"
    
    # Environment variable mappings
    ENV_MAPPINGS = {
        "GOMOKU_BASE_URL": ("base_url", str),
        "GOMOKU_TIMEOUT": ("timeout", float),
        "GOMOKU_AUTO_REFRESH_TOKEN": ("auto_refresh_token", bool),
        "GOMOKU_MAX_RETRIES": ("max_retries", int),
        "GOMOKU_LOG_LEVEL": ("log_level", str),
        "GOMOKU_DEBUG_MODE": ("debug_mode", bool),
        "GOMOKU_SAVE_CREDENTIALS": ("save_credentials", bool),
        "GOMOKU_ENCRYPT_CREDENTIALS": ("encrypt_credentials", bool),
        "GOMOKU_DEFAULT_DEVICE_NAME": ("default_device_info.device_name", str),
    }
    
    def __init__(
        self, 
        config_file: Optional[str] = None, 
        env_file: Optional[str] = None
    ):
        """
        Initialize the configuration manager.
        
        Args:
            config_file: Path to JSON configuration file
            env_file: Path to .env file
        """
        self.config_file = Path(config_file) if config_file else Path.home() / ".gomoku" / "config.json"
        self.env_file = Path(env_file) if env_file else Path.cwd() / ".env"
        
        logger.debug(f"ConfigManager initialized - Config: {self.config_file}, Env: {self.env_file}")
    
    def load_config(self, validate: bool = False) -> AuthConfig:
        """
        Load configuration from JSON file and environment variables.
        
        Args:
            validate: Whether to validate configuration values
            
        Returns:
            Loaded configuration object
            
        Raises:
            ConfigurationError: If validation fails
        """
        # Start with default config
        config_data = {}
        
        # Load from JSON file if it exists
        if self.config_file.exists():
            try:
                with self.config_file.open('r') as f:
                    config_data = json.load(f)
                logger.debug(f"Loaded configuration from {self.config_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load JSON config: {e}")
                config_data = {}
        
        # Load environment variables from .env file if it exists
        env_vars = self._load_env_file()
        
        # Override with environment variables
        env_overrides = self._process_env_variables(env_vars)
        config_data.update(env_overrides)
        
        # Create config object
        try:
            config = AuthConfig(**config_data)
        except ValidationError as e:
            if validate:
                raise ConfigurationError(f"Invalid configuration: {e}")
            else:
                logger.warning(f"Configuration validation failed, using defaults: {e}")
                config = AuthConfig()
        
        # Validate configuration if requested
        if validate:
            self._validate_config(config)
        
        return config
    
    def save_config(self, config: AuthConfig) -> None:
        """
        Save configuration to JSON file.
        
        Args:
            config: Configuration object to save
        """
        try:
            # Ensure config directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with self.config_file.open('w') as f:
                json.dump(config.model_dump(mode='json'), f, indent=2)
            
            logger.debug(f"Configuration saved to {self.config_file}")
            
        except (IOError, json.JSONEncodeError) as e:
            logger.error(f"Failed to save configuration: {e}")
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def save_profile(
        self, 
        profile_name: str, 
        user: UserProfile, 
        token: TokenInfo, 
        config: AuthConfig
    ) -> None:
        """
        Save a user profile to configuration.
        
        Args:
            profile_name: Name for the profile
            user: User profile information
            token: Token information
            config: Configuration object to update
        """
        try:
            profile_data = {
                "user": user.model_dump(mode='json'),
                "token": {
                    "token": token.token,
                    "expires_at": token.expires_at.isoformat(),
                    "device_name": token.device_name,
                    "device_info": getattr(token, 'device_info', {})
                }
            }
            
            config.profiles[profile_name] = profile_data
            logger.debug(f"Profile '{profile_name}' saved")
            
        except Exception as e:
            logger.error(f"Failed to save profile '{profile_name}': {e}")
            raise ConfigurationError(f"Failed to save profile: {e}")
    
    def load_profile(
        self, 
        profile_name: str, 
        config: AuthConfig
    ) -> Tuple[Optional[UserProfile], Optional[TokenInfo]]:
        """
        Load a user profile from configuration.
        
        Args:
            profile_name: Name of profile to load
            config: Configuration object
            
        Returns:
            Tuple of (user_profile, token_info) or (None, None) if not found
        """
        try:
            if profile_name not in config.profiles:
                return None, None
            
            profile_data = config.profiles[profile_name]
            
            # Parse user data
            user_data = profile_data["user"]
            user_data["date_joined"] = datetime.fromisoformat(user_data["date_joined"])
            user = UserProfile(**user_data)
            
            # Parse token data
            token_data = profile_data["token"]
            token_data["expires_at"] = datetime.fromisoformat(token_data["expires_at"])
            token = TokenInfo(**token_data)
            
            logger.debug(f"Profile '{profile_name}' loaded")
            return user, token
            
        except Exception as e:
            logger.warning(f"Failed to load profile '{profile_name}': {e}")
            return None, None
    
    def get_profile_names(self, config: AuthConfig) -> List[str]:
        """
        Get list of saved profile names.
        
        Args:
            config: Configuration object
            
        Returns:
            List of profile names
        """
        return list(config.profiles.keys())
    
    def delete_profile(self, profile_name: str, config: AuthConfig) -> bool:
        """
        Delete a user profile from configuration.
        
        Args:
            profile_name: Name of profile to delete
            config: Configuration object
            
        Returns:
            True if deleted, False if not found
        """
        if profile_name in config.profiles:
            del config.profiles[profile_name]
            
            # Clear current profile if it was the deleted one
            if config.current_profile == profile_name:
                config.current_profile = None
            
            logger.debug(f"Profile '{profile_name}' deleted")
            return True
        
        return False
    
    def create_backup(self) -> Path:
        """
        Create a backup of the current configuration.
        
        Returns:
            Path to the backup file
        """
        if not self.config_file.exists():
            raise ConfigurationError("No configuration file to backup")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.config_file.with_name(f"config_backup_{timestamp}.json")
        
        shutil.copy2(self.config_file, backup_path)
        logger.info(f"Configuration backed up to {backup_path}")
        
        return backup_path
    
    def restore_backup(self, backup_path: Path) -> bool:
        """
        Restore configuration from a backup file.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Validate backup file first
            with backup_path.open('r') as f:
                backup_data = json.load(f)
                AuthConfig(**backup_data)  # Validate structure
            
            # Restore the backup
            shutil.copy2(backup_path, self.config_file)
            logger.info(f"Configuration restored from {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def _load_env_file(self) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}
        
        if self.env_file.exists():
            try:
                with self.env_file.open('r') as f:
                    for line in f:
                        line = line.strip()
                        
                        # Skip empty lines and comments
                        if not line or line.startswith('#'):
                            continue
                        
                        # Parse key=value pairs
                        if '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
                
                logger.debug(f"Loaded {len(env_vars)} environment variables from {self.env_file}")
                
            except IOError as e:
                logger.warning(f"Failed to load .env file: {e}")
        
        # Also include actual environment variables
        for key in os.environ:
            if key.startswith(self.ENV_PREFIX):
                env_vars[key] = os.environ[key]
        
        return env_vars
    
    def _process_env_variables(self, env_vars: Dict[str, str]) -> Dict[str, Any]:
        """Process and convert environment variables to config values."""
        config_overrides = {}
        
        for env_key, env_value in env_vars.items():
            if env_key in self.ENV_MAPPINGS:
                config_path, value_type = self.ENV_MAPPINGS[env_key]
                
                try:
                    # Convert value to appropriate type
                    if value_type == bool:
                        converted_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif value_type == int:
                        converted_value = int(env_value)
                    elif value_type == float:
                        converted_value = float(env_value)
                    else:
                        converted_value = env_value
                    
                    # Handle nested paths like "default_device_info.device_name"
                    if '.' in config_path:
                        parts = config_path.split('.')
                        if parts[0] not in config_overrides:
                            config_overrides[parts[0]] = {}
                        config_overrides[parts[0]][parts[1]] = converted_value
                    else:
                        config_overrides[config_path] = converted_value
                    
                    logger.debug(f"Environment override: {config_path} = {converted_value}")
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid environment variable {env_key}={env_value}: {e}")
        
        return config_overrides
    
    def _validate_config(self, config: AuthConfig) -> None:
        """
        Validate configuration values.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ConfigurationError: If validation fails
        """
        if not config.base_url or not config.base_url.startswith(('http://', 'https://')):
            raise ConfigurationError("Invalid base_url: must be a valid HTTP/HTTPS URL")
        
        if config.timeout <= 0:
            raise ConfigurationError("Invalid timeout: must be greater than 0")
        
        if config.max_retries < 0:
            raise ConfigurationError("Invalid max_retries: must be >= 0")
        
        if config.log_level not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
            raise ConfigurationError(f"Invalid log_level: {config.log_level}")
        
        logger.debug("Configuration validation passed")