"""
HTML parser for extracting game state from SSE events.

This module parses HTML fragments received via SSE to extract
board state and game information for GUI updates.
"""

from typing import List, Optional, Union
from dataclasses import dataclass
from bs4 import BeautifulSoup


@dataclass
class ParsedGameState:
    """Represents parsed game state from HTML."""
    game_id: str
    board_size: int
    board_state: List[List[Optional[str]]]
    current_player: str
    game_status: str
    
    def get_stone_at(self, row: int, col: int) -> Optional[str]:
        """Get stone color at specific board position."""
        # Check bounds
        if row < 0 or row >= self.board_size or col < 0 or col >= self.board_size:
            return None
            
        return self.board_state[row][col]


class GameStateParser:
    """Parser for extracting game state from HTML fragments."""
    
    def __init__(self):
        """Initialize HTML parser."""
        pass
    
    def parse_game_state(self, html: str) -> ParsedGameState:
        """
        Parse game state from HTML fragment.
        
        Args:
            html: HTML fragment from SSE event
            
        Returns:
            ParsedGameState with extracted information
            
        Raises:
            SSEParseError: If HTML cannot be parsed
        """
        from .sse_client import SSEParseError
        
        try:
            from loguru import logger
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the game board container
            board_div = soup.find('div', class_='game-board-grid')
            if not board_div:
                logger.error("HTML Parser: Could not find game-board-grid div")
                logger.debug(f"HTML Parser: Available divs: {[div.get('class') for div in soup.find_all('div')]}")
                raise SSEParseError("Could not find game board in HTML")
            
            # Extract basic game information from data attributes
            game_id = board_div.get('data-game-id')
            board_size_str = board_div.get('data-board-size')
            current_player = board_div.get('data-current-player')
            game_status = board_div.get('data-game-status')
            
            logger.debug(f"HTML Parser: Extracted game_id={game_id}, board_size={board_size_str}")
            
            if not board_size_str:
                raise SSEParseError("Missing required game data attributes")
            
            # Allow game_id to be missing for some test cases
            if not game_id:
                game_id = "unknown"
            
            board_size = int(board_size_str)
            
            # Initialize empty board
            board_state = [[None for _ in range(board_size)] for _ in range(board_size)]
            
            # Parse board cells to extract stone positions
            intersections = soup.find_all('div', class_='board-intersection')
            
            for intersection in intersections:
                row_str = intersection.get('data-row')
                col_str = intersection.get('data-col')
                
                if row_str is not None and col_str is not None:
                    row = int(row_str)
                    col = int(col_str)
                    
                    # Check for black stones
                    black_stone = intersection.find('div', class_='stone-black')
                    if black_stone:
                        board_state[row][col] = 'black'
                        continue
                    
                    # Check for white stones  
                    white_stone = intersection.find('div', class_='stone-white')
                    if white_stone:
                        board_state[row][col] = 'white'
            
            # Count stones found for debugging
            stone_count = sum(1 for row in board_state for cell in row if cell is not None)
            logger.debug(f"HTML Parser: Parsed {stone_count} stones from {len(intersections)} intersections")
            
            return ParsedGameState(
                game_id=game_id,
                board_size=board_size,
                board_state=board_state,
                current_player=current_player or 'unknown',
                game_status=game_status or 'unknown'
            )
            
        except (ValueError, AttributeError) as e:
            raise SSEParseError(f"Failed to parse HTML: {str(e)}")