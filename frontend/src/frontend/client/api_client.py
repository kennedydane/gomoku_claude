"""
HTTP API client for communicating with the Gomoku backend.

This module provides an async HTTP client for all backend API operations.
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
import asyncio
from datetime import datetime

import httpx
from loguru import logger
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from frontend.auth.auth_manager import AuthManager
    from frontend.auth.models import UserProfile


# Response models (matching backend schemas)
class UserInfo(BaseModel):
    """User information model."""
    id: int
    username: str
    display_name: str


class RuleSetInfo(BaseModel):
    """Rule set information model."""
    id: int
    name: str
    board_size: int
    allow_overlines: bool


class BoardState(BaseModel):
    """Game board state model."""
    board: List[List[Optional[str]]]
    size: int


class GameInfo(BaseModel):
    """Game information model."""
    id: str
    black_player_id: int
    white_player_id: int
    ruleset_id: int
    status: str
    current_player: str
    board_state: BoardState
    winner_id: Optional[int] = None
    move_count: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_game_over: bool
    can_start: bool
    black_player: Optional[UserInfo] = None
    white_player: Optional[UserInfo] = None
    winner: Optional[UserInfo] = None
    ruleset: Optional[RuleSetInfo] = None


class MoveInfo(BaseModel):
    """Move information model."""
    id: int
    game_id: str
    player_id: int
    move_number: int
    row: int
    col: int
    player_color: str
    is_winning_move: bool
    created_at: datetime


class APIClient:
    """Async HTTP client for the Gomoku backend API."""
    
    def __init__(
        self, 
        base_url: str = "http://localhost:8000", 
        timeout: float = 30.0, 
        auth_manager: Optional["AuthManager"] = None
    ):
        """Initialize the API client.
        
        Args:
            base_url: Base URL of the API server
            timeout: Request timeout in seconds
            auth_manager: Optional authentication manager for authenticated requests
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth_manager = auth_manager
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"Initialized API client for {self.base_url}")
        if auth_manager:
            logger.debug("API client configured with authentication manager")
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
        return self._client
    
    @client.setter
    def client(self, value: httpx.AsyncClient) -> None:
        """Set the HTTP client (primarily for testing)."""
        self._client = value
    
    @client.deleter
    def client(self) -> None:
        """Delete the HTTP client (primarily for testing)."""
        self._client = None
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        # Close auth manager if it exists
        if self.auth_manager:
            await self.auth_manager.close()
            
        logger.debug("API client closed")
    
    async def health_check(self) -> bool:
        """Check if the API server is running.
        
        Returns:
            True if server is responding, False otherwise
        """
        try:
            response = await self.client.get("/")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    # Authentication properties and methods
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        if not self.auth_manager:
            return False
        return self.auth_manager.is_authenticated()
    
    @property
    def current_user(self) -> Optional["UserProfile"]:
        """Get current authenticated user."""
        if not self.auth_manager:
            return None
        return self.auth_manager.get_current_user()
    
    async def login(
        self,
        username: str,
        password: str,
        device_name: str = "Desktop App",
        device_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Login with username and password.
        
        Args:
            username: User's username
            password: User's password  
            device_name: Device identifier
            device_info: Device information
            
        Returns:
            True if login successful
        """
        if not self.auth_manager:
            logger.warning("No auth manager configured for login")
            return False
            
        return await self.auth_manager.login(
            username=username,
            password=password,
            device_name=device_name,
            device_info=device_info or {}
        )
    
    async def register_user(
        self,
        username: str,
        password: str,
        email: str,
        display_name: Optional[str] = None,
        device_name: str = "Desktop App",
        device_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register a new user.
        
        Args:
            username: Desired username
            password: User's password
            email: User's email
            display_name: Optional display name
            device_name: Device identifier
            device_info: Device information
            
        Returns:
            True if registration successful
        """
        if not self.auth_manager:
            logger.warning("No auth manager configured for registration")
            return False
            
        return await self.auth_manager.register(
            username=username,
            password=password,
            email=email,
            display_name=display_name,
            device_name=device_name,
            device_info=device_info or {}
        )
    
    def logout(self) -> None:
        """Logout current user."""
        if self.auth_manager:
            self.auth_manager.logout()
    
    async def _make_authenticated_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an authenticated request with automatic token refresh.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional arguments for the request
            
        Returns:
            Response data as dictionary
        """
        if not self.auth_manager or not self.auth_manager.is_authenticated():
            raise ValueError("Authentication required but not available")
        
        try:
            # Try the request with current authentication
            return await self.auth_manager.make_authenticated_request(method, endpoint, **kwargs)
            
        except Exception as e:
            # Import here to avoid circular import
            from frontend.auth.exceptions import TokenExpiredError
            
            # If token expired, try to refresh and retry once
            if isinstance(e, TokenExpiredError):
                logger.debug("Token expired, attempting refresh")
                try:
                    success = await self.auth_manager.refresh_token()
                    if success:
                        logger.debug("Token refresh successful, retrying request")
                        return await self.auth_manager.make_authenticated_request(method, endpoint, **kwargs)
                    else:
                        logger.warning("Token refresh failed")
                        raise e
                except Exception as refresh_error:
                    logger.error(f"Token refresh failed: {refresh_error}")
                    raise e
            else:
                # Re-raise non-token errors
                raise e
    
    # User management
    async def create_user(self, username: str, email: str, display_name: str) -> UserInfo:
        """Create a new user.
        
        Args:
            username: Unique username
            email: User email address
            display_name: Display name for the user
            
        Returns:
            Created user information
        """
        payload = {
            "username": username,
            "email": email,
            "display_name": display_name
        }
        
        # Use authenticated request if auth manager is available and authenticated
        if self.auth_manager and self.auth_manager.is_authenticated():
            user_data = await self._make_authenticated_request("POST", "/api/v1/users/", json=payload)
        else:
            response = await self.client.post("/api/v1/users/", json=payload)
            response.raise_for_status()
            user_data = response.json()
        
        logger.debug(f"Created user: {user_data['username']}")
        return UserInfo(**user_data)
    
    async def get_users(self) -> List[UserInfo]:
        """Get list of all users.
        
        Returns:
            List of user information
        """
        # Use authenticated request if auth manager is available and authenticated
        if self.auth_manager and self.auth_manager.is_authenticated():
            users_data = await self._make_authenticated_request("GET", "/api/v1/users/")
        else:
            response = await self.client.get("/api/v1/users/")
            response.raise_for_status()
            users_data = response.json()
        
        return [UserInfo(**user) for user in users_data]
    
    async def get_user(self, user_id: int) -> UserInfo:
        """Get a specific user by ID.
        
        Args:
            user_id: User ID to retrieve
            
        Returns:
            User information
        """
        response = await self.client.get(f"/api/v1/users/{user_id}")
        response.raise_for_status()
        
        user_data = response.json()
        return UserInfo(**user_data)
    
    # Rule set management
    async def get_rulesets(self) -> List[RuleSetInfo]:
        """Get list of all rule sets.
        
        Returns:
            List of rule set information
        """
        response = await self.client.get("/api/v1/rulesets/")
        response.raise_for_status()
        
        rulesets_data = response.json()
        return [RuleSetInfo(**ruleset) for ruleset in rulesets_data]
    
    async def get_ruleset(self, ruleset_id: int) -> RuleSetInfo:
        """Get a specific rule set by ID.
        
        Args:
            ruleset_id: Rule set ID to retrieve
            
        Returns:
            Rule set information
        """
        response = await self.client.get(f"/api/v1/rulesets/{ruleset_id}")
        response.raise_for_status()
        
        ruleset_data = response.json()
        return RuleSetInfo(**ruleset_data)
    
    # Game management
    async def create_game(self, black_player_id: int, white_player_id: int, ruleset_id: int) -> GameInfo:
        """Create a new game.
        
        Args:
            black_player_id: ID of the player playing black
            white_player_id: ID of the player playing white
            ruleset_id: ID of the rule set to use
            
        Returns:
            Created game information
        """
        payload = {
            "black_player_id": black_player_id,
            "white_player_id": white_player_id,
            "ruleset_id": ruleset_id
        }
        
        # Use authenticated request if auth manager is available and authenticated
        if self.auth_manager and self.auth_manager.is_authenticated():
            game_data = await self._make_authenticated_request("POST", "/api/v1/games/", json=payload)
        else:
            response = await self.client.post("/api/v1/games/", json=payload)
            response.raise_for_status()
            game_data = response.json()
        
        logger.info(f"Created game: {game_data['id']}")
        return GameInfo(**game_data)
    
    async def get_game(self, game_id: str) -> GameInfo:
        """Get a specific game by ID.
        
        Args:
            game_id: Game ID to retrieve
            
        Returns:
            Game information
        """
        response = await self.client.get(f"/api/v1/games/{game_id}")
        response.raise_for_status()
        
        game_data = response.json()
        return GameInfo(**game_data)
    
    async def start_game(self, game_id: str) -> GameInfo:
        """Start a game.
        
        Args:
            game_id: Game ID to start
            
        Returns:
            Updated game information
        """
        response = await self.client.put(f"/api/v1/games/{game_id}/start")
        response.raise_for_status()
        
        game_data = response.json()
        logger.info(f"Started game: {game_id}")
        return GameInfo(**game_data)
    
    async def make_move(self, game_id: str, player_id: int, row: int, col: int) -> MoveInfo:
        """Make a move in a game.
        
        Args:
            game_id: Game ID to make move in
            player_id: ID of player making the move
            row: Board row position (0-based)
            col: Board column position (0-based)
            
        Returns:
            Move information
        """
        payload = {
            "player_id": player_id,
            "row": row,
            "col": col
        }
        
        # Use authenticated request if auth manager is available and authenticated
        if self.auth_manager and self.auth_manager.is_authenticated():
            move_data = await self._make_authenticated_request("POST", f"/api/v1/games/{game_id}/moves/", json=payload)
        else:
            response = await self.client.post(f"/api/v1/games/{game_id}/moves/", json=payload)
            response.raise_for_status()
            move_data = response.json()
        
        logger.debug(f"Made move in game {game_id}: ({row}, {col})")
        return MoveInfo(**move_data)
    
    async def get_game_moves(self, game_id: str) -> List[MoveInfo]:
        """Get all moves for a game.
        
        Args:
            game_id: Game ID to get moves for
            
        Returns:
            List of move information
        """
        response = await self.client.get(f"/api/v1/games/{game_id}/moves/")
        response.raise_for_status()
        
        moves_data = response.json()
        return [MoveInfo(**move) for move in moves_data]