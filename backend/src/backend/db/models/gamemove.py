"""
GameMove SQLAlchemy model for tracking individual moves in Gomoku games.

This module defines the GameMove model which tracks individual moves made
during Gomoku games, including position, player information, sequence order,
and validation rules to ensure proper game flow.
"""

from datetime import datetime, timezone
from typing import Any, Optional, List

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Enum as SQLEnum, ForeignKey,
    Integer, String, UniqueConstraint, func, select, event
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from ..database import Base
from .game import Player, GameStatus


class GameMove(Base):
    """
    GameMove model representing individual moves in Gomoku games.

    This model tracks each move made during a game, including the position,
    player information, sequence order, and timing. It enforces game rules
    through validation and database constraints to ensure proper game flow.

    Attributes:
        id: Primary key (auto-increment integer)
        game_id: Foreign key to Game (UUID string)
        player_id: Foreign key to User (player who made the move)
        move_number: Sequence number within the game (1, 2, 3, ...)
        row: Board row position (0-based, 0-14 for 15x15 board)
        col: Board column position (0-based, 0-14 for 15x15 board)
        player_color: Color of the player making the move (BLACK or WHITE)
        created_at: Timestamp when the move was made
        is_winning_move: Boolean indicating if this move won the game
    """

    __tablename__ = "game_moves"

    # Primary key - auto-increment integer for simple ordering
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment integer)"
    )

    # Game relationship - foreign key to games table
    game_id: Mapped[str] = mapped_column(
        String(36),  # UUID length
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to Game (UUID string)"
    )

    # Player relationship - foreign key to users table
    player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        comment="Foreign key to User (player who made the move)"
    )

    # Move sequence number within the game
    move_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Sequence number within the game (1, 2, 3, ...)"
    )

    # Board position - row coordinate (0-based)
    row: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Board row position (0-based, 0-14 for 15x15 board)"
    )

    # Board position - column coordinate (0-based)
    col: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Board column position (0-based, 0-14 for 15x15 board)"
    )

    # Player color for this move
    player_color: Mapped[Player] = mapped_column(
        SQLEnum(Player),
        nullable=False,
        index=True,
        comment="Color of the player making the move (BLACK or WHITE)"
    )

    # Timestamp when the move was made
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),  # Use timezone=False for SQLite compatibility
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        server_default=func.now(),
        comment="Timestamp when the move was made"
    )

    # Flag indicating if this move won the game
    is_winning_move: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Boolean indicating if this move won the game"
    )

    # Relationships (will be loaded when needed)
    game: Mapped["Game"] = relationship(
        "Game",
        back_populates="moves",
        lazy="select"
    )

    player: Mapped["User"] = relationship(
        "User",
        lazy="select"
    )

    # Table-level constraints
    __table_args__ = (
        # Unique constraint: only one move per position per game
        UniqueConstraint(
            "game_id", "row", "col",
            name="uq_game_moves_game_position"
        ),
        # Unique constraint: only one move per sequence number per game
        UniqueConstraint(
            "game_id", "move_number",
            name="uq_game_moves_game_sequence"
        ),
        # Check constraint: move number must be positive
        CheckConstraint(
            "move_number > 0",
            name="ck_game_moves_move_number_positive"
        ),
        # Check constraint: row must be within board bounds (0-14)
        CheckConstraint(
            "row >= 0 AND row <= 14",
            name="ck_game_moves_row_bounds"
        ),
        # Check constraint: col must be within board bounds (0-14)
        CheckConstraint(
            "col >= 0 AND col <= 14",
            name="ck_game_moves_col_bounds"
        ),
        # Index for efficient game move queries
        {"extend_existing": True}
    )

    def __init__(self, **kwargs):
        """Initialize GameMove with proper validation."""
        super().__init__(**kwargs)
        
        # Perform complex validations that require database access
        # These will be checked when the object is persisted

    def __repr__(self) -> str:
        """
        Return a string representation of the GameMove instance.

        Returns:
            str: String representation showing key attributes
        """
        return (
            f"<GameMove(id={self.id}, game_id={self.game_id}, "
            f"move_number={self.move_number}, row={self.row}, col={self.col}, "
            f"player_color={self.player_color}, is_winning_move={self.is_winning_move})>"
        )

    def __str__(self) -> str:
        """
        Return a human-readable string representation.

        Returns:
            str: Human-readable description of the move
        """
        return f"Move {self.move_number}: {self.player_color.value.upper()} at ({self.row},{self.col})"

    @property
    def is_black_move(self) -> bool:
        """
        Check if this is a black player move.

        Returns:
            bool: True if the move was made by the black player
        """
        return self.player_color == Player.BLACK

    @property
    def is_white_move(self) -> bool:
        """
        Check if this is a white player move.

        Returns:
            bool: True if the move was made by the white player
        """
        return self.player_color == Player.WHITE

    @property
    def position_tuple(self) -> tuple[int, int]:
        """
        Get the position as a tuple.

        Returns:
            tuple[int, int]: Position as (row, col) tuple
        """
        return (self.row, self.col)

    @validates("row", "col")
    def validate_position(self, key: str, position: int) -> int:
        """
        Validate that row and column are within board bounds.

        Args:
            key: The field name being validated
            position: The position value to validate

        Returns:
            int: The validated position

        Raises:
            ValueError: If position is outside board bounds (0-14)
        """
        if position < 0 or position > 14:
            raise ValueError("Position must be within board bounds (0-14)")
        return position

    @validates("move_number")
    def validate_move_number(self, key: str, move_number: int) -> int:
        """
        Validate that move number is positive.

        Args:
            key: The field name being validated
            move_number: The move number to validate

        Returns:
            int: The validated move number

        Raises:
            ValueError: If move number is not positive
        """
        if move_number <= 0:
            raise ValueError("Move number must be positive")
        return move_number

    @validates("player_color")
    def validate_player_color_sequence(self, key: str, player_color: Player) -> Player:
        """
        Validate that player colors alternate correctly (black starts first).

        Args:
            key: The field name being validated
            player_color: The player color to validate

        Returns:
            Player: The validated player color

        Raises:
            ValueError: If the player turn order is incorrect
        """
        # Check if this is the correct color for the move number
        # Odd moves should be BLACK, even moves should be WHITE
        if hasattr(self, 'move_number') and self.move_number is not None:
            expected_color = Player.BLACK if self.move_number % 2 == 1 else Player.WHITE
            if player_color != expected_color:
                raise ValueError("Invalid player turn order")
        
        return player_color

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the GameMove instance to a dictionary.

        This is useful for serialization to JSON or for API responses.

        Returns:
            Dict[str, Any]: Dictionary representation of the move
        """
        return {
            "id": self.id,
            "game_id": self.game_id,
            "player_id": self.player_id,
            "move_number": self.move_number,
            "row": self.row,
            "col": self.col,
            "player_color": self.player_color.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_winning_move": self.is_winning_move,
            "is_black_move": self.is_black_move,
            "is_white_move": self.is_white_move,
            "position_tuple": list(self.position_tuple),
        }

    @classmethod
    async def get_moves_by_game(
        cls, 
        session: AsyncSession, 
        game_id: str
    ) -> List["GameMove"]:
        """
        Get all moves for a specific game ordered by move number.

        Args:
            session: Database session
            game_id: ID of the game

        Returns:
            List[GameMove]: List of moves ordered by move number
        """
        result = await session.execute(
            select(cls)
            .where(cls.game_id == game_id)
            .order_by(cls.move_number)
        )
        return result.scalars().all()

    @classmethod
    async def get_moves_by_player(
        cls,
        session: AsyncSession,
        player_id: int
    ) -> List["GameMove"]:
        """
        Get all moves made by a specific player.

        Args:
            session: Database session
            player_id: ID of the player

        Returns:
            List[GameMove]: List of moves made by the player
        """
        result = await session.execute(
            select(cls)
            .where(cls.player_id == player_id)
            .order_by(cls.created_at.desc())
        )
        return result.scalars().all()

    @classmethod
    async def is_position_occupied(
        cls,
        session: AsyncSession,
        game_id: str,
        row: int,
        col: int
    ) -> bool:
        """
        Check if a position is occupied in a specific game.

        Args:
            session: Database session
            game_id: ID of the game
            row: Row coordinate
            col: Column coordinate

        Returns:
            bool: True if position is occupied, False otherwise
        """
        result = await session.execute(
            select(cls)
            .where(
                cls.game_id == game_id,
                cls.row == row,
                cls.col == col
            )
        )
        move = result.scalar_one_or_none()
        return move is not None

    @classmethod
    async def get_last_move(
        cls,
        session: AsyncSession,
        game_id: str
    ) -> Optional["GameMove"]:
        """
        Get the most recent move in a game.

        Args:
            session: Database session
            game_id: ID of the game

        Returns:
            Optional[GameMove]: The last move, or None if no moves exist
        """
        result = await session.execute(
            select(cls)
            .where(cls.game_id == game_id)
            .order_by(cls.move_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_move_count(
        cls,
        session: AsyncSession,
        game_id: str
    ) -> int:
        """
        Get the total number of moves in a game.

        Args:
            session: Database session
            game_id: ID of the game

        Returns:
            int: Total number of moves in the game
        """
        result = await session.execute(
            select(func.count(cls.id))
            .where(cls.game_id == game_id)
        )
        return result.scalar() or 0

    async def validate_before_insert(self, session: AsyncSession) -> None:
        """
        Perform complex validations that require database access.
        
        This method should be called before inserting a new move.
        
        Args:
            session: Database session for validation queries
            
        Raises:
            ValueError: If any validation fails
        """
        # Check if game exists and is active
        from .game import Game  # Import here to avoid circular imports
        result = await session.execute(
            select(Game).where(Game.id == self.game_id)
        )
        game = result.scalar_one_or_none()
        
        if not game:
            raise ValueError(f"Game {self.game_id} does not exist")
            
        if game.status != GameStatus.ACTIVE:
            raise ValueError("Can only add moves to ACTIVE games")
        
        # Check if position is already occupied
        is_occupied = await self.is_position_occupied(
            session, self.game_id, self.row, self.col
        )
        if is_occupied:
            raise ValueError(f"Position ({self.row}, {self.col}) is already occupied")
        
        # Check if move numbers are sequential
        last_move = await self.get_last_move(session, self.game_id)
        expected_move_number = 1 if not last_move else last_move.move_number + 1
        
        if self.move_number != expected_move_number:
            raise ValueError("Move numbers must be sequential")


# Event handlers for validation
@event.listens_for(GameMove, 'before_insert')
def validate_game_move_before_insert(mapper, connection, target):
    """Validate GameMove before insertion."""
    # Note: This is a synchronous event handler, so we can't use async database queries here
    # The complex validations will need to be done at the application level
    # before calling session.add(move) and session.commit()
    pass