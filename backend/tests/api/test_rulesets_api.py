"""
Test suite for RuleSet API endpoints.

Tests all ruleset-related endpoints following TDD principles:
- POST /api/v1/rulesets/ - Create custom ruleset
- GET /api/v1/rulesets/ - List rulesets
- GET /api/v1/rulesets/standard - Get standard ruleset (creates if not exists)
- GET /api/v1/rulesets/presets - Get all preset rulesets
- GET /api/v1/rulesets/{id} - Get ruleset by ID
- GET /api/v1/rulesets/name/{name} - Get ruleset by name
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import RuleSet


class TestCreateRuleSet:
    """Test POST /api/v1/rulesets/ endpoint."""
    
    async def test_create_ruleset_success(self, async_client: AsyncClient):
        """Test successful custom ruleset creation."""
        ruleset_data = {
            "name": "Custom Rules",
            "board_size": 19,
            "allow_overlines": True,
            "forbidden_moves": {"custom_rule": "value"},
            "description": "My custom Gomoku rules"
        }
        
        response = await async_client.post("/api/v1/rulesets/", json=ruleset_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Custom Rules"
        assert data["board_size"] == 19
        assert data["allow_overlines"] is True
        assert data["forbidden_moves"] == {"custom_rule": "value"}
        assert data["description"] == "My custom Gomoku rules"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    async def test_create_ruleset_minimal_data(self, async_client: AsyncClient):
        """Test ruleset creation with only required fields."""
        ruleset_data = {
            "name": "Minimal Rules",
            "board_size": 15,
            "allow_overlines": False
        }
        
        response = await async_client.post("/api/v1/rulesets/", json=ruleset_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Rules"
        assert data["board_size"] == 15
        assert data["allow_overlines"] is False
        assert data["forbidden_moves"] == {}
        assert data["description"] is None
    
    async def test_create_ruleset_duplicate_name(self, async_client: AsyncClient, sample_ruleset):
        """Test ruleset creation fails with duplicate name."""
        ruleset_data = {
            "name": sample_ruleset.name,
            "board_size": 19,
            "allow_overlines": True
        }
        
        response = await async_client.post("/api/v1/rulesets/", json=ruleset_data)
        
        assert response.status_code == 400
        assert "Ruleset with this name already exists" in response.json()["detail"]
    
    async def test_create_ruleset_invalid_board_size_small(self, async_client: AsyncClient):
        """Test ruleset creation fails with board size too small."""
        ruleset_data = {
            "name": "Invalid Small",
            "board_size": 4,  # Too small
            "allow_overlines": False
        }
        
        response = await async_client.post("/api/v1/rulesets/", json=ruleset_data)
        
        assert response.status_code == 422
        assert "greater than or equal to 5" in str(response.json())
    
    async def test_create_ruleset_invalid_board_size_large(self, async_client: AsyncClient):
        """Test ruleset creation fails with board size too large."""
        ruleset_data = {
            "name": "Invalid Large",
            "board_size": 25,  # Too large
            "allow_overlines": False
        }
        
        response = await async_client.post("/api/v1/rulesets/", json=ruleset_data)
        
        assert response.status_code == 422
        assert "less than or equal to 19" in str(response.json())
    
    async def test_create_ruleset_empty_name(self, async_client: AsyncClient):
        """Test ruleset creation fails with empty name."""
        ruleset_data = {
            "name": "",
            "board_size": 15,
            "allow_overlines": False
        }
        
        response = await async_client.post("/api/v1/rulesets/", json=ruleset_data)
        
        assert response.status_code == 422
        assert "String should have at least 1 character" in str(response.json())


class TestListRuleSets:
    """Test GET /api/v1/rulesets/ endpoint."""
    
    async def test_list_rulesets_empty(self, async_client: AsyncClient):
        """Test listing rulesets when database is empty."""
        response = await async_client.get("/api/v1/rulesets/")
        
        assert response.status_code == 200
        assert response.json() == []
    
    async def test_list_rulesets_with_data(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test listing rulesets with existing data."""
        # Create multiple rulesets
        ruleset1 = RuleSet(name="Alpha Rules", board_size=15, allow_overlines=False)
        ruleset2 = RuleSet(name="Beta Rules", board_size=19, allow_overlines=True)
        db_session.add_all([ruleset1, ruleset2])
        await db_session.commit()
        
        response = await async_client.get("/api/v1/rulesets/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Should be ordered by name
        names = [ruleset["name"] for ruleset in data]
        assert names == ["Alpha Rules", "Beta Rules"]
    
    async def test_list_rulesets_pagination(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test ruleset list pagination."""
        # Create multiple rulesets
        for i in range(5):
            ruleset = RuleSet(name=f"Rules{i:02d}", board_size=15, allow_overlines=False)
            db_session.add(ruleset)
        await db_session.commit()
        
        # Test limit
        response = await async_client.get("/api/v1/rulesets/?limit=3")
        assert response.status_code == 200
        assert len(response.json()) == 3
        
        # Test skip
        response = await async_client.get("/api/v1/rulesets/?skip=2&limit=2")
        assert response.status_code == 200
        assert len(response.json()) == 2
    
    async def test_list_rulesets_filter_by_board_size(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test filtering rulesets by board size."""
        # Create rulesets with different board sizes
        ruleset15 = RuleSet(name="Rules15", board_size=15, allow_overlines=False)
        ruleset19 = RuleSet(name="Rules19", board_size=19, allow_overlines=False)
        db_session.add_all([ruleset15, ruleset19])
        await db_session.commit()
        
        # Filter by board_size=15
        response = await async_client.get("/api/v1/rulesets/?board_size=15")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Rules15"
        
        # Filter by board_size=19
        response = await async_client.get("/api/v1/rulesets/?board_size=19")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Rules19"


class TestGetStandardRuleSet:
    """Test GET /api/v1/rulesets/standard endpoint."""
    
    async def test_get_standard_ruleset_creates_if_not_exists(self, async_client: AsyncClient):
        """Test getting standard ruleset creates it if it doesn't exist."""
        response = await async_client.get("/api/v1/rulesets/standard")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Standard"
        assert data["board_size"] == 15
        assert data["allow_overlines"] is False
        assert "Standard Gomoku rules" in data["description"]
        assert "id" in data
    
    async def test_get_standard_ruleset_existing(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test getting standard ruleset when it already exists."""
        # Create standard ruleset manually
        standard_ruleset = RuleSet.create_standard_ruleset()
        db_session.add(standard_ruleset)
        await db_session.commit()
        await db_session.refresh(standard_ruleset)
        
        response = await async_client.get("/api/v1/rulesets/standard")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == standard_ruleset.id
        assert data["name"] == "Standard"


class TestGetPresetRuleSets:
    """Test GET /api/v1/rulesets/presets endpoint."""
    
    async def test_get_preset_rulesets_creates_all(self, async_client: AsyncClient):
        """Test getting preset rulesets creates all if they don't exist."""
        response = await async_client.get("/api/v1/rulesets/presets")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have all 5 preset rulesets
        assert len(data) == 5
        
        names = [ruleset["name"] for ruleset in data]
        expected_names = ["Standard", "Renju", "Freestyle", "Caro", "Swap2"]
        assert set(names) == set(expected_names)
        
        # Verify each has proper structure
        for ruleset in data:
            assert "id" in ruleset
            assert "name" in ruleset
            assert "board_size" in ruleset
            assert "allow_overlines" in ruleset
            assert "description" in ruleset
    
    async def test_get_preset_rulesets_existing(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test getting preset rulesets when some already exist."""
        # Create one preset manually
        standard_ruleset = RuleSet.create_standard_ruleset()
        db_session.add(standard_ruleset)
        await db_session.commit()
        
        response = await async_client.get("/api/v1/rulesets/presets")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5


class TestGetRuleSet:
    """Test GET /api/v1/rulesets/{ruleset_id} endpoint."""
    
    async def test_get_ruleset_success(self, async_client: AsyncClient, sample_ruleset):
        """Test successful ruleset retrieval."""
        response = await async_client.get(f"/api/v1/rulesets/{sample_ruleset.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_ruleset.id
        assert data["name"] == sample_ruleset.name
        assert data["board_size"] == sample_ruleset.board_size
        assert data["allow_overlines"] == sample_ruleset.allow_overlines
    
    async def test_get_ruleset_not_found(self, async_client: AsyncClient):
        """Test ruleset retrieval with non-existent ID."""
        response = await async_client.get("/api/v1/rulesets/99999")
        
        assert response.status_code == 404
        assert "Ruleset not found" in response.json()["detail"]
    
    async def test_get_ruleset_invalid_id(self, async_client: AsyncClient):
        """Test ruleset retrieval with invalid ID format."""
        response = await async_client.get("/api/v1/rulesets/invalid")
        
        assert response.status_code == 422


class TestGetRuleSetByName:
    """Test GET /api/v1/rulesets/name/{name} endpoint."""
    
    async def test_get_ruleset_by_name_success(self, async_client: AsyncClient, sample_ruleset):
        """Test successful ruleset retrieval by name."""
        response = await async_client.get(f"/api/v1/rulesets/name/{sample_ruleset.name}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_ruleset.id
        assert data["name"] == sample_ruleset.name
    
    async def test_get_ruleset_by_name_not_found(self, async_client: AsyncClient):
        """Test ruleset retrieval with non-existent name."""
        response = await async_client.get("/api/v1/rulesets/name/NonExistent")
        
        assert response.status_code == 404
        assert "Ruleset not found" in response.json()["detail"]
    
    async def test_get_ruleset_by_name_url_encoded(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test ruleset retrieval with URL-encoded name."""
        # Create ruleset with spaces in name
        ruleset = RuleSet(name="Custom Rules", board_size=15, allow_overlines=False)
        db_session.add(ruleset)
        await db_session.commit()
        
        # URL encode the name (spaces become %20)
        response = await async_client.get("/api/v1/rulesets/name/Custom%20Rules")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Custom Rules"


class TestRuleSetAPIIntegration:
    """Integration tests for ruleset API workflows."""
    
    async def test_ruleset_lifecycle(self, async_client: AsyncClient):
        """Test complete ruleset lifecycle: create -> read by ID -> read by name."""
        # 1. Create ruleset
        ruleset_data = {
            "name": "Lifecycle Rules",
            "board_size": 17,
            "allow_overlines": True,
            "description": "Test lifecycle rules"
        }
        
        create_response = await async_client.post("/api/v1/rulesets/", json=ruleset_data)
        assert create_response.status_code == 201
        ruleset = create_response.json()
        ruleset_id = ruleset["id"]
        
        # 2. Read ruleset by ID
        get_response = await async_client.get(f"/api/v1/rulesets/{ruleset_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Lifecycle Rules"
        
        # 3. Read ruleset by name
        get_by_name_response = await async_client.get("/api/v1/rulesets/name/Lifecycle%20Rules")
        assert get_by_name_response.status_code == 200
        assert get_by_name_response.json()["id"] == ruleset_id
    
    async def test_preset_rulesets_consistency(self, async_client: AsyncClient):
        """Test that preset rulesets are consistent across calls."""
        # First call to create presets
        response1 = await async_client.get("/api/v1/rulesets/presets")
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Second call should return same data
        response2 = await async_client.get("/api/v1/rulesets/presets")
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Should have same number of rulesets
        assert len(data1) == len(data2)
        
        # Should have same IDs for each named ruleset
        ids1 = {ruleset["name"]: ruleset["id"] for ruleset in data1}
        ids2 = {ruleset["name"]: ruleset["id"] for ruleset in data2}
        assert ids1 == ids2
    
    async def test_standard_ruleset_integration(self, async_client: AsyncClient):
        """Test standard ruleset integration with presets."""
        # Get standard ruleset
        standard_response = await async_client.get("/api/v1/rulesets/standard")
        assert standard_response.status_code == 200
        standard_data = standard_response.json()
        
        # Get presets which should include the same standard
        presets_response = await async_client.get("/api/v1/rulesets/presets")
        assert presets_response.status_code == 200
        presets_data = presets_response.json()
        
        # Find standard ruleset in presets
        standard_from_presets = next(
            (r for r in presets_data if r["name"] == "Standard"), 
            None
        )
        assert standard_from_presets is not None
        assert standard_from_presets["id"] == standard_data["id"]