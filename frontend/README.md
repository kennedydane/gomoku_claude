# Gomoku Frontend

A Python-based GUI frontend for the Gomoku game that connects to a Django REST API backend.

## Overview

This frontend provides a clean, intuitive interface for playing Gomoku (Five-in-a-Row) with the following features:

- **Interactive Board**: Click-to-place stone mechanics on a 15x15 grid
- **Real-time Gameplay**: Alternating turns between black and white players
- **Win Detection**: Automatic detection of 5-in-a-row victories
- **Game Management**: Start new games, reset board state
- **Backend Integration**: Communicates with Django REST API for game logic

## Architecture

- **GUI Framework**: Tkinter (Python standard library)
- **API Client**: Custom HTTP client using `requests` library
- **Backend**: Django REST API running on `http://localhost:8001`

## Quick Start

### Prerequisites

- Python 3.12+ with `uv` package manager
- Django backend running on port 8001

### Installation & Running

1. **Install dependencies**:
   ```bash
   cd frontend
   uv sync
   ```

2. **Start the Django backend** (if not already running):
   ```bash
   cd ../backend
   uv run python manage.py runserver 8001
   ```

3. **Launch the GUI**:
   ```bash
   cd ../frontend
   uv run python simple_gomoku.py
   ```

## Game Controls

- **Mouse Click**: Place stones on board intersections
- **New Game Button**: Start a fresh game
- **Window Close**: Exit the application

## Game Rules

- **Turn Order**: Black player always goes first
- **Objective**: Get exactly 5 stones in a row (horizontal, vertical, or diagonal)
- **Board Size**: 15x15 grid
- **Win Condition**: First player to achieve 5-in-a-row wins
- **No Overlines**: Lines of 6+ stones do not count as wins (configurable via backend)

## Project Structure

```
frontend/
├── README.md              # This file
├── RUN_GAME.md           # Quick start guide
├── simple_gomoku.py      # Main GUI application
├── gomoku_gui.py         # Alternative GUI implementation
├── pyproject.toml        # Python dependencies
├── src/                  # Source code modules
│   └── frontend/
│       ├── client/       # API client code
│       ├── game/         # Game state management
│       ├── ui/           # UI components
│       └── main.py       # Application entry point
├── tests/                # Test files
├── test_gui.py          # GUI functionality tests
├── test_gameplay.py     # Game logic tests
└── test_win.py          # Win condition tests
```

## API Integration

The frontend connects to the Django backend's REST API:

- **Base URL**: `http://localhost:8001/api/v1/`
- **Endpoints Used**:
  - `GET /games/` - List games
  - `POST /games/` - Create new game
  - `POST /games/{id}/start/` - Start game
  - `POST /games/{id}/move/` - Make move
  - `GET /users/` - Get player information
  - `GET /rulesets/` - Get game rules

## Testing

Run the included test files to verify functionality:

```bash
# Test GUI components
uv run python test_gui.py

# Test game logic
uv run python test_gameplay.py

# Test win detection
uv run python test_win.py
```

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

## Contributing

When making changes to the frontend:

1. Test with all three test files
2. Verify API integration still works
3. Check both GUI implementations (`simple_gomoku.py` and `gomoku_gui.py`)
4. Update this README if adding new features

## License

Part of the Gomoku Claude project.