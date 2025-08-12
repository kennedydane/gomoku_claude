"""
GameMove Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ..db.models.game import Player


class GameMoveBase(BaseModel):
    """Base game move schema with common fields."""
    
    row: int = Field(
        ..., 
        ge=0, 
        le=14,
        description="Board row position (0-based, 0-14)"
    )
    col: int = Field(
        ..., 
        ge=0, 
        le=14,
        description="Board column position (0-based, 0-14)"
    )
    
    @field_validator('row', 'col')
    @classmethod
    def validate_position(cls, v):
        """Validate board position is within bounds."""
        if v < 0 or v > 14:
            raise ValueError('Position must be within board bounds (0-14)')
        return v


class GameMoveCreate(GameMoveBase):
    """Schema for creating a new move."""
    
    player_id: int = Field(
        ...,
        description="ID of the player making the move"
    )


class GameMoveResponse(GameMoveBase):
    """Schema for game move API responses."""
    
    id: int
    game_id: str = Field(description="Game UUID") 
    player_id: int
    move_number: int = Field(description="Sequence number within game")
    player_color: Player = Field(description="Color of player making move")
    created_at: datetime
    is_winning_move: bool = Field(description="Whether this move won the game")
    is_black_move: bool = Field(description="Whether this is a black move")
    is_white_move: bool = Field(description="Whether this is a white move")
    position_tuple: list[int] = Field(description="Position as [row, col] array")
    
    # Related data (when included)
    player: Optional[dict] = None
    game: Optional[dict] = None
    
    model_config = {"from_attributes": True}