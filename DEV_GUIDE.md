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
13. [Web Interface Panel Development](#web-interface-panel-development)
14. [Centralized WebSocket Notification System](#centralized-websocket-notification-system)

---

## Architecture Overview

### Technology Stack

**Backend:**
- Django 5.2 with Django REST Framework
- PostgreSQL database
- Daphne ASGI server for SSE support
- django-eventstream for real-time features

**Frontend:**
- HTMX for dynamic interactions (web client)
- Bootstrap 5 for responsive design (web client)
- Minimal JavaScript (progressive enhancement)
- CSS Grid for game board layout
- DearPyGui for desktop GUI client
- Server-Sent Events (SSE) for real-time updates

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

**Query Optimization Patterns:**
```python
# Always use select_related for foreign keys
games = Game.objects.select_related('black_player', 'white_player', 'ruleset')

# Use prefetch_related for reverse foreign keys  
users = User.objects.prefetch_related('black_games', 'white_games')

# Strategic indexes for frequently queried fields
class Meta:
    indexes = [
        models.Index(fields=['status', 'created_at']),
        models.Index(fields=['black_player', 'white_player']),
    ]
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

### django-htmx Library (Evaluated but Not Used)

**Decision**: We evaluated the `django-htmx` library (https://django-htmx.readthedocs.io/) but decided against adoption.

**What django-htmx Provides:**
- `request.htmx` object instead of `request.headers.get('HX-Request')`
- Response helpers: `HttpResponseClientRedirect`, `push_url()`, `retarget()`, etc.
- Template tags for HTMX script inclusion
- Trigger client events via `HX-Trigger` headers

**Why We Didn't Adopt It:**
1. **High Risk, Low Reward**: Our HTMX integration was working perfectly with 346+ tests passing
2. **Minimal Functional Benefits**: Provides developer convenience, not new functionality
3. **Current Patterns Work**: `request.headers.get('HX-Request')` is simple and effective
4. **Production Ready**: Focus should be on new features, not refactoring working systems
5. **Real-time Features**: Our SSE + HTMX integration works excellently without additional layers

**Recommendation**: Only consider django-htmx for new projects. For existing working HTMX implementations, the refactoring cost outweighs the benefits.

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

### Modern Testing Framework (pytest)

**Major Migration to pytest:**
- **Framework**: Migrated from Django TestCase to pytest + pytest-django
- **Coverage**: 86% overall code coverage with detailed reporting
- **Test Count**: 226 tests with 84.5% pass rate (191 passing)
- **Benefits**: Better fixtures, improved isolation, modern testing patterns

### pytest Development Patterns

**Test Structure:**
```python
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from users.models import EnhancedToken

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture  
def test_user(db):
    User = get_user_model()
    return User.objects.create_user(username='testuser', password='testpass')

@pytest.mark.api
@pytest.mark.django_db
class TestGameAPI:
    def test_game_creation(self, api_client, test_user):
        token = EnhancedToken.objects.create_for_device(user=test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        # Test implementation
```

### Test Categories

**API Tests**: REST endpoint validation with pytest
```python
def test_make_move_success(self, api_client, game_users, user_tokens, active_game):
    user1, user2, user3 = game_users
    token1, token2, token3 = user_tokens
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token1.key}')
    response = api_client.post(move_url, {'row': 7, 'col': 7}, format='json')
    assert response.status_code == 200
```

**Model Tests**: Database validation and business logic
```python
def test_ruleset_validation(rulesets):
    mini_ruleset = next(rs for rs in rulesets if rs.name == 'Mini Gomoku')
    assert mini_ruleset.board_size == 8
    assert mini_ruleset.allow_overlines == True
```

**Web Interface Tests**: HTMX interactions with Beautiful Soup
```python
def test_htmx_move_updates_board(self, client, authenticated_user, active_game):
    response = client.post(url, data, HTTP_HX_REQUEST='true')
    soup = BeautifulSoup(response.content, 'html.parser')
    stones = soup.find_all('div', class_='stone-black')
    assert len(stones) == 1
```

### Testing Improvements

**✅ Major Achievements:**
- **Converted 61 tests** from Django TestCase to pytest format
- **Removed unreliable tests**: Eliminated Selenium and JavaScript integration tests
- **Fixed authentication**: Proper EnhancedToken usage throughout test suite
- **Improved coverage**: Detailed coverage reporting with 86% overall coverage
- **Better isolation**: Proper test database handling and unique test data

### Testing Best Practices

1. **Use pytest Fixtures**: Modular, reusable test setup with dependency injection
2. **Factory Pattern**: Create test data with factory-boy for consistent, isolated tests
3. **Test Edge Cases**: Invalid moves, boundary conditions, authentication failures
4. **Beautiful Soup for HTML**: Validate web interface output with proper HTML parsing
5. **Database Isolation**: Use unique test data to prevent conflicts between tests

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

### Database Best Practices

**Model Design Patterns:**
- Use JSONField for complex data (board_state, device_info)
- Add unique constraints where appropriate (friendship pairs)
- Include proper foreign key relationships with cascading deletes

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

### Authentication Testing

**Manual Testing:**
- Complete test GUI (`test_auth_gui_manual.py`) for manual validation
- Comprehensive test scenarios covering all authentication flows

**Unit Testing:**
- Authentication manager logic and form validation
- Configuration management and API client integration

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

## Desktop GUI Client Development

### Architecture Overview

The desktop GUI client uses **DearPyGui** for the interface and implements real-time gameplay through **Server-Sent Events (SSE)**. The client reuses the existing backend SSE infrastructure by parsing HTML events instead of requiring separate JSON APIs.

### Key Components

**GUI Framework:**
- **DearPyGui**: Modern OpenGL-based GUI framework with immediate mode rendering
- **Threading Model**: Background threads for SSE connections to avoid blocking the UI
- **Event Loop Integration**: Careful coordination between DearPyGui and async/await patterns

**Real-time Updates:**
- **SSE Client**: Async client connecting to django-eventstream endpoints
- **HTML Parser**: BeautifulSoup-based parsing of SSE HTML events
- **Authentication Integration**: Token-based authentication for SSE connections

### SSE Implementation Strategy

**HTML Parsing Approach:**
```python
# Instead of creating separate JSON SSE events, reuse existing HTML events
html_content = sse_event_data
soup = BeautifulSoup(html_content, 'html.parser')
board_div = soup.find('div', class_='game-board-grid')
game_id = board_div.get('data-game-id')
```

**Benefits:**
- Single source of truth for SSE events (no duplication)
- Automatic consistency between web and desktop clients
- Leverages existing battle-tested SSE infrastructure

### Authentication Integration

**Token Management:**
```python
class SSEClient:
    def __init__(self, auth_manager, on_game_update):
        # Get current token for SSE authentication
        token = self.auth_manager.get_current_token()
        self.headers = {"Authorization": f"Token {token}"}
```

**URL Construction:**
```python
# SSE endpoint with user-specific channel
user_id = auth_manager.get_current_user().id
endpoint_url = f"{base_url}/api/v1/events/?channel=user-{user_id}"
```

### Threading Model

**Background SSE Processing:**
```python
class SSEIntegration:
    def start_connection(self):
        # Run SSE client in background thread
        self.sse_thread = threading.Thread(
            target=self._run_sse_loop, 
            daemon=True
        )
        self.sse_thread.start()
    
    def _run_sse_loop(self):
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.sse_client.connect())
```

### Template Integration

**Backend Template Updates:**
```html
<!-- Added data attributes for GUI parsing -->
<div class="game-board-grid" 
     data-game-id="{{ game.id }}"
     data-board-size="{{ game.ruleset.board_size }}"
     data-current-player="{{ game.current_player }}"
     data-game-status="{{ game.status }}">
```

**GUI HTML Parsing:**
```python
# Parse board intersections for stone positions
intersections = soup.find_all('div', class_='board-intersection')
for intersection in intersections:
    row = int(intersection.get('data-row'))
    col = int(intersection.get('data-col'))
    
    if intersection.find('div', class_='stone-black'):
        board_state[row][col] = 'black'
    elif intersection.find('div', class_='stone-white'):
        board_state[row][col] = 'white'
```

### Bidirectional Updates

**GUI → Web:**
- GUI makes move via REST API
- Backend triggers SSE event for all connected clients
- Web browser receives SSE event and updates via HTMX

**Web → GUI:**
- Web client makes move via HTMX
- Backend triggers SSE event for all connected clients  
- GUI receives SSE event, parses HTML, and updates board

### Connection Management

**Robust Reconnection:**
```python
async def _connection_loop(self):
    while self.should_connect:
        try:
            await self.sse_client.connect()
            await self.sse_client._listen_for_events()
        except Exception as e:
            logger.warning(f"SSE connection failed: {e}")
            await asyncio.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, 30)  # Exponential backoff
