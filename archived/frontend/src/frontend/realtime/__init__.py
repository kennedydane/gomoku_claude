"""
Real-time communication module for Gomoku frontend.

This module handles Server-Sent Events (SSE) connections and real-time
updates between the GUI client and the backend server.
"""

from .sse_client import SSEClient, SSEEvent, SSEConnectionError, SSEParseError
from .html_parser import GameStateParser, ParsedGameState

__all__ = [
    'SSEClient',
    'SSEEvent', 
    'SSEConnectionError',
    'SSEParseError',
    'GameStateParser',
    'ParsedGameState'
]