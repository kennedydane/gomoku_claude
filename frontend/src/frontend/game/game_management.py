#!/usr/bin/env python3
"""
Game management functionality for the frontend.

This module contains the core logic for filtering, sorting, and formatting
game information for display in the GUI. By separating this logic from the
GUI components, it becomes easily testable.
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime


def filter_games_by_criteria(games: List[Dict[str, Any]], filter_type: str, user_id: str) -> List[Dict[str, Any]]:
    """
    Filter games based on specified criteria.
    
    Args:
        games: List of game dictionaries from API
        filter_type: Filter criteria ("all", "active", "completed", "your_turn", "waiting")
        user_id: Current user's ID
        
    Returns:
        Filtered list of games
    """
    if filter_type == "all":
        return games.copy()
    
    filtered_games = []
    
    for game in games:
        # Only include games where the user is a player
        if not is_user_in_game(game, user_id):
            continue
            
        status = game.get("status", "UNKNOWN")
        
        if filter_type == "active" and status == "ACTIVE":
            filtered_games.append(game)
        elif filter_type == "completed" and status in ("COMPLETED", "FINISHED"):
            filtered_games.append(game)
        elif filter_type == "waiting" and status == "WAITING":
            filtered_games.append(game)
        elif filter_type == "your_turn" and status == "ACTIVE":
            # Check if it's user's turn
            if is_users_turn(game, user_id):
                filtered_games.append(game)
    
    return filtered_games


def is_user_in_game(game: Dict[str, Any], user_id: str) -> bool:
    """
    Check if the user is a player in the game.
    
    Args:
        game: Game dictionary
        user_id: Current user's ID or username
        
    Returns:
        True if user is black or white player, False otherwise
    """
    # Support both ID-based and username-based matching
    return (game.get("black_player_id") == user_id or 
            game.get("white_player_id") == user_id or
            game.get("black_player_username") == user_id or
            game.get("white_player_username") == user_id)


def is_users_turn(game: Dict[str, Any], user_id: str) -> bool:
    """
    Determine if it's the user's turn in a game.
    
    Args:
        game: Game dictionary
        user_id: Current user's ID or username
        
    Returns:
        True if it's the user's turn, False otherwise
    """
    current_player_color = game.get("current_player", "BLACK").lower()
    
    # Check both ID and username formats
    if current_player_color == "black":
        current_player = (game.get("black_player_id") or 
                         game.get("black_player_username"))
    else:
        current_player = (game.get("white_player_id") or
                         game.get("white_player_username"))
    
    return current_player == user_id


def sort_games_for_display(games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort games for optimal display order.
    
    Priority order:
    1. Active games first
    2. Within same status, newer games first
    
    Args:
        games: List of game dictionaries
        
    Returns:
        Sorted list of games
    """
    if not games:
        return []
    
    # Separate active and non-active games
    active_games = [g for g in games if g.get("status") == "ACTIVE"]
    other_games = [g for g in games if g.get("status") != "ACTIVE"]
    
    # Sort each group by date (newest first)
    active_games.sort(key=lambda g: g.get("created_at", ""), reverse=True)
    other_games.sort(key=lambda g: g.get("created_at", ""), reverse=True)
    
    # Combine: active games first, then others
    return active_games + other_games


def determine_player_role(game: Dict[str, Any], user_id: str) -> Tuple[str, str]:
    """
    Determine user's role (color) and opponent ID/username in a game.
    
    Args:
        game: Game dictionary
        user_id: Current user's ID or username
        
    Returns:
        Tuple of (player_color, opponent_id_or_username)
    """
    black_player = game.get("black_player_id") or game.get("black_player_username")
    white_player = game.get("white_player_id") or game.get("white_player_username")
    
    if black_player == user_id:
        return "Black", white_player
    else:
        return "White", black_player


def get_game_status_info(game: Dict[str, Any], user_id: str) -> Tuple[str, Tuple[int, int, int]]:
    """
    Get formatted status information and color for a game.
    
    Args:
        game: Game dictionary
        user_id: Current user's ID
        
    Returns:
        Tuple of (status_text, color_rgb_tuple)
    """
    status = game.get("status", "UNKNOWN")
    
    if status == "ACTIVE":
        if is_users_turn(game, user_id):
            return "🔥 YOUR TURN", (255, 200, 100)  # Orange/yellow
        else:
            return "⏳ Opponent's Turn", (100, 200, 255)  # Light blue
    elif status in ("COMPLETED", "FINISHED"):
        winner = game.get("winner_id") or game.get("winner_username")
        if winner == user_id:
            return "✅ You Won!", (100, 255, 100)  # Green
        elif winner:
            return "❌ You Lost", (255, 100, 100)  # Red
        else:
            return "⚫ Draw", (150, 150, 150)  # Gray
    elif status == "WAITING":
        return "⏸️ Waiting", (255, 255, 100)  # Yellow
    else:
        return f"❓ {status}", (150, 150, 150)  # Gray


