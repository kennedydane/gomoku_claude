# Gomoku Frontend

A Python-based GUI frontend for the Gomoku game that connects to a Django REST API backend.

## Overview

This frontend provides a clean, intuitive interface for playing Gomoku (Five-in-a-Row) with comprehensive authentication and configuration management:

### Core Features
- **Interactive Board**: Click-to-place stone mechanics on configurable board sizes
- **Enhanced Authentication**: Complete user management with login, registration, and profile switching
- **Configuration Management**: JSON and environment variable configuration support
- **Real-time Gameplay**: Alternating turns with automatic token refresh
- **Win Detection**: Automatic detection of 5-in-a-row victories
- **Multi-Profile Support**: Save and switch between multiple user accounts
- **Debug Logging**: Comprehensive logging with configurable levels

### Authentication System
- **Token-based Authentication**: Enhanced tokens with expiration and device tracking
- **User Registration**: Create new user accounts through the frontend
- **Automatic Token Refresh**: Seamless token renewal without user intervention
- **Profile Management**: Save, load, and switch between multiple user profiles
- **Credential Persistence**: Secure credential storage with optional encryption

## Architecture

### Core Components
- **GUI Framework**: DearPyGui (Modern OpenGL-based interface)
- **Authentication Manager**: Comprehensive auth system with profile management
- **Configuration Manager**: JSON and environment variable configuration
- **API Client**: httpx async HTTP client with automatic authentication
- **Backend Integration**: Django REST API with enhanced token authentication

### New Authentication Architecture
- **AuthManager**: Central authentication coordinator with profile management
- **ConfigManager**: Configuration loading from JSON files and environment variables
- **APIClient**: HTTP client with integrated authentication and auto-refresh
- **Enhanced Tokens**: Server-side tokens with expiration, device tracking, and refresh capability

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

4. **Launch the GUI**:
   ```bash
   cd ../frontend
   uv run python simple_gomoku.py
   ```

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

- **Login Button**: Authenticate with backend (username: admin, password: admin123)
- **New Game Button**: Start a fresh game (requires login)
- **Mouse Click**: Place stones on board intersections (requires active game)
- **Window Close**: Exit the application

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
│       ├── game/         # Game state management
│       ├── ui/           # UI components
│       └── main.py       # Application entry point
├── tests/                # Comprehensive test suite
│   ├── test_auth_manager.py        # AuthManager tests (16 tests)
│   ├── test_api_client_auth.py     # API client auth tests (16 tests)
│   ├── test_config_management.py   # Config management tests (16 tests)
│   ├── test_integration_full.py    # Full integration tests (4 tests)
│   ├── test_gui.py                # GUI functionality tests
│   ├── test_gameplay.py           # Game logic tests
│   └── test_win.py                # Win condition tests
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
- `POST /api/v1/games/{id}/moves/` - Make move (authenticated)
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
uv run python -m pytest tests/test_integration_full.py -v      # Integration tests
```

### Legacy GUI Tests
```bash
# Test GUI components (legacy)
uv run python test_gui.py

# Test game logic
uv run python test_gameplay.py

# Test win detection
uv run python test_win.py
```

### Test Coverage
- **Authentication System**: 32 tests covering login, registration, token refresh, profiles
- **Configuration Management**: 16 tests covering JSON, env vars, validation, backup/restore  
- **API Integration**: 16 tests covering authenticated requests, auto-refresh, error handling
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