"""
RuleSet SQLAlchemy model for Gomoku game rules.

This module defines the RuleSet model which handles different Gomoku rule variations
including Standard, Renju, Freestyle, Caro, and tournament rules like Swap2.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class RuleSet(Base):
    """
    RuleSet model representing different Gomoku game rule configurations.

    This model supports various Gomoku variants including:
    - Standard Gomoku: Exactly 5 in a row wins, overlines don't count
    - Renju: 15×15 board with forbidden moves for Black (3-3, 4-4, overlines)
    - Freestyle: Overlines count as wins
    - Caro: Unblocked 5-in-a-row or overlines to win
    - Swap2: Tournament opening rule

    Attributes:
        id: Primary key identifier
        name: Unique name of the rule set (e.g., "Standard", "Renju")
        board_size: Size of the game board (typically 15 or 19)
        allow_overlines: Whether lines longer than 5 count as wins
        forbidden_moves: JSON field storing complex rule configurations
        description: Optional human-readable description of the rules
        created_at: Timestamp of when the ruleset was created
        updated_at: Timestamp of when the ruleset was last modified
    """

    __tablename__ = "rulesets"

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key identifier"
    )

    # Core rule configuration
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique name of the rule set"
    )

    board_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Size of the game board (e.g., 15 for 15x15)"
    )

    allow_overlines: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
        comment="Whether lines longer than 5 stones count as wins"
    )

    # Flexible JSON field for complex rule storage
    forbidden_moves: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="JSON field storing complex rule configurations and forbidden move patterns"
    )

    def __init__(self, **kwargs):
        """Initialize RuleSet with proper forbidden_moves handling."""
        # Convert None to empty dict for forbidden_moves
        if kwargs.get("forbidden_moves") is None:
            kwargs["forbidden_moves"] = {}
        super().__init__(**kwargs)

    # Optional description
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description of the rules"
    )

    # Timestamp fields with automatic management
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),  # Use timezone=False for SQLite compatibility
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=func.now(),
        comment="Timestamp of when the ruleset was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),  # Use timezone=False for SQLite compatibility
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        comment="Timestamp of when the ruleset was last modified"
    )

    def __repr__(self) -> str:
        """
        Return a string representation of the RuleSet instance.

        Returns:
            str: String representation showing key attributes
        """
        return (
            f"<RuleSet(id={self.id}, name='{self.name}', "
            f"board_size={self.board_size}, allow_overlines={self.allow_overlines})>"
        )

    def __str__(self) -> str:
        """
        Return a human-readable string representation.

        Returns:
            str: Human-readable description of the ruleset
        """
        return f"{self.name} ({self.board_size}x{self.board_size})"

    @property
    def is_standard_gomoku(self) -> bool:
        """
        Check if this is a standard Gomoku ruleset.

        Standard Gomoku has no forbidden moves and doesn't allow overlines.
        Board size can vary but common sizes are supported.

        Returns:
            bool: True if this represents standard Gomoku rules
        """
        return (
            not self.forbidden_moves and
            not self.allow_overlines and
            self.board_size >= 9  # Allow various board sizes
        )

    @property
    def is_renju(self) -> bool:
        """
        Check if this is a Renju ruleset.

        Renju typically has forbidden moves for Black and uses a 15x15 board.

        Returns:
            bool: True if this appears to be Renju rules
        """
        return (
            self.board_size == 15 and
            not self.allow_overlines and
            bool(self.forbidden_moves.get("black_forbidden") or
                 self.forbidden_moves.get("renju"))
        )

    @property
    def is_freestyle(self) -> bool:
        """
        Check if this is a Freestyle Gomoku ruleset.

        Freestyle Gomoku allows overlines and typically has no forbidden moves.

        Returns:
            bool: True if this appears to be Freestyle rules
        """
        return (
            self.allow_overlines and
            not bool(self.forbidden_moves.get("black_forbidden"))
        )

    def get_forbidden_moves_for_player(self, is_black: bool) -> dict[str, Any]:
        """
        Get the forbidden move rules for a specific player.

        Args:
            is_black: True for Black player, False for White player

        Returns:
            Dict[str, Any]: Dictionary of forbidden move rules for the player
        """
        if not self.forbidden_moves:
            return {}

        player_key = "black_forbidden" if is_black else "white_forbidden"
        return self.forbidden_moves.get(player_key, {})

    def has_opening_rule(self) -> bool:
        """
        Check if this ruleset includes special opening rules.

        Returns:
            bool: True if the ruleset has opening rules like Swap2
        """
        return bool(
            self.forbidden_moves.get("opening_rule") or
            self.forbidden_moves.get("swap2") or
            self.forbidden_moves.get("tournament_settings")
        )

    def get_win_condition(self) -> str:
        """
        Get the win condition description for this ruleset.

        Returns:
            str: Description of how to win under these rules
        """
        if self.allow_overlines:
            return "5 or more in a row"
        else:
            return "Exactly 5 in a row"

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the RuleSet instance to a dictionary.

        This is useful for serialization to JSON or for API responses.

        Returns:
            Dict[str, Any]: Dictionary representation of the ruleset
        """
        return {
            "id": self.id,
            "name": self.name,
            "board_size": self.board_size,
            "allow_overlines": self.allow_overlines,
            "forbidden_moves": self.forbidden_moves,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "win_condition": self.get_win_condition(),
            "is_standard_gomoku": self.is_standard_gomoku,
            "is_renju": self.is_renju,
            "is_freestyle": self.is_freestyle,
            "has_opening_rule": self.has_opening_rule()
        }

    @classmethod
    def create_standard_ruleset(cls) -> "RuleSet":
        """
        Create a standard Gomoku ruleset.

        Returns:
            RuleSet: A new RuleSet instance with standard Gomoku rules
        """
        return cls(
            name="Standard",
            board_size=15,
            allow_overlines=False,
            description="Standard Gomoku rules - exactly 5 in a row wins"
        )

    @classmethod
    def create_renju_ruleset(cls) -> "RuleSet":
        """
        Create a Renju ruleset with forbidden moves for Black.

        Returns:
            RuleSet: A new RuleSet instance with Renju rules
        """
        forbidden_moves = {
            "black_forbidden": {
                "three_three": True,
                "four_four": True,
                "overlines": True
            },
            "board_size_restriction": 15
        }

        return cls(
            name="Renju",
            board_size=15,
            allow_overlines=False,
            forbidden_moves=forbidden_moves,
            description="Renju rules with forbidden moves for Black (3-3, 4-4, overlines)"
        )

    @classmethod
    def create_freestyle_ruleset(cls) -> "RuleSet":
        """
        Create a Freestyle Gomoku ruleset.

        Returns:
            RuleSet: A new RuleSet instance with Freestyle rules
        """
        return cls(
            name="Freestyle",
            board_size=15,
            allow_overlines=True,
            description="Freestyle Gomoku - overlines count as wins"
        )

    @classmethod
    def create_caro_ruleset(cls) -> "RuleSet":
        """
        Create a Caro ruleset.

        Returns:
            RuleSet: A new RuleSet instance with Caro rules
        """
        caro_rules = {
            "win_condition": "unblocked_five_or_overline",
            "blocking_required": True
        }

        return cls(
            name="Caro",
            board_size=15,
            allow_overlines=True,
            forbidden_moves=caro_rules,
            description="Caro rules - unblocked 5-in-a-row or overlines to win"
        )

    @classmethod
    def create_swap2_ruleset(cls) -> "RuleSet":
        """
        Create a Swap2 tournament ruleset.

        Returns:
            RuleSet: A new RuleSet instance with Swap2 tournament rules
        """
        swap2_rules = {
            "opening_rule": "swap2",
            "tournament_format": True,
            "phases": ["initial_moves", "swap_decision", "normal_play"]
        }

        return cls(
            name="Swap2",
            board_size=15,
            allow_overlines=False,
            forbidden_moves=swap2_rules,
            description="Swap2 tournament opening rule"
        )
