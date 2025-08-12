# Gomoku Game System

A modern, full-stack implementation of Gomoku (Five-in-a-Row) featuring a FastAPI backend with PostgreSQL database and a Dear PyGUI desktop client.

## What is Gomoku?

Gomoku (五目並べ, "five points in a row") is an abstract strategy board game traditionally played with Go pieces on a Go board. The objective is to be the first player to form an unbroken chain of exactly five stones horizontally, vertically, or diagonally.

### Game Rules

**Basic Rules:**
- Two players alternate placing black and white stones on a board
- The first player to get exactly 5 stones in a row wins
- Standard boards are 15×15 or 19×19
- In most variations, overlines (6+ stones in a row) do not count as wins

**Rule Variations Supported:**

1. **Standard Gomoku** - Exactly 5 in a row wins, overlines don't count
2. **Renju** - 15×15 board with forbidden moves for Black:
   - 3-3: Cannot create two open rows of 3 simultaneously
   - 4-4: Cannot create two rows of 4 simultaneously  
   - Overlines: Black cannot create 6+ in a row
3. **Freestyle Gomoku** - Overlines count as wins
4. **Caro** - Must have unblocked 5-in-a-row or overlines to win
5. **Swap2 Opening** - Tournament standard opening protocol

### Tournament History

Gomoku has been played competitively since 1989, with modern tournaments using the Swap2 opening rule since 2009 to balance the first-player advantage.

## Architecture

This implementation consists of two main components:

- **Backend**: FastAPI server providing REST API for game logic and state management
- **Frontend**: Dear PyGUI desktop application for interactive gameplay
- **Database**: PostgreSQL for persistent game storage
- **Containerization**: Docker Compose for easy development and deployment

## Installation

### Prerequisites

- Python 3.9 or higher
- [UV package manager](https://github.com/astral-sh/uv) 
- Docker and Docker Compose
- Git

### Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd gomoku_claude
```

2. **Install dependencies with UV:**
```bash
# Install backend dependencies
cd backend
uv sync

# Install frontend dependencies  
cd ../frontend
uv sync
cd ..
```

3. **Start the database services:**
```bash
docker compose up -d postgres pgadmin
```

4. **Run database migrations:**
```bash
cd backend
uv run alembic upgrade head
cd ..
```

## Usage

### Development Mode

**Start the backend server:**
```bash
cd backend
uv run fastapi dev app/main.py
```
The API will be available at http://localhost:8000
Interactive API docs at http://localhost:8000/docs

**Start the frontend application:**
```bash
cd frontend
uv run python -m gomoku_gui.main
```

**Enable debug logging:**
```bash
# Backend
uv run fastapi dev app/main.py --debug

# Frontend  
uv run python -m gomoku_gui.main --debug
```

### Production Mode

**Start all services:**
```bash
docker compose up -d
```

This starts:
- PostgreSQL database on port 5432
- FastAPI backend on port 8000
- pgAdmin web interface on port 5050

### Database Management

**Access pgAdmin:**
- URL: http://localhost:5050
- Email: admin@gomoku.com
- Password: admin

**Direct PostgreSQL access:**
```bash
docker compose exec postgres psql -U gomoku_user -d gomoku_db
```

## Development

### Project Structure

```
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/routes/     # REST API endpoints
│   │   ├── core/           # Configuration
│   │   ├── db/models/      # SQLAlchemy models
│   │   ├── services/       # Game logic
│   │   ├── schemas/        # Pydantic schemas
│   │   └── main.py         # FastAPI app
│   ├── tests/              # Backend tests
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/               # Dear PyGUI client
│   ├── gomoku_gui/
│   │   ├── ui/            # GUI components  
│   │   ├── client/        # API client
│   │   ├── game/          # Game state
│   │   └── main.py        # Application entry
│   ├── tests/             # Frontend tests
│   └── pyproject.toml
├── docker-compose.yml      # Container orchestration
├── TODO.md                # Task tracking
└── README.md              # This file
```

### Testing

**Run backend tests:**
```bash
cd backend
uv run pytest
```

**Run frontend tests:**
```bash
cd frontend  
uv run pytest
```

**Run all tests:**
```bash
uv run pytest backend/tests/ frontend/tests/
```

### Code Quality

The project follows Test-Driven Development (TDD) principles:

1. Write tests first
2. Implement minimal code to pass
3. Refactor and improve
4. Repeat

**Linting and formatting:**
```bash
# Backend
cd backend
uv run ruff check .
uv run ruff format .

# Frontend
cd frontend
uv run ruff check .
uv run ruff format .
```

## API Documentation

Once the backend is running, interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

- `POST /games/` - Create a new game
- `GET /games/{game_id}/` - Get game state
- `POST /games/{game_id}/moves/` - Make a move
- `GET /games/{game_id}/moves/` - Get move history
- `PUT /games/{game_id}/rules/` - Update rule configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Implement the feature
5. Ensure all tests pass
6. Submit a pull request

## Future Features

- Computer AI opponents with adjustable difficulty
- Multiple concurrent games
- Tournament bracket system
- Game replay and analysis
- Spectator mode
- Online multiplayer support

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

This project was designed and implemented with the assistance of **Claude**, Anthropic's AI assistant. Claude provided architectural guidance, code implementation, documentation, and followed Test-Driven Development principles throughout the development process.

Special thanks to:
- **Claude (Anthropic)** - AI assistant for system design, implementation, and documentation
- **FastAPI** - Modern, fast web framework for building APIs
- **Dear PyGUI** - GPU-accelerated Python GUI framework
- **UV** - Fast Python package and project manager
- **SQLAlchemy** - Python SQL toolkit and ORM
- **PostgreSQL** - Advanced open source relational database
- **Docker** - Containerization platform for consistent development environments

The gomoku rules implementation follows international tournament standards and supports multiple rule variations used in competitive play.