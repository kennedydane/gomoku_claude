"""
Game service layer for multi-game business logic.

This module contains the abstract base service and game-specific implementations
for different game types (Gomoku, Go).
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from django.db import transaction

from core.exceptions import InvalidMoveError, GameStateError, PlayerError
from .models import Game, GameMove, GameStatus, Player


class BaseGameService(ABC):
    """Abstract base class for game-specific services."""
    
    @abstractmethod
    def validate_move(self, game, player_id: int, row: int, col: int) -> None:
        """Validate a move before it's made."""
        pass
    
    @abstractmethod
    def make_move(self, game, player_id: int, row: int, col: int):
        """Make a move in the game."""
        pass
    
    @abstractmethod
    def check_win(self, game, last_row: int, last_col: int) -> bool:
        """Check if the last move resulted in a win."""
        pass
    
    @abstractmethod
    def get_valid_moves(self, game) -> List[Tuple[int, int]]:
        """Get all valid moves for the current player."""
        pass
    
    @abstractmethod
    def resign_game(self, game, player_id: int) -> None:
        """Handle a player resigning from the game."""
        pass


class GomokuGameService(BaseGameService):
    """Game service for Gomoku games."""
    
    def validate_move(self, game: Game, player_id: int, row: int, col: int) -> None:
        """Validate a Gomoku move."""
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
    
    @transaction.atomic
    def make_move(self, game: Game, player_id: int, row: int, col: int) -> GameMove:
        """Make a move in a Gomoku game."""
        # Refresh game from database with lock to prevent race conditions
        game = Game.objects.select_for_update().get(pk=game.pk)
        
        # Validate the move
        self.validate_move(game, player_id, row, col)
        
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
        if self.check_win(game, row, col):
            move.is_winning_move = True
            move.save()
            game.finish_game(winner=player)
        else:
            # Switch turns
            game.current_player = Player.WHITE if game.current_player == Player.BLACK else Player.BLACK
            game.save()
        
        return move
    
    def check_win(self, game: Game, last_row: int, last_col: int) -> bool:
        """Check for Gomoku win condition (5 in a row)."""
        board = game.board_state.get('board', [])
        if not board:
            return False
        
        color = board[last_row][last_col]
        if not color:
            return False
        
        board_size = game.ruleset.board_size
        allow_overlines = game.ruleset.allow_overlines
        
        # Check all four directions
        directions = [
            (0, 1),   # Horizontal
            (1, 0),   # Vertical
            (1, 1),   # Diagonal \
            (1, -1),  # Diagonal /
        ]
        
        for direction in directions:
            # Count in both directions plus the placed stone
            positive_count, _, _ = self.count_stones_in_direction(
                board, board_size, last_row, last_col, direction, color
            )
            negative_count, _, _ = self.count_stones_in_direction(
                board, board_size, last_row, last_col, 
                (-direction[0], -direction[1]), color
            )
            
            total = 1 + positive_count + negative_count
            
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
    def count_stones_in_direction(
        board: List[List[Optional[str]]], 
        board_size: int, 
        start_row: int, 
        start_col: int, 
        direction: Tuple[int, int], 
        color: str
    ) -> Tuple[int, int, int]:
        """Count stones in a given direction with enhanced information."""
        direction_dr, direction_dc = direction
        consecutive_count = 0
        count_with_gap = 0
        max_potential = 0
        
        r, c = start_row + direction_dr, start_col + direction_dc
        found_gap = False
        
        # Count consecutive stones first
        while 0 <= r < board_size and 0 <= c < board_size:
            if board[r][c] == color:
                consecutive_count += 1
                r += direction_dr
                c += direction_dc
            else:
                break
        
        # Reset position for gap counting
        r, c = start_row + direction_dr, start_col + direction_dc
        
        # Count stones allowing one gap
        while 0 <= r < board_size and 0 <= c < board_size:
            cell_value = board[r][c]
            
            if cell_value == color:
                count_with_gap += 1
            elif cell_value is None and not found_gap:
                # Found empty space, look ahead
                found_gap = True
                next_r, next_c = r + direction_dr, c + direction_dc
                if (0 <= next_r < board_size and 0 <= next_c < board_size and 
                    board[next_r][next_c] == color):
                    # Continue scanning after the gap
                    r, c = next_r, next_c
                    continue
                else:
                    break
            else:
                # Either opponent stone or second gap
                break
            
            r += direction_dr
            c += direction_dc
        
        # Calculate maximum potential (reach until opponent or edge)
        r, c = start_row + direction_dr, start_col + direction_dc
        while 0 <= r < board_size and 0 <= c < board_size:
            if board[r][c] is not None and board[r][c] != color:
                # Hit opponent stone
                break
            max_potential += 1
            r += direction_dr
            c += direction_dc
        
        return consecutive_count, count_with_gap, max_potential
    
    def get_valid_moves(self, game: Game) -> List[Tuple[int, int]]:
        """Get valid Gomoku moves."""
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
    
    def resign_game(self, game: Game, player_id: int) -> None:
        """Handle Gomoku game resignation."""
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


