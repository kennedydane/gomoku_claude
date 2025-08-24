# Service Layer Architecture

This document describes the enhanced modular service layer architecture implemented to support multiple game types and improve code maintainability.

## Overview

The service layer has been refactored from a monolithic structure to a modular, extensible architecture that makes adding new game types (like Chess) straightforward while maintaining strict separation of concerns.

## Architecture Components

### 1. Interfaces (`games/interfaces.py`)

Defines contracts and protocols that all game services must implement:

```python
@runtime_checkable
class GameServiceInterface(Protocol):
    """Protocol defining the interface for game-specific services."""
    def validate_move(...) -> None
    def make_move(...) -> GameMove  
    def check_win(...) -> bool
    def get_valid_moves(...) -> List[Tuple[int, int]]
    def resign_game(...) -> None
    def initialize_board(...) -> dict

class BaseGameService(ABC):
    """Abstract base class providing common functionality."""
    # Common implementations with abstract methods for game-specific logic
```

### 2. Move Validators (`games/validators.py`)

Separate validation logic for each game type:

```python
class BaseMoveValidator(ABC):
    def validate_move(self, game, player_id, row, col) -> None
    def validate_basic_conditions(...) -> None  # Common validations

class GomokuMoveValidator(BaseMoveValidator):
    # Gomoku-specific move validation

class GoMoveValidator(BaseMoveValidator): 
    # Go-specific validation (pass moves, suicide rule, etc.)

class ChessMoveValidator(BaseMoveValidator):
    # Placeholder for Chess piece movement validation
```

### 3. State Managers (`games/state_managers.py`)

Dedicated classes for managing game board state:

```python
class BaseStateManager(ABC):
    def initialize_board(self, game) -> Dict[str, Any]
    def update_board_state(self, game, row, col, player) -> None

class GomokuStateManager(BaseStateManager):
    # Simple board state with last move tracking

class GoStateManager(BaseStateManager):
    # Complex state with passes, captures, ko tracking

class ChessStateManager(BaseStateManager):
    # Placeholder for chess piece positions, castling rights, etc.
```

### 4. Service Factory Pattern

Centralized service creation with automatic registration:

```python
class GameServiceFactory:
    @classmethod
    def get_service(cls, game_type: str) -> GameServiceInterface
    
# Services auto-register themselves:
GameServiceRegistry.register('GOMOKU', GomokuGameService)
GameServiceRegistry.register('GO', GoGameService) 
```

## Implementation Example

### Current Game Services

The existing game services have been updated to use the modular architecture:

```python
class GomokuGameService(BaseGameService):
    def validate_move(self, game, player_id, row, col):
        """Validate using modular validator."""
        validator = MoveValidatorFactory.get_validator('GOMOKU')
        validator.validate_move(game, player_id, row, col)
    
    def make_move(self, game, player_id, row, col):
        """Make move using modular state manager."""
        # ... player logic ...
        state_manager = StateManagerFactory.get_manager('GOMOKU')
        state_manager.update_board_state(game, row, col, player_color)
        # ... game end logic ...
```

### Adding a New Game Type

To add Chess support, you would create:

```python
# 1. Chess-specific validator
class ChessMoveValidator(BaseMoveValidator):
    def validate_move(self, game, player_id, from_row, from_col, to_row, to_col):
        # Piece movement rules, check detection, etc.

# 2. Chess-specific state manager  
class ChessStateManager(BaseStateManager):
    def initialize_board(self, game):
        return {
            'board': chess_starting_position,
            'castling_rights': {'white_king': True, ...},
            'en_passant_target': None,
            'fifty_move_counter': 0
        }

# 3. Chess game service
class ChessGameService(BaseGameService):
    # Inherits common functionality, implements chess-specific logic

# 4. Register the service
GameServiceRegistry.register('CHESS', ChessGameService)
```

## Benefits

### 1. Separation of Concerns
- **Validation**: Isolated in validator classes
- **State Management**: Centralized in state manager classes  
- **Business Logic**: Focused in service classes
- **Type Safety**: Protocol-based interfaces ensure consistency

### 2. Extensibility  
- Adding new games requires minimal changes to existing code
- Factory patterns enable dynamic service discovery
- Registry patterns allow runtime service management

### 3. Testability
- Each component can be tested independently
- Modular structure enables focused unit tests
- Mock implementations easier to create

### 4. Maintainability
- Single responsibility principle enforced
- Clear contracts via interfaces
- Reduced coupling between components

## Migration Notes

### What Changed
- Game services no longer contain inline validation logic
- Board state updates delegated to dedicated state managers
- Factory patterns replace direct service instantiation
- Protocol-based type checking added

### What Stayed the Same
- Public API for game services unchanged
- Database models and relationships untouched
- WebSocket notification system preserved
- View layer integration maintained

## Testing Strategy

The modular architecture enables comprehensive testing at multiple levels:

```python
# Unit tests for individual components
def test_gomoku_validator():
    validator = GomokuMoveValidator()
    # Test validation logic in isolation

def test_go_state_manager():
    manager = GoStateManager() 
    # Test state updates in isolation

# Integration tests for complete services
def test_chess_service_integration():
    service = GameServiceFactory.get_service('CHESS')
    # Test complete move workflow
```

## Future Enhancements

### Potential Extensions
- **Move History**: Centralized move recording system
- **AI Integration**: Pluggable AI engines per game type
- **Rule Variants**: Support for game rule modifications
- **Performance**: Caching and optimization layers

### Architectural Improvements
- **Event System**: Pub/sub for game events
- **Command Pattern**: Undo/redo functionality
- **Strategy Pattern**: Different scoring algorithms
- **Observer Pattern**: Real-time spectator support

## Summary

The new service architecture transforms the game system from a collection of monolithic services into a clean, modular, and extensible framework. This foundation supports the project's goal of potentially adding new board games while maintaining code quality and developer productivity.