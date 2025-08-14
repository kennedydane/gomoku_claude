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
    """Authentication configuration data."""
    current_profile: Optional[str] = Field(None, description="Currently active profile")
    profiles: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Saved user profiles")
    default_device_info: Dict[str, Any] = Field(default_factory=dict, description="Default device information")