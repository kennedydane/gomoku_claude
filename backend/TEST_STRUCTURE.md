# Test Structure Documentation

## 📁 Test Organization

The test suite is organized by functionality and scope, with clear separation between different types of tests.

### Directory Structure

```
backend/
└── tests/                          # Centralized Test Directory (pytest-based)
    ├── conftest.py                 # Shared test configurations and fixtures
    ├── factories.py                # Test data factories (Factory Boy with Faker)
    │
    ├── test_challenge_system.py    # Challenge system integration tests
    ├── test_dashboard_panels.py    # Dashboard panel functionality tests
    ├── test_database_configuration.py # Database configuration tests
    ├── test_embedded_game_dashboard.py # Embedded game dashboard tests
    ├── test_friend_system.py       # Friend system integration tests
    ├── test_game_board.py          # Interactive game board tests
    ├── test_game_services.py       # Game service layer tests
    ├── test_games_models.py        # Game model tests
    ├── test_pending_challenges.py   # Challenge notification tests
    ├── test_registration_removal.py # Registration functionality removal tests
    ├── test_rulesets.py            # Ruleset validation tests
    ├── test_services.py            # Core service layer tests
    ├── test_standardized_rulesets.py # Standardized ruleset tests
    ├── test_subclassed_rulesets.py  # Multi-game architecture tests
    ├── test_users_models.py        # User model tests
    ├── test_web_views.py           # Web interface view tests
    ├── test_websocket_consumer.py  # WebSocket consumer tests
    ├── test_websocket_integration.py # WebSocket integration tests
    └── test_websocket_performance.py # WebSocket performance tests
```

## 🧪 Test Categories

### 1. Core System Tests
**Purpose**: Test fundamental game mechanics, models, and business logic
- **Game Models**: Game creation, board initialization, move validation (`test_games_models.py`)
- **User Models**: User statistics, authentication, profile management (`test_users_models.py`) 
- **Game Services**: Win detection, move processing, game state management (`test_game_services.py`)
- **Service Layer**: Core business logic and domain services (`test_services.py`)
- **Rulesets**: Multi-game architecture, Gomoku/Go rule validation (`test_rulesets.py`, `test_standardized_rulesets.py`, `test_subclassed_rulesets.py`)

### 2. Web Interface Tests  
**Purpose**: Test Django views, templates, and user interactions
- **Web Views**: Dashboard, authentication, game views (`test_web_views.py`)
- **Game Board**: Interactive board rendering and move handling (`test_game_board.py`)
- **Dashboard Panels**: Game lists, user statistics, navigation (`test_dashboard_panels.py`)
- **Embedded Game Dashboard**: Single-view game interface (`test_embedded_game_dashboard.py`)

### 3. Social Features Tests
**Purpose**: Test player-to-player interactions and challenges
- **Friend System**: Friend requests, management, social features (`test_friend_system.py`)
- **Challenge System**: Game challenges, acceptance, notifications (`test_challenge_system.py`)
- **Pending Challenges**: Challenge notifications and real-time updates (`test_pending_challenges.py`)

### 4. Real-Time Communication Tests
**Purpose**: Test WebSocket infrastructure and live game updates
- **WebSocket Consumer**: Message routing, authentication, connection handling (`test_websocket_consumer.py`)
- **WebSocket Integration**: End-to-end real-time functionality (`test_websocket_integration.py`)
- **WebSocket Performance**: Connection optimization and scalability (`test_websocket_performance.py`)

### 5. Configuration and System Tests
**Purpose**: Test system configuration and architectural decisions
- **Database Configuration**: SQLite/PostgreSQL compatibility (`test_database_configuration.py`)
- **Registration Removal**: Verification of removed registration functionality (`test_registration_removal.py`)

## 🎯 Test Execution

### Run All Tests
```bash
uv run python manage.py test
```

### Run by Category
```bash
# All pytest-based tests (current structure)
uv run python -m pytest tests/ -v

# Core system tests
uv run python -m pytest tests/test_games_models.py tests/test_users_models.py tests/test_game_services.py -v

# Web interface tests
uv run python -m pytest tests/test_web_views.py tests/test_game_board.py tests/test_dashboard_panels.py -v

# Social features tests  
uv run python -m pytest tests/test_friend_system.py tests/test_challenge_system.py -v

# Real-time communication tests
uv run python -m pytest tests/test_websocket_consumer.py tests/test_websocket_integration.py -v

# Configuration and system tests
uv run python -m pytest tests/test_database_configuration.py tests/test_registration_removal.py -v
```

### Run Specific Test Files
```bash
# Core functionality
uv run python -m pytest tests/test_games_models.py -v
uv run python -m pytest tests/test_game_services.py -v

# Multi-game architecture
uv run python -m pytest tests/test_rulesets.py tests/test_standardized_rulesets.py -v

# WebSocket functionality
uv run python -m pytest tests/test_websocket_consumer.py -v
uv run python -m pytest tests/test_websocket_integration.py -v
```

## 📊 Test Coverage

### Current Test Metrics (Updated)
- **Total Test Files**: 19 files (all in centralized `tests/` directory)
- **Core System Tests**: 6 files (Models, services, business logic)
- **Web Interface Tests**: 4 files (Views, dashboard, game board)
- **Social Features Tests**: 3 files (Friends, challenges, notifications)
- **WebSocket Tests**: 3 files (Consumer, integration, performance)
- **System Configuration Tests**: 3 files (Database, registration removal, multi-game architecture)

### Test Distribution (Estimated)
```
Core System Tests:           ~120 tests (Models, services, game logic)
Web Interface Tests:         ~80 tests (Views, templates, interactions)
Social Features Tests:       ~60 tests (Friends, challenges)
WebSocket Tests:             ~40 tests (Real-time communication)
System Configuration Tests:  ~30 tests (Architecture, configuration)
────────────────────────────────────────
Total:                       ~330 tests
```

## 🛠️ Test Infrastructure

### Shared Test Utilities
- **`tests/conftest.py`**: Pytest fixtures and configurations
- **`tests/factories.py`**: Factory Boy test data generation with Faker integration
- **Pytest Framework**: Advanced test discovery, fixtures, and parametrization
- **Factory Boy + Faker**: Realistic test data generation with dynamic values
- **Django Test Database**: Isolated test database for each test run

### Test Data Management
- **Factories**: Dynamic test object creation using Factory Boy and Faker
- **Fixtures**: Reusable test data setups via pytest fixtures
- **Database Isolation**: Each test gets clean database state via Django test framework
- **Mock Objects**: External service simulation where needed

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
@pytest.mark.django_db
class TestNewFeatureAPI:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.user = UserFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_new_feature_success(self):
        # Test implementation using pytest assertions
        assert response.status_code == 200
        assert 'expected_data' in response.data
```

### For Web Interface  
```python
# Add to tests/test_new_feature.py
@pytest.mark.django_db
class TestNewFeatureWeb:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.client = Client()
        self.user = UserFactory()
    
    def test_new_feature_renders(self):
        # Test implementation using pytest assertions
        response = self.client.get('/new-feature/')
        assert response.status_code == 200
        assert b'expected_content' in response.content
```

### For WebSocket Functionality
```python
# Add to tests/test_websocket_consumer.py
@pytest.mark.asyncio
@pytest.mark.django_db
class TestNewWebSocketFeature:
    async def test_new_websocket_message(self):
        # Test implementation using pytest assertions
        consumer = WebSocketConsumer()
        # Test implementation
        assert consumer is not None
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