```

**Visual Status Indicators:**
```python
def update_sse_status(self, status):
    color = {
        'Connected': (0, 255, 0),     # Green
        'Connecting': (255, 255, 0),  # Yellow  
        'Disconnected': (255, 0, 0)   # Red
    }[status]
    dpg.configure_item("sse_status", default_value=status, color=color)
```

### Lessons Learned

**Template Caching Issues:**
- Django template changes may require server restart in production
- Template caching can prevent SSE HTML updates from reflecting code changes
- Solution: Restart django server after template modifications

**Authentication Compatibility:**
- GUI auth manager wraps direct AuthManager instance
- SSE client must detect wrapper vs direct instance for compatibility
- Solution: Duck typing to handle both authentication patterns

**HTML Parsing Edge Cases:**
- Missing data attributes cause "game unknown" parsing errors
- Template updates require careful coordination with HTML parser expectations
- Solution: Comprehensive logging and graceful fallback to "unknown" game ID

---

## Performance Optimization

### Key Performance Principles

**Database Efficiency:**
- Query optimization covered in [Database Design](#database-design) section
- Avoid N+1 queries with proper use of `select_related()` and `prefetch_related()`

**Frontend Efficiency:**
- **Minimal JavaScript**: Only 50 lines vs 200+ in complex solutions
- **Optimized CSS**: CSS Grid with custom properties for dynamic sizing  
- **Efficient SSE**: HTML fragments instead of JSON + client-side rendering

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

**Test Coverage:**
- Model tests: Token creation, expiration, device tracking (15 tests)
- Manager tests: Token management operations (3 tests)  
- Authentication tests: API authentication flows (3 tests)
- Endpoint tests: Registration and token management (18 tests)

### Best Practices

**Token Security:**
- Tokens use cryptographically secure random generation
- Automatic expiration prevents indefinite access
- Device tracking aids in security monitoring
- Expired tokens are automatically cleaned up

**Database Design:**
- Strategic indexes on key, user+expires_at, and expires_at fields
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
uv run pytest tests/test_game_crud.py::TestGameCRUD::test_new_feature -v

# 2. Run test to confirm failure
uv run pytest tests/test_game_crud.py -v

# 3. Write minimal implementation (GREEN)
# Edit views.py, models.py, etc.

# 4. Run test to confirm pass
uv run pytest tests/test_game_crud.py::TestGameCRUD::test_new_feature -v

# 5. Refactor and run all tests (REFACTOR)
uv run pytest

# 6. Check coverage and update documentation
uv run coverage report
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
# All tests with pytest (226 tests, 86% coverage)
uv run pytest

# Run with coverage reporting
uv run coverage run -m pytest
uv run coverage report
uv run coverage html

# Specific test modules
uv run pytest tests/test_game_crud.py          # Game CRUD API tests
uv run pytest tests/test_user_management.py    # User management tests
uv run pytest tests/test_rulesets.py          # Ruleset validation tests

# Web interface tests
uv run pytest web/test_friend_system.py       # Friend system tests
uv run pytest web/test_views.py              # Web view tests

# Generate HTML reports
uv run pytest --html=test_reports/pytest_report.html --self-contained-html
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

## Web Interface Panel Development

### Panel Architecture (Phase 11)

The enhanced web interface implements a 3-column dashboard with dynamic panels that update in real-time via SSE. This section documents the architectural patterns and best practices established in Phase 11.

### Dashboard Layout Structure

**3-Column Responsive Layout:**
```html
<div class="container-fluid">
  <div class="row">
    <!-- Left Panel - Games (col-lg-3 col-md-4) -->
    <div class="col-lg-3 col-md-4 d-none d-md-block">
      {% include 'web/partials/games_panel.html' %}
    </div>
    
    <!-- Main Content (col-lg-6 col-md-8 col-12) -->
    <div class="col-lg-6 col-md-8 col-12">
      <!-- Main dashboard content -->
    </div>
    
    <!-- Right Panel - Friends (col-lg-3 d-none d-lg-block) -->
    <div class="col-lg-3 d-none d-lg-block">
      {% include 'web/partials/friends_panel.html' %}
    </div>
  </div>
