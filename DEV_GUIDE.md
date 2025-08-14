# Gomoku Development Guide

## Overview

This development guide documents the key lessons learned, best practices, and architectural decisions made during the development of this full-stack Gomoku game. It serves as a reference for future development and maintenance.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Django & DRF Lessons](#django--drf-lessons)
3. [HTMX Integration](#htmx-integration)
4. [Server-Sent Events (SSE)](#server-sent-events-sse)
5. [Testing Strategy](#testing-strategy)
6. [Database Design](#database-design)
7. [Enhanced Authentication System](#enhanced-authentication-system)
8. [Frontend Development](#frontend-development)
9. [Performance Optimization](#performance-optimization)
10. [Security Considerations](#security-considerations)
11. [Debugging Tips](#debugging-tips)
12. [Common Pitfalls](#common-pitfalls)

---

## Architecture Overview

### Technology Stack

**Backend:**
- Django 5.2 with Django REST Framework
- PostgreSQL database
- Daphne ASGI server for SSE support
- django-eventstream for real-time features

**Frontend:**
- HTMX for dynamic interactions
- Bootstrap 5 for responsive design
- Minimal JavaScript (progressive enhancement)
- CSS Grid for game board layout

**Key Architectural Decisions:**
- **Service Layer Pattern**: Game logic separated into `GameService` class
- **Template-Based SSE**: HTML fragments sent via SSE instead of JSON
- **Progressive Enhancement**: Works without JavaScript, enhanced with HTMX
- **Test-Driven Development**: All features built with TDD methodology

---

## Django & DRF Lessons

### Service Layer Pattern

**Best Practice**: Keep business logic in service classes, not views.

```python
# ❌ Bad: Business logic in view
class GameMoveView(View):
    def post(self, request, game_id):
        game = Game.objects.get(id=game_id)
        # Complex game logic here...
        
# ✅ Good: Business logic in service
class GameMoveView(View):
    def post(self, request, game_id):
        game = Game.objects.get(id=game_id)
        move = GameService.make_move(game, request.user.id, row, col)
```

### Custom Exceptions

**Lesson**: Create domain-specific exceptions for better error handling.

```python
# Custom exceptions in core/exceptions.py
class InvalidMoveError(Exception):
    """Raised when a move is invalid"""
    pass

class GameStateError(Exception):
    """Raised when game state is invalid"""
    pass
```

### Database Optimization

**Key Patterns:**
```python
# Always use select_related for foreign keys
games = Game.objects.select_related('black_player', 'white_player', 'ruleset')

# Use prefetch_related for reverse foreign keys
users = User.objects.prefetch_related('black_games', 'white_games')
```

### Mixins for Code Reuse

```python
class UserGamesMixin:
    """Reusable mixin for user game queries"""
    def get_user_games_query(self, user):
        return Q(black_player=user) | Q(white_player=user)
```

---

## HTMX Integration

### Core Principles

1. **HTML Over JSON**: Return HTML fragments, not JSON responses
2. **Progressive Enhancement**: Basic functionality without JavaScript
3. **Declarative Interactions**: Use `hx-*` attributes instead of event listeners

### Best Practices

**✅ Good HTMX Patterns:**
```html
<!-- Simple form submission -->
<form hx-post="/games/123/move/" 
      hx-target="#game-board" 
      hx-swap="innerHTML">
  
<!-- Include CSRF token dynamically -->
<div hx-include="[name='csrfmiddlewaretoken']">
```

**❌ Avoid Anti-Patterns:**
```html
<!-- Don't use static CSRF tokens in templates -->
<div hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>

<!-- Don't mix HTMX with complex JavaScript -->
<div onclick="complexJavaScriptFunction()">
```

### HTMX + Django Views

**Server-side pattern for HTMX:**
```python
def game_move_view(request, game_id):
    # Process the move
    move = GameService.make_move(game, user_id, row, col)
    
    # Return HTML fragment for HTMX
    if request.headers.get('HX-Request'):
        return render(request, 'partials/game_board.html', {'game': game})
    
    # Fallback for non-HTMX requests
    return redirect('game_detail', game_id=game_id)
```

---

## Server-Sent Events (SSE)

### Critical Lessons Learned

#### 1. HTML Escaping Issues

**Problem**: `django-eventstream` JSON-encodes data by default, escaping HTML quotes.

**Solution**: Use `json_encode=False` parameter.

```python
# ❌ Wrong: HTML gets escaped
send_event(channel, event_name, html_content)

# ✅ Correct: Raw HTML preserved
send_event(channel, event_name, html_content, json_encode=False)
```

#### 2. CSRF Token Handling

**Problem**: Static CSRF tokens in SSE-updated content don't match page tokens.

**Solution**: Use dynamic CSRF token inclusion.

```html
<!-- ❌ Wrong: Static token -->
<div hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>

<!-- ✅ Correct: Dynamic token -->
<div hx-include="[name='csrfmiddlewaretoken']">
```

#### 3. HTMX SSE Extension vs Manual JavaScript

**Key Insight**: Trust HTMX patterns instead of fighting them.

```html
<!-- ✅ Simple and effective -->
<div hx-ext="sse" 
     sse-connect="/api/v1/events/?channel=user-{{ user.id }}" 
     sse-swap="game_move">
```

**Avoid**: Complex manual JavaScript SSE handling that bypasses HTMX.

### SSE Implementation Pattern

```python
# In views.py
def make_move_view(request, game_id):
    # Process move
    move = GameService.make_move(game, user_id, row, col)
    
    # Send SSE to opponent
    opponent_id = get_opponent_id(game, request.user)
    board_html = render_to_string('partials/game_board.html', {
        'game': game,
        'csrf_token': get_token(request)
    }, request=request).strip()
    
    # Clean up for SSE protocol
    board_html_sse = board_html.replace('\n\n', ' ').strip()
    
    # Send with json_encode=False to prevent escaping
    send_event(f'user-{opponent_id}', 'game_move', board_html_sse, json_encode=False)
```

---

## Testing Strategy

### TDD Methodology

**Red-Green-Refactor Cycle:**
1. **Red**: Write failing test defining desired behavior
2. **Green**: Write minimal code to make test pass
3. **Refactor**: Improve code while keeping tests green

### Test Categories

**Unit Tests**: Individual functions and methods
```python
def test_game_service_validates_move_bounds(self):
    with self.assertRaises(InvalidMoveError):
        GameService.make_move(self.game, self.user.id, -1, 0)
```

**Integration Tests**: Full workflows
```python
def test_complete_game_workflow(self):
    # Create challenge
    response = self.client.post('/api/challenges/', data)
    # Accept challenge  
    response = self.client.post(f'/api/challenges/{challenge_id}/respond/', {'action': 'accept'})
    # Make moves and verify game state
```

**Web Interface Tests**: HTMX interactions
```python
def test_htmx_move_updates_board(self):
    response = self.client.post(url, data, HTTP_HX_REQUEST='true')
    self.assertContains(response, 'stone-black')
```

### Testing Best Practices

1. **Use Factory Pattern**: Create test data with factory methods
2. **Test Edge Cases**: Invalid moves, boundary conditions, race conditions
3. **Mock External Dependencies**: Don't rely on external services in tests
4. **Test Both Happy Path and Error Cases**: Comprehensive coverage

---

## Database Design

### Key Models

**Game State Management:**
```python
class Game(models.Model):
    board_state = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=GameStatus.choices)
    current_player = models.CharField(max_length=5, choices=[('BLACK', 'Black'), ('WHITE', 'White')])
```

**Friendship System:**
```python
class Friendship(models.Model):
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests')
    addressee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_requests')
    status = models.CharField(max_length=10, choices=FriendshipStatus.choices)
    
    class Meta:
        unique_together = ['requester', 'addressee']
```

### Database Optimization

**Strategic Indexes:**
```python
class Meta:
    indexes = [
        models.Index(fields=['status', 'created_at']),  # Game filtering
        models.Index(fields=['black_player', 'white_player']),  # Player games
    ]
```

**Query Optimization:**
- Use `select_related()` for foreign keys
- Use `prefetch_related()` for reverse foreign keys
- Add database indexes for frequently queried fields

---

## Frontend GUI Authentication System

### Overview

The frontend includes a comprehensive GUI authentication system built with DearPyGUI, providing desktop application authentication capabilities with the same enhanced token system used by the backend API.

### Architecture

**Core Components:**
- **AuthManager**: Backend integration for token management and API calls
- **AuthenticationManager**: GUI coordinator managing authentication dialogs
- **LoginDialog/RegisterDialog**: Modal dialogs with form validation
- **APIClient**: Authenticated HTTP client with auto-refresh capabilities

**Key Features:**
- **GUI Authentication Dialogs**: Native desktop login/registration forms
- **Form Validation**: Real-time validation with user-friendly error messages
- **Token Management**: Automatic token refresh and session restoration
- **Profile Persistence**: Save and switch between multiple user accounts
- **Async Integration**: Proper threading for GUI compatibility with async operations

### Implementation Pattern

**Main Application Integration:**
```python
# Initialize authentication after DearPyGUI context
dpg.create_context()

auth_manager = AuthenticationManager(
    config_file="gomoku_config.json",
    env_file=".env"
)

api_client = APIClient(
    base_url="http://localhost:8001",
    auth_manager=auth_manager.auth_manager
)

# Protected operations check authentication
def create_new_game():
    if not auth_manager.is_authenticated():
        show_login_required_message()
        return
    # ... proceed with game creation
```

**Threading Pattern for GUI Compatibility:**
```python
def _on_login_clicked(self):
    async def login_task():
        success = await self.perform_login()
        if success:
            self.hide()
            if self._on_success_callback:
                self._on_success_callback()
    
    # Handle event loop compatibility
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(login_task())
    except RuntimeError:
        # No event loop running, create new thread
        def run_login():
            try:
                asyncio.run(login_task())
            except Exception as e:
                logger.error(f"Error in login thread: {e}")
        threading.Thread(target=run_login, daemon=True).start()
```

### Configuration System

**Multi-layer Configuration:**
```python
# Environment variables (highest priority)
GOMOKU_BASE_URL=http://localhost:8001
GOMOKU_AUTO_REFRESH_TOKEN=true
GOMOKU_LOG_LEVEL=DEBUG

# JSON configuration (medium priority)
{
  "base_url": "http://localhost:8001",
  "timeout": 30.0,
  "profiles": {
    "default": {
      "username": "user",
      "last_login": "2025-08-14T10:30:00Z"
    }
  }
}
```

### Error Handling Patterns

**HTTP Client Error Handling:**
```python
async def _make_request(self, method, endpoint, **kwargs):
    try:
        # Try existing client
        response = await self.client.request(method, endpoint, **kwargs)
    except RuntimeError as e:
        if "event loop" in str(e).lower():
            # Create new client for this thread's event loop
            async with httpx.AsyncClient(base_url=self.base_url) as new_client:
                response = await new_client.request(method, endpoint, **kwargs)
        else:
            raise
    
    response.raise_for_status()
    return response.json()
```

### Testing Strategy

**Manual Testing Application:**
- Complete test GUI (`test_auth_gui_manual.py`) for manual validation
- Comprehensive test scenarios covering all authentication flows
- Error simulation and edge case testing
- User experience validation

**Unit Tests:**
- Authentication manager logic tests
- Form validation tests
- Configuration management tests
- API client integration tests

### Best Practices

**GUI Development:**
1. **Initialization Order**: Create DearPyGUI context before authentication dialogs
2. **Thread Safety**: Use threading for async operations in GUI callbacks
3. **Error Handling**: Graceful degradation with user-friendly error messages
4. **Resource Cleanup**: Proper cleanup of HTTP clients and authentication resources

**Authentication Flow:**
1. **Session Restoration**: Automatically restore saved authentication on startup
2. **Protected Operations**: Guard all API calls with authentication checks
3. **Token Refresh**: Transparent token refresh without user intervention
4. **Profile Management**: Support multiple user profiles with easy switching

---

## Frontend Development

### CSS Grid for Game Board

**Dynamic Board Sizing:**
```css
.game-board-grid {
    display: grid;
    grid-template-columns: repeat(var(--board-size), 1fr);
    grid-template-rows: repeat(var(--board-size), 1fr);
}
```

**Template Integration:**
```html
<div class="game-board-grid" 
     style="--board-size: {{ game.ruleset.board_size }};">
```

### Responsive Design Patterns

**Mobile-First Approach:**
```css
/* Base styles for mobile */
.board-intersection {
    width: var(--intersection-size, 30px);
}

/* Tablet adjustments */
@media (max-width: 768px) {
    .board-intersection {
        --intersection-size: calc(var(--base-intersection-size, 30px) * 0.8);
    }
}
```

### Progressive Enhancement

**Core Principle**: Essential functionality works without JavaScript.

```html
<!-- Works without JavaScript -->
<form method="post" action="/games/123/move/">
    <input type="hidden" name="row" value="0">
    <input type="hidden" name="col" value="0">
    <button type="submit">Make Move</button>
</form>

<!-- Enhanced with HTMX -->
<div hx-post="/games/123/move/" 
     hx-vals='{"row": 0, "col": 0}'
     hx-target="#game-board">
```

---

## Performance Optimization

### Database Performance

**Query Optimization:**
```python
# ❌ N+1 queries
for game in Game.objects.all():
    print(game.black_player.username)  # Database hit per game

# ✅ Single query
games = Game.objects.select_related('black_player', 'white_player')
for game in games:
    print(game.black_player.username)  # No additional queries
```

### Frontend Performance

**Minimal JavaScript**: Only 50 lines vs 200+ in complex solutions
**Optimized CSS**: CSS Grid with custom properties for dynamic sizing
**Efficient SSE**: HTML fragments instead of JSON + client-side rendering

### ASGI Server Configuration

**Production Setup:**
```python
# asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gomoku.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
})
```

**Development Command:**
```bash
uv run daphne -p 8001 gomoku.asgi:application
```

---

## Enhanced Authentication System

### Overview

The enhanced authentication system extends Django's basic token authentication with modern features required for desktop and mobile applications. Built using TDD methodology with 36 comprehensive tests.

### Architecture

**Enhanced Token Model:**
```python
class EnhancedToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=40, unique=True)
    device_name = models.CharField(max_length=100, blank=True)
    device_info = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used = models.DateTimeField(null=True, blank=True)
```

**Key Features:**
- **Automatic Expiration**: Tokens expire after 7 days (configurable)
- **Device Tracking**: Associate tokens with specific devices/applications
- **Usage Monitoring**: Track when tokens were last used
- **Multiple Tokens**: Users can have multiple active tokens for different devices
- **Token Refresh**: Refresh expiring tokens without re-authentication

### API Endpoints

**User Registration:**
```bash
POST /api/v1/auth/register/
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "securepass123",
  "display_name": "New User",
  "device_name": "Mobile App",
  "device_info": {"os": "iOS", "version": "15.0"}
}
```

**Enhanced Token Obtain:**
```bash
POST /api/v1/auth/token/
{
  "username": "user",
  "password": "password",
  "device_name": "Desktop App",
  "device_info": {"os": "Linux", "app": "Gomoku-Client-v1.0"}
}
```

**Token Refresh:**
```bash
POST /api/v1/auth/token/refresh/
Authorization: Token YOUR_TOKEN_HERE
```

### Authentication Backend

**Custom Authentication:**
```python
class EnhancedTokenAuthentication(TokenAuthentication):
    model = EnhancedToken
    
    def authenticate_credentials(self, key):
        token = self.model.objects.get(key=key)
        
        # Check expiration
        if token.is_expired:
            raise AuthenticationFailed('Token has expired.')
        
        # Update usage tracking
        token.update_last_used()
        
        return (token.user, token)
```

### Development Patterns

**TDD Implementation:**
1. **RED**: Write failing tests for desired behavior
2. **GREEN**: Implement minimal code to pass tests
3. **REFACTOR**: Clean up implementation while maintaining test coverage

**Test Categories:**
- **Model Tests**: Token creation, expiration, device tracking (15 tests)
- **Manager Tests**: Token management operations (3 tests)
- **Authentication Tests**: API authentication flows (3 tests)
- **Endpoint Tests**: Registration and token management (18 tests)

### Best Practices

**Token Security:**
- Tokens use cryptographically secure random generation
- Automatic expiration prevents indefinite access
- Device tracking aids in security monitoring
- Expired tokens are automatically cleaned up

**Database Optimization:**
- Strategic indexes on key, user+expires_at, and expires_at
- Efficient queries with select_related for user data
- Bulk cleanup operations for expired tokens

**Error Handling:**
- Standardized error responses across all endpoints
- Proper HTTP status codes (400, 401, 403)
- Detailed validation messages for registration

### Mobile/Desktop Integration

**Device Information Structure:**
```json
{
  "device_name": "User-friendly device name",
  "device_info": {
    "os": "iOS/Android/Windows/Linux",
    "version": "OS version",
    "app": "Application name",
    "app_version": "Application version"
  }
}
```

**Frontend Implementation Patterns:**
- Configuration-based credential storage
- Automatic token refresh before expiration
- Multiple user profile support
- Secure token storage (keychain/keystore for mobile)

---

## Security Considerations

### CSRF Protection

**HTMX Integration:**
```html
<!-- Dynamic CSRF for HTMX -->
<div hx-include="[name='csrfmiddlewaretoken']">

<!-- In templates, ensure CSRF token is available -->
{% csrf_token %}
```

### Input Validation

**Server-Side Validation:**
```python
def make_move(self, game, user_id, row, col):
    # Validate bounds
    if not (0 <= row < game.ruleset.board_size):
        raise InvalidMoveError("Row out of bounds")
    
    # Validate turn
    if game.current_player_id != user_id:
        raise PlayerError("Not your turn")
```

### Authentication Patterns

**Dual Authentication System:**
- Web Interface: Django sessions
- API: DRF token authentication

---

## Debugging Tips

### SSE Debugging

**Browser Console:**
```javascript
// Check SSE connection
const eventSource = new EventSource('/api/v1/events/?channel=user-123');
eventSource.onmessage = (event) => console.log('SSE:', event.data);
```

**Server-Side Logging:**
```python
import logging
logger = logging.getLogger(__name__)

def send_move_update(channel, html_data):
    logger.info(f"📤 SSE: Sending to {channel}, data length: {len(html_data)}")
    send_event(channel, 'game_move', html_data, json_encode=False)
```

### HTMX Debugging

**Enable HTMX Logging:**
```html
<script>
    htmx.config.historyCacheSize = 0;  // Disable cache for debugging
    document.body.addEventListener('htmx:afterRequest', function(event) {
        console.log('HTMX Request:', event.detail);
    });
</script>
```

### Database Query Analysis

**Enable Query Logging:**
```python
# settings.py
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
}
```

---

## Common Pitfalls

### 1. SSE Data Escaping

**Problem**: HTML gets escaped in SSE transmission
**Solution**: Use `json_encode=False` in `send_event()`

### 2. CSRF Token Mismatch

**Problem**: Static CSRF tokens in dynamic content
**Solution**: Use `hx-include="[name='csrfmiddlewaretoken']"`

### 3. Complex JavaScript Over HTMX

**Problem**: Fighting HTMX with manual DOM manipulation
**Solution**: Trust HTMX patterns and declarative approach

### 4. N+1 Database Queries

**Problem**: Looping over objects without prefetching relations
**Solution**: Use `select_related()` and `prefetch_related()`

### 5. Missing Database Migrations

**Problem**: Model changes without corresponding migrations
**Solution**: Always run `makemigrations` after model changes

### 6. Static File Issues in Production

**Problem**: Static files not served properly with ASGI server
**Solution**: Configure static file serving in ASGI application

### 7. GUI Event Loop Conflicts (DearPyGUI + AsyncIO)

**Problem**: "RuntimeError: no running event loop" or "Event loop is closed" errors when integrating async operations with DearPyGUI callbacks.

**Root Cause**: DearPyGUI runs in its own event loop, but async operations try to use asyncio event loops. When GUI callbacks try to use `asyncio.create_task()` or `asyncio.run()`, they conflict with the GUI's event loop.

**Solutions**:

**Threading Pattern for GUI Callbacks:**
```python
def _on_button_clicked(self):
    async def async_task():
        result = await some_async_operation()
        # Update GUI with result
    
    # Handle event loop compatibility
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(async_task())
    except RuntimeError:
        # No event loop running, create new thread
        import threading
        def run_task():
            try:
                asyncio.run(async_task())
            except Exception as e:
                logger.error(f"Error in async thread: {e}")
        threading.Thread(target=run_task, daemon=True).start()
```

**HTTP Client Across Event Loops:**
```python
async def _make_request(self, method, endpoint, **kwargs):
    try:
        # Try existing client first
        response = await self.client.request(method, endpoint, **kwargs)
    except RuntimeError as e:
        if "event loop" in str(e).lower():
            # Create new client for this thread's event loop
            async with httpx.AsyncClient(base_url=self.base_url) as new_client:
                response = await new_client.request(method, endpoint, **kwargs)
        else:
            raise
    return response.json()
```

**Clean Shutdown Pattern:**
```python
finally:
    # Cleanup authentication system
    if auth_manager:
        try:
            asyncio.run(auth_manager.close())
        except RuntimeError as e:
            if "event loop" in str(e).lower():
                logger.debug("Skipping cleanup - event loop already closed")
            else:
                logger.error(f"Error during cleanup: {e}")
        except Exception as e:
            logger.error(f"Error closing auth manager: {e}")
```

**Key Insights**:
- DearPyGUI initialization must happen before creating authentication dialogs
- HTTP clients are bound to specific event loops and can't be shared across threads
- Use daemon threads for background async operations to prevent hanging on exit
- Always handle both "no event loop" and "event loop closed" scenarios

---

## Development Workflow

### TDD Development Cycle

```bash
# 1. Write failing test (RED)
uv run python manage.py test web.tests.test_game_board::TestGameBoard::test_new_feature

# 2. Run test to confirm failure
uv run python manage.py test web.tests.test_game_board

# 3. Write minimal implementation (GREEN)
# Edit views.py, templates/, etc.

# 4. Run test to confirm pass
uv run python manage.py test web.tests.test_game_board

# 5. Refactor and run all tests (REFACTOR)
uv run python manage.py test

# 6. Update documentation
```

### Git Workflow

```bash
# Feature development
git checkout -b feature/sse-bug-fixes
git add .
git commit -m "Fix SSE HTML escaping with json_encode=False

- Add json_encode=False parameter to send_event calls
- Fix CSRF token handling in dynamic content
- Simplify HTMX SSE integration approach

🤖 Generated with Claude Code"

git push origin feature/sse-bug-fixes
```

---

## Tools & Commands Reference

### Development Server

```bash
# ASGI server for SSE support
uv run daphne -p 8001 gomoku.asgi:application

# Traditional Django server (no SSE)
uv run python manage.py runserver 8001
```

### Testing

```bash
# All tests
uv run python manage.py test

# Specific app
uv run python manage.py test web

# Specific test class
uv run python manage.py test web.tests.test_game_board::TestGameBoard

# With coverage
uv run coverage run --source='.' manage.py test
uv run coverage report
```

### Database

```bash
# Migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# Shell with Django context
uv run python manage.py shell

# Admin user
uv run python manage.py createsuperuser
```

---

## Conclusion

This development guide captures the key lessons learned during the development of a production-ready, real-time multiplayer Gomoku game. The most important insights are:

1. **Trust Framework Patterns**: Don't fight HTMX with complex JavaScript
2. **Test-Driven Development**: Write tests first, implement minimal solutions
3. **Progressive Enhancement**: Ensure basic functionality without JavaScript
4. **Service Layer Architecture**: Keep business logic separate from views
5. **Performance First**: Optimize database queries and minimize client-side complexity

The combination of Django + HTMX + SSE provides a powerful, modern web development stack that prioritizes simplicity, performance, and maintainability.