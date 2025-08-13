# Gomoku Django Backend

A Django-based REST API backend for a Gomoku (Five in a Row) game application.

## Features

- **Game Management**: Create, start, and manage Gomoku games
- **Authentication**: Token-based authentication system
- **Real-time Updates**: Server-sent events for game updates
- **Move Validation**: Comprehensive move validation and win detection
- **Challenge System**: Player-to-player game challenges
- **Session Management**: Track active player sessions

## Tech Stack

- Django 5.2
- Django REST Framework
- PostgreSQL
- Django Channels (WebSocket support)
- Token Authentication

## Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Start PostgreSQL (Docker):**
   ```bash
   docker compose up postgres -d
   ```

3. **Run migrations:**
   ```bash
   uv run python manage.py migrate
   ```

4. **Create admin user:**
   ```bash
   uv run python manage.py createsuperuser
   ```

5. **Start development server:**
   ```bash
   uv run python manage.py runserver 8001
   ```

## API Endpoints

### Authentication
- `POST /api/v1/auth/token/` - Get authentication token

### Games
- `GET /api/v1/games/` - List games
- `POST /api/v1/games/` - Create new game
- `GET /api/v1/games/{id}/` - Get game details
- `POST /api/v1/games/{id}/start/` - Start game
- `POST /api/v1/games/{id}/move/` - Make move
- `POST /api/v1/games/{id}/resign/` - Resign from game
- `GET /api/v1/games/{id}/moves/` - Get game moves

### Users
- `GET /api/v1/users/` - List users
- `POST /api/v1/users/` - Create user

### Challenges
- `GET /api/v1/challenges/` - List challenges
- `POST /api/v1/challenges/` - Create challenge
- `POST /api/v1/challenges/{id}/respond/` - Respond to challenge

## Authentication

All API endpoints require authentication using Token Authentication:

```bash
curl -H "Authorization: Token YOUR_TOKEN_HERE" http://localhost:8001/api/v1/games/
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
uv run python manage.py test

# Run specific app tests
uv run python manage.py test games
uv run python manage.py test users

# Run with coverage
uv run coverage run manage.py test
uv run coverage report
```

## Development

- Admin interface: http://localhost:8001/admin/
- API root: http://localhost:8001/api/v1/
- Database: PostgreSQL on localhost:5434

## Security Features

- Token-based authentication required for all operations
- CORS configuration for frontend integration
- Input validation on all endpoints
- Race condition protection with database locking
- Player validation to prevent same user as both players

## Development Status ✅ PRODUCTION READY

### Phase 1 Security Fixes (Completed)
-  Implemented authentication system for API endpoints
-  Added player validation to prevent same user as both players  
-  Added race condition protection for concurrent moves
-  Secured CORS configuration
-  Enhanced input validation across all endpoints

### Next: Phase 2 Architecture Refactoring
- Database query optimization with indexes and select_related
- Improved error handling across the stack
- Code structure improvements

### Phase 3: Testing & Quality (Pending)
- API endpoint tests (~95 additional tests)
- Integration test suite expansion
- Performance benchmarks