"""
Authentication data models.

This module defines the data models used for authentication,
including tokens, user profiles, and configuration structures.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class TokenInfo(BaseModel):
    """Enhanced token information."""
    token: str = Field(..., description="Authentication token")
    expires_at: datetime = Field(..., description="Token expiration time")
    device_name: str = Field(default="", description="Device identifier")
    device_info: Dict[str, Any] = Field(default_factory=dict, description="Additional device information")


class UserProfile(BaseModel):
    """User profile information."""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: Optional[str] = Field(None, description="Email address")
    display_name: str = Field(default="", description="Display name")
    date_joined: datetime = Field(..., description="Registration date")


class AuthConfig(BaseModel):
    """Enhanced authentication configuration data."""
    # Server configuration
    base_url: str = Field(default="http://localhost:8001", description="Base URL of the API server")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    
    # Authentication settings
    current_profile: Optional[str] = Field(None, description="Currently active profile")
    auto_refresh_token: bool = Field(default=True, description="Automatically refresh tokens")
    max_retries: int = Field(default=3, description="Maximum request retries")
    
    # Profile management
    profiles: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Saved user profiles")
    default_device_info: Dict[str, Any] = Field(default_factory=dict, description="Default device information")
    
    # Logging and debugging
    log_level: str = Field(default="INFO", description="Logging level")
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    
    # Security settings
    save_credentials: bool = Field(default=True, description="Save credentials to disk")
    encrypt_credentials: bool = Field(default=False, description="Encrypt saved credentials")