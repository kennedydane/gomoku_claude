"""
User SQLAlchemy model for Gomoku game players.

This module defines the User model which handles player information, statistics,
and authentication data for the Gomoku game system.
"""

import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, validates

from ..database import Base


class User(Base):
    """
    User model representing players in the Gomoku game system.

    This model stores player information including authentication data,
    game statistics, and profile information. It supports user management
    features like soft deletion and comprehensive game statistics tracking.

    Attributes:
        id: Primary key identifier
        username: Unique username (3-50 characters, alphanumeric + underscore/hyphen)
        email: Optional unique email address
        display_name: Optional display name for the user
        games_played: Total number of completed games
        games_won: Total number of games won
        is_active: Boolean flag for soft deletion
        created_at: Timestamp of when the user was created
        updated_at: Timestamp of when the user was last modified
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key identifier"
    )

    # Username - required, unique, indexed
    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique username (3-50 characters, case-insensitive)"
    )

    # Email - optional, unique when provided, indexed
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Optional unique email address"
    )

    # Display name - optional, for user interface
    display_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Optional display name for user interface"
    )

    # Game statistics
    games_played: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        index=True,
        comment="Total number of completed games"
    )

    games_won: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        index=True,
        comment="Total number of games won"
    )

    # Soft deletion flag
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
        comment="Boolean flag for soft deletion (True = active)"
    )

    # Timestamp fields with automatic management
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),  # Use timezone=False for SQLite compatibility
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=func.now(),
        comment="Timestamp of when the user was created"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),  # Use timezone=False for SQLite compatibility
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        comment="Timestamp of when the user was last modified"
    )

    # Table-level constraints
    __table_args__ = (
        CheckConstraint(
            "length(username) >= 3",
            name="ck_users_username_min_length"
        ),
        CheckConstraint(
            "games_won <= games_played",
            name="ck_users_games_won_not_exceed_played"
        ),
        CheckConstraint(
            "games_played >= 0",
            name="ck_users_games_played_non_negative"
        ),
        CheckConstraint(
            "games_won >= 0",
            name="ck_users_games_won_non_negative"
        ),
    )

    def __init__(self, **kwargs):
        """Initialize User with proper validation."""
        super().__init__(**kwargs)

    @validates("username")
    def validate_username(self, key: str, username: str) -> str:
        """
        Validate username format and length.

        Args:
            key: The field name being validated
            username: The username to validate

        Returns:
            str: The validated username in lowercase

        Raises:
            ValueError: If username doesn't meet requirements
        """
        if not username:
            raise ValueError("Username is required")

        # Convert to lowercase for case-insensitive storage
        username = username.lower().strip()

        # Check length
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if len(username) > 50:
            raise ValueError("Username cannot exceed 50 characters")

        # Check format - Unicode letters, numbers, underscore and hyphen
        if not re.match(r"^[\w-]+$", username, re.UNICODE):
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )

        return username

    @validates("email")
    def validate_email(self, key: str, email: Optional[str]) -> Optional[str]:
        """
        Validate email format if provided.

        Args:
            key: The field name being validated
            email: The email to validate

        Returns:
            Optional[str]: The validated email or None

        Raises:
            ValueError: If email format is invalid
        """
        if email is None or email.strip() == "":
            return None

        email = email.lower().strip()

        # Basic email format validation
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("Invalid email format")

        if len(email) > 255:
            raise ValueError("Email cannot exceed 255 characters")

        return email

    @validates("games_played", "games_won")
    def validate_game_stats(self, key: str, value: int) -> int:
        """
        Validate game statistics.

        Args:
            key: The field name being validated
            value: The value to validate

        Returns:
            int: The validated value

        Raises:
            ValueError: If value is invalid
        """
        if value < 0:
            raise ValueError(f"{key} cannot be negative")

        # Check that games_won doesn't exceed games_played
        # Use getattr with default to handle None values during initialization
        if key == "games_won":
            games_played = getattr(self, "games_played", 0)
            if games_played is not None and value > games_played:
                raise ValueError("Games won cannot exceed games played")
        elif key == "games_played":
            games_won = getattr(self, "games_won", 0)
            if games_won is not None and games_won > value:
                raise ValueError("Games won cannot exceed games played")

        return value

    def __repr__(self) -> str:
        """
        Return a string representation of the User instance.

        Returns:
            str: String representation showing key attributes
        """
        return (
            f"<User(id={self.id}, username='{self.username}', "
            f"email='{self.email}', games_played={self.games_played}, "
            f"games_won={self.games_won}, is_active={self.is_active})>"
        )

    def __str__(self) -> str:
        """
        Return a human-readable string representation.

        Returns:
            str: Display name if available, otherwise username
        """
        return self.display_name or self.username

    @property
    def win_rate(self) -> float:
        """
        Calculate the user's win rate.

        Returns:
            float: Win rate as a decimal between 0.0 and 1.0
        """
        games_played = self.games_played or 0
        games_won = self.games_won or 0
        
        if games_played == 0:
            return 0.0
        return games_won / games_played

    @property
    def losses(self) -> int:
        """
        Calculate the number of games lost.

        Returns:
            int: Number of games lost
        """
        games_played = self.games_played or 0
        games_won = self.games_won or 0
        return games_played - games_won

    @property
    def has_played_games(self) -> bool:
        """
        Check if the user has played any games.

        Returns:
            bool: True if the user has played at least one game
        """
        games_played = self.games_played or 0
        return games_played > 0

    @property
    def is_experienced(self) -> bool:
        """
        Check if the user is considered experienced (10+ games).

        Returns:
            bool: True if the user has played 10 or more games
        """
        games_played = self.games_played or 0
        return games_played >= 10

    @property
    def display_name_or_username(self) -> str:
        """
        Get the display name if available, otherwise the username.

        Returns:
            str: Display name or username
        """
        return self.display_name or self.username

    def update_game_stats(self, won: bool) -> None:
        """
        Update game statistics after a game is completed.

        Args:
            won: True if the user won the game, False otherwise
        """
        self.games_played += 1
        if won:
            self.games_won += 1

    def reset_stats(self) -> None:
        """Reset all game statistics to zero."""
        # Set both together to avoid validation issues
        self.__dict__['games_played'] = 0
        self.__dict__['games_won'] = 0

    def activate(self) -> None:
        """Activate the user (set is_active to True)."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate the user (soft deletion - set is_active to False)."""
        self.is_active = False

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the User instance to a dictionary.

        This is useful for serialization to JSON or for API responses.

        Returns:
            Dict[str, Any]: Dictionary representation of the user
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "games_played": self.games_played,
            "games_won": self.games_won,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "win_rate": self.win_rate,
            "losses": self.losses,
            "has_played_games": self.has_played_games,
            "is_experienced": self.is_experienced,
        }

    @classmethod
    def create_user(
        cls,
        username: str,
        email: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> "User":
        """
        Create a new user with the given parameters.

        Args:
            username: The unique username
            email: Optional email address
            display_name: Optional display name

        Returns:
            User: A new User instance
        """
        return cls(
            username=username,
            email=email,
            display_name=display_name
        )

    @classmethod
    def create_guest_user(cls, username: str) -> "User":
        """
        Create a guest user (no email, temporary).

        Args:
            username: The temporary username

        Returns:
            User: A new User instance configured as a guest
        """
        return cls(
            username=username,
            email=None,
            display_name=f"Guest {username}"
        )