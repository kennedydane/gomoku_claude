# How to Run the Gomoku Game

## Quick Start

1. **Ensure backend is running** (already running on port 8001)
   ```bash
   # If not running, start it with:
   cd backend
   uv run uvicorn backend.main:app --reload --port 8001
   ```

2. **Run the GUI**
   ```bash
   cd frontend
   uv run python simple_gomoku.py
   ```

3. **Play the game!**
   - Click "New Game" to start
   - Click on the board to place stones
   - Get 5 in a row to win!

## Controls

- **Mouse**: Click on board intersections to place stones
- **New Game Button**: Start a fresh game
- **Window Close**: Exit the application

## Game Rules

- Black always goes first
- Players alternate turns
- First to get exactly 5 stones in a row wins
- Valid directions: horizontal, vertical, diagonal

## Troubleshooting

If the game doesn't work:

1. Check backend is running:
   ```bash
   curl http://localhost:8001/
   ```

2. Check you have the dependencies:
   ```bash
   cd frontend
   uv sync
   ```

3. Make sure port 8001 is not blocked by firewall

Enjoy playing Gomoku!