class GoGameService(BaseGameService):
    """Game service for Go games."""
    
    def validate_move(self, game: Game, player_id: int, row: int, col: int) -> None:
        """Validate a Go move."""
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
        
        # Check for pass move (row=-1, col=-1)
        is_pass_move = row == -1 and col == -1
        
        if not is_pass_move:
            # Check board boundaries for regular moves
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
        
        # Check if position is already occupied (only for regular moves)
        if not is_pass_move:
            board = game.board_state.get('board', [])
            if board and board[row][col] is not None:
                raise InvalidMoveError(
                    f"Position ({row}, {col}) is already occupied",
                    details={'row': row, 'col': col, 'occupied_by': board[row][col]}
                )
        
        # Check for Ko rule violation (only for regular moves)
        if not is_pass_move:
            ko_position = game.board_state.get('ko_position')
            if ko_position and ko_position == [row, col]:
                raise InvalidMoveError(
                    f"Ko rule violation: Cannot immediately recapture at ({row}, {col})",
                    details={'row': row, 'col': col, 'ko_position': ko_position}
                )
        
        # Check for suicide rule (can't play a move that kills your own group unless it captures opponent)
        # TODO: Implement suicide detection after implementing group logic
    
    @transaction.atomic
    def make_move(self, game: Game, player_id: int, row: int, col: int) -> GameMove:
        """Make a move in a Go game."""
        # Refresh game from database with lock to prevent race conditions
        game = Game.objects.select_for_update().get(pk=game.pk)
        
        # Validate the move
        self.validate_move(game, player_id, row, col)
        
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
        
        # Place the stone
        board[row][col] = player_color
        
        # Reset consecutive passes since a move was made
        game.board_state['consecutive_passes'] = 0
        
        # Clear Ko position (will be set if this move creates a Ko situation)
        game.board_state['ko_position'] = None
        
        # TODO: Handle captures - check adjacent opponent groups for liberties
        # TODO: Update captured stones count
        # TODO: Check for Ko situation
        
        # Update board state
        game.board_state = {
            'size': game.ruleset.board_size, 
            'board': board,
            'captured_stones': game.board_state.get('captured_stones', {'black': 0, 'white': 0}),
            'ko_position': game.board_state.get('ko_position'),
            'consecutive_passes': game.board_state.get('consecutive_passes', 0)
        }
        
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
        
        # Go games don't end immediately on move placement (unlike Gomoku)
        # They end when both players pass consecutively or resign
        # Switch turns
        game.current_player = Player.WHITE if game.current_player == Player.BLACK else Player.BLACK
        game.save()
        
        return move
    
    def check_win(self, game: Game, last_row: int, last_col: int) -> bool:
        """Check for Go win condition (territory scoring)."""
        # Go games don't have immediate win conditions like Gomoku
        # They end when both players pass consecutively
        # Then territory is scored to determine the winner
        consecutive_passes = game.board_state.get('consecutive_passes', 0)
        return consecutive_passes >= 2
    
    def get_valid_moves(self, game: Game) -> List[Tuple[int, int]]:
        """Get valid Go moves."""
        if game.status != GameStatus.ACTIVE:
            return []
        
        board = game.board_state.get('board', [])
        if not board:
            game.initialize_board()
            board = game.board_state['board']
        
        valid_moves = []
        board_size = game.ruleset.board_size
        ko_position = game.board_state.get('ko_position')
        
        for row in range(board_size):
            for col in range(board_size):
                # Position must be empty
                if board[row][col] is not None:
                    continue
                    
                # Position cannot be Ko
                if ko_position and ko_position == [row, col]:
                    continue
                
                # TODO: Check for suicide rule
                # For now, assume all empty non-Ko positions are valid
                valid_moves.append((row, col))
        
        return valid_moves
    
    def resign_game(self, game: Game, player_id: int) -> None:
        """Handle Go game resignation."""
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
    
    @transaction.atomic
    def pass_turn(self, game: Game, player_id: int) -> GameMove:
        """Handle a pass move in Go."""
        # Validate it's the correct player's turn
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
        
        # Determine player
        if player_id == game.black_player_id:
            player_color = Player.BLACK
            player = game.black_player
        else:
            player_color = Player.WHITE
            player = game.white_player
        
        # Increment consecutive passes
        consecutive_passes = game.board_state.get('consecutive_passes', 0) + 1
        game.board_state['consecutive_passes'] = consecutive_passes
        
        # Create pass move (using -1, -1 to indicate pass)
        game.move_count += 1
        move = GameMove.objects.create(
            game=game,
            player=player,
            move_number=game.move_count,
            row=-1,  # Special value for pass
            col=-1,  # Special value for pass
            player_color=player_color
        )
        
        # Check if game ends (both players passed)
        if consecutive_passes >= 2:
            # TODO: Calculate territory score to determine winner
            # For now, just end the game without a winner (draw)
            game.finish_game(winner=None)  # This will be a draw
        else:
            # Switch turns
            game.current_player = Player.WHITE if game.current_player == Player.BLACK else Player.BLACK
            game.save()
        
        return move


class GameServiceFactory:
    """Factory for creating game-specific services."""
    
    _services = {
        'GOMOKU': GomokuGameService(),
        'GO': GoGameService()
    }
    
    @classmethod
    def get_service(cls, game_type: str) -> BaseGameService:
        """Get the appropriate service for a game type."""
        if game_type not in cls._services:
            raise ValueError(f"Unsupported game type: {game_type}")
        return cls._services[game_type]