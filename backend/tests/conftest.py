"""
Test configuration and fixtures for the backend tests.

This module provides pytest fixtures for database testing, including
async database sessions and test database setup/teardown.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.db.database import Base


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the test session.
    
    This fixture ensures that async tests run properly by providing
    a consistent event loop throughout the test session.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Create a test database engine using SQLite in memory.
    
    This provides a fast, isolated database for testing that doesn't
    require PostgreSQL to be running during tests.
    """
    # Use SQLite in-memory database for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,  # Set to True for SQL debugging
    )
    
    # Enable foreign key constraints for SQLite
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for testing.
    
    This fixture provides a clean database session for each test,
    with automatic cleanup after the test completes to ensure
    test isolation.
    
    Args:
        test_engine: The test database engine fixture
        
    Yields:
        AsyncSession: An async database session for testing
    """
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            # Clean up all data after each test for proper isolation
            try:
                # Delete all data from all tables
                for table in reversed(Base.metadata.sorted_tables):
                    await session.execute(table.delete())
                await session.commit()
            except Exception:
                # If cleanup fails, just close the session
                pass
            finally:
                await session.close()


@pytest_asyncio.fixture
async def db_session_commit(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session that commits transactions.
    
    This fixture is useful for tests that need to verify database
    constraints, triggers, or other database-level behaviors that
    require actual commits.
    
    Args:
        test_engine: The test database engine fixture
        
    Yields:
        AsyncSession: An async database session that commits changes
    """
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session
        # Clean up after the test by removing all data
        async with session.begin():
            # Get all table names and delete data
            for table in reversed(Base.metadata.sorted_tables):
                await session.execute(table.delete())
            await session.commit()


# Pytest configuration
pytest_plugins = ['pytest_asyncio']


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


@pytest.fixture(autouse=True)
def setup_test_logging(caplog):
    """
    Set up logging for tests.
    
    This fixture automatically configures logging for all tests,
    making it easier to debug test failures.
    """
    caplog.set_level("INFO")