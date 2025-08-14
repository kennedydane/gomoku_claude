#!/usr/bin/env python3
"""
Tests for game management functionality.

This module tests the game filtering, sorting, and display logic
used in the GUI game management interface.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import the testable functions we'll extract
from frontend.game.game_management import (
    filter_games_by_criteria,
    sort_games_for_display,
    format_game_info,
    get_game_status_info,
    determine_player_role
)


class TestGameFiltering:
    """Test game filtering functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = "user-123"
        self.opponent_id = "opponent-456"
        
        self.sample_games = [
            {
                "id": "game-1",
                "status": "ACTIVE",
                "current_player": "BLACK",
                "black_player_id": self.user_id,
                "white_player_id": self.opponent_id,
                "created_at": "2025-01-15T10:00:00Z",
                "winner_id": None,
                "ruleset": {"board_size": 15}
            },
            {
                "id": "game-2", 
                "status": "ACTIVE",
                "current_player": "WHITE",
                "black_player_id": self.opponent_id,
                "white_player_id": self.user_id,
                "created_at": "2025-01-15T11:00:00Z",
                "winner_id": None,
                "ruleset": {"board_size": 15}
            },
            {
                "id": "game-3",
                "status": "COMPLETED", 
                "current_player": "BLACK",
                "black_player_id": self.user_id,
                "white_player_id": self.opponent_id,
                "created_at": "2025-01-14T15:00:00Z",
                "winner_id": self.user_id,
                "ruleset": {"board_size": 19}
            },
            {
                "id": "game-4",
                "status": "WAITING",
                "current_player": "BLACK", 
                "black_player_id": self.user_id,
                "white_player_id": self.opponent_id,
                "created_at": "2025-01-15T09:00:00Z",
                "winner_id": None,
                "ruleset": {"board_size": 15}
            }
        ]

    def test_filter_all_games(self):
        """Test filtering for all games."""
        result = filter_games_by_criteria(self.sample_games, "all", self.user_id)
        assert len(result) == 4
        assert result == self.sample_games

    def test_filter_active_games(self):
        """Test filtering for active games only."""
        result = filter_games_by_criteria(self.sample_games, "active", self.user_id)
        assert len(result) == 2
        assert all(game["status"] == "ACTIVE" for game in result)
        assert result[0]["id"] in ["game-1", "game-2"]
        assert result[1]["id"] in ["game-1", "game-2"]

    def test_filter_completed_games(self):
        """Test filtering for completed games only."""
        result = filter_games_by_criteria(self.sample_games, "completed", self.user_id)
        assert len(result) == 1
        assert result[0]["id"] == "game-3"
        assert result[0]["status"] == "COMPLETED"

    def test_filter_your_turn_games(self):
        """Test filtering for games where it's the user's turn."""
        result = filter_games_by_criteria(self.sample_games, "your_turn", self.user_id)
        assert len(result) == 2
        # game-1: user is black, current_player is BLACK -> user's turn
        # game-2: user is white, current_player is WHITE -> user's turn
        game_ids = {game["id"] for game in result}
        assert "game-1" in game_ids
        assert "game-2" in game_ids

    def test_filter_waiting_games(self):
        """Test filtering for waiting games."""
        result = filter_games_by_criteria(self.sample_games, "waiting", self.user_id)
        assert len(result) == 1
        assert result[0]["id"] == "game-4"
        assert result[0]["status"] == "WAITING"

    def test_filter_empty_list(self):
        """Test filtering with empty game list."""
        result = filter_games_by_criteria([], "all", self.user_id)
        assert result == []

    def test_filter_no_matches(self):
        """Test filtering with no matching games."""
        games_without_user = [
            {
                "id": "other-game",
                "status": "ACTIVE",
                "black_player_id": "other-1",
                "white_player_id": "other-2"
            }
        ]
        result = filter_games_by_criteria(games_without_user, "active", self.user_id)
        assert result == []


