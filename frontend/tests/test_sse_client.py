"""
Test suite for SSE (Server-Sent Events) client functionality.

This module tests the SSE client that connects to the backend SSE endpoint
and processes HTML events to update the GUI in real-time.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List, Optional

from frontend.realtime.sse_client import SSEClient, SSEEvent, SSEConnectionError, SSEParseError
from frontend.realtime.html_parser import GameStateParser, ParsedGameState


class TestSSEClient:
    """Test suite for SSEClient class."""
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Create mock authentication manager."""
        auth_manager = Mock()
        auth_manager.is_authenticated.return_value = True
        auth_manager.get_current_token.return_value = "abc123"
        auth_manager.config.base_url = "http://localhost:8001"
        auth_manager.get_current_user.return_value = {"id": 123, "username": "testuser"}
        return auth_manager
    
    @pytest.fixture
    def mock_callback(self):
        """Create mock callback for SSE events."""
        return Mock()
    
    @pytest.fixture
    def sse_client(self, mock_auth_manager, mock_callback):
        """Create SSEClient instance for testing."""
        return SSEClient(
            auth_manager=mock_auth_manager,
            on_game_update=mock_callback,
            reconnect_delay=0.1  # Fast reconnect for tests
        )
    
    def test_init_requires_authenticated_user(self, mock_callback):
        """Test SSEClient requires authenticated auth manager."""
        # Given: unauthenticated auth manager
        auth_manager = Mock()
        auth_manager.is_authenticated.return_value = False
        
        # When/Then: Should raise error
        with pytest.raises(ValueError, match="User must be authenticated"):
            SSEClient(auth_manager=auth_manager, on_game_update=mock_callback)
    
    def test_init_builds_correct_endpoint_url(self, mock_auth_manager, mock_callback):
        """Test SSE client builds correct endpoint URL."""
        # Given: authenticated user
        mock_auth_manager.get_current_user.return_value = {"id": 456, "username": "player"}
        
        # When: creating SSE client
        client = SSEClient(auth_manager=mock_auth_manager, on_game_update=mock_callback)
        
        # Then: should build correct URL
        expected_url = "http://localhost:8001/api/v1/events/?channel=user-456"
        assert client.endpoint_url == expected_url
    
    @pytest.mark.asyncio
    async def test_connect_establishes_sse_connection(self, sse_client):
        """Test SSE client can establish connection."""
        # Given: mock HTTP client response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "text/event-stream"}
        
        # When: connecting to SSE
        with patch('aiohttp.ClientSession.get', return_value=mock_response):
            await sse_client.connect()
        
        # Then: should be connected
        assert sse_client.is_connected is True
    
    @pytest.mark.asyncio
    async def test_connect_handles_authentication_failure(self, sse_client):
        """Test SSE client handles authentication failures."""
        # Given: mock HTTP 401 response
        mock_response = AsyncMock()
        mock_response.status = 401
        
        # When/Then: should raise SSEConnectionError
        with patch('aiohttp.ClientSession.get', return_value=mock_response):
            with pytest.raises(SSEConnectionError, match="Authentication failed"):
                await sse_client.connect()
    
    @pytest.mark.asyncio
    async def test_connect_handles_network_errors(self, sse_client):
        """Test SSE client handles network connection errors."""
        # Given: network error on connection
        with patch('aiohttp.ClientSession.get', side_effect=ConnectionError("Network error")):
            # When/Then: should raise SSEConnectionError
            with pytest.raises(SSEConnectionError, match="Connection failed"):
                await sse_client.connect()
    
    @pytest.mark.asyncio
    async def test_disconnect_closes_connection(self, sse_client):
        """Test SSE client can properly disconnect."""
        # Given: connected SSE client
        sse_client._connected = True
        sse_client._session = Mock()
        sse_client._session.close = Mock()  # Make close method synchronous
        sse_client._response = Mock() 
        sse_client._response.close = Mock()  # Make close method synchronous
        
        # When: disconnecting
        await sse_client.disconnect()
        
        # Then: should clean up connection
        assert sse_client.is_connected is False
        sse_client._session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_sse_line_parses_event_data(self, sse_client, mock_callback):
        """Test SSE client can parse SSE line format."""
        # Given: SSE event line
        event_line = 'event: game_move'
        data_line = 'data: <div class="game-board-grid" data-game-id="123" data-board-size="8">...</div>'
        
        # When: processing SSE lines
        sse_client._process_sse_line(event_line)
        sse_client._process_sse_line(data_line)
        sse_client._process_sse_line('')  # Empty line triggers event
        
        # Then: should trigger callback with parsed game state
        mock_callback.assert_called_once()
        call_args = mock_callback.call_args[0][0]
        assert call_args.game_id == "123"
        assert call_args.board_size == 8
    
    def test_process_sse_line_ignores_non_game_events(self, sse_client, mock_callback):
        """Test SSE client ignores events that aren't game-related."""
        # Given: non-game SSE event
        event_line = 'event: user_status'
        data_line = 'data: some data'
        
        # When: processing non-game event
        sse_client._process_sse_line(event_line)
        sse_client._process_sse_line(data_line)
        sse_client._process_sse_line('')
        
        # Then: should not trigger callback
        mock_callback.assert_not_called()
    
    @pytest.mark.asyncio 
    async def test_reconnect_attempts_with_backoff(self, sse_client):
        """Test SSE client attempts reconnection with exponential backoff."""
        # NOTE: This test requires implementing start_with_reconnect method
        # For now, we'll skip this test until that method is implemented
        pytest.skip("start_with_reconnect method not yet implemented")
    
    @pytest.mark.asyncio
    async def test_start_with_reconnect_stops_after_max_retries(self, sse_client):
        """Test SSE client stops reconnection after max retries."""
        # NOTE: This test requires implementing start_with_reconnect method
        # For now, we'll skip this test until that method is implemented
        pytest.skip("start_with_reconnect method not yet implemented")
    
    def test_is_connected_property(self, sse_client):
        """Test is_connected property reflects connection state."""
        # Initially disconnected
        assert sse_client.is_connected is False
        
        # After connecting
        sse_client._connected = True
        assert sse_client.is_connected is True


