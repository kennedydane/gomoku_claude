# Gomoku Game - Full Stack Django Application

A complete Gomoku (Five in a Row) game with Django backend API and responsive web interface.

## Features

### **🎮 Game Features**
- **Interactive Game Board**: CSS Grid-based responsive game board
- **Real-time Gameplay**: Server-Sent Events (SSE) for instant move updates
- **Move Validation**: Comprehensive move validation and win detection
- **Challenge System**: Player-to-player game challenges with accept/reject
- **Friend System**: Add friends, send/accept friend requests

### **🔐 Authentication & Security**
- **Web Authentication**: Django sessions with login/logout
- **API Authentication**: Token-based authentication for API endpoints
- **CSRF Protection**: Built-in CSRF protection for all forms
- **Input Validation**: Comprehensive validation across all endpoints

### **⚡ Real-time Features**
- **Server-Sent Events**: ASGI-powered real-time game updates
- **HTMX Integration**: Dynamic web interface without complex JavaScript
- **Live Game Board**: Opponent moves appear instantly

## Tech Stack

### **Backend**
- Django 5.2 with ASGI (Daphne)
- Django REST Framework
- PostgreSQL with optimized queries
- Django-eventstream for SSE
- Comprehensive test suite (300+ tests)

### **Frontend** 
- HTMX for dynamic interactions
- Bootstrap 5 responsive design
- CSS Grid for game board
- Server-Sent Events for real-time updates

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

5. **Collect static files:**
   ```bash
   uv run python manage.py collectstatic --noinput
   ```

6. **Start ASGI server (required for SSE):**
   ```bash
   uv run daphne -p 8001 gomoku.asgi:application
   ```

## Web Interface

Access the complete web interface at: **http://localhost:8001/**

- **Home**: Game overview and navigation
- **Dashboard**: Your games, challenges, and stats  
- **Friends**: Manage friends and send challenges
- **Games**: Interactive game board with real-time updates

### **Web Authentication**
- Register new account or login with existing credentials
- Session-based authentication for web interface
- Token-based authentication for API access

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

Run the comprehensive 300+ test suite:

```bash
# Run all tests (300+ tests)
uv run python manage.py test

# Run specific app tests  
uv run python manage.py test games      # API tests
uv run python manage.py test users      # User management tests
uv run python manage.py test web        # Web interface tests (74 tests)

# Run web-specific test suites
uv run python manage.py test web.test_challenge_system  # Challenge system TDD (11 tests)
uv run python manage.py test web.test_friend_system     # Friend system TDD (25 tests)
uv run python manage.py test web.test_game_board        # Game board TDD (20 tests)

# Run with coverage
uv run coverage run manage.py test
uv run coverage report
```

### **Test Categories**
- **API Tests**: Comprehensive REST API endpoint testing
- **Web Interface Tests**: TDD-developed web functionality (74 tests)
- **Integration Tests**: End-to-end workflows
- **Game Logic Tests**: Move validation, win detection, rule enforcement
- **Authentication Tests**: Both API token and web session auth
- **Real-time Tests**: SSE and HTMX interactions

### **Test-Driven Development (TDD)**
This project was built using rigorous TDD methodology with Django's built-in test framework:

#### **Testing Framework**
- **Django Test Framework**: Uses `django.test.TestCase` for database isolation
- **Factory Pattern**: Test data generation using factory classes
- **Client Testing**: HTTP request/response testing with Django test client
- **Coverage**: High test coverage across all components

#### **TDD Process**
1. **RED**: Write failing test defining desired functionality
2. **GREEN**: Write minimal code to make test pass  
3. **REFACTOR**: Improve code quality while maintaining test coverage

#### **Test Structure**
```
tests/
├── factories.py          # Test data factories
web/
├── test_views.py         # View functionality tests
├── test_challenge_system.py  # Challenge system TDD (13+ tests)
├── test_friend_system.py     # Friend system TDD (25+ tests)
└── test_game_board.py        # Game board TDD (20+ tests)
```

## Development

### **Development URLs**
- **Web Interface**: http://localhost:8001/ (main application)
- **Admin Interface**: http://localhost:8001/admin/
- **API Root**: http://localhost:8001/api/v1/
- **SSE Endpoint**: http://localhost:8001/api/v1/events/

### **Development Stack** 
- **ASGI Server**: Daphne (required for SSE)
- **Database**: PostgreSQL on localhost:5434
- **Frontend**: HTMX + Bootstrap 5 + SSE
- **Testing**: Django test framework with 300+ tests

## Security Features

### **Web Security**
- Django session authentication with CSRF protection
- Input validation and XSS prevention
- Secure cookie configuration
- Form validation with Django forms

### **API Security**  
- Token-based authentication required for all operations
- CORS configuration for frontend integration
- Race condition protection with database locking
- Player validation to prevent same user as both players

### **Real-time Security**
- User-specific SSE channels (user-{id})
- Authentication required for SSE connections
- ASGI middleware security

## Development Status ✅ PRODUCTION READY

### **🎉 All Major Development Complete!**

**✅ Phases 1-6: Security → Architecture → Testing → Advanced Features → Web Interface → Real-time**

#### **Phase 1-2: Security & Architecture** ✅
- Authentication system (web + API)
- Database optimization with indexes
- Race condition protection
- Error handling framework

#### **Phase 3-4: Testing & Advanced Features** ✅  
- 300+ comprehensive test suite
- TDD methodology implementation
- Game logic validation
- Challenge and friend systems

#### **Phase 5-6: Web Interface & Real-time** ✅
- Complete responsive web application
- HTMX-first dynamic interactions  
- Server-Sent Events for real-time gameplay
- Progressive enhancement design

### **Production-Ready Features**
- **Scalable**: ASGI server with connection pooling
- **Tested**: 300+ tests with TDD methodology
- **Secure**: Comprehensive authentication and validation
- **Fast**: Optimized database queries and caching
- **Modern**: HTMX + SSE for excellent UX without complexity