</div>
```

### Panel Development Patterns

**1. Partial Templates:**
- Create separate partial templates for each panel: `web/partials/games_panel.html`, `web/partials/friends_panel.html`
- Use consistent naming conventions and structure
- Include proper CSS styling within each partial

**2. View Context Integration:**
```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    
    # Panel data
    context.update({
        'active_games': active_games,
        'recent_finished_games': recent_finished_games[:5],
        'friends': Friendship.objects.get_friends(user),
    })
    return context
```

**3. SSE Real-Time Updates:**
```html
<div hx-ext="sse" 
     sse-connect="/api/v1/events/?channel=user-{{ user.id }}" 
     sse-swap="dashboard_update">
  {% include 'web/partials/games_panel.html' %}
</div>
```

### CSS Styling Conventions

**Panel Styling:**
```css
.games-panel, .friends-panel {
    height: fit-content;
    max-height: 70vh;
    overflow-y: auto;
}

/* Responsive behavior */
@media (max-width: 768px) {
    .games-panel, .friends-panel {
        max-height: 50vh;
    }
}
```

**Turn Indicator Animations:**
```css
.my-turn {
    animation: pulse-panel 2s infinite;
}

@keyframes pulse-panel {
    0% { box-shadow: 0 0 0 0 rgba(25, 135, 84, 0.5); }
    70% { box-shadow: 0 0 0 4px rgba(25, 135, 84, 0); }
    100% { box-shadow: 0 0 0 0 rgba(25, 135, 84, 0); }
}
```

### SSE Panel Update Implementation

**Backend SSE Events:**
```python
# Send both game board update AND panel update
send_event(channel, 'game_move', board_html_sse, json_encode=False)
send_event(channel, 'dashboard_update', panel_html_sse, json_encode=False)
```

**Frontend HTMX SSE:**
- Use `sse-swap` attributes to specify which events update which panels
- Maintain separate event channels for different types of updates
- Ensure proper HTML escaping prevention with `json_encode=False`

### Panel Testing Approach

**TDD Implementation:**
1. **RED**: Write failing tests for panel structure and behavior
2. **GREEN**: Implement minimal template and view logic
3. **REFACTOR**: Optimize queries and enhance UX

**Test Examples:**
- Navigation: `test_challenges_menu_removed_from_navigation()`
- Layout: `test_dashboard_three_column_layout()`
- Content: `test_games_panel_shows_active_games()`
- SSE: `test_sse_updates_turn_indicators()`

### Mobile Responsive Design

**Collapsible Panels:**
```html
<!-- Mobile Panels (Collapsible) -->
<div class="d-md-none mt-4">
  <div class="row">
    <div class="col-6">
      <button class="btn btn-outline-primary w-100" 
              data-bs-toggle="collapse" 
              data-bs-target="#mobile-games-panel">
        <i class="bi bi-grid-3x3-gap"></i> Games
      </button>
    </div>
  </div>
  
  <div class="collapse mt-3" id="mobile-games-panel">
    {% include 'web/partials/games_panel.html' %}
  </div>
