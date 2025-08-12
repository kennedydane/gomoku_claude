"""
API test fixtures and configuration.

This module provides test fixtures for API testing with httpx.AsyncClient
and FastAPI's test capabilities.
"""

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from backend.main import create_app
from backend.db.database import get_db


@pytest_asyncio.fixture
async def test_app():
    """Create a test FastAPI application."""
    app = create_app()
    return app


@pytest_asyncio.fixture
async def test_app_with_db(test_app, db_session: AsyncSession):
    """Create a test FastAPI application with database dependency override."""
    
    # Override the get_db dependency to use our test database
    async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
    
    test_app.dependency_overrides[get_db] = get_test_db
    
    yield test_app
    
    # Clean up dependency overrides
    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(test_app_with_db) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing API endpoints."""
    async with AsyncClient(
        transport=ASGITransport(app=test_app_with_db),
        base_url="http://testserver"
    ) as client:
        yield client


@pytest.fixture
def sync_client(test_app_with_db) -> TestClient:
    """Create a synchronous HTTP client for simple API tests."""
    return TestClient(test_app_with_db)