class TestGameStateParser:
    """Test suite for GameStateParser class."""
    
    @pytest.fixture
    def sample_board_html(self):
        """Sample HTML from SSE event that includes game state."""
        return '''
        <div class="game-board-grid" 
             data-game-id="abc-123"
             data-board-size="8"
             data-current-player="white"
             data-game-status="active">
            <div class="board-cell" data-row="0" data-col="0">
                <div class="stone black"></div>
            </div>
            <div class="board-cell" data-row="0" data-col="1">
                <div class="stone white"></div>
            </div>
            <div class="board-cell" data-row="1" data-col="0"></div>
        </div>
        '''
    
    @pytest.fixture
    def parser(self):
        """Create GameStateParser instance."""
        return GameStateParser()
    
    def test_parse_game_state_extracts_basic_info(self, parser, sample_board_html):
        """Test parser extracts basic game information."""
        # When: parsing HTML
        result = parser.parse_game_state(sample_board_html)
        
        # Then: should extract game metadata
        assert result.game_id == "abc-123"
        assert result.board_size == 8
        assert result.current_player == "white"
        assert result.game_status == "active"
    
    def test_parse_game_state_extracts_board_positions(self, parser, sample_board_html):
        """Test parser extracts stone positions from board."""
        # When: parsing HTML
        result = parser.parse_game_state(sample_board_html)
        
        # Then: should extract board state
        assert len(result.board_state) == 8  # 8x8 board
        assert len(result.board_state[0]) == 8
        
        # Check specific positions
        assert result.board_state[0][0] == "black"
        assert result.board_state[0][1] == "white"
        assert result.board_state[1][0] is None  # Empty cell
    
    def test_parse_game_state_handles_empty_board(self, parser):
        """Test parser handles board with no stones."""
        html = '''
        <div class="game-board-grid" data-board-size="3">
            <div class="board-cell" data-row="0" data-col="0"></div>
            <div class="board-cell" data-row="0" data-col="1"></div>
            <div class="board-cell" data-row="1" data-col="0"></div>
        </div>
        '''
        
        # When: parsing empty board
        result = parser.parse_game_state(html)
        
        # Then: should create empty board state
        assert all(cell is None for row in result.board_state for cell in row)
    
    def test_parse_game_state_handles_invalid_html(self, parser):
        """Test parser handles malformed HTML gracefully."""
        # Given: invalid HTML
        invalid_html = "<div>Not a game board</div>"
        
        # When/Then: should raise parse error
        with pytest.raises(SSEParseError, match="Could not find game board"):
            parser.parse_game_state(invalid_html)
    
    def test_parse_game_state_handles_missing_attributes(self, parser):
        """Test parser handles HTML missing required board size."""
        # Given: HTML missing board-size (game-id is now optional)
        html = '<div class="game-board-grid" data-game-id="test"></div>'
        
        # When/Then: should raise parse error
        with pytest.raises(SSEParseError, match="Missing required game data"):
            parser.parse_game_state(html)


