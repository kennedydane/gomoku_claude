"""
Test suite for User API endpoints.

Tests all user-related endpoints following TDD principles:
- POST /api/v1/users/ - Create user
- GET /api/v1/users/ - List users  
- GET /api/v1/users/{id} - Get user by ID
- GET /api/v1/users/username/{username} - Get user by username
- PUT /api/v1/users/{id} - Update user
- DELETE /api/v1/users/{id} - Delete user (soft delete)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User


class TestCreateUser:
    """Test POST /api/v1/users/ endpoint."""
    
    async def test_create_user_success(self, async_client: AsyncClient):
        """Test successful user creation."""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "display_name": "New User"
        }
        
        response = await async_client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["display_name"] == "New User"
        assert data["games_played"] == 0
        assert data["games_won"] == 0
        assert data["win_rate"] == 0.0
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    async def test_create_user_minimal_data(self, async_client: AsyncClient):
        """Test user creation with only required fields."""
        user_data = {
            "username": "minimaluser"
        }
        
        response = await async_client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "minimaluser"
        assert data["email"] is None
        assert data["display_name"] is None
    
    async def test_create_user_duplicate_username(self, async_client: AsyncClient, sample_user):
        """Test user creation fails with duplicate username."""
        user_data = {
            "username": sample_user.username,
            "email": "different@example.com"
        }
        
        response = await async_client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 400
        assert "Username already exists" in response.json()["detail"]
    
    async def test_create_user_duplicate_email(self, async_client: AsyncClient, sample_user):
        """Test user creation fails with duplicate email."""
        user_data = {
            "username": "verydifferentuser",  # Ensure username is very different
            "email": sample_user.email
        }
        
        response = await async_client.post("/api/v1/users/", json=user_data)
        
        # Could be username or email depending on which constraint triggers first
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "already exists" in detail
    
    async def test_create_user_invalid_username_too_short(self, async_client: AsyncClient):
        """Test user creation fails with username too short."""
        user_data = {
            "username": "ab"  # Only 2 characters
        }
        
        response = await async_client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 422
        assert "String should have at least 3 characters" in str(response.json())
    
    async def test_create_user_invalid_username_too_long(self, async_client: AsyncClient):
        """Test user creation fails with username too long."""
        user_data = {
            "username": "a" * 51  # 51 characters
        }
        
        response = await async_client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 422
        assert "String should have at most 50 characters" in str(response.json())
    
    async def test_create_user_invalid_email(self, async_client: AsyncClient):
        """Test user creation fails with invalid email."""
        user_data = {
            "username": "testuser",
            "email": "invalid-email"
        }
        
        response = await async_client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 422
        assert "value is not a valid email address" in str(response.json())
    
    async def test_create_user_username_normalization(self, async_client: AsyncClient):
        """Test username is normalized to lowercase."""
        user_data = {
            "username": "CamelCaseUser",
            "email": "camel@example.com"
        }
        
        response = await async_client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "camelcaseuser"


class TestListUsers:
    """Test GET /api/v1/users/ endpoint."""
    
    async def test_list_users_empty(self, async_client: AsyncClient):
        """Test listing users when database is empty."""
        response = await async_client.get("/api/v1/users/")
        
        assert response.status_code == 200
        assert response.json() == []
    
    async def test_list_users_with_data(self, async_client: AsyncClient, sample_user, sample_user2):
        """Test listing users with existing data."""
        response = await async_client.get("/api/v1/users/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Should be ordered by created_at desc (newest first)
        usernames = [user["username"] for user in data]
        assert usernames == ["testuser2", "testuser"]  # sample_user2 created after sample_user
    
    async def test_list_users_pagination(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test user list pagination."""
        # Create multiple users
        for i in range(5):
            user = User(username=f"user{i}", email=f"user{i}@example.com")
            db_session.add(user)
        await db_session.commit()
        
        # Test limit
        response = await async_client.get("/api/v1/users/?limit=3")
        assert response.status_code == 200
        assert len(response.json()) == 3
        
        # Test skip
        response = await async_client.get("/api/v1/users/?skip=2&limit=2")
        assert response.status_code == 200
        assert len(response.json()) == 2
    
    async def test_list_users_active_filter(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test filtering active vs inactive users."""
        # Create active and inactive users
        active_user = User(username="activeuser", is_active=True)
        inactive_user = User(username="inactiveuser", is_active=False)
        db_session.add_all([active_user, inactive_user])
        await db_session.commit()
        
        # Test active_only=True (default)
        response = await async_client.get("/api/v1/users/")
        assert response.status_code == 200
        usernames = [user["username"] for user in response.json()]
        assert "activeuser" in usernames
        assert "inactiveuser" not in usernames
        
        # Test active_only=False
        response = await async_client.get("/api/v1/users/?active_only=false")
        assert response.status_code == 200
        usernames = [user["username"] for user in response.json()]
        assert "activeuser" in usernames
        assert "inactiveuser" in usernames


class TestGetUser:
    """Test GET /api/v1/users/{user_id} endpoint."""
    
    async def test_get_user_success(self, async_client: AsyncClient, sample_user):
        """Test successful user retrieval."""
        response = await async_client.get(f"/api/v1/users/{sample_user.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_user.id
        assert data["username"] == sample_user.username
        assert data["email"] == sample_user.email
    
    async def test_get_user_not_found(self, async_client: AsyncClient):
        """Test user retrieval with non-existent ID."""
        response = await async_client.get("/api/v1/users/99999")
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    async def test_get_user_invalid_id(self, async_client: AsyncClient):
        """Test user retrieval with invalid ID format."""
        response = await async_client.get("/api/v1/users/invalid")
        
        assert response.status_code == 422


class TestGetUserByUsername:
    """Test GET /api/v1/users/username/{username} endpoint."""
    
    async def test_get_user_by_username_success(self, async_client: AsyncClient, sample_user):
        """Test successful user retrieval by username."""
        response = await async_client.get(f"/api/v1/users/username/{sample_user.username}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_user.id
        assert data["username"] == sample_user.username
    
    async def test_get_user_by_username_case_insensitive(self, async_client: AsyncClient, sample_user):
        """Test user retrieval by username is case insensitive."""
        response = await async_client.get(f"/api/v1/users/username/{sample_user.username.upper()}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == sample_user.username.lower()
    
    async def test_get_user_by_username_not_found(self, async_client: AsyncClient):
        """Test user retrieval with non-existent username."""
        response = await async_client.get("/api/v1/users/username/nonexistent")
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


class TestUpdateUser:
    """Test PUT /api/v1/users/{user_id} endpoint."""
    
    async def test_update_user_success(self, async_client: AsyncClient, sample_user):
        """Test successful user update."""
        update_data = {
            "email": "updated@example.com",
            "display_name": "Updated Name"
        }
        
        response = await async_client.put(f"/api/v1/users/{sample_user.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "updated@example.com"
        assert data["display_name"] == "Updated Name"
        assert data["username"] == sample_user.username  # Unchanged
    
    async def test_update_user_partial(self, async_client: AsyncClient, sample_user):
        """Test partial user update."""
        update_data = {
            "display_name": "Only Display Name Changed"
        }
        
        response = await async_client.put(f"/api/v1/users/{sample_user.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Only Display Name Changed"
        assert data["email"] == sample_user.email  # Unchanged
    
    async def test_update_user_deactivate(self, async_client: AsyncClient, sample_user):
        """Test deactivating user."""
        update_data = {
            "is_active": False
        }
        
        response = await async_client.put(f"/api/v1/users/{sample_user.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
    
    async def test_update_user_not_found(self, async_client: AsyncClient):
        """Test updating non-existent user."""
        update_data = {
            "display_name": "New Name"
        }
        
        response = await async_client.put("/api/v1/users/99999", json=update_data)
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    async def test_update_user_duplicate_email(self, async_client: AsyncClient, sample_user, sample_user2):
        """Test updating user fails with duplicate email."""
        update_data = {
            "email": sample_user2.email
        }
        
        response = await async_client.put(f"/api/v1/users/{sample_user.id}", json=update_data)
        
        assert response.status_code == 400
        assert "Email already exists" in response.json()["detail"]


class TestDeleteUser:
    """Test DELETE /api/v1/users/{user_id} endpoint."""
    
    async def test_delete_user_success(self, async_client: AsyncClient, sample_user, db_session):
        """Test successful user soft deletion."""
        response = await async_client.delete(f"/api/v1/users/{sample_user.id}")
        
        assert response.status_code == 204
        assert response.content == b""
        
        # Verify user is soft deleted (is_active=False)
        await db_session.refresh(sample_user)
        assert sample_user.is_active is False
    
    async def test_delete_user_not_found(self, async_client: AsyncClient):
        """Test deleting non-existent user."""
        response = await async_client.delete("/api/v1/users/99999")
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    async def test_delete_user_idempotent(self, async_client: AsyncClient, sample_user):
        """Test deleting already deleted user."""
        # First deletion
        response = await async_client.delete(f"/api/v1/users/{sample_user.id}")
        assert response.status_code == 204
        
        # Second deletion should still succeed
        response = await async_client.delete(f"/api/v1/users/{sample_user.id}")
        assert response.status_code == 204


class TestUserAPIIntegration:
    """Integration tests for user API workflows."""
    
    async def test_user_lifecycle(self, async_client: AsyncClient):
        """Test complete user lifecycle: create -> read -> update -> delete."""
        # 1. Create user
        user_data = {
            "username": "lifecycleuser",
            "email": "lifecycle@example.com",
            "display_name": "Lifecycle User"
        }
        
        create_response = await async_client.post("/api/v1/users/", json=user_data)
        assert create_response.status_code == 201
        user = create_response.json()
        user_id = user["id"]
        
        # 2. Read user
        get_response = await async_client.get(f"/api/v1/users/{user_id}")
        assert get_response.status_code == 200
        assert get_response.json()["username"] == "lifecycleuser"
        
        # 3. Update user
        update_data = {"display_name": "Updated Lifecycle User"}
        update_response = await async_client.put(f"/api/v1/users/{user_id}", json=update_data)
        assert update_response.status_code == 200
        assert update_response.json()["display_name"] == "Updated Lifecycle User"
        
        # 4. Delete user
        delete_response = await async_client.delete(f"/api/v1/users/{user_id}")
        assert delete_response.status_code == 204
        
        # 5. Verify user is soft deleted (still exists but inactive)
        get_response = await async_client.get(f"/api/v1/users/{user_id}")
        assert get_response.status_code == 200
        assert get_response.json()["is_active"] is False