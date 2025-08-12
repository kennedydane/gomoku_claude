"""
Comprehensive tests for the Game model.

This module contains tests for the Game SQLAlchemy model following TDD principles.
Tests cover model creation, validation, relationships, game logic, and edge cases.
"""

import uuid
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.game import Game, GameStatus, Player
from backend.db.models.user import User
from backend.db.models.ruleset import RuleSet


class TestGameEnums:
    """Test cases for Game enums."""

    def test_game_status_enum_values(self) -> None:
        """Test that GameStatus enum has all required values."""
        assert GameStatus.WAITING.value == "waiting"
        assert GameStatus.ACTIVE.value == "active"
        assert GameStatus.FINISHED.value == "finished"
        assert GameStatus.ABANDONED.value == "abandoned"

    def test_player_enum_values(self) -> None:
        """Test that Player enum has all required values."""
        assert Player.BLACK.value == "black"
        assert Player.WHITE.value == "white"


class TestGameModel:
    """Test cases for basic Game model functionality."""

    async def test_create_game_with_required_fields(self, db_session: AsyncSession) -> None:
        """Test creating a game with only required fields."""
        # Create necessary related objects
        black_player = User(username="blackplayer")
        ruleset = RuleSet(name="Test Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(ruleset)

        # Create white player 
        white_player = User(username="whitetest")
        db_session.add(white_player)
        await db_session.commit()
        await db_session.refresh(white_player)
        
        # Create game
        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        assert game.id is not None
        assert isinstance(game.id, str)  # UUID as string
        assert len(game.id) == 36  # UUID format
        assert game.black_player_id == black_player.id
        assert game.white_player_id == white_player.id
        assert game.ruleset_id == ruleset.id
        assert game.status == GameStatus.WAITING
        assert game.current_player == Player.BLACK
        assert game.board_state is not None
        assert isinstance(game.board_state, dict)
        assert game.winner_id is None
        assert game.move_count == 0
        assert game.started_at is None
        assert game.finished_at is None
        assert isinstance(game.created_at, datetime)
        assert isinstance(game.updated_at, datetime)

    async def test_create_game_with_all_fields(self, db_session: AsyncSession) -> None:
        """Test creating a game with all fields populated."""
        # Create necessary related objects
        black_player = User(username="blackplayer2")
        white_player = User(username="whiteplayer2")
        ruleset = RuleSet(name="Test Rules 2", board_size=19, allow_overlines=True)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        # Create game with all fields
        custom_board = {"board": [[None for _ in range(19)] for _ in range(19)], "size": 19}
        started_time = datetime.now()
        
        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id,
            status=GameStatus.ACTIVE,
            current_player=Player.WHITE,
            board_state=custom_board,
            move_count=5,
            started_at=started_time
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        assert game.black_player_id == black_player.id
        assert game.white_player_id == white_player.id
        assert game.ruleset_id == ruleset.id
        assert game.status == GameStatus.ACTIVE
        assert game.current_player == Player.WHITE
        assert game.board_state == custom_board
        assert game.winner_id is None
        assert game.move_count == 5
        assert game.started_at == started_time
        assert game.finished_at is None

    async def test_default_board_state_initialization(self, db_session: AsyncSession) -> None:
        """Test that board state is properly initialized with default values."""
        black_player = User(username="boardtest")
        ruleset = RuleSet(name="Board Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Check default board state
        expected_board = {
            "board": [[None for _ in range(15)] for _ in range(15)],
            "size": 15
        }
        assert game.board_state == expected_board
        assert game.board_state["size"] == 15
        assert len(game.board_state["board"]) == 15
        assert len(game.board_state["board"][0]) == 15
        assert all(cell is None for row in game.board_state["board"] for cell in row)


class TestGameRelationships:
    """Test cases for Game model relationships."""

    async def test_black_player_relationship(self, db_session: AsyncSession) -> None:
        """Test the relationship to the black player."""
        black_player = User(username="blackrel")
        ruleset = RuleSet(name="Rel Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Load the relationship
        result = await db_session.execute(
            select(Game).where(Game.id == game.id).options()
        )
        loaded_game = result.scalar_one()
        
        # Test relationship loading
        assert loaded_game.black_player_id == black_player.id

    async def test_white_player_relationship(self, db_session: AsyncSession) -> None:
        """Test the relationship to the white player."""
        black_player = User(username="blackrel2")
        white_player = User(username="whiterel2")
        ruleset = RuleSet(name="Rel Rules 2", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Load the relationship
        result = await db_session.execute(
            select(Game).where(Game.id == game.id)
        )
        loaded_game = result.scalar_one()
        
        assert loaded_game.white_player_id == white_player.id

    async def test_ruleset_relationship(self, db_session: AsyncSession) -> None:
        """Test the relationship to the ruleset."""
        black_player = User(username="rulerel")
        ruleset = RuleSet(name="Rule Rel", board_size=19, allow_overlines=True)
        
        db_session.add_all([black_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Load the relationship
        result = await db_session.execute(
            select(Game).where(Game.id == game.id)
        )
        loaded_game = result.scalar_one()
        
        assert loaded_game.ruleset_id == ruleset.id

    async def test_winner_relationship(self, db_session: AsyncSession) -> None:
        """Test the relationship to the winner."""
        black_player = User(username="winnerrel")
        white_player = User(username="winnerrel2")
        ruleset = RuleSet(name="Winner Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id,
            status=GameStatus.FINISHED,
            winner_id=black_player.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Load the relationship
        result = await db_session.execute(
            select(Game).where(Game.id == game.id)
        )
        loaded_game = result.scalar_one()
        
        assert loaded_game.winner_id == black_player.id


class TestGameConstraints:
    """Test cases for Game model constraints and validation."""

    async def test_black_player_required(self, db_session: AsyncSession) -> None:
        """Test that black_player_id is required."""
        ruleset = RuleSet(name="Constraint Rules", board_size=15, allow_overlines=False)
        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=None,  # This should fail
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_ruleset_required(self, db_session: AsyncSession) -> None:
        """Test that ruleset_id is required."""
        black_player = User(username="constrainttest")
        db_session.add(black_player)
        await db_session.commit()
        await db_session.refresh(black_player)

        game = Game(
            black_player_id=black_player.id,
            ruleset_id=None  # This should fail
        )

        db_session.add(game)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_foreign_key_constraints(self, db_session: AsyncSession) -> None:
        """Test foreign key constraints for non-existent references."""
        # Test with non-existent black player
        game = Game(
            black_player_id=999999,  # Non-existent ID
            ruleset_id=1
        )

        db_session.add(game)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_move_count_non_negative(self, db_session: AsyncSession) -> None:
        """Test that move_count cannot be negative."""
        black_player = User(username="movetest")
        ruleset = RuleSet(name="Move Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(ruleset)

        # This should fail with ValueError during model validation
        with pytest.raises(ValueError):
            game = Game(
                black_player_id=black_player.id,
                ruleset_id=ruleset.id,
                move_count=-1  # This should fail
            )

    async def test_winner_must_be_player(self, db_session: AsyncSession) -> None:
        """Test that winner must be either black or white player."""
        black_player = User(username="winnertest1")
        white_player = User(username="winnertest2")
        other_user = User(username="otheruser")
        ruleset = RuleSet(name="Winner Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, other_user, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(other_user)
        await db_session.refresh(ruleset)

        # This should fail - winner is not one of the players  
        with pytest.raises(ValueError):
            game = Game(
                black_player_id=black_player.id,
                white_player_id=white_player.id,
                ruleset_id=ruleset.id,
                winner_id=other_user.id
            )


class TestGameLogicMethods:
    """Test cases for Game model logic methods."""

    async def test_initialize_board(self, db_session: AsyncSession) -> None:
        """Test board initialization method."""
        black_player = User(username="boardlogic")
        ruleset = RuleSet(name="Logic Rules", board_size=19, allow_overlines=False)
        
        db_session.add_all([black_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Test initialize_board method
        game.initialize_board(19)
        
        expected_board = {
            "board": [[None for _ in range(19)] for _ in range(19)],
            "size": 19
        }
        assert game.board_state == expected_board

    async def test_is_valid_position(self, db_session: AsyncSession) -> None:
        """Test position validation method."""
        black_player = User(username="poslogic")
        ruleset = RuleSet(name="Position Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Test valid positions
        assert game.is_valid_position(0, 0) is True
        assert game.is_valid_position(7, 7) is True
        assert game.is_valid_position(14, 14) is True

        # Test invalid positions
        assert game.is_valid_position(-1, 0) is False
        assert game.is_valid_position(0, -1) is False
        assert game.is_valid_position(15, 0) is False
        assert game.is_valid_position(0, 15) is False

    async def test_make_move(self, db_session: AsyncSession) -> None:
        """Test making a move in the game."""
        black_player = User(username="movelogic")
        white_player = User(username="movelogic2")
        ruleset = RuleSet(name="Move Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id,
            status=GameStatus.ACTIVE
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Make first move (black)
        success = game.make_move(7, 7)
        assert success is True
        assert game.board_state["board"][7][7] == "black"
        assert game.current_player == Player.WHITE
        assert game.move_count == 1

        # Make second move (white)
        success = game.make_move(7, 8)
        assert success is True
        assert game.board_state["board"][7][8] == "white"
        assert game.current_player == Player.BLACK
        assert game.move_count == 2

    async def test_make_move_invalid_position(self, db_session: AsyncSession) -> None:
        """Test making a move to an invalid position."""
        black_player = User(username="invalidmove")
        ruleset = RuleSet(name="Invalid Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            ruleset_id=ruleset.id,
            status=GameStatus.ACTIVE
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Try invalid positions
        assert game.make_move(-1, 0) is False
        assert game.make_move(0, -1) is False
        assert game.make_move(15, 0) is False
        assert game.make_move(0, 15) is False

        # Move count should not change
        assert game.move_count == 0
        assert game.current_player == Player.BLACK

    async def test_make_move_occupied_position(self, db_session: AsyncSession) -> None:
        """Test making a move to an already occupied position."""
        black_player = User(username="occupiedmove")
        white_player = User(username="occupiedmove2")
        ruleset = RuleSet(name="Occupied Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id,
            status=GameStatus.ACTIVE
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Make first move
        assert game.make_move(7, 7) is True
        assert game.board_state["board"][7][7] == "black"
        assert game.current_player == Player.WHITE

        # Try to move to same position
        assert game.make_move(7, 7) is False
        assert game.current_player == Player.WHITE  # Should not change
        assert game.move_count == 1  # Should not increment

    async def test_start_game(self, db_session: AsyncSession) -> None:
        """Test starting a game."""
        black_player = User(username="startlogic")
        white_player = User(username="startlogic2")
        ruleset = RuleSet(name="Start Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Start the game
        game.start_game()
        
        assert game.status == GameStatus.ACTIVE
        assert isinstance(game.started_at, datetime)
        assert game.current_player == Player.BLACK

    async def test_end_game(self, db_session: AsyncSession) -> None:
        """Test ending a game."""
        black_player = User(username="endlogic")
        white_player = User(username="endlogic2")
        ruleset = RuleSet(name="End Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id,
            status=GameStatus.ACTIVE
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # End the game with black player winning
        game.end_game(black_player.id)
        
        assert game.status == GameStatus.FINISHED
        assert game.winner_id == black_player.id
        assert isinstance(game.finished_at, datetime)

    async def test_abandon_game(self, db_session: AsyncSession) -> None:
        """Test abandoning a game."""
        black_player = User(username="abandonlogic")
        white_player = User(username="abandonlogic2")
        ruleset = RuleSet(name="Abandon Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id,
            status=GameStatus.ACTIVE
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Abandon the game
        game.abandon_game()
        
        assert game.status == GameStatus.ABANDONED
        assert isinstance(game.finished_at, datetime)
        assert game.winner_id is None  # No winner when abandoned


class TestGameStateQueries:
    """Test cases for Game model state query methods."""

    async def test_is_game_over(self, db_session: AsyncSession) -> None:
        """Test game over detection."""
        black_player = User(username="gameovertest")
        ruleset = RuleSet(name="GameOver Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(ruleset)

        # Test active game
        game = Game(
            black_player_id=black_player.id,
            ruleset_id=ruleset.id,
            status=GameStatus.ACTIVE
        )
        assert game.is_game_over is False

        # Test finished game
        game.status = GameStatus.FINISHED
        assert game.is_game_over is True

        # Test abandoned game
        game.status = GameStatus.ABANDONED
        assert game.is_game_over is True

        # Test waiting game
        game.status = GameStatus.WAITING
        assert game.is_game_over is False


    async def test_can_start(self, db_session: AsyncSession) -> None:
        """Test if game can be started."""
        black_player = User(username="canstarttest")
        white_player = User(username="canstarttest2")
        ruleset = RuleSet(name="CanStart Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        # Test single player game (can start)
        game = Game(
            black_player_id=black_player.id,
            ruleset_id=ruleset.id,
            status=GameStatus.WAITING
        )
        assert game.can_start is True  # Single player games can start immediately

        # Test two player game waiting (can start)
        game.white_player_id = white_player.id
        assert game.can_start is True

        # Test already active game (cannot start)
        game.status = GameStatus.ACTIVE
        assert game.can_start is False

        # Test finished game (cannot start)
        game.status = GameStatus.FINISHED
        assert game.can_start is False


class TestGameStringRepresentations:
    """Test cases for Game model string representations."""

    async def test_repr(self, db_session: AsyncSession) -> None:
        """Test __repr__ method."""
        black_player = User(username="reprtest")
        ruleset = RuleSet(name="Repr Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        repr_str = repr(game)
        assert f"Game(id={game.id}" in repr_str
        assert f"status={GameStatus.WAITING}" in repr_str
        assert f"move_count=0" in repr_str

    async def test_str(self, db_session: AsyncSession) -> None:
        """Test __str__ method."""
        black_player = User(username="strtest", display_name="Black Player")
        white_player = User(username="strtest2", display_name="White Player")
        ruleset = RuleSet(name="Str Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        # Two player game
        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        str_repr = str(game)
        assert str_repr == "Two Player Game"

        # Single player game
        game2 = Game(
            black_player_id=black_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game2)
        await db_session.commit()
        await db_session.refresh(game2)

        str_repr2 = str(game2)
        assert str_repr2 == "Single Player Game"


class TestGameToDictMethod:
    """Test cases for Game model to_dict method."""

    async def test_to_dict_basic(self, db_session: AsyncSession) -> None:
        """Test to_dict method with basic game."""
        black_player = User(username="dicttest")
        white_player = User(username="dicttest2")
        ruleset = RuleSet(name="Dict Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id,
            status=GameStatus.ACTIVE,
            move_count=3
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        result = game.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == game.id
        assert result["black_player_id"] == black_player.id
        assert result["white_player_id"] == white_player.id
        assert result["ruleset_id"] == ruleset.id
        assert result["status"] == "active"
        assert result["current_player"] == "black"
        assert result["board_state"] == game.board_state
        assert result["winner_id"] is None
        assert result["move_count"] == 3
        assert result["started_at"] is None
        assert result["finished_at"] is None
        assert "created_at" in result
        assert "updated_at" in result
        assert result["is_game_over"] is False
        assert result["can_start"] is False  # Already active


class TestGameEdgeCases:
    """Test cases for Game model edge cases and error conditions."""

    async def test_board_state_with_moves(self, db_session: AsyncSession) -> None:
        """Test board state with actual moves."""
        black_player = User(username="edgetest")
        white_player = User(username="edgetest2")
        ruleset = RuleSet(name="Edge Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        # Create board with some moves
        board = [[None for _ in range(15)] for _ in range(15)]
        board[7][7] = "black"
        board[7][8] = "white"
        board[8][7] = "black"
        
        board_state = {"board": board, "size": 15}

        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id,
            board_state=board_state,
            move_count=3,
            current_player=Player.WHITE
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        assert game.board_state["board"][7][7] == "black"
        assert game.board_state["board"][7][8] == "white"
        assert game.board_state["board"][8][7] == "black"
        assert game.move_count == 3
        assert game.current_player == Player.WHITE

    async def test_game_status_transitions(self, db_session: AsyncSession) -> None:
        """Test valid game status transitions."""
        black_player = User(username="transitiontest")
        white_player = User(username="transitiontest2")
        ruleset = RuleSet(name="Transition Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, white_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(white_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            white_player_id=white_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # WAITING -> ACTIVE
        assert game.status == GameStatus.WAITING
        game.start_game()
        assert game.status == GameStatus.ACTIVE

        # ACTIVE -> FINISHED
        game.end_game(black_player.id)
        assert game.status == GameStatus.FINISHED
        assert game.winner_id == black_player.id

    async def test_uuid_id_format(self, db_session: AsyncSession) -> None:
        """Test that game IDs are properly formatted UUIDs."""
        black_player = User(username="uuidtest")
        ruleset = RuleSet(name="UUID Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(ruleset)

        game = Game(
            black_player_id=black_player.id,
            ruleset_id=ruleset.id
        )

        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)

        # Test UUID format
        assert isinstance(game.id, str)
        assert len(game.id) == 36
        assert game.id.count('-') == 4
        
        # Test that it's a valid UUID
        try:
            uuid_obj = uuid.UUID(game.id)
            assert str(uuid_obj) == game.id
        except ValueError:
            pytest.fail(f"Game ID {game.id} is not a valid UUID")

    async def test_multiple_games_different_ids(self, db_session: AsyncSession) -> None:
        """Test that multiple games get different UUIDs."""
        black_player = User(username="multitest")
        ruleset = RuleSet(name="Multi Rules", board_size=15, allow_overlines=False)
        
        db_session.add_all([black_player, ruleset])
        await db_session.commit()
        await db_session.refresh(black_player)
        await db_session.refresh(ruleset)

        games = []
        for i in range(5):
            game = Game(
                black_player_id=black_player.id,
                ruleset_id=ruleset.id
            )
            db_session.add(game)
            games.append(game)

        await db_session.commit()
        
        # Refresh all games
        for game in games:
            await db_session.refresh(game)

        # Check all IDs are different
        game_ids = [game.id for game in games]
        assert len(set(game_ids)) == 5  # All IDs should be unique