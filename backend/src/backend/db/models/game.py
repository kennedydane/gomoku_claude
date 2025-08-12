"""
Game SQLAlchemy model for Gomoku game management.

This module defines the Game model which manages active Gomoku games,
including board state, player relationships, and game flow logic.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, List

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, DateTime, Enum as SQLEnum, 
    ForeignKey, Integer, String, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from ..database import Base


class GameStatus(Enum):
    """Enumeration of possible game statuses."""
    WAITING = "WAITING"      # Waiting for second player
    ACTIVE = "ACTIVE"        # Game in progress  
    FINISHED = "FINISHED"    # Game completed
    ABANDONED = "ABANDONED"  # Game abandoned


class Player(Enum):
    """Enumeration of players in the game."""
    BLACK = "BLACK"
    WHITE = "WHITE"


class Game(Base):
    """
    Game model representing active Gomoku games.

    This model is the central entity that manages game state, including
    player relationships, board state, move tracking, and game flow logic.
    It supports both single-player and two-player games with comprehensive
    game state management.

    Attributes:
        id: Primary key (UUID for external API security)
        black_player_id: Foreign key to User (black player)
        white_player_id: Foreign key to User (white player, nullable for single player)
        ruleset_id: Foreign key to RuleSet
        status: Current game status (WAITING, ACTIVE, FINISHED, ABANDONED)
        current_player: Which player's turn it is (BLACK or WHITE)
        board_state: JSON field containing board representation
        winner_id: Foreign key to User (winner, nullable)
        move_count: Number of moves made in the game
        started_at: When game became active (nullable)
        finished_at: When game ended (nullable)
        created_at: Timestamp of game creation
        updated_at: Timestamp of last modification
    """

    __tablename__ = "games"

    # Primary key - UUID for external API security
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Primary key (UUID for external API security)"
    )

    # Player relationships
    black_player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="Foreign key to User (black player)"
    )

    white_player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="Foreign key to User (white player)"
    )

    # Ruleset relationship
    ruleset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rulesets.id"),
        nullable=False,
        index=True,
        comment="Foreign key to RuleSet"
    )

    # Game status
    status: Mapped[GameStatus] = mapped_column(
        SQLEnum(GameStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=GameStatus.WAITING,
        index=True,
        comment="Current game status"
    )

    # Current player turn
    current_player: Mapped[Player] = mapped_column(
        SQLEnum(Player, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=Player.BLACK,
        index=True,
        comment="Which player's turn it is"
    )

    # Board state as JSON
    board_state: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {"board": [[None for _ in range(15)] for _ in range(15)], "size": 15},
        comment="JSON field containing board representation"
    )

    # Winner relationship
    winner_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
        comment="Foreign key to User (winner, nullable)"
    )

    # Move tracking
    move_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        index=True,
        comment="Number of moves made in the game"
    )

    # Game timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False),  # Use timezone=False for SQLite compatibility
        nullable=True,
        comment="When game became active"
    )

    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False),  # Use timezone=False for SQLite compatibility
        nullable=True,
        comment="When game ended"
    )

    # Timestamp fields with automatic management
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),  # Use timezone=False for SQLite compatibility
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=func.now(),
        comment="Timestamp of game creation"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),  # Use timezone=False for SQLite compatibility
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        comment="Timestamp of last modification"
    )

    # Relationships (will be loaded when needed)
    black_player: Mapped["User"] = relationship(
        "User",
        foreign_keys=[black_player_id],
        lazy="select"
    )

    white_player: Mapped["User"] = relationship(
        "User", 
        foreign_keys=[white_player_id],
        lazy="select"
    )

    winner: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[winner_id],
        lazy="select"
    )

    ruleset: Mapped["RuleSet"] = relationship(
        "RuleSet",
        lazy="select"
    )

    moves: Mapped[List["GameMove"]] = relationship(
        "GameMove",
        back_populates="game",
        cascade="all, delete-orphan",
        lazy="select"
    )

    # Table-level constraints
    __table_args__ = (
        CheckConstraint(
            "move_count >= 0",
            name="ck_games_move_count_non_negative"
        ),
        CheckConstraint(
            "winner_id IN (black_player_id, white_player_id) OR winner_id IS NULL",
            name="ck_games_winner_must_be_player"
        ),
        CheckConstraint(
            "started_at IS NULL OR status != 'waiting'",
            name="ck_games_started_at_not_waiting"
        ),
        CheckConstraint(
            "finished_at IS NULL OR status IN ('finished', 'abandoned')",
            name="ck_games_finished_at_only_when_done"
        ),
    )

    def __init__(self, **kwargs):
        """Initialize Game with proper board state handling."""
        # Initialize board_state if not provided
        if "board_state" not in kwargs or kwargs["board_state"] is None:
            # Get board size from ruleset if available, otherwise default to 15
            board_size = 15
            if "ruleset_id" in kwargs:
                # We can't access the ruleset here, so use default
                # Board size will be set properly when the game is created with a ruleset
                pass
            kwargs["board_state"] = {
                "board": [[None for _ in range(board_size)] for _ in range(board_size)],
                "size": board_size
            }
        
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """
        Return a string representation of the Game instance.

        Returns:
            str: String representation showing key attributes
        """
        return (
            f"<Game(id={self.id}, status={self.status}, "
            f"current_player={self.current_player}, move_count={self.move_count}, "
            f"black_player_id={self.black_player_id}, white_player_id={self.white_player_id})>"
        )

    def __str__(self) -> str:
        """
        Return a human-readable string representation.

        Returns:
            str: Human-readable description of the game
        """
        return f"Game: {self.status.value} (Move {self.move_count})"

    @property
    def is_game_over(self) -> bool:
        """
        Check if the game is over.

        Returns:
            bool: True if the game is finished or abandoned
        """
        return self.status in (GameStatus.FINISHED, GameStatus.ABANDONED)


    @property
    def can_start(self) -> bool:
        """
        Check if the game can be started.

        A game can be started if it's in WAITING status and both players are assigned.

        Returns:
            bool: True if the game can be started
        """
        return (self.status == GameStatus.WAITING and 
                self.black_player_id is not None and 
                self.white_player_id is not None)

    def initialize_board(self, board_size: int) -> None:
        """
        Initialize or reinitialize the game board.

        Args:
            board_size: Size of the board (e.g., 15 for 15x15)
        """
        self.board_state = {
            "board": [[None for _ in range(board_size)] for _ in range(board_size)],
            "size": board_size
        }

    def is_valid_position(self, row: int, col: int) -> bool:
        """
        Check if a position is valid on the board.

        Args:
            row: Row coordinate (0-based)
            col: Column coordinate (0-based)

        Returns:
            bool: True if the position is valid and empty
        """
        board_size = self.board_state.get("size", 15)
        
        # Check bounds
        if row < 0 or row >= board_size or col < 0 or col >= board_size:
            return False
            
        # Check if position is empty
        board = self.board_state.get("board", [])
        if row >= len(board) or col >= len(board[row]):
            return False
            
        return board[row][col] is None

    def make_move(self, row: int, col: int) -> bool:
        """
        Make a move at the specified position.

        Args:
            row: Row coordinate (0-based)
            col: Column coordinate (0-based)

        Returns:
            bool: True if the move was successful, False otherwise
        """
        # Check if game is active
        if self.status != GameStatus.ACTIVE:
            return False

        # Validate position
        if not self.is_valid_position(row, col):
            return False

        # Make the move
        player_color = self.current_player.value
        self.board_state["board"][row][col] = player_color
        
        # Update game state
        self.move_count += 1
        
        # Switch current player
        if self.current_player == Player.BLACK:
            self.current_player = Player.WHITE
        else:
            self.current_player = Player.BLACK

        return True

    def start_game(self) -> None:
        """
        Start the game.

        Changes status to ACTIVE and sets started_at timestamp.
        """
        if self.status == GameStatus.WAITING:
            self.status = GameStatus.ACTIVE
            self.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
            self.current_player = Player.BLACK

    def end_game(self, winner_id: Optional[int] = None) -> None:
        """
        End the game with optional winner.

        Args:
            winner_id: ID of the winning player, or None for draw
        """
        if self.status == GameStatus.ACTIVE:
            self.status = GameStatus.FINISHED
            self.winner_id = winner_id
            self.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def abandon_game(self) -> None:
        """
        Abandon the game.

        Sets status to ABANDONED and finished_at timestamp.
        """
        if self.status in (GameStatus.WAITING, GameStatus.ACTIVE):
            self.status = GameStatus.ABANDONED
            self.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
            # Winner remains None for abandoned games

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the Game instance to a dictionary.

        This is useful for serialization to JSON or for API responses.

        Returns:
            Dict[str, Any]: Dictionary representation of the game
        """
        return {
            "id": self.id,
            "black_player_id": self.black_player_id,
            "white_player_id": self.white_player_id,
            "ruleset_id": self.ruleset_id,
            "status": self.status.value,
            "current_player": self.current_player.value,
            "board_state": self.board_state,
            "winner_id": self.winner_id,
            "move_count": self.move_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_game_over": self.is_game_over,
            "can_start": self.can_start,
        }


    @classmethod
    def create_game(
        cls,
        black_player_id: int,
        white_player_id: int,
        ruleset_id: int
    ) -> "Game":
        """
        Create a new game.

        Args:
            black_player_id: ID of the black player
            white_player_id: ID of the white player  
            ruleset_id: ID of the ruleset to use

        Returns:
            Game: A new Game instance
        """
        return cls(
            black_player_id=black_player_id,
            white_player_id=white_player_id,
            ruleset_id=ruleset_id,
            status=GameStatus.WAITING
        )

    @validates("winner_id")
    def validate_winner(self, key: str, winner_id: Optional[int]) -> Optional[int]:
        """
        Validate that winner is one of the players.

        Args:
            key: The field name being validated
            winner_id: The winner ID to validate

        Returns:
            Optional[int]: The validated winner ID

        Raises:
            ValueError: If winner is not one of the players
        """
        if winner_id is None:
            return None
            
        # Winner must be either black or white player
        if winner_id not in (self.black_player_id, self.white_player_id):
            raise ValueError("Winner must be either the black or white player")
            
        return winner_id

    @validates("move_count")
    def validate_move_count(self, key: str, move_count: int) -> int:
        """
        Validate move count is non-negative.

        Args:
            key: The field name being validated
            move_count: The move count to validate

        Returns:
            int: The validated move count

        Raises:
            ValueError: If move count is negative
        """
        if move_count < 0:
            raise ValueError("Move count cannot be negative")
        return move_count