"""
pytest configuration and fixtures for backend testing.
"""
import pytest


# Let Django handle test database setup automatically
@pytest.fixture(scope="session")
def django_db_setup():
    """Configure test database - let Django handle this automatically."""
    pass