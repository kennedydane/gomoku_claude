"""
Game Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..db.models.game import GameStatus, Player


class GameBase(BaseModel):
    """Base game schema with common fields."""
    
    ruleset_id: int = Field(
        ...,
        description="ID of the ruleset to use for this game"
    )


class GameCreateSinglePlayer(GameBase):
    """Schema for creating a single-player game."""
    
    black_player_id: int = Field(
        ...,
        description="ID of the player (will play as black)"
    )


class GameCreateTwoPlayer(GameBase):
    """Schema for creating a two-player game."""
    
    black_player_id: int = Field(
        ...,
        description="ID of the black player"
    )
    white_player_id: int = Field(
        ..., 
        description="ID of the white player"
    )


class GameCreate(BaseModel):
    """Union schema for creating games."""
    
    ruleset_id: int = Field(
        ...,
        description="ID of the ruleset to use"
    )
    black_player_id: int = Field(
        ...,
        description="ID of the black player"
    )
    white_player_id: Optional[int] = Field(
        None,
        description="ID of the white player (None for single-player)"
    )


class GameUpdate(BaseModel):
    """Schema for updating game state."""
    
    status: Optional[str] = Field(None, pattern="^(WAITING|ACTIVE|FINISHED|ABANDONED)$")
    winner_id: Optional[int] = None


class GameState(BaseModel):
    """Schema for detailed game state information."""
    
    board: list[list[Optional[str]]] = Field(
        description="2D array representing board state"
    )
    size: int = Field(description="Board size")
    
    model_config = {"from_attributes": True}


class GameResponse(BaseModel):
    """Schema for game API responses."""
    
    id: str = Field(description="Game UUID")
    black_player_id: int
    white_player_id: Optional[int] = None
    ruleset_id: int
    status: GameStatus
    current_player: Player
    board_state: GameState
    winner_id: Optional[int] = None
    move_count: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_game_over: bool
    is_single_player: bool
    can_start: bool
    
    # Related data (when included)
    black_player: Optional[Dict[str, Any]] = None
    white_player: Optional[Dict[str, Any]] = None
    winner: Optional[Dict[str, Any]] = None
    ruleset: Optional[Dict[str, Any]] = None
    
    model_config = {"from_attributes": True}