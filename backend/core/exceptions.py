"""
Custom exception handling for the Gomoku API.

Provides standardized error responses and logging.
"""

import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from django.http import Http404
from django.core.exceptions import ValidationError, PermissionDenied

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides standardized error responses.
    
    Returns a consistent error response format:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {...}  // Optional additional details
        },
        "request_id": "uuid"  // For tracking
    }
    """
    # Get the standard DRF error response
    response = exception_handler(exc, context)
    
    if response is not None:
        request = context.get('request')
        request_id = getattr(request, 'id', 'unknown') if request else 'unknown'
        
        # Log the error
        logger.error(
            f"API Error - Request ID: {request_id}, "
            f"Exception: {exc.__class__.__name__}, "
            f"Message: {str(exc)}"
        )
        
        # Standardize the error response format
        custom_response_data = {
            'error': {
                'code': get_error_code(exc),
                'message': get_error_message(exc, response),
                'request_id': request_id
            }
        }
        
        # Add details if available
        if hasattr(response, 'data') and response.data:
            if isinstance(response.data, dict):
                custom_response_data['error']['details'] = response.data
            else:
                custom_response_data['error']['details'] = {'detail': response.data}
        
        response.data = custom_response_data
    
    return response


def get_error_code(exc):
    """
    Get standardized error code based on exception type.
    """
    error_codes = {
        'ValidationError': 'VALIDATION_ERROR',
        'PermissionDenied': 'PERMISSION_DENIED',
        'NotAuthenticated': 'AUTHENTICATION_REQUIRED',
        'AuthenticationFailed': 'AUTHENTICATION_FAILED',
        'NotFound': 'RESOURCE_NOT_FOUND',
        'Http404': 'RESOURCE_NOT_FOUND',
        'MethodNotAllowed': 'METHOD_NOT_ALLOWED',
        'ParseError': 'PARSE_ERROR',
        'UnsupportedMediaType': 'UNSUPPORTED_MEDIA_TYPE',
        'Throttled': 'RATE_LIMIT_EXCEEDED',
    }
    
    exc_name = exc.__class__.__name__
    return error_codes.get(exc_name, 'INTERNAL_ERROR')


def get_error_message(exc, response):
    """
    Get user-friendly error message.
    """
    # Custom messages for common errors
    if hasattr(exc, 'default_detail'):
        return str(exc.default_detail)
    
    if hasattr(response, 'data') and response.data:
        if isinstance(response.data, dict):
            # Try to extract the first error message
            for key, value in response.data.items():
                if isinstance(value, list) and value:
                    return f"{key}: {value[0]}"
                elif isinstance(value, str):
                    return f"{key}: {value}"
        elif isinstance(response.data, list) and response.data:
            return str(response.data[0])
    
    return str(exc) or "An error occurred"


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