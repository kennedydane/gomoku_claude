# Test Structure Documentation

## 📁 Test Organization

The test suite is organized by functionality and scope, with clear separation between different types of tests.

### Directory Structure

```
backend/
├── tests/                          # Core API and Integration Tests
│   ├── conftest.py                 # Shared test configurations and fixtures
│   ├── factories.py                # Test data factories (Factory Boy)
│   ├── test_auth_endpoints.py      # Authentication API tests
│   ├── test_challenge_system.py    # Challenge API tests
│   ├── test_game_crud.py          # Game CRUD API tests
│   ├── test_move_validation.py     # Move validation and game logic tests
│   ├── test_rulesets.py           # Ruleset API tests
│   ├── test_user_management.py     # User management API tests
│   ├── test_websocket_integration.py # WebSocket integration tests
│   └── test_websocket_performance.py # WebSocket performance tests
│
├── web/                            # Web Interface Tests (TDD)
│   ├── test_challenge_system.py   # Web challenge interface tests
│   ├── test_friend_system.py      # Friend system web tests
│   ├── test_game_board.py         # Interactive game board tests
│   ├── test_pending_challenges.py  # Challenge notifications tests
│   ├── test_phase11_panels.py     # Dashboard panels tests
│   ├── test_phase12_single_view.py # Single view interface tests
│   ├── test_views.py              # General web view tests
│   └── test_websocket_consumer.py  # WebSocket consumer tests
│
├── users/                          # User App Tests
│   ├── test_enhanced_auth.py       # Enhanced authentication tests
│   └── test_models.py             # User model tests
│
├── games/                          # Game App Tests
│   ├── test_models.py             # Game model tests
│   └── test_services.py           # Game service layer tests
│
└── core/                           # Core App Tests
    └── tests.py                   # Core functionality tests
```

## 🧪 Test Categories

### 1. API Tests (`tests/`)
**Purpose**: Test REST API endpoints, business logic, and data validation
- **Authentication**: Token-based auth, user registration, login/logout
- **Game CRUD**: Game creation, retrieval, updates, validation
- **Move Validation**: Game mechanics, win detection, turn management
- **Challenge System**: Player-to-player challenges and responses
- **User Management**: User profiles, statistics, management
- **Rulesets**: Game rule configurations and validation

### 2. Web Interface Tests (`web/`)
**Purpose**: Test Django views, templates, and HTMX interactions
- **TDD Methodology**: Red-Green-Refactor development cycle
- **Template Rendering**: HTML generation and context validation
- **HTMX Integration**: Dynamic updates and partial rendering
- **Form Handling**: User input validation and error handling
- **Real-time Features**: WebSocket integration and SSE functionality

### 3. WebSocket Tests
**Purpose**: Test real-time communication infrastructure and centralized notifications
- **Consumer Tests** (`web/test_websocket_consumer.py`): WebSocket message handling
- **Integration Tests** (`tests/test_websocket_integration.py`): End-to-end WebSocket functionality
- **Performance Tests** (`tests/test_websocket_performance.py`): Connection optimization validation
- **Centralized Service Tests**: WebSocketNotificationService testing for consistent notification patterns

### 4. App-Specific Tests
**Purpose**: Test individual Django app components
- **Model Tests**: Database models, relationships, validation
- **Service Tests**: Business logic, domain services
- **Authentication Tests**: Enhanced token system, security

## 🎯 Test Execution

### Run All Tests
```bash
uv run python manage.py test
```

### Run by Category
```bash
# API and Integration Tests
uv run python manage.py test tests

# Web Interface Tests  
uv run python manage.py test web

# WebSocket Tests
uv run python -m pytest web/test_websocket_consumer.py -v
uv run python -m pytest tests/test_websocket_integration.py -v
uv run python -m pytest tests/test_websocket_performance.py -v

# App-Specific Tests
uv run python manage.py test users
uv run python manage.py test games
uv run python manage.py test core
```

### Run Specific Test Files
```bash
# API Tests
uv run python -m pytest tests/test_challenge_system.py -v
uv run python -m pytest tests/test_move_validation.py -v

# Web Tests
uv run python -m pytest web/test_friend_system.py -v
uv run python -m pytest web/test_game_board.py -v
```

## 📊 Test Coverage

### Current Test Metrics
- **Total Test Files**: 18 files
- **API Tests**: 8 files (Core REST API functionality)
- **Web Tests**: 8 files (Django views, HTMX, and centralized services)
- **WebSocket Tests**: 3 files (Real-time communication and centralized notifications)
- **App Tests**: 5 files (Individual app components)

### Test Distribution
```
API Tests (tests/):           ~170 tests
Web Interface Tests (web/):   ~140 tests (includes centralized service tests)
WebSocket Tests:              ~40 tests (includes centralized notification tests)
App-Specific Tests:           ~50 tests
────────────────────────────────────────
Total:                        ~400 tests
```

