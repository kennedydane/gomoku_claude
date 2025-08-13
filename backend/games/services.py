"""
Game service layer for Gomoku business logic.

This module contains the GameService class which handles move validation,
win detection, and game state management.
"""

from typing import Optional, Tuple
from django.db import transaction
from core.exceptions import InvalidMoveError, GameStateError, PlayerError

from .models import Game, GameMove, GameStatus, Player


class GameService:
    """
    Service class for Gomoku game business logic.
    
    Handles move validation, win detection, and game state management.
    """
    
    @staticmethod
    def validate_move(game: Game, player_id: int, row: int, col: int) -> None:
        """
        Validate a move before it's made.
        
        Args:
            game: The game instance
            player_id: ID of the player making the move
            row: Row coordinate (0-based)
            col: Column coordinate (0-based)
            
        Raises:
            ValueError: If the move is invalid
        """
        # Check if game is active
        if game.status != GameStatus.ACTIVE:
            raise GameStateError(
                f"Cannot make move in game with status: {game.status}",
                details={'current_status': game.status, 'game_id': str(game.id)}
            )
        
        # Check if it's the correct player's turn
        if game.current_player == Player.BLACK:
            expected_player_id = game.black_player_id
        else:
            expected_player_id = game.white_player_id
        
        if player_id != expected_player_id:
            current_player_name = "Black" if game.current_player == Player.BLACK else "White"
            raise PlayerError(
                f"It's {current_player_name}'s turn, not yours",
                details={
                    'current_player': current_player_name,
                    'expected_player_id': expected_player_id,
                    'actual_player_id': player_id
                }
            )
        
        # Check board boundaries
        board_size = game.ruleset.board_size
        if row < 0 or row >= board_size or col < 0 or col >= board_size:
            raise InvalidMoveError(
                f"Move out of bounds. Board size is {board_size}x{board_size}",
                details={
                    'row': row, 'col': col, 
                    'board_size': board_size,
                    'valid_range': f"0-{board_size-1}"
                }
            )
        
        # Check if position is already occupied
        board = game.board_state.get('board', [])
        if board and board[row][col] is not None:
            raise InvalidMoveError(
                f"Position ({row}, {col}) is already occupied",
                details={'row': row, 'col': col, 'occupied_by': board[row][col]}
            )
    
    @staticmethod
    @transaction.atomic
    def make_move(game: Game, player_id: int, row: int, col: int) -> GameMove:
        """
        Make a move in the game.
        
        Args:
            game: The game instance
            player_id: ID of the player making the move
            row: Row coordinate (0-based)
            col: Column coordinate (0-based)
            
        Returns:
            The created GameMove instance
            
        Raises:
            ValueError: If the move is invalid
        """
        # Refresh game from database with lock to prevent race conditions
        game = Game.objects.select_for_update().get(pk=game.pk)
        
        # Validate the move
        GameService.validate_move(game, player_id, row, col)
        
        # Determine player color
        if player_id == game.black_player_id:
            player_color = Player.BLACK
            player = game.black_player
        else:
            player_color = Player.WHITE
            player = game.white_player
        
        # Update board state
        board = game.board_state.get('board', [])
        if not board:
            game.initialize_board()
            board = game.board_state['board']
        
        board[row][col] = player_color
        game.board_state = {'size': game.ruleset.board_size, 'board': board}
        
        # Create the move
        game.move_count += 1
        move = GameMove.objects.create(
            game=game,
            player=player,
            move_number=game.move_count,
            row=row,
            col=col,
            player_color=player_color
        )
        
        # Check for win
        if GameService.check_win(game, row, col):
            move.is_winning_move = True
            move.save()
            game.finish_game(winner=player)
        else:
            # Switch turns
            game.current_player = Player.WHITE if game.current_player == Player.BLACK else Player.BLACK
            game.save()
        
        return move
    
    @staticmethod
    def check_win(game: Game, last_row: int, last_col: int) -> bool:
        """
        Check if the last move resulted in a win.
        
        Args:
            game: The game instance
            last_row: Row of the last move
            last_col: Column of the last move
            
        Returns:
            True if the last move won the game
        """
        board = game.board_state.get('board', [])
        if not board:
            return False
        
        color = board[last_row][last_col]
        if not color:
            return False
        
        board_size = game.ruleset.board_size
        allow_overlines = game.ruleset.allow_overlines
        
        # Helper function to count consecutive stones
        def count_direction(dr: int, dc: int) -> int:
            """Count consecutive stones in one direction."""
            count = 0
            r, c = last_row + dr, last_col + dc
            
            while 0 <= r < board_size and 0 <= c < board_size:
                if board[r][c] == color:
                    count += 1
                    r += dr
                    c += dc
                else:
                    break
            
            return count
        
        # Check all four directions
        directions = [
            (0, 1),   # Horizontal
            (1, 0),   # Vertical
            (1, 1),   # Diagonal \
            (1, -1),  # Diagonal /
        ]
        
        for dr, dc in directions:
            # Count in both directions plus the placed stone
            total = 1 + count_direction(dr, dc) + count_direction(-dr, -dc)
            
            if allow_overlines:
                # Any line of 5 or more wins
                if total >= 5:
                    return True
            else:
                # Exactly 5 in a row wins
                if total == 5:
                    return True
        
        return False
    
    @staticmethod
    def get_valid_moves(game: Game) -> list[Tuple[int, int]]:
        """
        Get all valid moves for the current player.
        
        Args:
            game: The game instance
            
        Returns:
            List of (row, col) tuples for valid moves
        """
        if game.status != GameStatus.ACTIVE:
            return []
        
        board = game.board_state.get('board', [])
        if not board:
            game.initialize_board()
            board = game.board_state['board']
        
        valid_moves = []
        board_size = game.ruleset.board_size
        
        for row in range(board_size):
            for col in range(board_size):
                if board[row][col] is None:
                    valid_moves.append((row, col))
        
        return valid_moves
    
    @staticmethod
    def resign_game(game: Game, player_id: int) -> None:
        """
        Handle a player resigning from the game.
        
        Args:
            game: The game instance
            player_id: ID of the resigning player
        """
        if game.status != GameStatus.ACTIVE:
            raise GameStateError(
                f"Can only resign from active games, current status: {game.status}",
                details={'current_status': game.status, 'game_id': str(game.id)}
            )
        
        # Determine winner (the other player)
        if player_id == game.black_player_id:
            winner = game.white_player
        elif player_id == game.white_player_id:
            winner = game.black_player
        else:
            raise PlayerError(
                "You are not a player in this game",
                details={
                    'player_id': player_id,
                    'black_player_id': game.black_player_id,
                    'white_player_id': game.white_player_id,
                    'game_id': str(game.id)
                }
            )
        
        game.finish_game(winner=winner)