</div>
```

### Panel Performance

**Efficient Data Loading:**
```python
# Optimized queries with select_related for panel data
active_games = Game.objects.select_related(
    'black_player', 'white_player', 'ruleset'
).filter(user_games_query, status=GameStatus.ACTIVE).order_by('-created_at')

# Limited result sets to prevent UI clutter
recent_finished_games = games.filter(status=GameStatus.FINISHED).order_by('-finished_at')[:5]
```

**SSE Event Efficiency:**
- Only send panel updates when relevant data changes
- Use efficient HTML template rendering
- Minimize SSE event payload size

### Best Practices

**Panel Development:**
1. **Consistent Styling**: Use Bootstrap 5 classes and custom CSS consistently across panels
2. **Responsive Design**: Test panels on mobile devices and ensure collapsible behavior works
3. **Performance**: Limit panel data (e.g., max 5 recent games) to prevent UI clutter and improve performance
4. **Accessibility**: Include proper ARIA labels and keyboard navigation support

**SSE Integration:**
1. **Event Naming**: Use descriptive event names (`dashboard_update`, `friends_update`)
2. **Error Handling**: Always wrap SSE functionality in try-catch blocks
3. **Fallback Behavior**: Ensure panels work without SSE (progressive enhancement)

**Testing Approach:**
1. **TDD First**: Write tests before implementing panel features
2. **Integration**: Test complete workflows from dashboard to game play
3. **Responsive**: Verify panel behavior across screen sizes
4. **SSE**: Mock SSE events to test real-time functionality

### Common Patterns

**Turn Indicator Logic:**
```html
{% if game.current_player == 'BLACK' %}
  {% if user == game.black_player %}
    <span class="badge bg-success my-turn">Your Turn</span>
  {% else %}
    <span class="badge bg-secondary their-turn">Their Turn</span>
  {% endif %}
{% else %}
  <!-- Similar logic for WHITE player -->
{% endif %}
```

**Panel Navigation:**
```javascript
// Panel item click handler
<div onclick="window.location.href='{% url 'web:game_detail' game_id=game.id %}'"
     style="cursor: pointer;">