class TestGameSorting:
    """Test game sorting functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.games = [
            {
                "id": "game-1",
                "status": "COMPLETED",
                "created_at": "2025-01-15T10:00:00Z"
            },
            {
                "id": "game-2",
                "status": "ACTIVE", 
                "created_at": "2025-01-15T11:00:00Z"
            },
            {
                "id": "game-3",
                "status": "ACTIVE",
                "created_at": "2025-01-15T09:00:00Z"
            },
            {
                "id": "game-4",
                "status": "WAITING",
                "created_at": "2025-01-15T12:00:00Z"
            }
        ]

    def test_sort_active_games_first(self):
        """Test that active games appear before other statuses."""
        result = sort_games_for_display(self.games)
        
        # Active games should be first
        assert result[0]["status"] == "ACTIVE"
        assert result[1]["status"] == "ACTIVE"
        
        # Within active games, newer should be first
        assert result[0]["created_at"] > result[1]["created_at"]

    def test_sort_by_creation_date_within_status(self):
        """Test sorting by creation date within same status."""
        result = sort_games_for_display(self.games)
        
        # Check that within same status, newer games come first
        active_games = [g for g in result if g["status"] == "ACTIVE"]
        assert len(active_games) == 2
        assert active_games[0]["created_at"] > active_games[1]["created_at"]

    def test_sort_empty_list(self):
        """Test sorting empty list."""
        result = sort_games_for_display([])
        assert result == []

    def test_sort_single_game(self):
        """Test sorting single game."""
        single_game = [self.games[0]]
        result = sort_games_for_display(single_game)
        assert result == single_game


class TestGameDisplayInfo:
    """Test game display information formatting."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = "user-123"
        self.opponent_id = "opponent-456"

    def test_determine_player_role_black(self):
        """Test determining player role when user is black."""
        game = {
            "black_player_id": self.user_id,
            "white_player_id": self.opponent_id
        }
        role, opponent_id = determine_player_role(game, self.user_id)
        assert role == "Black"
        assert opponent_id == self.opponent_id

    def test_determine_player_role_white(self):
        """Test determining player role when user is white."""
        game = {
            "black_player_id": self.opponent_id,
            "white_player_id": self.user_id
        }
        role, opponent_id = determine_player_role(game, self.user_id)
        assert role == "White"
        assert opponent_id == self.opponent_id

    def test_determine_player_role_practice_game(self):
        """Test determining player role in practice game (user vs self)."""
        game = {
            "black_player_id": self.user_id,
            "white_player_id": self.user_id
        }
        role, opponent_id = determine_player_role(game, self.user_id)
        assert role == "Black"  # Default to black in practice
        assert opponent_id == self.user_id

    def test_get_status_info_your_turn(self):
        """Test status info when it's user's turn."""
        game = {
            "status": "ACTIVE",
            "current_player": "BLACK",
            "black_player_id": self.user_id,
            "white_player_id": self.opponent_id
        }
        status_text, color = get_game_status_info(game, self.user_id)
        assert "YOUR TURN" in status_text
        assert color == (255, 200, 100)  # Orange/yellow

    def test_get_status_info_opponent_turn(self):
        """Test status info when it's opponent's turn.""" 
        game = {
            "status": "ACTIVE",
            "current_player": "WHITE",
            "black_player_id": self.user_id,
            "white_player_id": self.opponent_id
        }
        status_text, color = get_game_status_info(game, self.user_id)
        assert "Opponent's Turn" in status_text
        assert color == (100, 200, 255)  # Light blue

    def test_get_status_info_won_game(self):
        """Test status info for won game."""
        game = {
            "status": "COMPLETED",
            "winner_id": self.user_id
        }
        status_text, color = get_game_status_info(game, self.user_id)
        assert "You Won" in status_text
        assert color == (100, 255, 100)  # Green

    def test_get_status_info_lost_game(self):
        """Test status info for lost game."""
        game = {
            "status": "COMPLETED", 
            "winner_id": self.opponent_id
        }
        status_text, color = get_game_status_info(game, self.user_id)
        assert "You Lost" in status_text
        assert color == (255, 100, 100)  # Red

    def test_get_status_info_draw_game(self):
        """Test status info for draw game."""
        game = {
            "status": "COMPLETED",
            "winner_id": None
        }
        status_text, color = get_game_status_info(game, self.user_id)
        assert "Draw" in status_text
        assert color == (150, 150, 150)  # Gray

    def test_get_status_info_waiting_game(self):
        """Test status info for waiting game."""
        game = {
            "status": "WAITING"
        }
        status_text, color = get_game_status_info(game, self.user_id)
        assert "Waiting" in status_text
        assert color == (255, 255, 100)  # Yellow

    def test_format_game_info_standard(self):
        """Test formatting standard game information."""
        game = {
            "id": "game-12345678",
            "status": "ACTIVE",
            "current_player": "BLACK", 
            "black_player_id": self.user_id,
            "white_player_id": self.opponent_id,
            "created_at": "2025-01-15T10:30:00Z",
            "ruleset": {"board_size": 15}
        }
        
        info = format_game_info(game, self.user_id)
        
        assert "game-123" in info["game_id_short"]
        assert info["player_color"] == "Black"
        assert "Player " in info["opponent_name"]
        assert info["board_size"] == 15
        assert "01/15 10:30" in info["date_str"]

    def test_format_game_info_practice_game(self):
        """Test formatting practice game information."""
        game = {
            "id": "practice-game",
            "black_player_id": self.user_id,
            "white_player_id": self.user_id,
            "ruleset": {"board_size": 19}
        }
        
        info = format_game_info(game, self.user_id)
        assert info["opponent_name"] == "Yourself (Practice)"
        assert info["board_size"] == 19

    def test_format_game_info_no_date(self):
        """Test formatting game info with no creation date."""
        game = {
            "id": "no-date-game",
            "black_player_id": self.user_id,
            "white_player_id": self.opponent_id,
            "created_at": None,
            "ruleset": {"board_size": 15}
        }
        
        info = format_game_info(game, self.user_id)
        assert info["date_str"] == ""

    def test_format_game_info_invalid_date(self):
        """Test formatting game info with invalid date."""
        game = {
            "id": "invalid-date-game", 
            "black_player_id": self.user_id,
            "white_player_id": self.opponent_id,
            "created_at": "invalid-date-string",
            "ruleset": {"board_size": 15}
        }
        
        info = format_game_info(game, self.user_id)
        assert "invalid" in info["date_str"]


