"""
Game service layer for multi-game business logic.

This module contains the abstract base service and game-specific implementations
for different game types (Gomoku, Go).
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Set, Dict
from django.db import transaction
import copy

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
            # Determine player color for Ko check
            player_color = Player.BLACK if player_id == game.black_player_id else Player.WHITE
            
            if self.is_ko_violation(game, row, col, player_color):
                raise InvalidMoveError(
                    f"Ko rule violation: This move would repeat a previous board position at ({row}, {col})",
                    details={'row': row, 'col': col}
                )
        
        # Check for suicide rule (can't play a move that kills your own group unless it captures opponent)
        if not is_pass_move:
            board = game.board_state.get('board', [])
            if board:
                # Determine player color
                player_color = Player.BLACK if player_id == game.black_player_id else Player.WHITE
                
                # Check for Ko violation first (takes precedence over suicide)
                if self.is_ko_violation(game, row, col, player_color):
                    raise InvalidMoveError(
                        f"Ko rule violation at ({row}, {col})",
                        details={'row': row, 'col': col, 'player_color': player_color}
                    )
                
                # Check if this move would be suicide (only if it doesn't capture opponent stones)
                if self.check_suicide_rule(board, row, col, player_color):
                    raise InvalidMoveError(
                        f"Suicide move not allowed at ({row}, {col})",
                        details={'row': row, 'col': col, 'player_color': player_color}
                    )
    
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
        
        # Handle pass move
        is_pass_move = row == -1 and col == -1
        
        if is_pass_move:
            # Increment consecutive passes for pass moves
            consecutive_passes = game.board_state.get('consecutive_passes', 0) + 1
        else:
            # Update board state for regular moves
            board = game.board_state.get('board', [])
            if not board:
                game.initialize_board()
                board = game.board_state['board']
            
            
            # Place the stone
            board[row][col] = player_color
            
            # Reset consecutive passes since a stone was placed
            consecutive_passes = 0
        
        # Handle captures - check adjacent opponent groups for liberties
        captured_stones_count = {'black': 0, 'white': 0}
        ko_position = None
        
        if not is_pass_move:
            # Check for captures after placing the stone
            capture_result = self.check_captures(board, row, col, player_color)
            
            if capture_result['total_captured'] > 0:
                # Remove captured stones
                removed_count = self.remove_captured_stones(board, capture_result['captured_groups'])
                
                # Update captured stones count
                if capture_result['opponent_color'] == Player.WHITE:
                    captured_stones_count['white'] = removed_count
                else:
                    captured_stones_count['black'] = removed_count
                
                # Ko detection: Set ko_position if this is a potential Ko situation
                # Ko occurs when exactly one stone is captured and the capturing position
                # could be immediately recaptured to restore the previous board state
                ko_position = None
                if (capture_result['total_captured'] == 1 and 
                    len(capture_result['captured_groups']) == 1 and 
                    len(capture_result['captured_groups'][0]) == 1):
                    
                    # Single stone captured - check if recapture would create Ko
                    captured_position = list(capture_result['captured_groups'][0])[0]
                    ko_position = [captured_position[0], captured_position[1]]
            
            # After capturing opponent stones, check if the placed stone itself should be captured
            # This handles cases where a move captures opponent stones but the placed stone
            # is then immediately captured (suicide capture scenario)
            opponent_color = Player.WHITE if player_color == Player.BLACK else Player.BLACK
            self_capture_result = self.check_captures(board, row, col, opponent_color)
            
            if self_capture_result['total_captured'] > 0:
                # The placed stone and its group get captured
                self_removed_count = self.remove_captured_stones(board, self_capture_result['captured_groups'])
                
                # Update captured stones count for the player's own stones
                if player_color == Player.WHITE:
                    captured_stones_count['white'] += self_removed_count
                else:
                    captured_stones_count['black'] += self_removed_count
        
        # Update board state
        if is_pass_move:
            # For pass moves, just update the consecutive passes
            current_board = game.board_state.get('board', [])
            if not current_board:
                game.initialize_board()
                current_board = game.board_state['board']
        else:
            current_board = board
            
        # Update captured stones count by adding new captures to existing totals
        existing_captured = game.board_state.get('captured_stones', {'black': 0, 'white': 0})
        updated_captured = {
            'black': existing_captured['black'] + captured_stones_count['black'],
            'white': existing_captured['white'] + captured_stones_count['white']
        }
        
        # Always update the full board state with current values
        game.board_state = {
            'game_type': 'GO',
            'size': game.ruleset.board_size, 
            'board': current_board,
            'captured_stones': updated_captured,
            'consecutive_passes': consecutive_passes,
            'ko_position': ko_position
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
        
        # Save the game with updated board state
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
        
        # Get current player color for validation
        if game.current_player == Player.BLACK:
            player_color = Player.BLACK
        else:
            player_color = Player.WHITE
        
        for row in range(board_size):
            for col in range(board_size):
                # Position must be empty
                if board[row][col] is not None:
                    continue
                    
                # Check for Ko violation using new board history system
                if self.is_ko_violation(game, row, col, player_color):
                    continue
                
                # Check for suicide rule violation
                if self.check_suicide_rule(board, row, col, player_color):
                    continue
                
                valid_moves.append((row, col))
        
        # Always add pass move as valid
        valid_moves.append((-1, -1))
        
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
    
    def find_group(self, board: List[List], row: int, col: int) -> Set[Tuple[int, int]]:
        """Find all stones connected to the stone at (row, col) using flood-fill."""
        if not board or row < 0 or row >= len(board) or col < 0 or col >= len(board[0]):
            return set()
        
        stone_color = board[row][col]
        if stone_color is None:
            return set()
        
        group = set()
        to_visit = [(row, col)]
        visited = set()
        
        while to_visit:
            current_row, current_col = to_visit.pop()
            if (current_row, current_col) in visited:
                continue
                
            visited.add((current_row, current_col))
            
            # Check if position is valid and has the same color stone
            if (0 <= current_row < len(board) and 
                0 <= current_col < len(board[0]) and 
                board[current_row][current_col] == stone_color):
                
                group.add((current_row, current_col))
                
                # Add adjacent positions to visit
                for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    next_row, next_col = current_row + dr, current_col + dc
                    if (next_row, next_col) not in visited:
                        to_visit.append((next_row, next_col))
        
        return group
    
    def get_group_liberties(self, board: List[List], group: Set[Tuple[int, int]]) -> Set[Tuple[int, int]]:
        """Get all empty adjacent positions (liberties) for a group."""
        liberties = set()
        board_size = len(board)
        
        for row, col in group:
            # Check all adjacent positions
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                adj_row, adj_col = row + dr, col + dc
                
                # Check if adjacent position is valid and empty
                if (0 <= adj_row < board_size and 
                    0 <= adj_col < board_size and 
                    board[adj_row][adj_col] is None):
                    liberties.add((adj_row, adj_col))
        
        return liberties
    
    def check_captures(self, board: List[List], row: int, col: int, player_color: str) -> Dict:
        """Check for captures after placing a stone at (row, col)."""
        captured_groups = []
        total_captured = 0
        processed_groups = set()  # Track processed groups using frozensets
        
        # Get opponent color
        opponent_color = Player.WHITE if player_color == Player.BLACK else Player.BLACK
        
        # Check all adjacent positions for opponent stones
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            adj_row, adj_col = row + dr, col + dc
            
            # Check if adjacent position is valid and has opponent stone
            if (0 <= adj_row < len(board) and 
                0 <= adj_col < len(board[0]) and 
                board[adj_row][adj_col] == opponent_color):
                
                # Find the opponent group
                opponent_group = self.find_group(board, adj_row, adj_col)
                
                # Convert to frozenset for reliable comparison
                group_signature = frozenset(opponent_group)
                
                # Skip if we already checked this group
                if group_signature in processed_groups:
                    continue
                
                # Mark this group as processed
                processed_groups.add(group_signature)
                
                # Check if this group has any liberties
                liberties = self.get_group_liberties(board, opponent_group)
                
                # If no liberties, the group is captured
                if len(liberties) == 0:
                    captured_groups.append(opponent_group)
                    total_captured += len(opponent_group)
        
        return {
            'captured_groups': captured_groups,
            'total_captured': total_captured,
            'opponent_color': opponent_color
        }
    
    def remove_captured_stones(self, board: List[List], captured_groups: List[Set]) -> int:
        """Remove captured stones from board and return count."""
        total_removed = 0
        
        for group in captured_groups:
            for row, col in group:
                if board[row][col] is not None:
                    board[row][col] = None
                    total_removed += 1
        
        return total_removed
    
    def check_suicide_rule(self, board: List[List], row: int, col: int, player_color: str) -> bool:
        """Check if placing a stone would be suicide (illegal unless it captures opponent)."""
        # Create a temporary board with the new stone
        temp_board = copy.deepcopy(board)
        temp_board[row][col] = player_color
        
        # Check if this move captures any opponent stones
        capture_result = self.check_captures(temp_board, row, col, player_color)
        has_captures = capture_result['total_captured'] > 0
        
        # Find the group that the new stone belongs to
        new_stone_group = self.find_group(temp_board, row, col)
        
        # Check if the new group has any liberties
        liberties = self.get_group_liberties(temp_board, new_stone_group)
        has_liberties = len(liberties) > 0
        
        # Suicide is only allowed if it captures opponent stones
        is_suicide = not has_liberties and not has_captures
        
        return is_suicide
    
    def boards_equal(self, board1: List[List], board2: List[List]) -> bool:
        """Compare two board states for equality."""
        if len(board1) != len(board2):
            return False
        
        for i in range(len(board1)):
            if len(board1[i]) != len(board2[i]):
                return False
            for j in range(len(board1[i])):
                if board1[i][j] != board2[i][j]:
                    return False
        
        return True
    
    def reconstruct_board_state_at_move(self, game: Game, target_move_number: int) -> Optional[List[List]]:
        """
        Recursively reconstruct board state at a specific move number.
        Uses formula: state at move n = state at move n-1 + move n
        
        Args:
            game: The game instance
            target_move_number: Move number to reconstruct board state for (0 = empty board)
        
        Returns:
            Board state at the specified move, or None if invalid move number
        """
        from django.core.cache import cache
        from django.conf import settings
        
        # Validate target move number
        if target_move_number < 0 or target_move_number > game.move_count:
            return None
        
        # Check cache first
        cache_key = f"game_{game.id}_move_{target_move_number}"
        cached_board = cache.get(cache_key)
        if cached_board is not None:
            return cached_board
        
        # Base case: move 0 is empty board
        if target_move_number == 0:
            board_size = game.ruleset.board_size
            board = [[None for _ in range(board_size)] for _ in range(board_size)]
            cache.set(cache_key, copy.deepcopy(board), 
                     timeout=getattr(settings, 'GAME_BOARD_CACHE_TIMEOUT', 600))
            return board
        
        # Recursive case: get board at move n-1, then apply move n
        previous_board = self.reconstruct_board_state_at_move(game, target_move_number - 1)
        if previous_board is None:
            return None
        
        # Copy the previous board state
        board = copy.deepcopy(previous_board)
        
        # Get the move at target_move_number
        try:
            current_move = game.moves.get(move_number=target_move_number)
        except game.moves.model.DoesNotExist:
            return None
        
        # Apply the current move to the board
        # Skip pass moves (row=-1, col=-1)
        if current_move.row != -1 and current_move.col != -1:
            # Place stone on board
            board[current_move.row][current_move.col] = current_move.player_color
            
            # Apply captures that would have occurred
            capture_result = self.check_captures(board, current_move.row, current_move.col, current_move.player_color)
            if capture_result['total_captured'] > 0:
                self.remove_captured_stones(board, capture_result['captured_groups'])
        
        # Cache the reconstructed board state
        cache.set(cache_key, copy.deepcopy(board), 
                 timeout=getattr(settings, 'GAME_BOARD_CACHE_TIMEOUT', 600))
        
        return board
    
    def get_board_state_moves_back(self, game: Game, moves_back: int) -> Optional[List[List]]:
        """
        Get board state from N moves ago using move history reconstruction.
        
        Args:
            game: The game instance
            moves_back: Number of moves to go back (1 = previous move, 2 = two moves ago)
        
        Returns:
            Board state from moves_back moves ago, or None if not enough moves
        """
        if moves_back <= 0:
            return game.board_state['board']
        
        target_move_number = game.move_count - moves_back
        if target_move_number < 0:
            return None
        
        return self.reconstruct_board_state_at_move(game, target_move_number)
    
    
    def is_ko_violation(self, game: Game, row: int, col: int, player_color: str) -> bool:
        """Check if move would create Ko violation by comparing to board 1 move ago."""
        # Need at least 1 previous move to have a Ko situation
        # Ko rule: cannot immediately recapture to restore the board position before opponent's capturing move
        if game.move_count < 1:
            return False
        
        # Simulate the proposed move
        current_board = copy.deepcopy(game.board_state['board'])
        current_board[row][col] = player_color
        
        # Apply captures that would result from this move
        capture_result = self.check_captures(current_board, row, col, player_color)
        if capture_result['total_captured'] > 0:
            self.remove_captured_stones(current_board, capture_result['captured_groups'])
        
        # Get board state from 1 move ago (before opponent's capturing move)
        # This is the position that should not be restored immediately
        one_move_ago_board = self.get_board_state_moves_back(game, 1)
        
        if one_move_ago_board is None:
            return False
        
        # Ko violation if boards would be identical
        return self.boards_equal(current_board, one_move_ago_board)
    


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