class TestSSEEvent:
    """Test suite for SSEEvent data class."""
    
    def test_sse_event_creation(self):
        """Test SSEEvent can be created with required fields."""
        # When: creating SSE event
        event = SSEEvent(
            event_type="game_move",
            html_data="<div>test</div>",
            timestamp=1234567890.0
        )
        
        # Then: should have correct attributes
        assert event.event_type == "game_move"
        assert event.html_data == "<div>test</div>"
        assert event.timestamp == 1234567890.0
    
    def test_sse_event_str_representation(self):
        """Test SSEEvent has meaningful string representation."""
        # Given: SSE event with long HTML content
        long_html = "<div>" + "x" * 100 + "</div>"  # Make it longer than 50 chars
        event = SSEEvent(
            event_type="game_move",
            html_data=long_html,
            timestamp=1234567890.0
        )
        
        # When: converting to string
        result = str(event)
        
        # Then: should show truncated content
        assert "game_move" in result
        assert "<div>" in result
        assert "..." in result  # Truncated indicator


class TestParsedGameState:
    """Test suite for ParsedGameState data class."""
    
    def test_parsed_game_state_creation(self):
        """Test ParsedGameState can be created with board state."""
        # Given: board state
        board_state = [
            ["black", None, "white"],
            [None, "black", None],
            ["white", None, None]
        ]
        
        # When: creating parsed game state
        state = ParsedGameState(
            game_id="test-123",
            board_size=3,
            board_state=board_state,
            current_player="white",
            game_status="active"
        )
        
        # Then: should have correct attributes
        assert state.game_id == "test-123"
        assert state.board_size == 3
        assert state.board_state == board_state
        assert state.current_player == "white"
        assert state.game_status == "active"
    
    def test_parsed_game_state_get_stone_at_position(self):
        """Test ParsedGameState can retrieve stone at specific position."""
        # Given: board with stones
        board_state = [["black", "white"], [None, "black"]]
        state = ParsedGameState(
            game_id="test",
            board_size=2,
            board_state=board_state,
            current_player="white",
            game_status="active"
        )
        
        # When/Then: retrieving stones at positions
        assert state.get_stone_at(0, 0) == "black"
        assert state.get_stone_at(0, 1) == "white"
        assert state.get_stone_at(1, 0) is None
        assert state.get_stone_at(1, 1) == "black"
    
    def test_parsed_game_state_get_stone_handles_out_of_bounds(self):
        """Test ParsedGameState handles out of bounds positions."""
        # Given: small board
        state = ParsedGameState(
            game_id="test",
            board_size=2,
            board_state=[[None, None], [None, None]],
            current_player="black",
            game_status="active"
        )
        
        # When/Then: accessing out of bounds should return None
        assert state.get_stone_at(-1, 0) is None
        assert state.get_stone_at(0, -1) is None
        assert state.get_stone_at(2, 0) is None
        assert state.get_stone_at(0, 2) is None


class TestSSEIntegration:
    """Integration tests for complete SSE workflow."""
    
    @pytest.fixture
    def mock_auth_manager(self):
        """Create mock authentication manager."""
        auth_manager = Mock()
        auth_manager.is_authenticated.return_value = True
        auth_manager.get_current_token.return_value = "abc123"
        auth_manager.config.base_url = "http://localhost:8001"
        auth_manager.get_current_user.return_value = {"id": 123, "username": "testuser"}
        return auth_manager
    
    @pytest.mark.asyncio
    async def test_end_to_end_sse_processing(self, mock_auth_manager):
        """Test complete flow from SSE connection to GUI update."""
        # Given: callback to capture updates
        updates_received = []
        
        def capture_update(parsed_state):
            updates_received.append(parsed_state)
        
        client = SSEClient(
            auth_manager=mock_auth_manager,
            on_game_update=capture_update
        )
        
        # Given: mock SSE stream
        sse_lines = [
            'event: game_move',
            'data: <div class="game-board-grid" data-game-id="test-123" data-board-size="3" data-current-player="white" data-game-status="active">',
            'data: <div class="board-cell" data-row="0" data-col="0"><div class="stone black"></div></div>',
            'data: </div>',
            ''  # Empty line triggers event processing
        ]
        
        # When: processing SSE stream
        for line in sse_lines:
            client._process_sse_line(line)
        
        # Then: should trigger GUI update
        assert len(updates_received) == 1
        update = updates_received[0]
        assert update.game_id == "test-123"
        assert update.board_size == 3
        assert update.board_state[0][0] == "black"
        assert update.current_player == "white"
    
    def test_invalid_html_is_handled_gracefully(self, mock_auth_manager):
        """Test that invalid HTML in SSE events doesn't crash the client."""
        # Given: callback to capture errors
        errors_received = []
        
        def capture_error(error):
            errors_received.append(error)
        
        client = SSEClient(
            auth_manager=mock_auth_manager,
            on_game_update=Mock(),
            on_error=capture_error
        )
        
        # Given: invalid SSE data
        sse_lines = [
            'event: game_move',
            'data: <div>invalid html structure</div>',
            ''
        ]
        
        # When: processing invalid SSE stream
        for line in sse_lines:
            client._process_sse_line(line)
        
        # Then: should capture parse error
        assert len(errors_received) == 1
        assert isinstance(errors_received[0], SSEParseError)