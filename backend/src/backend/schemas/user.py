"""
User Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base user schema with common fields."""
    
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        description="Unique username (3-50 characters)"
    )
    email: Optional[EmailStr] = Field(
        None, 
        description="Optional email address"
    )
    display_name: Optional[str] = Field(
        None, 
        max_length=100,
        description="Optional display name"
    )
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens and underscores')
        return v.lower()


class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    
    email: Optional[EmailStr] = None
    display_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user API responses."""
    
    id: int
    games_played: int = Field(description="Total games played")
    games_won: int = Field(description="Total games won") 
    win_rate: float = Field(description="Win percentage (0.0-1.0)")
    is_active: bool = Field(description="Account active status")
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}