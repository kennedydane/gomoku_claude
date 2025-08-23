# Gomoku Claude - Master Documentation Index

This file serves as the master index for all documentation in the Gomoku Claude project. All markdown files are organized by category and purpose.

## 📚 Documentation Structure

### Primary Documentation
- **[README.md](README.md)** - Main project overview, installation, usage, and features
- **[DEV_GUIDE.md](DEV_GUIDE.md)** - Developer guide for contributing and development setup
- **[CLIENT_OPTIMIZATION.md](CLIENT_OPTIMIZATION.md)** - Client-side performance optimization guide (45.1% size reduction)
- **[TODO.md](TODO.md)** - Project-wide todo items and future enhancements
- **[DOCKER_README.md](DOCKER_README.md)** - Docker-specific setup and deployment guide

### Backend Documentation
- **[backend/README.md](backend/README.md)** - Backend-specific documentation and API details
- **[backend/TODO.md](backend/TODO.md)** - Backend-specific todo items and technical debt
- **[backend/TEST_STRUCTURE.md](backend/TEST_STRUCTURE.md)** - Testing architecture and structure documentation
- **[backend/WEBSOCKET_MIGRATION.md](backend/WEBSOCKET_MIGRATION.md)** - WebSocket migration and real-time features documentation
- **[backend/fixtures/README.md](backend/fixtures/README.md)** - Database fixtures and test data documentation
- **[backend/web/TODO.md](backend/web/TODO.md)** - Web interface specific todo items

### Archived Components Documentation
- **[archived/README.md](archived/README.md)** - Overview of archived components and why they were archived
- **[archived/api/README.md](archived/api/README.md)** - Archived REST API documentation and restoration guide
- **[archived/frontend/README.md](archived/frontend/README.md)** - Archived desktop GUI frontend documentation
- **[archived/frontend/MANUAL_TEST_GUIDE.md](archived/frontend/MANUAL_TEST_GUIDE.md)** - Manual testing procedures for archived GUI
- **[archived/frontend/RUN_GAME.md](archived/frontend/RUN_GAME.md)** - How to run the archived desktop game client
- **[archived/frontend/TODO.md](archived/frontend/TODO.md)** - Archived frontend todo items

### Development Tools Documentation
- **[scripts/build.js](scripts/build.js)** - Production build script for asset optimization
- **[scripts/watch.js](scripts/watch.js)** - Development file watcher for automatic rebuilds
- **[build.config.js](build.config.js)** - Build system configuration and optimization settings
- **[package.json](package.json)** - Node.js dependencies and build automation scripts
- **[.claude/agents/docker-compose-expert.md](.claude/agents/docker-compose-expert.md)** - Claude Code agent for Docker Compose assistance
- **[.claude/agents/python-quality-guardian.md](.claude/agents/python-quality-guardian.md)** - Claude Code agent for Python code quality

## 📋 Documentation Categories

### 🚀 Getting Started
For new users and developers:
1. [README.md](README.md) - Start here for project overview
2. [DEV_GUIDE.md](DEV_GUIDE.md) - Development environment setup
3. [DOCKER_README.md](DOCKER_README.md) - Docker deployment guide

### 🏗️ Architecture & Technical Details
For understanding the system architecture:
- [backend/README.md](backend/README.md) - Backend architecture and API endpoints
- [backend/TEST_STRUCTURE.md](backend/TEST_STRUCTURE.md) - Testing architecture
- [backend/WEBSOCKET_MIGRATION.md](backend/WEBSOCKET_MIGRATION.md) - Real-time features implementation

### 🧪 Testing & Quality
For testing and quality assurance:
- [backend/TEST_STRUCTURE.md](backend/TEST_STRUCTURE.md) - Comprehensive testing documentation
- [archived/frontend/MANUAL_TEST_GUIDE.md](archived/frontend/MANUAL_TEST_GUIDE.md) - Manual testing procedures
- [backend/fixtures/README.md](backend/fixtures/README.md) - Test data and fixtures

### 📦 Archived Components
For understanding legacy components:
- [archived/README.md](archived/README.md) - Why components were archived
- [archived/api/README.md](archived/api/README.md) - REST API that was removed
- [archived/frontend/README.md](archived/frontend/README.md) - Desktop GUI that was archived

### 🔧 Development Tools
For development workflow enhancement:
- [.claude/agents/docker-compose-expert.md](.claude/agents/docker-compose-expert.md) - Docker assistance
- [.claude/agents/python-quality-guardian.md](.claude/agents/python-quality-guardian.md) - Code quality tools

### 📝 Planning & Progress
For tracking development progress:
- [TODO.md](TODO.md) - Project-wide todo items
- [backend/TODO.md](backend/TODO.md) - Backend specific tasks
- [backend/web/TODO.md](backend/web/TODO.md) - Web interface tasks

## 🎯 Project Evolution

The Gomoku Claude project has evolved through several major phases:

### Phase 1-10: Core Development
- Initial FastAPI → Django migration
- User management and authentication systems
- Game logic and rule implementations
- Web interface development with Bootstrap 5 + htmx

### Phase 11-12: Interface Enhancement
- Enhanced 3-column dashboard layout
- Single-view dashboard with embedded game board
- Real-time panel updates via Server-Sent Events

### Phase 13-14: Real-time & Optimization
- Challenge system simplification
- Centralized WebSocket notification system
- Race condition fixes and CSRF handling

### Phase 15: Multi-Game Architecture
- RuleSet subclassing (GomokuRuleSet, GoRuleSet)
- Service layer abstraction for multiple game types
- Standardized board sizes and validation
- Project cleanup and API removal

### Phase 16: Performance Optimization & Real-time Fixes (Current)
- Fixed turn switching and capture rendering bugs
- Implemented 45.1% asset size reduction through build optimization
- Added client-side build system with Node.js toolchain
- Created targeted WebSocket updates with capture detection
- Established Progressive Web App (PWA) foundation

## 🏛️ Current Architecture

**Web-Only Architecture** (as of Phase 16):
- **Backend**: Django web application with optimized WebSocket system
- **Frontend**: Bootstrap 5 responsive web interface with PWA capabilities
- **Build System**: Node.js-based asset optimization pipeline (45.1% size reduction)
- **Database**: PostgreSQL with Django ORM
- **Real-time**: Centralized WebSocket notifications with targeted updates
- **Authentication**: Django sessions (no API tokens)
- **Deployment**: Docker Compose for development and production

**Archived Components**:
- REST API (Django REST Framework) - archived as unused
- Desktop GUI (Dear PyGUI) - archived as project focused on web-only

## 📊 Documentation Statistics

- **Total .md files**: 19
- **Primary documentation**: 5 files (added CLIENT_OPTIMIZATION.md)
- **Backend documentation**: 6 files  
- **Archived documentation**: 6 files
- **Development tools**: 6 files (added build system documentation)

## 🔄 Maintenance

This documentation index should be updated whenever:
- New .md files are added to the project
- Existing documentation files are moved or renamed
- Major architectural changes affect documentation structure
- New phases or major features are implemented

Last updated: Phase 16 (Performance Optimization & Real-time Gameplay Fixes)