```

---

## Centralized WebSocket Notification System

### Architecture Philosophy (Phase 14)

The centralized WebSocket notification system was introduced in Phase 14 to address the growing complexity of scattered WebSocket update code across multiple views. This section documents the architectural patterns and best practices for maintainable real-time notification systems.

### Problem Statement

**Before Centralization:**
- WebSocket update code scattered across 6+ locations (GameMoveView, GameResignView, ChallengeFriendView, RespondChallengeView, etc.)
- Inconsistent notification patterns and error handling
- Code duplication and maintenance complexity
- CSRF token issues in WebSocket-delivered content
- Race conditions between HTMX and WebSocket updates

### Centralized Service Architecture

**WebSocketNotificationService Class:**
```python
# web/services.py
class WebSocketNotificationService:
    """
    Centralized service for all WebSocket notifications.
    Eliminates code duplication and provides consistent notification patterns.
    """
    
    EVENT_DEFINITIONS = {
        'game_move': {
            'template': 'web/partials/dashboard_game_panel.html',
            'context_builder': '_build_game_context'
        },
        'dashboard_update': {
            'template': 'web/partials/games_panel.html',
            'context_builder': '_build_dashboard_context'
        },
        'friends_update': {
            'template': 'web/partials/friends_panel.html',
            'context_builder': '_build_friends_context'
        }
    }
    
    def send_notification(self, event_type, user_ids, context_data):
        """Send standardized WebSocket notification."""
        event_def = self.EVENT_DEFINITIONS[event_type]
        
        for user_id in user_ids:
            try:
                # Build user-specific context
                context = self._build_context(event_def['context_builder'], user_id, context_data)
                
                # Render template with proper context
                html_content = render_to_string(event_def['template'], context)
                
                # Send via WebSocket
                WebSocketMessageSender.send_to_user_sync(user_id, event_type, html_content)
                
            except Exception as e:
                logger.error(f"Failed to send {event_type} to user {user_id}: {e}")
```

### Key Benefits

**1. Code Deduplication:**
- Single source of truth for all WebSocket notifications
- Eliminated 6+ instances of scattered WebSocket update code
- Consistent error handling and logging across all notifications

**2. Standardized Event Definitions:**
- EVENT_DEFINITIONS dictionary provides clear structure for all notification types
- Template and context builder patterns ensure consistency
- Easy to add new notification types with standardized patterns

**3. Maintainability:**
- Clear separation of concerns with service layer architecture
- Comprehensive error handling and fallback mechanisms
- Consistent template caching and rendering optimization

### Integration Patterns

**Before (Scattered Code):**
```python
# In GameMoveView
board_html = render_to_string('web/partials/game_board.html', context)
WebSocketMessageSender.send_to_user_sync(opponent.id, 'game_move', board_html)

# In GameResignView  
games_html = render_to_string('web/partials/games_panel.html', context)
WebSocketMessageSender.send_to_user_sync(opponent.id, 'dashboard_update', games_html)

# In ChallengeFriendView
friends_html = render_to_string('web/partials/friends_panel.html', context)
WebSocketMessageSender.send_to_user_sync(challenged.id, 'friends_update', friends_html)
```

**After (Centralized Service):**
```python
# All views use centralized service
notification_service = WebSocketNotificationService()
notification_service.send_game_move_update([opponent.id], {'game': game, 'user': opponent})
notification_service.send_dashboard_update([user.id, opponent.id], {'updated_game': game})
notification_service.send_friends_update([challenged.id], {'new_challenge': challenge})
```

### CSRF Token Client-Side Handling

**Problem Solved:**
WebSocket-delivered content contained stale CSRF tokens that didn't match the page session, causing "CSRF token from POST incorrect" errors.

**Solution - Client-Side JavaScript:**
```javascript
// static/js/csrf-handling.js
document.addEventListener('htmx:configRequest', function(event) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (csrfToken) {
        event.detail.headers['X-CSRFToken'] = csrfToken;
    }
});
```

**Benefits:**
- Automatic CSRF token injection for all HTMX requests
- Uses current page session tokens instead of stale WebSocket tokens
- Eliminates server-side CSRF token generation complexity in WebSocket updates
- Works seamlessly with Django's CSRF middleware

### Race Condition Resolution

**Problem:**
HTMX responses and WebSocket notifications could conflict, causing DOM overwrites and "htmx:swapError" console errors.

**Solution - Coordination Pattern:**
```html
<!-- HTMX actions use hx-swap="none" to prevent DOM conflicts -->
<button hx-post="/games/123/resign/" 
        hx-swap="none"
        hx-confirm="Are you sure?">
    Resign Game
