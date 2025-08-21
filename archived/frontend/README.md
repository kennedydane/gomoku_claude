# Gomoku Frontend

A Python-based GUI frontend for the Gomoku game that connects to a Django REST API backend.

## Overview

This frontend provides a clean, intuitive interface for playing Gomoku (Five-in-a-Row) with comprehensive authentication and configuration management:

### Core Features
- **Interactive Board**: Click-to-place stone mechanics on configurable board sizes
- **Enhanced Authentication**: Complete user management with login, registration, and profile switching
- **Game Management**: Multi-game support with filtering, sorting, and game switching
- **Real-time Updates**: Bidirectional real-time gameplay using Server-Sent Events (SSE)
- **Configuration Management**: JSON and environment variable configuration support
- **Win Detection**: Automatic detection of 5-in-a-row victories
- **Multi-Profile Support**: Save and switch between multiple user accounts
- **Debug Logging**: Comprehensive logging with configurable levels

### Authentication System
- **Token-based Authentication**: Enhanced tokens with expiration and device tracking
- **User Registration**: Create new user accounts through the frontend
- **Automatic Token Refresh**: Seamless token renewal without user intervention
- **Profile Management**: Save, load, and switch between multiple user profiles
- **Credential Persistence**: Secure credential storage with optional encryption
- **GUI Integration**: Complete authentication interface integrated into main application
- **Protected Operations**: All game operations require authentication
- **Session Restoration**: Automatic login restoration on application startup