def format_game_info(game: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Format game information for display.
    
    Args:
        game: Game dictionary from API
        user_id: Current user's ID
        
    Returns:
        Dictionary with formatted game information
    """
    # Basic game info
    game_id = game.get("id", "")
    game_id_short = game_id[:8] if len(game_id) >= 8 else game_id
    
    # Player role and opponent
    player_color, opponent_id = determine_player_role(game, user_id)
    
    if opponent_id == user_id:
        opponent_name = "Yourself (Practice)"
    elif opponent_id:
        # If it's a username, use it directly; if it's an ID, truncate
        if isinstance(opponent_id, str) and not opponent_id.isdigit():
            opponent_name = opponent_id  # It's a username
        else:
            opponent_name = f"Player {str(opponent_id)[:8]}"  # It's an ID
    else:
        opponent_name = "Unknown"
    
    # Board size - API doesn't provide ruleset info in game list, default to 15
    ruleset = game.get("ruleset", {})
    if isinstance(ruleset, dict):
        board_size = ruleset.get("board_size", 15)
    else:
        board_size = 15
    
    # Format creation date
    created_at = game.get("created_at", "")
    date_str = format_date_string(created_at)
    
    # Status information
    status_text, status_color = get_game_status_info(game, user_id)
    
    return {
        "game_id_short": game_id_short,
        "player_color": player_color,
        "opponent_name": opponent_name,
        "board_size": board_size,
        "date_str": date_str,
        "status_text": status_text,
        "status_color": status_color,
        "full_game": game
    }


def format_date_string(date_str: str) -> str:
    """
    Format ISO date string for display.
    
    Args:
        date_str: ISO format date string
        
    Returns:
        Formatted date string (MM/DD HH:MM) or empty string if invalid
    """
    if not date_str:
        return ""
    
    try:
        # Handle various ISO format variations
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%m/%d %H:%M")
    except (ValueError, TypeError):
        # Fallback for invalid dates
        return date_str[:10] if len(date_str) >= 10 else date_str


def get_filter_display_name(filter_type: str) -> str:
    """
    Get user-friendly display name for filter type.
    
    Args:
        filter_type: Internal filter type
        
    Returns:
        Human-readable filter name
    """
    filter_names = {
        "all": "games",
        "active": "active games",
        "completed": "completed games",
        "your_turn": "games where it's your turn",
        "waiting": "waiting games"
    }
    return filter_names.get(filter_type, "games")


# Game management workflow functions

def process_games_for_display(
    games: List[Dict[str, Any]], 
    filter_type: str, 
    user_id: str
) -> List[Dict[str, Any]]:
    """
    Complete workflow to process games for display.
    
    This function combines filtering, sorting, and formatting in one call.
    
    Args:
        games: Raw games list from API
        filter_type: Filter criteria 
        user_id: Current user's ID
        
    Returns:
        List of formatted game info dictionaries ready for display
    """
    # Filter games based on criteria
    filtered_games = filter_games_by_criteria(games, filter_type, user_id)
    
    # Sort for optimal display order
    sorted_games = sort_games_for_display(filtered_games)
    
    # Format each game for display
    formatted_games = []
    for game in sorted_games:
        formatted_info = format_game_info(game, user_id)
        formatted_games.append(formatted_info)
    
    return formatted_games


def get_games_summary(games: List[Dict[str, Any]], user_id: str) -> Dict[str, int]:
    """
    Get summary statistics for user's games.
    
    Args:
        games: List of user's games
        user_id: Current user's ID
        
    Returns:
        Dictionary with game count statistics
    """
    summary = {
        "total": len(games),
        "active": 0,
        "completed": 0,
        "waiting": 0,
        "your_turn": 0,
        "won": 0,
        "lost": 0,
        "draws": 0
    }
    
    for game in games:
        status = game.get("status", "")
        
        if status == "ACTIVE":
            summary["active"] += 1
            if is_users_turn(game, user_id):
                summary["your_turn"] += 1
        elif status == "COMPLETED":
            summary["completed"] += 1
            winner_id = game.get("winner_id")
            if winner_id == user_id:
                summary["won"] += 1
            elif winner_id:
                summary["lost"] += 1
            else:
                summary["draws"] += 1
        elif status == "WAITING":
            summary["waiting"] += 1
    
    return summary