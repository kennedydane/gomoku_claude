"""
Comprehensive tests for the User model.

This module contains tests for the User SQLAlchemy model following TDD principles.
Tests cover model creation, validation, relationships, and edge cases.
"""

import re
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.user import User


class TestUserModel:
    """Test cases for basic User model functionality."""

    async def test_create_user_with_required_fields(self, db_session: AsyncSession) -> None:
        """Test creating a user with only required fields."""
        user = User(username="testuser")

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email is None
        assert user.display_name is None
        assert user.games_played == 0
        assert user.games_won == 0
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        # For SQLite compatibility, timestamps are timezone-naive
        assert user.created_at.tzinfo is None
        assert user.updated_at.tzinfo is None

    async def test_create_user_with_all_fields(self, db_session: AsyncSession) -> None:
        """Test creating a user with all fields populated."""
        user = User(
            username="fulluser",
            email="fulluser@example.com",
            display_name="Full User Name",
            games_played=10,
            games_won=7,
            is_active=True
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.username == "fulluser"
        assert user.email == "fulluser@example.com"
        assert user.display_name == "Full User Name"
        assert user.games_played == 10
        assert user.games_won == 7
        assert user.is_active is True

    async def test_create_user_with_email_only(self, db_session: AsyncSession) -> None:
        """Test creating a user with email but no display name."""
        user = User(
            username="emailuser",
            email="email@example.com"
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.username == "emailuser"
        assert user.email == "email@example.com"
        assert user.display_name is None

    async def test_create_user_with_display_name_only(self, db_session: AsyncSession) -> None:
        """Test creating a user with display name but no email."""
        user = User(
            username="displayuser",
            display_name="Display User"
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.username == "displayuser"
        assert user.email is None
        assert user.display_name == "Display User"

    async def test_create_inactive_user(self, db_session: AsyncSession) -> None:
        """Test creating an inactive user (soft deletion)."""
        user = User(
            username="inactiveuser",
            is_active=False
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.username == "inactiveuser"
        assert user.is_active is False


class TestUserValidation:
    """Test cases for User model validation and constraints."""

    async def test_username_required(self, db_session: AsyncSession) -> None:
        """Test that username is required."""
        with pytest.raises(IntegrityError):
            user = User(email="test@example.com")
            db_session.add(user)
            await db_session.commit()

    async def test_username_uniqueness(self, db_session: AsyncSession) -> None:
        """Test that usernames must be unique."""
        # Create first user
        user1 = User(username="uniqueuser")
        db_session.add(user1)
        await db_session.commit()

        # Try to create another with same username
        with pytest.raises(IntegrityError):
            user2 = User(username="uniqueuser")
            db_session.add(user2)
            await db_session.commit()

    async def test_username_case_insensitive_uniqueness(self, db_session: AsyncSession) -> None:
        """Test that username uniqueness is case-insensitive."""
        # Create first user
        user1 = User(username="CaseTest")
        db_session.add(user1)
        await db_session.commit()

        # Try to create another with different case
        with pytest.raises(IntegrityError):
            user2 = User(username="casetest")
            db_session.add(user2)
            await db_session.commit()

    async def test_email_uniqueness(self, db_session: AsyncSession) -> None:
        """Test that emails must be unique when provided."""
        # Create first user with email
        user1 = User(username="user1", email="unique@example.com")
        db_session.add(user1)
        await db_session.commit()

        # Try to create another with same email
        with pytest.raises(IntegrityError):
            user2 = User(username="user2", email="unique@example.com")
            db_session.add(user2)
            await db_session.commit()

    async def test_email_optional_allows_multiple_nulls(self, db_session: AsyncSession) -> None:
        """Test that multiple users can have null email."""
        users = [
            User(username="nullemail1"),
            User(username="nullemail2"),
            User(username="nullemail3")
        ]

        for user in users:
            db_session.add(user)
        await db_session.commit()

        # Verify all were created with null emails
        for user in users:
            await db_session.refresh(user)
            assert user.email is None

    async def test_username_length_validation(self, db_session: AsyncSession) -> None:
        """Test username length constraints."""
        # Test minimum length (should be at least 3 characters)
        with pytest.raises(ValueError, match="Username must be at least 3 characters"):
            user = User(username="ab")  # Too short

    async def test_username_format_validation(self, db_session: AsyncSession) -> None:
        """Test valid username formats."""
        valid_usernames = [
            "validformat1",
            "valid_format2",
            "valid-format3", 
            "ValidFormat4",
            "v1b2c3d4",
            "valid_format_underscores",
            "valid-format-hyphens"
        ]

        users = []
        for username in valid_usernames:
            user = User(username=username)
            users.append(user)
            db_session.add(user)

        await db_session.commit()

        # Verify all were created
        assert len(users) == len(valid_usernames)
        for user in users:
            await db_session.refresh(user)
            assert user.id is not None

    async def test_games_played_defaults_to_zero(self, db_session: AsyncSession) -> None:
        """Test that games_played defaults to 0."""
        user = User(username="defaulttest")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.games_played == 0

    async def test_games_won_defaults_to_zero(self, db_session: AsyncSession) -> None:
        """Test that games_won defaults to 0."""
        user = User(username="wontest")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.games_won == 0

    async def test_is_active_defaults_to_true(self, db_session: AsyncSession) -> None:
        """Test that is_active defaults to True."""
        user = User(username="activetest")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.is_active is True

    async def test_games_won_cannot_exceed_games_played(self, db_session: AsyncSession) -> None:
        """Test validation that games_won cannot exceed games_played."""
        # This should be validated at the model level
        with pytest.raises(ValueError, match="Games won cannot exceed games played"):
            user = User(
                username="invalidstats",
                games_played=5,
                games_won=10  # Invalid: more wins than games
            )


class TestUserStatistics:
    """Test cases for user statistics and calculated properties."""

    async def test_win_rate_calculation(self, db_session: AsyncSession) -> None:
        """Test win rate calculation with various scenarios."""
        # User with 0 games
        user1 = User(username="nogames")
        assert user1.win_rate == 0.0

        # User with some wins
        user2 = User(username="somewins", games_played=10, games_won=7)
        assert user2.win_rate == 0.7

        # User with perfect record
        user3 = User(username="perfect", games_played=5, games_won=5)
        assert user3.win_rate == 1.0

        # User with no wins
        user4 = User(username="nowins", games_played=10, games_won=0)
        assert user4.win_rate == 0.0

    async def test_loss_count_calculation(self, db_session: AsyncSession) -> None:
        """Test calculation of losses."""
        user = User(username="losses", games_played=15, games_won=8)
        assert user.losses == 7

        # User with no games
        user2 = User(username="nolosses")
        assert user2.losses == 0

    async def test_has_played_games_property(self, db_session: AsyncSession) -> None:
        """Test has_played_games property."""
        user1 = User(username="played", games_played=1)
        assert user1.has_played_games is True

        user2 = User(username="notplayed")
        assert user2.has_played_games is False

    async def test_is_experienced_property(self, db_session: AsyncSession) -> None:
        """Test is_experienced property (e.g., 10+ games)."""
        user1 = User(username="newbie", games_played=5)
        assert user1.is_experienced is False

        user2 = User(username="veteran", games_played=25)
        assert user2.is_experienced is True

        user3 = User(username="exactly", games_played=10)
        assert user3.is_experienced is True


class TestUserTimestamps:
    """Test cases for created_at and updated_at timestamp behavior."""

    async def test_created_at_auto_populated(self, db_session: AsyncSession) -> None:
        """Test that created_at is automatically set on creation."""
        user = User(username="timestamp")

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)
        assert user.created_at.tzinfo is None  # SQLite compatibility

        # Verify it's recent (be generous with timing due to test environment)
        now = datetime.now()
        time_diff = abs((now - user.created_at).total_seconds())
        assert time_diff < 86400  # Should be less than 24 hours ago

    async def test_updated_at_auto_populated(self, db_session: AsyncSession) -> None:
        """Test that updated_at is automatically set on creation."""
        user = User(username="updatetest")

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.updated_at is not None
        assert user.updated_at.tzinfo is None
        # On creation, updated_at should be very close to created_at
        time_diff = abs((user.updated_at - user.created_at).total_seconds())
        assert time_diff < 1

    async def test_updated_at_changes_on_update(self, db_session: AsyncSession) -> None:
        """Test that updated_at is automatically updated when record changes."""
        user = User(username="autoupdate")

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        original_updated_at = user.updated_at

        # Wait a small amount and update
        import asyncio
        await asyncio.sleep(0.1)

        user.display_name = "Updated Name"
        await db_session.commit()
        await db_session.refresh(user)

        assert user.updated_at > original_updated_at

    async def test_created_at_unchanged_on_update(self, db_session: AsyncSession) -> None:
        """Test that created_at doesn't change when record is updated."""
        user = User(username="stablecreated")

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        original_created_at = user.created_at

        user.display_name = "Updated Name"
        await db_session.commit()
        await db_session.refresh(user)

        assert user.created_at == original_created_at


class TestUserQueries:
    """Test cases for querying User records."""

    async def test_query_by_username(self, db_session: AsyncSession) -> None:
        """Test querying users by username."""
        users = [
            User(username="alice"),
            User(username="bob"),
            User(username="charlie"),
        ]

        for user in users:
            db_session.add(user)
        await db_session.commit()

        # Query for specific user
        result = await db_session.execute(
            select(User).where(User.username == "bob")
        )
        bob_user = result.scalar_one()

        assert bob_user.username == "bob"

    async def test_query_by_email(self, db_session: AsyncSession) -> None:
        """Test querying users by email."""
        users = [
            User(username="user1", email="user1@example.com"),
            User(username="user2", email="user2@example.com"),
            User(username="user3"),  # No email
        ]

        for user in users:
            db_session.add(user)
        await db_session.commit()

        # Query for user with email
        result = await db_session.execute(
            select(User).where(User.email == "user2@example.com")
        )
        user = result.scalar_one()

        assert user.username == "user2"
        assert user.email == "user2@example.com"

    async def test_query_active_users(self, db_session: AsyncSession) -> None:
        """Test querying only active users."""
        users = [
            User(username="active1", is_active=True),
            User(username="active2", is_active=True),
            User(username="inactive", is_active=False),
        ]

        for user in users:
            db_session.add(user)
        await db_session.commit()

        # Query for active users only
        result = await db_session.execute(
            select(User).where(User.is_active.is_(True))
        )
        active_users = result.scalars().all()

        assert len(active_users) == 2
        usernames = {user.username for user in active_users}
        assert usernames == {"active1", "active2"}

    async def test_query_by_games_played_range(self, db_session: AsyncSession) -> None:
        """Test querying users by games played range."""
        users = [
            User(username="newbie", games_played=2),
            User(username="casual", games_played=15),
            User(username="serious", games_played=50),
            User(username="expert", games_played=200),
        ]

        for user in users:
            db_session.add(user)
        await db_session.commit()

        # Query for users with 10-100 games
        result = await db_session.execute(
            select(User).where(
                User.games_played >= 10,
                User.games_played <= 100
            )
        )
        moderate_players = result.scalars().all()

        assert len(moderate_players) == 2
        usernames = {user.username for user in moderate_players}
        assert usernames == {"casual", "serious"}

    async def test_order_by_win_rate(self, db_session: AsyncSession) -> None:
        """Test ordering users by calculated win rate."""
        # Note: This test may need adjustment based on how win_rate is implemented
        # as a hybrid property or calculated field
        users = [
            User(username="average", games_played=10, games_won=5),    # 0.5
            User(username="good", games_played=10, games_won=8),       # 0.8
            User(username="poor", games_played=10, games_won=2),       # 0.2
            User(username="perfect", games_played=5, games_won=5),     # 1.0
        ]

        for user in users:
            db_session.add(user)
        await db_session.commit()

        # For now, just verify we can query and calculate win rates
        result = await db_session.execute(select(User))
        all_users = result.scalars().all()

        # Sort by win rate in Python for now
        sorted_users = sorted(all_users, key=lambda u: u.win_rate, reverse=True)

        assert sorted_users[0].username == "perfect"    # 1.0
        assert sorted_users[1].username == "good"       # 0.8
        assert sorted_users[2].username == "average"    # 0.5
        assert sorted_users[3].username == "poor"       # 0.2


class TestUserEdgeCases:
    """Test cases for edge cases and error conditions."""

    async def test_username_with_special_characters(self, db_session: AsyncSession) -> None:
        """Test usernames with allowed special characters."""
        special_usernames = [
            "user_123",
            "test-user",
            "User_Name-123",
            "a1b2c3_test"
        ]

        for username in special_usernames:
            user = User(username=username)
            db_session.add(user)

        await db_session.commit()

        result = await db_session.execute(select(User))
        users = result.scalars().all()
        assert len(users) == len(special_usernames)

    async def test_very_long_username(self, db_session: AsyncSession) -> None:
        """Test handling of maximum length usernames."""
        # Test at the boundary (50 characters)
        long_username = "a" * 50
        user = User(username=long_username)

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.username == long_username

    async def test_very_long_email(self, db_session: AsyncSession) -> None:
        """Test handling of very long email addresses."""
        long_email = "a" * 200 + "@example.com"
        user = User(username="longemail", email=long_email)

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.email == long_email

    async def test_very_long_display_name(self, db_session: AsyncSession) -> None:
        """Test handling of very long display names."""
        long_display = "A" * 200
        user = User(username="longdisplay", display_name=long_display)

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.display_name == long_display

    async def test_large_game_statistics(self, db_session: AsyncSession) -> None:
        """Test handling of large game counts."""
        user = User(
            username="hardcore",
            games_played=1000000,
            games_won=750000
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.games_played == 1000000
        assert user.games_won == 750000
        assert user.win_rate == 0.75

    async def test_unicode_in_all_fields(self, db_session: AsyncSession) -> None:
        """Test Unicode support in all text fields."""
        user = User(
            username="unicode测试",
            email="测试@example.com",
            display_name="Display Name 测试 🎮"
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.username == "unicode测试"
        assert user.email == "测试@example.com"
        assert "🎮" in user.display_name

    async def test_email_format_variations(self, db_session: AsyncSession) -> None:
        """Test various valid email formats."""
        valid_emails = [
            "simple@example.com",
            "with.dots@example.com",
            "with+plus@example.com",
            "with-hyphens@example.com",
            "numbers123@example.com",
            "subdomain@mail.example.com",
        ]

        for i, email in enumerate(valid_emails):
            user = User(username=f"user{i}", email=email)
            db_session.add(user)

        await db_session.commit()

        result = await db_session.execute(select(User))
        users = result.scalars().all()
        assert len(users) == len(valid_emails)


class TestUserUtilityMethods:
    """Test cases for User utility methods."""

    async def test_str_and_repr_methods(self, db_session: AsyncSession) -> None:
        """Test the __str__ and __repr__ methods."""
        user = User(username="testuser", display_name="Test User")

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Test __str__ - should show display name if available, else username
        str_result = str(user)
        assert "Test User" in str_result or "testuser" in str_result

        # Test __repr__ - should be unambiguous
        repr_result = repr(user)
        assert "User" in repr_result
        assert "testuser" in repr_result
        assert str(user.id) in repr_result

    async def test_to_dict_method(self, db_session: AsyncSession) -> None:
        """Test the to_dict serialization method."""
        user = User(
            username="dictuser",
            email="dict@example.com",
            display_name="Dict User",
            games_played=20,
            games_won=15,
            is_active=True
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        result = user.to_dict()

        # Check all expected keys are present
        expected_keys = {
            "id", "username", "email", "display_name", "games_played", "games_won",
            "is_active", "created_at", "updated_at", "win_rate", "losses", 
            "has_played_games", "is_experienced"
        }
        assert set(result.keys()) == expected_keys

        # Check values
        assert result["id"] == user.id
        assert result["username"] == "dictuser"
        assert result["email"] == "dict@example.com"
        assert result["display_name"] == "Dict User"
        assert result["games_played"] == 20
        assert result["games_won"] == 15
        assert result["win_rate"] == 0.75
        assert result["losses"] == 5
        assert result["has_played_games"] is True
        assert result["is_experienced"] is True
        assert isinstance(result["created_at"], str)  # Should be ISO format
        assert isinstance(result["updated_at"], str)

    async def test_update_game_stats_method(self, db_session: AsyncSession) -> None:
        """Test method for updating game statistics."""
        user = User(username="statsuser")

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Update stats for a win
        user.update_game_stats(won=True)
        assert user.games_played == 1
        assert user.games_won == 1

        # Update stats for a loss
        user.update_game_stats(won=False)
        assert user.games_played == 2
        assert user.games_won == 1

        # Save and verify
        await db_session.commit()
        await db_session.refresh(user)

        assert user.games_played == 2
        assert user.games_won == 1
        assert user.win_rate == 0.5

    async def test_activate_deactivate_methods(self, db_session: AsyncSession) -> None:
        """Test methods for activating/deactivating users."""
        user = User(username="activeuser")

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Should start active
        assert user.is_active is True

        # Deactivate
        user.deactivate()
        assert user.is_active is False

        # Reactivate
        user.activate()
        assert user.is_active is True

    async def test_display_name_or_username_property(self, db_session: AsyncSession) -> None:
        """Test property that returns display name if available, else username."""
        # User with display name
        user1 = User(username="user1", display_name="Display Name")
        assert user1.display_name_or_username == "Display Name"

        # User without display name
        user2 = User(username="user2")
        assert user2.display_name_or_username == "user2"

    async def test_reset_stats_method(self, db_session: AsyncSession) -> None:
        """Test method for resetting user statistics."""
        user = User(
            username="resetuser",
            games_played=100,
            games_won=75
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Reset stats
        user.reset_stats()
        assert user.games_played == 0
        assert user.games_won == 0
        assert user.win_rate == 0.0


class TestUserModelIntegration:
    """Integration tests for User model functionality."""

    async def test_multiple_users_different_stats(self, db_session: AsyncSession) -> None:
        """Test creating multiple users with different statistics."""
        users_data = [
            ("alice", "alice@example.com", "Alice", 50, 35),
            ("bob", None, "Bob the Builder", 25, 10),
            ("charlie", "charlie@test.com", None, 100, 80),
            ("diana", None, None, 0, 0),
        ]

        users = []
        for username, email, display, played, won in users_data:
            user = User(
                username=username,
                email=email,
                display_name=display,
                games_played=played,
                games_won=won
            )
            users.append(user)
            db_session.add(user)

        await db_session.commit()

        # Refresh all users
        for user in users:
            await db_session.refresh(user)

        # Verify statistics
        alice = next(u for u in users if u.username == "alice")
        assert alice.win_rate == 0.7
        assert alice.is_experienced is True

        diana = next(u for u in users if u.username == "diana")
        assert diana.win_rate == 0.0
        assert diana.has_played_games is False

    async def test_user_lifecycle(self, db_session: AsyncSession) -> None:
        """Test complete user lifecycle from creation to deactivation."""
        # Create user
        user = User(username="lifecycle", email="life@example.com")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        original_created_at = user.created_at
        assert user.is_active is True

        # Play some games
        user.update_game_stats(won=True)
        user.update_game_stats(won=True)
        user.update_game_stats(won=False)

        await db_session.commit()
        await db_session.refresh(user)

        assert user.games_played == 3
        assert user.games_won == 2
        assert user.win_rate == 2/3

        # Update profile
        user.display_name = "Lifecycle User"
        await db_session.commit()
        await db_session.refresh(user)

        assert user.display_name == "Lifecycle User"
        assert user.updated_at > user.created_at
        assert user.created_at == original_created_at

        # Deactivate user
        user.deactivate()
        await db_session.commit()
        await db_session.refresh(user)

        assert user.is_active is False

        # User stats should be preserved even when inactive
        assert user.games_played == 3
        assert user.games_won == 2