class TestIntegrationScenarios:
    """Test complete game management scenarios."""

    def setup_method(self):
        """Set up integration test fixtures."""
        self.user_id = "user-123"
        self.games = [
            {
                "id": "urgent-game",
                "status": "ACTIVE", 
                "current_player": "BLACK",
                "black_player_id": self.user_id,
                "white_player_id": "opponent-1",
                "created_at": "2025-01-15T14:00:00Z",
                "ruleset": {"board_size": 15}
            },
            {
                "id": "waiting-game",
                "status": "ACTIVE",
                "current_player": "WHITE", 
                "black_player_id": self.user_id,
                "white_player_id": "opponent-2",
                "created_at": "2025-01-15T13:00:00Z",
                "ruleset": {"board_size": 19}
            },
            {
                "id": "won-game",
                "status": "COMPLETED",
                "black_player_id": self.user_id,
                "white_player_id": "opponent-3",
                "winner_id": self.user_id,
                "created_at": "2025-01-14T12:00:00Z",
                "ruleset": {"board_size": 15}
            }
        ]

    def test_complete_your_turn_filter_workflow(self):
        """Test complete workflow for 'your turn' filter."""
        # Filter games where it's user's turn
        filtered = filter_games_by_criteria(self.games, "your_turn", self.user_id)
        assert len(filtered) == 1
        assert filtered[0]["id"] == "urgent-game"
        
        # Sort the filtered games
        sorted_games = sort_games_for_display(filtered)
        assert len(sorted_games) == 1
        
        # Format the game info
        info = format_game_info(sorted_games[0], self.user_id)
        assert info["player_color"] == "Black"
        
        # Get status info
        status_text, color = get_game_status_info(sorted_games[0], self.user_id)
        assert "YOUR TURN" in status_text
        assert color == (255, 200, 100)

    def test_complete_active_games_workflow(self):
        """Test complete workflow for active games filter."""
        # Filter for active games
        filtered = filter_games_by_criteria(self.games, "active", self.user_id)
        assert len(filtered) == 2
        
        # Sort by priority (your turn first, then by date)
        sorted_games = sort_games_for_display(filtered)
        
        # Should be in correct priority order
        assert sorted_games[0]["id"] == "urgent-game"  # Newer and user's turn
        assert sorted_games[1]["id"] == "waiting-game"  # Older, opponent's turn
        
        # Verify status info for both
        urgent_status, urgent_color = get_game_status_info(sorted_games[0], self.user_id)
        waiting_status, waiting_color = get_game_status_info(sorted_games[1], self.user_id)
        
        assert "YOUR TURN" in urgent_status
        assert "Opponent's Turn" in waiting_status
        assert urgent_color == (255, 200, 100)
        assert waiting_color == (100, 200, 255)

    def test_empty_filter_results(self):
        """Test handling of empty filter results."""
        # Filter for a status that doesn't exist
        filtered = filter_games_by_criteria(self.games, "waiting", self.user_id) 
        assert filtered == []
        
        # Sort empty list
        sorted_games = sort_games_for_display(filtered)
        assert sorted_games == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])