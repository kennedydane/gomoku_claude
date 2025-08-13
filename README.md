# Gomoku Game System

A modern, full-stack implementation of Gomoku (Five-in-a-Row) featuring a Django REST Framework backend with PostgreSQL database, responsive web interface, and Dear PyGUI desktop client.

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

This implementation consists of four main components:

- **Backend**: Django REST Framework server providing REST API for game logic and state management
- **Web Interface**: Responsive Bootstrap 5 + htmx web application for browser-based gameplay
- **Desktop Frontend**: Dear PyGUI desktop application for native interactive gameplay
- **Database**: PostgreSQL for persistent game storage with Django admin interface
- **Containerization**: Docker Compose for easy development and deployment

## Installation

### Prerequisites

- Python 3.12 or higher (3.9+ supported)
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
# Install all dependencies (workspace setup)
uv sync
```

3. **Start the database services:**
```bash
# Development mode (database port exposed on 5434)
docker compose up -d postgres
```

4. **Run database migrations:**
```bash
# Apply all migrations to set up database schema
cd backend
uv run python manage.py migrate
```

5. **Create a superuser (optional):**
```bash
uv run python manage.py createsuperuser
# Or use the provided script: uv run python create_superuser.py
```

6. **Seed the database with test data (optional):**
```bash
uv run python manage.py seed_data
```

## Usage

### Development Mode

**Start the Django backend server:**
```bash
cd backend
uv run python manage.py runserver 8001
```
Services available:
- **Web Interface**: http://localhost:8001/ (Bootstrap 5 + htmx responsive web app)
- **REST API**: http://localhost:8001/api/v1/ (Django REST Framework browsable API)  
- **Admin Interface**: http://localhost:8001/admin/ (admin / admin123)

**Start the desktop frontend (optional):**
```bash
cd frontend
# Basic GUI client
uv run python simple_gomoku.py

# Enhanced GUI with logging
uv run python gomoku_gui.py --debug
```

**Note**: The web interface provides full gameplay functionality through your browser. The desktop frontend is optional for users preferring a native application.

**Database Access:**
- PostgreSQL: `localhost:5434` (exposed for development tools)
- Django Admin: http://localhost:8001/admin/ (replaces pgAdmin)

### Production Mode

**Using Docker Compose:**
```bash
# Start all services in production mode
docker compose --profile production up -d
```

## API Endpoints

The Django REST API provides the following endpoints:

### Users
- `GET /api/v1/users/` - List all users
- `POST /api/v1/users/` - Create a new user
- `GET /api/v1/users/{id}/` - Get user details
- `GET /api/v1/users/{id}/stats/` - Get user statistics
- `POST /api/v1/users/{id}/reset_stats/` - Reset user statistics

### Rule Sets
- `GET /api/v1/rulesets/` - List all rule sets
- `POST /api/v1/rulesets/` - Create a new rule set
- `GET /api/v1/rulesets/{id}/` - Get rule set details

### Games
- `GET /api/v1/games/` - List all games
- `POST /api/v1/games/` - Create a new game
- `GET /api/v1/games/{id}/` - Get game details
- `POST /api/v1/games/{id}/start/` - Start a game
- `POST /api/v1/games/{id}/move/` - Make a move
- `GET /api/v1/games/{id}/moves/` - Get move history
- `POST /api/v1/games/{id}/resign/` - Resign from game

### Sessions & Challenges
- `GET /api/v1/sessions/` - List player sessions
- `GET /api/v1/sessions/active/` - Get active sessions only
- `POST /api/v1/challenges/` - Create a challenge
- `GET /api/v1/challenges/pending/` - Get pending challenges
- `POST /api/v1/challenges/{id}/respond/` - Accept/reject challenge

### Friends
- `POST /api/send-friend-request/` - Send a friend request
- `POST /api/respond-friend-request/{id}/` - Accept/reject friend request
- `GET /api/friends-list/` - Get user's friends
- `GET /api/pending-requests/` - Get pending friend requests
- `GET /api/search-users/` - Search users to befriend

## Development Features

### Django Admin Interface
The Django admin interface provides a comprehensive view of all game data:
- **User Management**: View and manage players, including statistics
- **Game Management**: View games with visual board previews
- **Rule Sets**: Configure different game variations
- **Real-time Monitoring**: Track player sessions and game events

### Game Service Layer
The game logic is implemented in a service layer that handles:
- Move validation (bounds checking, turn validation)
- Win detection (5-in-a-row in all directions)
- Game state management
- Board initialization and updates

### Database Models
- **User**: Player accounts with game statistics
- **RuleSet**: Configurable game rule variations
- **Game**: Individual game sessions with board state
- **GameMove**: Move history and validation
- **PlayerSession**: Online player tracking
- **GameEvent**: Real-time event system
- **Challenge**: Player-to-player game invitations
- **Friendship**: Friend relationships and requests between users

## Testing

Run the test suite:
```bash
cd backend
# Run all tests (265+ total)
uv run python manage.py test

# Run web interface tests (43 tests)
uv run python manage.py test web

# Run with verbose output
uv run python manage.py test --verbosity=2
```

**Test Coverage:**
- **API Tests**: 220+ tests covering authentication, game logic, and challenges
- **Web Interface Tests**: 43 comprehensive TDD tests for web functionality (includes 25 friend system tests)
- **Integration Tests**: End-to-end workflows and edge cases

## Configuration

### Environment Variables
Create a `.env` file in the backend directory:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DB_NAME=gomoku_db
DB_USER=gomoku_user
DB_PASSWORD=your-password-here
DB_HOST=localhost
DB_PORT=5434
```

### Database Configuration
The application uses PostgreSQL with the following default connection:
- Host: localhost
- Port: 5434 (exposed from Docker)
- Database: gomoku_db
- User: gomoku_user

## Project Structure

```
gomoku_claude/
├── backend/              # Django REST Framework backend
│   ├── gomoku/          # Django project settings
│   ├── users/           # User management app
│   ├── games/           # Game logic and models
│   ├── web/             # Web interface app (Bootstrap + htmx)
│   ├── core/            # Shared utilities and commands
│   ├── templates/       # Django templates (base + web)
│   ├── static/          # CSS, JavaScript, images
│   └── manage.py        # Django management script
├── frontend/            # Dear PyGUI desktop client
│   ├── simple_gomoku.py # Basic game client
│   └── gomoku_gui.py    # Enhanced GUI with logging
├── docker-compose.yml   # Docker services configuration
├── data/               # Persistent data volumes
└── README.md           # This file
```

## Contributing

This project follows Test-Driven Development (TDD) principles:
1. Write tests for new features first
2. Implement the minimal code to pass tests
3. Refactor while keeping tests green

Key development practices:
- Use Django's built-in testing framework
- Follow Django coding conventions
- Use the Django admin for data management
- Implement comprehensive error handling

## Recent Major Changes

- ✅ **Friend System (NEW)**: Complete friend request/accept/reject system with TDD (25 tests)
- ✅ **Web Interface**: Complete responsive web app using Bootstrap 5 + htmx
- ✅ **TDD Methodology**: 43 comprehensive tests for web interface following TDD methodology
- ✅ **Django Migration Complete**: Migrated from FastAPI to Django + DRF
- ✅ **Admin Interface**: Built-in Django admin replaces pgAdmin
- ✅ **Comprehensive Testing**: 265+ tests with Django test framework integration
- ✅ **Service Layer**: Clean separation of business logic
- ✅ **Database Optimization**: Strategic indexing and query optimization

## License

[Add your license information here]