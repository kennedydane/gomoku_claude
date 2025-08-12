"""
Comprehensive tests for the RuleSet model.

This module contains tests for the RuleSet SQLAlchemy model following TDD principles.
Tests cover model creation, validation, relationships, and edge cases.
"""

from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.ruleset import RuleSet


class TestRuleSetModel:
    """Test cases for basic RuleSet model functionality."""

    async def test_create_standard_ruleset(self, db_session: AsyncSession) -> None:
        """Test creating a standard Gomoku ruleset."""
        ruleset = RuleSet(
            name="Standard",
            board_size=15,
            allow_overlines=False,
            description="Standard Gomoku rules - exactly 5 in a row wins"
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.id is not None
        assert ruleset.name == "Standard"
        assert ruleset.board_size == 15
        assert ruleset.allow_overlines is False
        assert ruleset.forbidden_moves == {}
        assert ruleset.description == "Standard Gomoku rules - exactly 5 in a row wins"
        assert isinstance(ruleset.created_at, datetime)
        assert isinstance(ruleset.updated_at, datetime)
        # For SQLite compatibility, timestamps are timezone-naive
        assert ruleset.created_at.tzinfo is None
        assert ruleset.updated_at.tzinfo is None

    async def test_create_renju_ruleset(self, db_session: AsyncSession) -> None:
        """Test creating a Renju ruleset with forbidden moves."""
        forbidden_moves = {
            "black_forbidden": {
                "three_three": True,
                "four_four": True,
                "overlines": True
            },
            "board_size_restriction": 15
        }

        ruleset = RuleSet(
            name="Renju",
            board_size=15,
            allow_overlines=False,
            forbidden_moves=forbidden_moves,
            description="Renju rules with forbidden moves for Black"
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.name == "Renju"
        assert ruleset.board_size == 15
        assert ruleset.allow_overlines is False
        assert ruleset.forbidden_moves == forbidden_moves
        assert ruleset.description == "Renju rules with forbidden moves for Black"

    async def test_create_freestyle_ruleset(self, db_session: AsyncSession) -> None:
        """Test creating a Freestyle ruleset."""
        ruleset = RuleSet(
            name="Freestyle",
            board_size=15,
            allow_overlines=True,
            description="Freestyle Gomoku - overlines count as wins"
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.name == "Freestyle"
        assert ruleset.board_size == 15
        assert ruleset.allow_overlines is True
        assert ruleset.forbidden_moves == {}

    async def test_create_caro_ruleset(self, db_session: AsyncSession) -> None:
        """Test creating a Caro ruleset."""
        caro_rules = {
            "win_condition": "unblocked_five_or_overline",
            "blocking_required": True
        }

        ruleset = RuleSet(
            name="Caro",
            board_size=15,
            allow_overlines=True,
            forbidden_moves=caro_rules,
            description="Caro rules - unblocked 5-in-a-row or overlines"
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.name == "Caro"
        assert ruleset.forbidden_moves == caro_rules

    async def test_create_swap2_ruleset(self, db_session: AsyncSession) -> None:
        """Test creating a Swap2 tournament ruleset."""
        swap2_rules = {
            "opening_rule": "swap2",
            "tournament_format": True,
            "phases": ["initial_moves", "swap_decision", "normal_play"]
        }

        ruleset = RuleSet(
            name="Swap2",
            board_size=15,
            allow_overlines=False,
            forbidden_moves=swap2_rules,
            description="Swap2 tournament opening rule"
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.name == "Swap2"
        assert ruleset.forbidden_moves == swap2_rules


class TestRuleSetValidation:
    """Test cases for RuleSet model validation and constraints."""

    async def test_name_required(self, db_session: AsyncSession) -> None:
        """Test that name is required."""
        with pytest.raises(IntegrityError):
            ruleset = RuleSet(
                board_size=15,
                allow_overlines=False
            )
            db_session.add(ruleset)
            await db_session.commit()

    async def test_board_size_required(self, db_session: AsyncSession) -> None:
        """Test that board_size is required."""
        with pytest.raises(IntegrityError):
            ruleset = RuleSet(
                name="Test",
                allow_overlines=False
            )
            db_session.add(ruleset)
            await db_session.commit()

    async def test_allow_overlines_required(self, db_session: AsyncSession) -> None:
        """Test that allow_overlines is required."""
        with pytest.raises(IntegrityError):
            ruleset = RuleSet(
                name="Test",
                board_size=15
            )
            db_session.add(ruleset)
            await db_session.commit()

    async def test_valid_board_sizes(self, db_session: AsyncSession) -> None:
        """Test various valid board sizes."""
        valid_sizes = [15, 19, 13, 9]

        for size in valid_sizes:
            ruleset = RuleSet(
                name=f"Test_{size}",
                board_size=size,
                allow_overlines=False
            )
            db_session.add(ruleset)

        await db_session.commit()

        # Verify all were created
        result = await db_session.execute(select(RuleSet))
        rulesets = result.scalars().all()
        assert len(rulesets) == len(valid_sizes)

    async def test_name_uniqueness(self, db_session: AsyncSession) -> None:
        """Test that ruleset names should be unique."""
        # Create first ruleset
        ruleset1 = RuleSet(
            name="Unique",
            board_size=15,
            allow_overlines=False
        )
        db_session.add(ruleset1)
        await db_session.commit()

        # Try to create another with same name
        with pytest.raises(IntegrityError):
            ruleset2 = RuleSet(
                name="Unique",
                board_size=19,
                allow_overlines=True
            )
            db_session.add(ruleset2)
            await db_session.commit()

    async def test_description_optional(self, db_session: AsyncSession) -> None:
        """Test that description is optional."""
        ruleset = RuleSet(
            name="No Description",
            board_size=15,
            allow_overlines=False
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.description is None


class TestRuleSetJSONField:
    """Test cases for the JSON forbidden_moves field."""

    async def test_empty_forbidden_moves(self, db_session: AsyncSession) -> None:
        """Test that forbidden_moves defaults to empty dict."""
        ruleset = RuleSet(
            name="Empty Rules",
            board_size=15,
            allow_overlines=False
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.forbidden_moves == {}

    async def test_complex_forbidden_moves_structure(self, db_session: AsyncSession) -> None:
        """Test storing complex JSON structure in forbidden_moves."""
        complex_rules = {
            "renju": {
                "black_restrictions": {
                    "three_three": {"enabled": True, "exceptions": ["center"]},
                    "four_four": {"enabled": True, "exceptions": []},
                    "overline": {"enabled": True, "length_limit": 5}
                },
                "white_restrictions": {},
                "board_specific": {
                    "corners": {"x": [0, 14], "y": [0, 14]},
                    "center": {"x": 7, "y": 7}
                }
            },
            "tournament_settings": {
                "time_control": {"type": "fischer", "base": 900, "increment": 15},
                "opening_book": {"enabled": False, "depth": 0}
            }
        }

        ruleset = RuleSet(
            name="Complex Rules",
            board_size=15,
            allow_overlines=False,
            forbidden_moves=complex_rules
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.forbidden_moves == complex_rules
        assert ruleset.forbidden_moves["renju"]["black_restrictions"]["three_three"]["enabled"] is True

    async def test_json_serialization_deserialization(self, db_session: AsyncSession) -> None:
        """Test that JSON data survives database round-trip."""
        original_data = {
            "arrays": [1, 2, 3, "test"],
            "nested": {"bool": True, "null": None},
            "number": 42.5,
            "unicode": "测试🎮"
        }

        ruleset = RuleSet(
            name="JSON Test",
            board_size=15,
            allow_overlines=False,
            forbidden_moves=original_data
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.forbidden_moves == original_data

    async def test_update_forbidden_moves(self, db_session: AsyncSession) -> None:
        """Test updating the forbidden_moves JSON field."""
        ruleset = RuleSet(
            name="Updatable",
            board_size=15,
            allow_overlines=False,
            forbidden_moves={"initial": "value"}
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        # Update the JSON field
        new_rules = {"updated": "value", "count": 123}
        ruleset.forbidden_moves = new_rules
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.forbidden_moves == new_rules


class TestRuleSetTimestamps:
    """Test cases for created_at and updated_at timestamp behavior."""

    async def test_created_at_auto_populated(self, db_session: AsyncSession) -> None:
        """Test that created_at is automatically set on creation."""
        ruleset = RuleSet(
            name="Timestamp Test",
            board_size=15,
            allow_overlines=False
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        # Just verify that created_at is set to a valid datetime
        assert ruleset.created_at is not None
        assert isinstance(ruleset.created_at, datetime)
        assert ruleset.created_at.tzinfo is None  # SQLite compatibility

        # Verify it's recent (within last few hours to account for timezone differences)
        now = datetime.now()
        time_diff = abs((now - ruleset.created_at).total_seconds())
        assert time_diff < 86400  # Should be less than 24 hours ago (very generous for testing)

    async def test_updated_at_auto_populated(self, db_session: AsyncSession) -> None:
        """Test that updated_at is automatically set on creation."""
        ruleset = RuleSet(
            name="Update Test",
            board_size=15,
            allow_overlines=False
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.updated_at is not None
        assert ruleset.updated_at.tzinfo is None  # SQLite compatibility
        # On creation, updated_at should be very close to created_at
        time_diff = abs((ruleset.updated_at - ruleset.created_at).total_seconds())
        assert time_diff < 1  # Should be less than 1 second difference

    async def test_updated_at_changes_on_update(self, db_session: AsyncSession) -> None:
        """Test that updated_at is automatically updated when record changes."""
        ruleset = RuleSet(
            name="Auto Update",
            board_size=15,
            allow_overlines=False
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        original_updated_at = ruleset.updated_at

        # Wait a small amount and update
        import asyncio
        await asyncio.sleep(0.1)

        ruleset.description = "Updated description"
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.updated_at > original_updated_at

    async def test_created_at_unchanged_on_update(self, db_session: AsyncSession) -> None:
        """Test that created_at doesn't change when record is updated."""
        ruleset = RuleSet(
            name="Stable Created",
            board_size=15,
            allow_overlines=False
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        original_created_at = ruleset.created_at

        # Update the record
        ruleset.description = "Updated description"
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.created_at == original_created_at


class TestRuleSetQueries:
    """Test cases for querying RuleSet records."""

    async def test_query_by_name(self, db_session: AsyncSession) -> None:
        """Test querying rulesets by name."""
        rulesets = [
            RuleSet(name="Standard", board_size=15, allow_overlines=False),
            RuleSet(name="Renju", board_size=15, allow_overlines=False),
            RuleSet(name="Freestyle", board_size=15, allow_overlines=True),
        ]

        for ruleset in rulesets:
            db_session.add(ruleset)
        await db_session.commit()

        # Query for specific ruleset
        result = await db_session.execute(
            select(RuleSet).where(RuleSet.name == "Renju")
        )
        renju_ruleset = result.scalar_one()

        assert renju_ruleset.name == "Renju"
        assert renju_ruleset.allow_overlines is False

    async def test_query_by_board_size(self, db_session: AsyncSession) -> None:
        """Test querying rulesets by board size."""
        rulesets = [
            RuleSet(name="Small", board_size=13, allow_overlines=False),
            RuleSet(name="Standard", board_size=15, allow_overlines=False),
            RuleSet(name="Large", board_size=19, allow_overlines=False),
        ]

        for ruleset in rulesets:
            db_session.add(ruleset)
        await db_session.commit()

        # Query for 15x15 boards
        result = await db_session.execute(
            select(RuleSet).where(RuleSet.board_size == 15)
        )
        standard_ruleset = result.scalar_one()

        assert standard_ruleset.board_size == 15
        assert standard_ruleset.name == "Standard"

    async def test_query_by_overlines_allowed(self, db_session: AsyncSession) -> None:
        """Test querying rulesets by overlines policy."""
        rulesets = [
            RuleSet(name="Standard", board_size=15, allow_overlines=False),
            RuleSet(name="Freestyle", board_size=15, allow_overlines=True),
            RuleSet(name="Caro", board_size=15, allow_overlines=True),
        ]

        for ruleset in rulesets:
            db_session.add(ruleset)
        await db_session.commit()

        # Query for rulesets that allow overlines
        result = await db_session.execute(
            select(RuleSet).where(RuleSet.allow_overlines.is_(True))
        )
        overline_rulesets = result.scalars().all()

        assert len(overline_rulesets) == 2
        names = {rs.name for rs in overline_rulesets}
        assert names == {"Freestyle", "Caro"}

    async def test_order_by_created_at(self, db_session: AsyncSession) -> None:
        """Test ordering rulesets by creation time."""
        import asyncio

        ruleset1 = RuleSet(name="First", board_size=15, allow_overlines=False)
        db_session.add(ruleset1)
        await db_session.commit()

        await asyncio.sleep(0.1)  # Ensure different timestamps

        ruleset2 = RuleSet(name="Second", board_size=15, allow_overlines=False)
        db_session.add(ruleset2)
        await db_session.commit()

        # Query ordered by created_at
        result = await db_session.execute(
            select(RuleSet).order_by(RuleSet.created_at)
        )
        ordered_rulesets = result.scalars().all()

        assert len(ordered_rulesets) == 2
        assert ordered_rulesets[0].name == "First"
        assert ordered_rulesets[1].name == "Second"
        assert ordered_rulesets[0].created_at < ordered_rulesets[1].created_at


class TestRuleSetEdgeCases:
    """Test cases for edge cases and error conditions."""

    async def test_extremely_long_name(self, db_session: AsyncSession) -> None:
        """Test handling of very long ruleset names."""
        long_name = "A" * 500  # Very long name

        ruleset = RuleSet(
            name=long_name,
            board_size=15,
            allow_overlines=False
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.name == long_name

    async def test_large_json_forbidden_moves(self, db_session: AsyncSession) -> None:
        """Test handling of large JSON data in forbidden_moves."""
        large_data = {
            f"rule_{i}": {
                "description": f"Rule number {i}" * 10,
                "conditions": list(range(100)),
                "metadata": {"created": f"2024-01-{i:02d}", "priority": i}
            }
            for i in range(1, 101)  # 100 rules
        }

        ruleset = RuleSet(
            name="Large JSON",
            board_size=15,
            allow_overlines=False,
            forbidden_moves=large_data
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert len(ruleset.forbidden_moves) == 100
        assert ruleset.forbidden_moves["rule_50"]["metadata"]["priority"] == 50

    async def test_unicode_in_all_fields(self, db_session: AsyncSession) -> None:
        """Test Unicode support in all text fields."""
        unicode_data = {
            "中文": "测试",
            "日本語": "テスト",
            "한국어": "테스트",
            "العربية": "اختبار",
            "русский": "тест",
            "emoji": "🎮🔥⭐"
        }

        ruleset = RuleSet(
            name="Unicode测试🎮",
            board_size=15,
            allow_overlines=False,
            forbidden_moves=unicode_data,
            description="Description with 中文, 日本語, and emoji 🎮"
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.name == "Unicode测试🎮"
        assert "🎮🔥⭐" in ruleset.forbidden_moves["emoji"]
        assert "中文" in ruleset.description

    async def test_null_vs_empty_json(self, db_session: AsyncSession) -> None:
        """Test distinction between null and empty JSON."""
        # Test with explicit None
        ruleset1 = RuleSet(
            name="Explicit None",
            board_size=15,
            allow_overlines=False,
            forbidden_moves=None
        )

        # Test with explicit empty dict
        ruleset2 = RuleSet(
            name="Empty Dict",
            board_size=15,
            allow_overlines=False,
            forbidden_moves={}
        )

        db_session.add_all([ruleset1, ruleset2])
        await db_session.commit()
        await db_session.refresh(ruleset1)
        await db_session.refresh(ruleset2)

        # Both should result in empty dict due to default value
        assert ruleset1.forbidden_moves == {}
        assert ruleset2.forbidden_moves == {}


class TestRuleSetClassMethods:
    """Test cases for RuleSet class method factories."""

    async def test_create_standard_ruleset_factory(self, db_session: AsyncSession) -> None:
        """Test the create_standard_ruleset factory method."""
        ruleset = RuleSet.create_standard_ruleset()

        assert ruleset.name == "Standard"
        assert ruleset.board_size == 15
        assert ruleset.allow_overlines is False
        assert ruleset.forbidden_moves == {}
        assert ruleset.description == "Standard Gomoku rules - exactly 5 in a row wins"

        # Test that it can be persisted
        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.id is not None
        assert ruleset.is_standard_gomoku is True
        assert ruleset.is_renju is False
        assert ruleset.is_freestyle is False

    async def test_create_renju_ruleset_factory(self, db_session: AsyncSession) -> None:
        """Test the create_renju_ruleset factory method."""
        ruleset = RuleSet.create_renju_ruleset()

        assert ruleset.name == "Renju"
        assert ruleset.board_size == 15
        assert ruleset.allow_overlines is False
        assert "black_forbidden" in ruleset.forbidden_moves
        assert ruleset.forbidden_moves["black_forbidden"]["three_three"] is True
        assert ruleset.forbidden_moves["black_forbidden"]["four_four"] is True
        assert ruleset.forbidden_moves["black_forbidden"]["overlines"] is True
        assert ruleset.description == "Renju rules with forbidden moves for Black (3-3, 4-4, overlines)"

        # Test that it can be persisted
        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.id is not None
        assert ruleset.is_standard_gomoku is False
        assert ruleset.is_renju is True
        assert ruleset.is_freestyle is False

    async def test_create_freestyle_ruleset_factory(self, db_session: AsyncSession) -> None:
        """Test the create_freestyle_ruleset factory method."""
        ruleset = RuleSet.create_freestyle_ruleset()

        assert ruleset.name == "Freestyle"
        assert ruleset.board_size == 15
        assert ruleset.allow_overlines is True
        assert ruleset.forbidden_moves == {}
        assert ruleset.description == "Freestyle Gomoku - overlines count as wins"

        # Test that it can be persisted
        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.id is not None
        assert ruleset.is_standard_gomoku is False
        assert ruleset.is_renju is False
        assert ruleset.is_freestyle is True

    async def test_create_caro_ruleset_factory(self, db_session: AsyncSession) -> None:
        """Test the create_caro_ruleset factory method."""
        ruleset = RuleSet.create_caro_ruleset()

        assert ruleset.name == "Caro"
        assert ruleset.board_size == 15
        assert ruleset.allow_overlines is True
        assert "win_condition" in ruleset.forbidden_moves
        assert ruleset.forbidden_moves["win_condition"] == "unblocked_five_or_overline"
        assert ruleset.forbidden_moves["blocking_required"] is True
        assert ruleset.description == "Caro rules - unblocked 5-in-a-row or overlines to win"

        # Test that it can be persisted
        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.id is not None

    async def test_create_swap2_ruleset_factory(self, db_session: AsyncSession) -> None:
        """Test the create_swap2_ruleset factory method."""
        ruleset = RuleSet.create_swap2_ruleset()

        assert ruleset.name == "Swap2"
        assert ruleset.board_size == 15
        assert ruleset.allow_overlines is False
        assert "opening_rule" in ruleset.forbidden_moves
        assert ruleset.forbidden_moves["opening_rule"] == "swap2"
        assert ruleset.forbidden_moves["tournament_format"] is True
        assert "phases" in ruleset.forbidden_moves
        assert ruleset.description == "Swap2 tournament opening rule"

        # Test that it can be persisted
        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        assert ruleset.id is not None
        assert ruleset.has_opening_rule() is True

    async def test_all_factory_methods_create_unique_names(self, db_session: AsyncSession) -> None:
        """Test that all factory methods create rulesets with unique names."""
        rulesets = [
            RuleSet.create_standard_ruleset(),
            RuleSet.create_renju_ruleset(),
            RuleSet.create_freestyle_ruleset(),
            RuleSet.create_caro_ruleset(),
            RuleSet.create_swap2_ruleset(),
        ]

        names = {rs.name for rs in rulesets}
        assert len(names) == 5  # All names should be unique
        assert names == {"Standard", "Renju", "Freestyle", "Caro", "Swap2"}

        # Test that they can all be persisted
        for ruleset in rulesets:
            db_session.add(ruleset)

        await db_session.commit()

        # Verify all were saved
        result = await db_session.execute(select(RuleSet))
        saved_rulesets = result.scalars().all()
        assert len(saved_rulesets) == 5


class TestRuleSetProperties:
    """Test cases for RuleSet property methods."""

    async def test_is_standard_gomoku_property(self, db_session: AsyncSession) -> None:
        """Test the is_standard_gomoku property."""
        # Standard ruleset should return True
        standard = RuleSet.create_standard_ruleset()
        assert standard.is_standard_gomoku is True

        # Renju should return False (has forbidden moves)
        renju = RuleSet.create_renju_ruleset()
        assert renju.is_standard_gomoku is False

        # Freestyle should return False (allows overlines)
        freestyle = RuleSet.create_freestyle_ruleset()
        assert freestyle.is_standard_gomoku is False

        # Custom standard-like but with wrong board size
        custom = RuleSet(
            name="Custom",
            board_size=13,  # Non-standard size
            allow_overlines=False
        )
        assert custom.is_standard_gomoku is True  # Still valid for different sizes

        # Custom with forbidden moves
        custom_with_rules = RuleSet(
            name="Custom Rules",
            board_size=15,
            allow_overlines=False,
            forbidden_moves={"some": "rule"}
        )
        assert custom_with_rules.is_standard_gomoku is False

    async def test_is_renju_property(self, db_session: AsyncSession) -> None:
        """Test the is_renju property."""
        # Renju ruleset should return True
        renju = RuleSet.create_renju_ruleset()
        assert renju.is_renju is True

        # Standard should return False
        standard = RuleSet.create_standard_ruleset()
        assert standard.is_renju is False

        # Custom renju-like with black_forbidden
        custom_renju = RuleSet(
            name="Custom Renju",
            board_size=15,
            allow_overlines=False,
            forbidden_moves={"black_forbidden": {"three_three": True}}
        )
        assert custom_renju.is_renju is True

        # Wrong board size for renju
        wrong_size = RuleSet(
            name="Wrong Size",
            board_size=19,
            allow_overlines=False,
            forbidden_moves={"black_forbidden": {"three_three": True}}
        )
        assert wrong_size.is_renju is False

    async def test_is_freestyle_property(self, db_session: AsyncSession) -> None:
        """Test the is_freestyle property."""
        # Freestyle ruleset should return True
        freestyle = RuleSet.create_freestyle_ruleset()
        assert freestyle.is_freestyle is True

        # Standard should return False
        standard = RuleSet.create_standard_ruleset()
        assert standard.is_freestyle is False

        # Custom freestyle with overlines but no black forbidden moves
        custom_freestyle = RuleSet(
            name="Custom Freestyle",
            board_size=19,
            allow_overlines=True,
            forbidden_moves={"other": "rules"}
        )
        assert custom_freestyle.is_freestyle is True

        # Allows overlines but has black forbidden moves (not pure freestyle)
        mixed = RuleSet(
            name="Mixed",
            board_size=15,
            allow_overlines=True,
            forbidden_moves={"black_forbidden": {"three_three": True}}
        )
        assert mixed.is_freestyle is False

    async def test_get_forbidden_moves_for_player(self, db_session: AsyncSession) -> None:
        """Test the get_forbidden_moves_for_player method."""
        # Renju ruleset with black forbidden moves
        renju = RuleSet.create_renju_ruleset()

        black_rules = renju.get_forbidden_moves_for_player(is_black=True)
        assert "three_three" in black_rules
        assert black_rules["three_three"] is True

        white_rules = renju.get_forbidden_moves_for_player(is_black=False)
        assert white_rules == {}  # No white restrictions in standard Renju

        # Custom ruleset with both black and white rules
        custom = RuleSet(
            name="Custom",
            board_size=15,
            allow_overlines=False,
            forbidden_moves={
                "black_forbidden": {"three_three": True},
                "white_forbidden": {"some_rule": True}
            }
        )

        black_rules = custom.get_forbidden_moves_for_player(is_black=True)
        assert black_rules == {"three_three": True}

        white_rules = custom.get_forbidden_moves_for_player(is_black=False)
        assert white_rules == {"some_rule": True}

        # Empty ruleset
        empty = RuleSet.create_standard_ruleset()
        assert empty.get_forbidden_moves_for_player(is_black=True) == {}
        assert empty.get_forbidden_moves_for_player(is_black=False) == {}

    async def test_has_opening_rule(self, db_session: AsyncSession) -> None:
        """Test the has_opening_rule method."""
        # Swap2 should have opening rule
        swap2 = RuleSet.create_swap2_ruleset()
        assert swap2.has_opening_rule() is True

        # Standard should not
        standard = RuleSet.create_standard_ruleset()
        assert standard.has_opening_rule() is False

        # Custom with tournament settings
        tournament = RuleSet(
            name="Tournament",
            board_size=15,
            allow_overlines=False,
            forbidden_moves={"tournament_settings": {"time_control": "fischer"}}
        )
        assert tournament.has_opening_rule() is True

    async def test_get_win_condition(self, db_session: AsyncSession) -> None:
        """Test the get_win_condition method."""
        # Standard Gomoku
        standard = RuleSet.create_standard_ruleset()
        assert standard.get_win_condition() == "Exactly 5 in a row"

        # Freestyle allows overlines
        freestyle = RuleSet.create_freestyle_ruleset()
        assert freestyle.get_win_condition() == "5 or more in a row"

        # Custom without overlines
        custom = RuleSet(
            name="Custom",
            board_size=15,
            allow_overlines=False
        )
        assert custom.get_win_condition() == "Exactly 5 in a row"

    async def test_to_dict_method(self, db_session: AsyncSession) -> None:
        """Test the to_dict serialization method."""
        ruleset = RuleSet.create_renju_ruleset()

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        result = ruleset.to_dict()

        # Check all expected keys are present
        expected_keys = {
            "id", "name", "board_size", "allow_overlines", "forbidden_moves",
            "description", "created_at", "updated_at", "win_condition",
            "is_standard_gomoku", "is_renju", "is_freestyle", "has_opening_rule"
        }
        assert set(result.keys()) == expected_keys

        # Check values
        assert result["id"] == ruleset.id
        assert result["name"] == "Renju"
        assert result["board_size"] == 15
        assert result["allow_overlines"] is False
        assert result["is_renju"] is True
        assert result["is_standard_gomoku"] is False
        assert result["win_condition"] == "Exactly 5 in a row"
        assert isinstance(result["created_at"], str)  # Should be ISO format
        assert isinstance(result["updated_at"], str)

    async def test_str_and_repr_methods(self, db_session: AsyncSession) -> None:
        """Test the __str__ and __repr__ methods."""
        ruleset = RuleSet(
            name="Test",
            board_size=15,
            allow_overlines=False
        )

        db_session.add(ruleset)
        await db_session.commit()
        await db_session.refresh(ruleset)

        # Test __str__
        str_result = str(ruleset)
        assert str_result == "Test (15x15)"

        # Test __repr__
        repr_result = repr(ruleset)
        expected = f"<RuleSet(id={ruleset.id}, name='Test', board_size=15, allow_overlines=False)>"
        assert repr_result == expected