### Game Management System
- **Multi-Game Support**: View and manage multiple active games simultaneously
- **Smart Filtering**: Filter games by status (All, Active, Your Turn, Completed)
- **Intelligent Sorting**: Games sorted by priority (active games first, then by date)
- **Game Information**: Display opponent name, board size, turn status, and game progress
- **One-Click Loading**: Load any game directly into the main game board
- **Status Indicators**: Visual indicators for game status (🔥 Your Turn, ⏳ Opponent's Turn, ✅ Won, ❌ Lost)
- **Real-time Updates**: Game list refreshes automatically to show current status

### Real-time Updates System
- **Server-Sent Events (SSE)**: Live connection to backend for instant game updates
- **Bidirectional Updates**: Changes made in GUI appear in web browser instantly and vice versa
- **HTML Parsing**: Intelligent parsing of SSE HTML events to extract game state
- **Automatic Reconnection**: Robust connection management with automatic retry logic
- **Authentication Integration**: Secure SSE connections with token-based authentication
- **Visual Indicators**: SSE connection status displayed in GUI interface

## Architecture

### Core Components
- **GUI Framework**: DearPyGui (Modern OpenGL-based interface)
- **Authentication Manager**: Comprehensive auth system with profile management
- **Configuration Manager**: JSON and environment variable configuration
- **API Client**: httpx async HTTP client with automatic authentication
- **SSE Client**: Server-Sent Events client for real-time updates
- **HTML Parser**: BeautifulSoup-based parser for extracting game state from SSE events
- **Backend Integration**: Django REST API with enhanced token authentication

### New Authentication Architecture
- **AuthManager**: Central authentication coordinator with profile management
- **ConfigManager**: Configuration loading from JSON files and environment variables
- **APIClient**: HTTP client with integrated authentication and auto-refresh
- **Enhanced Tokens**: Server-side tokens with expiration, device tracking, and refresh capability
- **SSEClient**: Async SSE client with authentication integration and HTML parsing
- **SSEIntegration**: Background thread management for SSE connections

## Quick Start

### Prerequisites

- Python 3.9+ with `uv` package manager
- Django backend running on port 8001

### Installation & Running

1. **Install dependencies**:
   ```bash
   cd frontend
   uv sync
   ```

2. **Configure the application** (optional):
   ```bash
   # Copy example configuration files
   cp .env.example .env
   cp config.example.json config.json
   
   # Edit configuration as needed
   nano .env  # Set GOMOKU_BASE_URL, etc.
   ```

3. **Start the Django backend** (if not already running):
   ```bash
   cd ../backend
   uv run python manage.py runserver 8001
   ```

4. **Run the main Gomoku GUI application**:
   ```bash
   cd frontend
   uv run python gomoku_gui.py
   ```
   
   Optional command line arguments:
   ```bash
   # Enable debug logging
   uv run python gomoku_gui.py --debug
   
   # Use different backend URL
   uv run python gomoku_gui.py --api-url http://localhost:9000
   
   # Combine options
   uv run python gomoku_gui.py --debug --api-url http://localhost:8001

### Configuration Options

The frontend supports multiple configuration methods:

1. **Environment Variables** (highest priority):
   ```bash
   export GOMOKU_BASE_URL=http://localhost:8001
   export GOMOKU_TIMEOUT=30.0
   export GOMOKU_LOG_LEVEL=DEBUG
   ```

2. **`.env` File** (medium priority):
   ```
   GOMOKU_BASE_URL=http://localhost:8001
   GOMOKU_AUTO_REFRESH_TOKEN=true
   GOMOKU_LOG_LEVEL=INFO
   ```

3. **JSON Configuration** (low priority):
   ```json
   {
     "base_url": "http://localhost:8001",
     "timeout": 30.0,
     "auto_refresh_token": true
   }
   ```

## Game Controls

### Main Application (gomoku_gui.py)
- **Login Button**: Open authentication dialog to login with existing credentials
- **Register Button**: Open registration dialog to create new user account
- **Logout Button**: Clear authentication state and return to login screen
- **New Game Button**: Start a fresh game (requires authentication)
- **My Games Button**: Open the game management panel to view and switch between games
- **Mouse Click**: Place stones on board intersections (requires active game)
- **Check Backend**: Verify backend connectivity and server status

### Game Management Panel ("My Games")
- **Game List**: View all your games with status indicators and opponent information
- **Filter Dropdown**: Filter games by status:
  - "All Games": Show all games you're participating in
  - "Active Games": Show only games currently in progress
  - "Your Turn": Show only games where it's your turn to move
  - "Completed Games": Show only finished games
- **Refresh Button**: Manually update the game list from the server
- **Load Game Button**: Click to load a specific game into the main board for play
- **Game Information Display**:
  - Game ID (shortened for readability)
  - Your color (Black/White) vs opponent name
  - Game status with colored indicators
  - Board size (if different from standard 15×15)
  - Game creation date and time

### Authentication Dialogs
- **Login Dialog**: Username/password authentication with "Remember Me" option
- **Registration Dialog**: Complete user registration with email validation
- **Password Toggle**: Show/hide password visibility in login/registration forms
- **Form Validation**: Real-time validation with user-friendly error messages

## Authentication

The frontend provides comprehensive authentication capabilities:

### Basic Authentication
1. **Login**: Use existing credentials to authenticate
2. **Registration**: Create new user accounts through the frontend
3. **Token Management**: Automatic token refresh and expiration handling
4. **Logout**: Clear authentication state and saved credentials

### Advanced Features
1. **Multiple Profiles**: Save and switch between different user accounts
2. **Credential Persistence**: Automatically save login credentials (configurable)
3. **Device Tracking**: Track authentication across different devices
4. **Auto-Refresh**: Seamless token renewal without re-authentication

### Programmatic Usage
```python
from frontend.auth.auth_manager import AuthManager
from frontend.client.api_client import APIClient

# Initialize with configuration
auth_manager = AuthManager(
    base_url="http://localhost:8001",
    config_file="config.json",
    env_file=".env"
)

# Login
success = await auth_manager.login("username", "password")

# Create API client with authentication
api_client = APIClient(auth_manager=auth_manager)

# All API calls will be automatically authenticated
users = await api_client.get_users()
```

## User Guide

### Getting Started with Game Management

1. **Login or Register**: Use the authentication system to create an account or log in
2. **Create Games**: Use the "New Game" button to start new games  
3. **View Your Games**: Click "My Games" to open the game management panel
4. **Filter Games**: Use the dropdown to filter by game status:
   - Show all games, active games only, games where it's your turn, or completed games
5. **Load Games**: Click "Load Game" next to any game to switch to it
6. **Game Status**: Visual indicators show:
   - 🔥 **YOUR TURN** (orange): It's your turn to make a move
   - ⏳ **Opponent's Turn** (blue): Waiting for opponent to move
   - ✅ **You Won!** (green): You won this game
   - ❌ **You Lost** (red): You lost this game
   - ⚫ **Draw** (gray): Game ended in a draw

### Workflow Example
```
1. Login → "My Games" → Filter to "Your Turn" → Click "Load Game" → Make move
2. Create new game → Switch between games using "My Games" panel
3. View completed games to review your wins/losses
```

## Game Rules

- **Turn Order**: Black player always goes first
- **Objective**: Get exactly 5 stones in a row (horizontal, vertical, or diagonal)
- **Board Size**: 15x15 grid
- **Win Condition**: First player to achieve 5-in-a-row wins
- **No Overlines**: Lines of 6+ stones do not count as wins (configurable via backend)

## Project Structure

```
frontend/
├── README.md              # This comprehensive guide
├── TODO.md               # Development roadmap and tasks
├── .env.example          # Environment configuration template
├── config.example.json   # JSON configuration template
├── pyproject.toml        # Python dependencies and project config
├── src/                  # Source code modules
│   └── frontend/
│       ├── auth/         # Authentication system
│       │   ├── auth_manager.py      # Main authentication coordinator
│       │   ├── config_manager.py    # Configuration management
│       │   ├── models.py           # Data models (tokens, users, config)
│       │   └── exceptions.py       # Authentication exceptions
│       ├── client/       # API client code
│       │   └── api_client.py       # HTTP client with auth integration
│       ├── game/         # Game state and management
│       │   ├── game_management.py  # Game filtering, sorting, and display logic
│       │   └── game_state.py       # Local game state management
│       ├── ui/           # UI components
│       │   └── auth_dialogs.py     # Authentication dialog components
│       └── main.py       # Application entry point
├── tests/                # Comprehensive test suite
│   ├── test_auth_manager.py        # AuthManager tests (16 tests)
│   ├── test_api_client_auth.py     # API client auth tests (16 tests)
│   ├── test_config_management.py   # Config management tests (16 tests)
│   ├── test_game_management.py     # Game management tests (27 tests)
│   ├── test_integration_full.py    # Full integration tests (4 tests)
│   ├── demo_gui.py                # GUI functionality demo
│   ├── demo_gameplay.py           # Game logic demo
│   └── demo_win.py                # Win condition demo
├── simple_gomoku.py      # Current GUI application
└── gomoku_gui.py         # Enhanced GUI (work in progress)
```

## API Integration

The frontend connects to the Django backend's enhanced REST API:

### Authentication Endpoints
- `POST /api/v1/auth/token/` - Enhanced token authentication with device tracking
- `POST /api/v1/auth/token/refresh/` - Token refresh for expired tokens  
- `POST /api/v1/auth/register/` - User registration with automatic login

### Game Endpoints
- `GET /api/v1/games/` - List games (authenticated)
- `POST /api/v1/games/` - Create new game (authenticated)
- `GET /api/v1/games/{id}/` - Get specific game details
- `POST /api/v1/games/{id}/start/` - Start game
- `POST /api/v1/games/{id}/move/` - Make move (authenticated)
- `GET /api/v1/games/{id}/moves/` - Get game moves

### User Management
- `GET /api/v1/users/` - Get user list (authenticated)
- `POST /api/v1/users/` - Create user (authenticated)
- `GET /api/v1/users/{id}/` - Get specific user

### Public Endpoints
- `GET /api/v1/rulesets/` - Get available rule sets (public)
- `GET /` - Health check endpoint (public)

### Authentication Flow
1. **Enhanced Token**: Includes expiration time, device name, and device info
2. **Automatic Refresh**: APIClient automatically refreshes expired tokens
3. **Device Tracking**: Server tracks which devices are authenticated
4. **Secure Headers**: All authenticated requests include `Authorization: Token <token>`

## Testing

The frontend includes a comprehensive test suite with 52+ tests covering all components:

### Run All Tests
```bash
# Run entire test suite
uv run python -m pytest tests/ -v

# Run specific test categories
uv run python -m pytest tests/test_auth_manager.py -v          # AuthManager tests
uv run python -m pytest tests/test_api_client_auth.py -v       # API client tests  
uv run python -m pytest tests/test_config_management.py -v     # Config management
uv run python -m pytest tests/test_game_management.py -v       # Game management tests
uv run python -m pytest tests/test_integration_full.py -v      # Integration tests
```

### Legacy GUI Tests
```bash
# Demo GUI components (legacy)
uv run python demo_gui.py

# Demo game logic
uv run python demo_gameplay.py

# Demo win detection
uv run python demo_win.py
```

### Test Coverage
- **Authentication System**: 32 tests covering login, registration, token refresh, profiles
- **Configuration Management**: 16 tests covering JSON, env vars, validation, backup/restore  
- **API Integration**: 16 tests covering authenticated requests, auto-refresh, error handling
- **Game Management**: 27 tests covering filtering, sorting, status display, and UI integration
- **Full Integration**: 4 tests covering complete system workflows
- **Legacy Components**: GUI, gameplay, and win detection tests

## Development

### Key Files

- **`simple_gomoku.py`**: Main application with Tkinter GUI
- **`src/frontend/client/api_client.py`**: HTTP client for backend API
- **`src/frontend/game/game_state.py`**: Local game state management
- **`src/frontend/ui/`**: UI component modules

### Backend Communication

The frontend communicates with the Django backend for:
- Game state persistence
- Move validation
- Win condition checking
- Player management
- Rule enforcement

### Local vs Remote State

- **Local State**: UI rendering, click handling, visual feedback
- **Remote State**: Game logic, move validation, persistence
- **Synchronization**: API calls keep local and remote state in sync

## Troubleshooting

### Common Issues

1. **"Connection refused" error**:
   - Ensure Django backend is running on port 8001
   - Check: `curl http://localhost:8001/api/v1/`

2. **GUI doesn't appear**:
   - If using SSH, enable X11 forwarding: `ssh -X`
   - Try running test files to verify installation

3. **Moves not registering**:
   - Check backend logs for API errors
   - Verify game is in ACTIVE status

4. **Dependencies missing**:
   ```bash
   uv sync --dev
   ```

### Debug Mode

For additional debugging information, check the backend API directly:

```bash
# Test API connectivity
curl http://localhost:8001/api/v1/users/

# Check game status
curl http://localhost:8001/api/v1/games/

# Access Django admin
open http://localhost:8001/admin/
```

## Configuration Reference

### Environment Variables

All configuration can be overridden with environment variables using the `GOMOKU_` prefix:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GOMOKU_BASE_URL` | string | `http://localhost:8001` | API server base URL |
| `GOMOKU_TIMEOUT` | float | `30.0` | Request timeout in seconds |
| `GOMOKU_AUTO_REFRESH_TOKEN` | bool | `true` | Automatically refresh expired tokens |
| `GOMOKU_MAX_RETRIES` | int | `3` | Maximum request retry attempts |
| `GOMOKU_LOG_LEVEL` | string | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `GOMOKU_DEBUG_MODE` | bool | `false` | Enable debug mode |
| `GOMOKU_SAVE_CREDENTIALS` | bool | `true` | Save credentials to disk |
| `GOMOKU_ENCRYPT_CREDENTIALS` | bool | `false` | Encrypt saved credentials |
| `GOMOKU_DEFAULT_DEVICE_NAME` | string | `Desktop App` | Default device identifier |

### JSON Configuration

Create a `config.json` file in the frontend directory:

```json
{
  "base_url": "http://localhost:8001",
  "timeout": 30.0,
  "auto_refresh_token": true,
  "max_retries": 3,
  "log_level": "INFO",
  "debug_mode": false,
  "save_credentials": true,
  "encrypt_credentials": false,
  "current_profile": "default",
  "profiles": {},
  "default_device_info": {
    "platform": "Linux",
    "app": "Gomoku Desktop",
    "version": "1.0.0"
  }
}
```

### Profile Management

The system supports multiple user profiles with automatic credential management:

```python
# List saved profiles
profiles = auth_manager.get_saved_profiles()

# Switch to a different profile  
success = auth_manager.switch_profile("work_account")

# Save current session as new profile
auth_manager.save_profile("personal_account", current_user, current_token)
```

## Contributing

When contributing to the frontend:

### Development Workflow
1. **Run Tests**: Execute the full test suite (`pytest tests/ -v`)
2. **Follow TDD**: Write tests before implementing features (RED-GREEN-REFACTOR)
3. **Update Documentation**: Keep README.md and TODO.md current
4. **Test Integration**: Verify backend API compatibility
5. **Check All Components**: Test both GUI implementations

### Code Standards  
- Use async/await patterns consistently
- Implement comprehensive error handling
- Follow Pydantic models for data structures
- Add logging with appropriate levels
- Write comprehensive docstrings

### Testing Requirements
- Maintain 100% test coverage for authentication components
- Write both unit and integration tests
- Mock external dependencies appropriately
- Test both success and error scenarios
- Validate configuration handling

### Pull Request Checklist
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Documentation updated (README.md, TODO.md)
- [ ] Configuration examples provided
- [ ] Error handling implemented
- [ ] Integration tested with backend
- [ ] Backward compatibility maintained

## License

Part of the Gomoku Claude project.