</button>
```

```python
# Views return HTTP 204 No Content for HTMX requests
def resign_view(request, game_id):
    # Process resignation
    game.resign(request.user)
    
    # Send WebSocket notifications to both players
    notification_service.send_dashboard_update([game.black_player.id, game.white_player.id], 
                                               {'updated_game': game})
    
    # Return empty response for HTMX (WebSocket handles UI updates)
    if request.headers.get('HX-Request'):
        return HttpResponse(status=204)  # No Content
    
    return redirect('dashboard')
```

**Benefits:**
- HTMX provides user interaction without DOM conflicts
- WebSocket notifications handle all visual updates
- Prevents race conditions between different update mechanisms
- Eliminates console errors and improves user experience

### Context Building Patterns

**User-Specific Context:**
```python
def _build_game_context(self, user_id, context_data):
    """Build game-specific context for notifications."""
    user = User.objects.get(id=user_id)
    game = context_data['game']
    
    return {
        'user': user,
        'selected_game': game,
        'csrf_token': get_token_for_user(user),  # User-specific token
    }

def _build_dashboard_context(self, user_id, context_data):
    """Build dashboard-specific context for notifications."""
    user = User.objects.get(id=user_id)
    
    # Get user's active games with optimized queries
    user_games_query = Q(black_player=user) | Q(white_player=user)
    active_games = Game.objects.select_related(
        'black_player', 'white_player', 'ruleset'
    ).filter(user_games_query, status=GameStatus.ACTIVE).order_by('-created_at')
    
    return {
        'user': user,
        'active_games': active_games[:3],  # Limit for performance
        'recent_finished_games': Game.objects.filter(
            user_games_query
        ).exclude(status=GameStatus.ACTIVE).order_by('-finished_at')[:2]
    }
```

### Testing Patterns

**Service Layer Testing:**
```python
def test_websocket_service_event_definitions():
    service = WebSocketNotificationService()
    assert 'game_move' in service.EVENT_DEFINITIONS
    assert 'dashboard_update' in service.EVENT_DEFINITIONS
    assert 'friends_update' in service.EVENT_DEFINITIONS

def test_notification_template_rendering():
    service = WebSocketNotificationService()
    context = service._build_game_context(user_id, {'game': test_game})
    
    assert 'user' in context
    assert 'selected_game' in context
    assert context['selected_game'] == test_game

def test_notification_error_handling():
    service = WebSocketNotificationService()
    
    # Test graceful handling of missing templates
    with patch('django.template.loader.render_to_string') as mock_render:
        mock_render.side_effect = TemplateDoesNotExist("missing_template.html")
        
        # Should not raise exception
        service.send_notification('invalid_event', [user.id], {})
```

**Integration Testing:**
```python
def test_challenge_acceptance_notifications():
    """Test that challenge acceptance sends proper notifications to both users."""
    challenge = create_test_challenge(challenger=user1, challenged=user2)
    
    with patch.object(WebSocketNotificationService, 'send_friends_update') as mock_send:
        # Accept challenge
        response = client.post(f'/api/challenges/{challenge.id}/respond/', {'action': 'accept'})
        
        # Verify notifications sent to both users
        assert mock_send.call_count == 2
        assert user1.id in [call[0][0][0] for call in mock_send.call_args_list]
        assert user2.id in [call[0][0][0] for call in mock_send.call_args_list]
```

### Performance Optimization

**Template Caching:**
```python
# Leverage Django's template caching for frequently rendered notifications
from django.template.loader import get_template

class WebSocketNotificationService:
    def __init__(self):
        # Pre-load and cache frequently used templates
        self._template_cache = {
            event_type: get_template(event_def['template'])
            for event_type, event_def in self.EVENT_DEFINITIONS.items()
        }
