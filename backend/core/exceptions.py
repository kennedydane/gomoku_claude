"""
Custom exception classes for the Gomoku web application.

Web-only exception handling - REST API exceptions archived.
"""

import logging

logger = logging.getLogger(__name__)


class GameError(Exception):
    """Base exception for game-related errors."""
    
    def __init__(self, message, code=None, details=None):
        self.message = message
        self.code = code or 'GAME_ERROR'
        self.details = details or {}
        super().__init__(self.message)


class InvalidMoveError(GameError):
    """Raised when an invalid move is attempted."""
    
    def __init__(self, message, details=None):
        super().__init__(message, 'INVALID_MOVE', details)


class GameStateError(GameError):
    """Raised when game is in invalid state for operation."""
    
    def __init__(self, message, details=None):
        super().__init__(message, 'INVALID_GAME_STATE', details)


class PlayerError(GameError):
    """Raised when player-related errors occur."""
    
    def __init__(self, message, details=None):
        super().__init__(message, 'PLAYER_ERROR', details)