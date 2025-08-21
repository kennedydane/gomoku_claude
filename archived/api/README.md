# Archived REST API Components

This directory contains the Django REST Framework API components that were part of the original multi-client architecture but are no longer actively maintained.

## Contents

### DRF ViewSets and Views
- **`games_views.py`**: Game management ViewSets (GameViewSet, PlayerSessionViewSet, ChallengeViewSet)
- **`users_views.py`**: User management ViewSets and enhanced authentication endpoints

### DRF Serializers
- **`games_serializers.py`**: Game-related serializers (GameSerializer, GameMoveSerializer, etc.)
- **`users_serializers.py`**: User-related serializers (UserSerializer, UserCreateSerializer, etc.)

### API Test Suite
- **`tests/`**: Complete API test suite with 250+ tests
  - `test_user_management.py`: User CRUD and authentication tests
  - `test_game_crud.py`: Game creation and management tests
  - `test_move_validation.py`: Move validation and gameplay tests
  - `test_auth_endpoints.py`: Enhanced authentication system tests
  - `test_challenge_system.py`: Challenge creation and response tests
  - `test_enhanced_auth.py`: Token-based authentication tests

## Original API Endpoints

The archived API provided these endpoints:

### Users
- `GET /api/v1/users/` - List all users
- `POST /api/v1/users/` - Create a new user
- `GET /api/v1/users/{id}/` - Get user details
- `GET /api/v1/users/{id}/stats/` - Get user statistics
- `POST /api/v1/users/{id}/reset_stats/` - Reset user statistics

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

### Authentication
- `POST /api/v1/auth/token/` - Enhanced token obtain
- `POST /api/v1/auth/token/refresh/` - Token refresh
- `POST /api/v1/auth/register/` - User registration
- `POST /api/v1/auth/token/legacy/` - Legacy token fallback

## Why This Was Archived

The Gomoku Claude project originally supported multiple client interfaces:
- Web interface (Bootstrap 5 + htmx) ✅ **Active**
- Desktop GUI (Dear PyGUI) ❌ **Archived**
- REST API for third-party clients ❌ **Archived**

Over the course of development, the project evolved to focus primarily on the web interface, which provides:
- Better cross-platform compatibility
- Easier deployment and maintenance  
- Modern responsive design
- Real-time multiplayer functionality via WebSocket notifications
- Simplified authentication via Django sessions

The REST API added complexity without providing value since no third-party clients were using it.

## Features (Archived)

**Complete REST API Implementation:**
- Django REST Framework ViewSets with proper HTTP methods
- Comprehensive serializers with validation
- Enhanced token-based authentication system
- Real-time event system integration
- Extensive test coverage (250+ API tests)
- Proper error handling and exception management

**Multi-Game Support:**
- Subclassed RuleSet architecture (GomokuRuleSet, GoRuleSet)
- Game service layer integration
- Move validation and win detection
- Challenge system between players

## Restoration

If you need to restore the REST API:

1. **Dependencies**: Re-add to `backend/gomoku/settings.py`:
   ```python
   INSTALLED_APPS = [
       # ... existing apps ...
       'rest_framework',
       'rest_framework.authtoken', 
       'corsheaders',
   ]
   
   MIDDLEWARE = [
       # ... existing middleware ...
       'corsheaders.middleware.CorsMiddleware',
   ]
   
   REST_FRAMEWORK = {
       'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
       'PAGE_SIZE': 100,
       'DEFAULT_AUTHENTICATION_CLASSES': [
           'rest_framework.authentication.SessionAuthentication',
           'users.authentication.EnhancedTokenAuthentication',
       ],
       'DEFAULT_PERMISSION_CLASSES': [
           'rest_framework.permissions.IsAuthenticated',
       ],
   }
   ```

2. **Views and Serializers**: Copy archived files back:
   ```bash
   cp archived/api/games_views.py backend/games/views.py
   cp archived/api/games_serializers.py backend/games/serializers.py
   cp archived/api/users_views.py backend/users/views.py
   cp archived/api/users_serializers.py backend/users/serializers.py
   ```

3. **URLs**: Restore API routes in `backend/gomoku/urls.py`:
   ```python
   from rest_framework.routers import DefaultRouter
   from users.views import UserViewSet
   from games.views import GameViewSet, PlayerSessionViewSet, ChallengeViewSet
   
   router = DefaultRouter()
   router.register(r'users', UserViewSet)
   router.register(r'games', GameViewSet)
   router.register(r'sessions', PlayerSessionViewSet) 
   router.register(r'challenges', ChallengeViewSet)
   
   urlpatterns = [
       path('api/v1/', include(router.urls)),
       # ... other patterns ...
   ]
   ```

4. **Tests**: Copy test files back to `backend/tests/`

5. **Package Dependencies**: Re-add DRF dependencies to `pyproject.toml`

All archived components include comprehensive documentation and were fully functional at the time of archival.