```

**Efficient Queries:**
```python
def _build_dashboard_context(self, user_id, context_data):
    # Use select_related to avoid N+1 queries
    active_games = Game.objects.select_related(
        'black_player', 'white_player', 'ruleset'
    ).filter(user_games_query, status=GameStatus.ACTIVE)
    
    # Limit results to prevent UI clutter and improve performance
    return {
        'active_games': active_games[:3],
        'recent_finished_games': finished_games[:2]
    }
```

### Development Patterns

**Service Instantiation:**
```python
# In views.py
class GameMoveView(APIView):
    def __init__(self):
        super().__init__()
        self.notification_service = WebSocketNotificationService()
    
    def post(self, request, game_id):
        # Process move
        move = GameService.make_move(game, request.user.id, row, col)
        
        # Send notifications via centralized service
        opponent = game.get_opponent(request.user)
        self.notification_service.send_game_move_update(
            [opponent.id], 
            {'game': game, 'user': opponent}
        )
```

**Error Recovery:**
```python
def send_notification(self, event_type, user_ids, context_data):
    """Send notification with comprehensive error handling."""
    for user_id in user_ids:
        try:
            # Build context and render template
            context = self._build_context(event_def['context_builder'], user_id, context_data)
            html_content = render_to_string(event_def['template'], context)
            
            # Send WebSocket notification
            WebSocketMessageSender.send_to_user_sync(user_id, event_type, html_content)
            logger.info(f"📤 Sent {event_type} to user {user_id}")
            
        except User.DoesNotExist:
            logger.warning(f"User {user_id} not found for {event_type} notification")
        except TemplateDoesNotExist as e:
            logger.error(f"Template not found for {event_type}: {e}")
        except Exception as e:
            logger.error(f"Failed to send {event_type} to user {user_id}: {e}")
```

### Best Practices

**1. Service Design:**
- Use dependency injection for testability
- Keep service methods focused and single-purpose
- Include comprehensive error handling with logging
- Design for extensibility with standardized patterns

**2. Event Definition Structure:**
- Use descriptive event type names
- Include template and context builder references
- Keep EVENT_DEFINITIONS as a class constant for easy discovery
- Document expected context data structure

**3. Context Building:**
- Build user-specific contexts for personalized notifications
- Use optimized queries with select_related/prefetch_related
- Limit data sets to prevent performance issues
- Include proper error handling for missing data

**4. Integration:**
- Use centralized service consistently across all views
- Avoid bypassing the service for direct WebSocket calls
- Test notification flows with comprehensive integration tests
- Monitor notification delivery with proper logging

### Migration Strategy

**From Scattered to Centralized:**
1. **Identify**: Find all locations with WebSocket update code
2. **Categorize**: Group updates by event type and target
3. **Extract**: Create event definitions and context builders
4. **Replace**: Update views to use centralized service
5. **Test**: Verify all notification flows work correctly
6. **Cleanup**: Remove old scattered WebSocket code

**Rollback Strategy:**
- Keep old WebSocket code commented during transition
- Use feature flags to switch between old and new systems
- Monitor logs for notification delivery issues
- Have quick rollback plan if problems arise

---

## Conclusion

This development guide captures the key lessons learned during the development of a production-ready, real-time multiplayer Gomoku game with enhanced web interface panels and centralized notification architecture. The most important insights are:

1. **Trust Framework Patterns**: Don't fight HTMX with complex JavaScript
2. **Test-Driven Development**: Write tests first, implement minimal solutions
3. **Progressive Enhancement**: Ensure basic functionality without JavaScript
4. **Service Layer Architecture**: Keep business logic separate from views, centralize cross-cutting concerns
5. **Performance First**: Optimize database queries and minimize client-side complexity
6. **Panel-Based UI**: Use consistent patterns for dynamic, real-time panel updates
7. **Centralized Services**: Eliminate code duplication with well-designed service layers
8. **Client-Side CSRF Handling**: Use JavaScript for seamless authentication in WebSocket scenarios
9. **Race Condition Prevention**: Coordinate HTMX and WebSocket updates to prevent DOM conflicts

The combination of Django + HTMX + centralized WebSocket notification system provides a powerful, modern web development stack that prioritizes simplicity, performance, and maintainability while delivering rich, real-time user experiences with minimal code duplication and maximum reliability.