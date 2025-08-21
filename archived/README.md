# Archived Components

This directory contains components that were part of the original multi-client architecture but are no longer actively maintained.

## Contents

### `frontend/` - Desktop GUI Client (Archived)
- **Technology**: Python Dear PyGUI desktop application
- **Status**: Fully functional but no longer maintained
- **Reason for Archival**: Project focus shifted to web-only interface
- **Last Updated**: During authentication system development phase

**Features (Archived)**:
- Interactive Gomoku game board
- Complete authentication system with profile management  
- Multi-game management and switching
- Real-time updates via Server-Sent Events
- Configuration management (JSON + environment variables)
- Comprehensive test suite (52+ tests)

**Documentation**: See `archived/frontend/README.md` for full details

## Why These Were Archived

The Gomoku Claude project originally supported multiple client interfaces:
- Web interface (Bootstrap 5 + htmx)
- Desktop GUI (Dear PyGUI) 
- REST API for third-party clients

Over the course of development, the project evolved to focus primarily on the web interface, which provides:
- Better cross-platform compatibility
- Easier deployment and maintenance
- Modern responsive design
- Real-time multiplayer functionality

The archived components remain fully functional and well-tested, but are no longer part of the active development roadmap.

## Restoration

If you need to restore any archived component:

1. **Desktop Frontend**: Copy `archived/frontend/` back to root directory
2. **Update Dependencies**: Re-add frontend workspace to root `pyproject.toml`
3. **Documentation**: Update main README.md to include frontend usage instructions

All archived components include comprehensive documentation and test suites for easy restoration if needed.