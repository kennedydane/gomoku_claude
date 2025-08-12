"""
RuleSet Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class RuleSetBase(BaseModel):
    """Base ruleset schema with common fields."""
    
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Unique name of the rule set"
    )
    board_size: int = Field(
        ..., 
        ge=5, 
        le=19,
        description="Board size (5-19, typically 15)"
    )
    allow_overlines: bool = Field(
        ...,
        description="Whether lines longer than 5 count as wins"
    )
    forbidden_moves: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON object with rule configurations"
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable description of the rules"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate ruleset name."""
        if not v.strip():
            raise ValueError('Ruleset name cannot be empty')
        return v.strip()
    
    @field_validator('board_size')
    @classmethod
    def validate_board_size(cls, v):
        """Validate board size is reasonable."""
        if v not in [9, 13, 15, 19]:  # Common board sizes
            # Allow other sizes but warn
            pass
        return v


class RuleSetCreate(RuleSetBase):
    """Schema for creating a new ruleset."""
    pass


class RuleSetResponse(RuleSetBase):
    """Schema for ruleset API responses."""
    
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}