## 🛠️ Test Infrastructure

### Shared Test Utilities
- **`tests/conftest.py`**: Pytest fixtures and configurations
- **`tests/factories.py`**: Factory Boy test data generation
- **Django Test Framework**: Database transactions and test client
- **Factory Boy**: Realistic test data generation
- **Pytest**: Advanced test discovery and execution

### Test Data Management
- **Fixtures**: Reusable test data setups
- **Factories**: Dynamic test object creation
- **Database Isolation**: Each test gets clean database state
- **Mock Objects**: External service simulation

### Coverage Reporting
```bash
# Generate coverage report
uv run coverage run -m pytest
uv run coverage html

# View coverage (excluded from git)
# Generated in htmlcov/ directory
```

## 🔄 TDD Methodology

### Red-Green-Refactor Cycle
1. **RED**: Write failing test first
2. **GREEN**: Write minimal code to pass test
3. **REFACTOR**: Improve code while keeping tests green

### TDD Examples in Codebase
- **Friend System** (`web/test_friend_system.py`): Complete TDD implementation
- **Challenge System** (`web/test_challenge_system.py`): Web interface TDD
- **WebSocket Migration** (`web/test_websocket_consumer.py`): Infrastructure TDD

## 🏗️ Centralized Service Testing

### WebSocket Notification Service Tests
**Purpose**: Test centralized notification system architecture

**Test Categories:**
- **Service Layer Tests**: WebSocketNotificationService class functionality
- **Event Definition Tests**: Validation of EVENT_DEFINITIONS structure
- **Template Rendering Tests**: Context building and template rendering with user-specific data
- **Error Handling Tests**: Comprehensive error recovery and fallback mechanisms
- **Integration Tests**: End-to-end notification delivery across multiple users

**Key Test Patterns:**
```python
# Service instantiation and event handling
def test_websocket_service_event_definitions():
    service = WebSocketNotificationService()
    assert 'game_move' in service.EVENT_DEFINITIONS
    assert 'dashboard_update' in service.EVENT_DEFINITIONS

# Template rendering with proper context
def test_notification_template_rendering():
    service = WebSocketNotificationService()
    context = service._build_game_context(user_id, {'game': test_game})
    assert 'user' in context
    assert 'selected_game' in context

# Error handling and fallback mechanisms  
def test_notification_error_handling():
    service = WebSocketNotificationService()
    # Test graceful handling of template errors, WebSocket failures
```

**CSRF Token Testing:**
- Client-side CSRF injection validation
- Session token vs WebSocket token testing
- Integration with Django CSRF middleware

**Race Condition Testing:**
- HTMX hx-swap="none" pattern validation
- WebSocket vs HTMX update coordination
- DOM conflict prevention testing

## 🧹 Test Maintenance

### Recently Cleaned Up
- ✅ Removed obsolete SSE test files (post-WebSocket migration)
- ✅ Organized WebSocket tests in proper directories  
- ✅ Removed generated HTML coverage reports from git
- ✅ Updated .gitignore for test artifacts
- ✅ Fixed import paths after file reorganization
- ✅ Added centralized service testing patterns and documentation

### Best Practices
- **One Test Per Behavior**: Each test validates one specific behavior
- **Descriptive Names**: Test names clearly describe what they validate
- **Fast Execution**: Tests run quickly for rapid feedback
- **Isolated Tests**: No dependencies between test cases
- **Comprehensive Coverage**: Both happy path and error scenarios

## 🚀 Adding New Tests

### For API Functionality
```python
# Add to tests/test_new_feature.py
class NewFeatureAPITests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)
    
    def test_new_feature_success(self):
        # Test implementation
        pass
```

### For Web Interface  
```python
# Add to web/test_new_feature.py
class NewFeatureWebTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
    
    def test_new_feature_renders(self):
        # Test implementation
        pass
```

### For WebSocket Functionality
```python
# Add to web/test_websocket_consumer.py
@pytest.mark.asyncio
class TestNewWebSocketFeature:
    async def test_new_websocket_message(self):
        # Test implementation
        pass
```

## 📈 Continuous Improvement

### Current Status: ✅ Well-Organized with Centralized Architecture
- Clear directory structure by functionality with centralized service testing
- Comprehensive test coverage across all components including WebSocket notification system
- Modern testing practices with TDD methodology and centralized service patterns
- Clean separation between API, web, infrastructure, and centralized service tests
- Proper test artifact management and centralized service validation
- Complete testing of CSRF handling, race condition fixes, and code deduplication

The test suite provides robust validation of all system components including the centralized notification architecture while maintaining fast execution and easy maintenance.