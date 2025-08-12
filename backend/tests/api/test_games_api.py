"""
Test suite for Game API endpoints.

Tests all game-related endpoints following TDD principles:
- POST /api/v1/games/ - Create game
- GET /api/v1/games/ - List games
- GET /api/v1/games/{id} - Get game by ID
- PUT /api/v1/games/{id}/start - Start game  
- PUT /api/v1/games/{id} - Update game
- POST /api/v1/games/{id}/moves/ - Make move
- GET /api/v1/games/{id}/moves/ - Get game moves
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Game, GameMove, GameStatus, Player, RuleSet, User


class TestCreateGame:
    """Test POST /api/v1/games/ endpoint."""
    
    async def test_create_single_player_game_success(self, async_client: AsyncClient, sample_user, sample_ruleset):
        """Test successful single-player game creation."""
        game_data = {
            "ruleset_id": sample_ruleset.id,
            "black_player_id": sample_user.id,
            "white_player_id": None
        }
        
        response = await async_client.post("/api/v1/games/", json=game_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["black_player_id"] == sample_user.id
        assert data["white_player_id"] is None
        assert data["ruleset_id"] == sample_ruleset.id
        assert data["status"] == "waiting"
        assert data["current_player"] == "black"
        assert data["move_count"] == 0
        assert data["is_single_player"] is True
        assert data["can_start"] is True
        assert data["is_game_over"] is False
        assert "id" in data
        assert "board_state" in data
        assert data["board_state"]["size"] == sample_ruleset.board_size
    
    async def test_create_two_player_game_success(self, async_client: AsyncClient, sample_user, sample_user2, sample_ruleset):
        """Test successful two-player game creation."""
        game_data = {
            "ruleset_id": sample_ruleset.id,
            "black_player_id": sample_user.id,
            "white_player_id": sample_user2.id
        }
        
        response = await async_client.post("/api/v1/games/", json=game_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["black_player_id"] == sample_user.id
        assert data["white_player_id"] == sample_user2.id
        assert data["is_single_player"] is False
        assert data["can_start"] is True
    
    async def test_create_game_nonexistent_ruleset(self, async_client: AsyncClient, sample_user):
        """Test game creation fails with non-existent ruleset."""
        game_data = {
            "ruleset_id": 99999,
            "black_player_id": sample_user.id,
            "white_player_id": None
        }
        
        response = await async_client.post("/api/v1/games/", json=game_data)
        
        assert response.status_code == 404
        assert "Ruleset not found" in response.json()["detail"]
    
    async def test_create_game_nonexistent_black_player(self, async_client: AsyncClient, sample_ruleset):
        """Test game creation fails with non-existent black player."""
        game_data = {
            "ruleset_id": sample_ruleset.id,
            "black_player_id": 99999,
            "white_player_id": None
        }
        
        response = await async_client.post("/api/v1/games/", json=game_data)
        
        assert response.status_code == 404
        assert "Black player not found" in response.json()["detail"]
    
    async def test_create_game_nonexistent_white_player(self, async_client: AsyncClient, sample_user, sample_ruleset):
        """Test game creation fails with non-existent white player."""
        game_data = {
            "ruleset_id": sample_ruleset.id,
            "black_player_id": sample_user.id,
            "white_player_id": 99999
        }
        
        response = await async_client.post("/api/v1/games/", json=game_data)
        
        assert response.status_code == 404
        assert "White player not found" in response.json()["detail"]
    
    async def test_create_game_same_player_both_colors(self, async_client: AsyncClient, sample_user, sample_ruleset):
        """Test game creation fails when same player is both black and white."""
        game_data = {
            "ruleset_id": sample_ruleset.id,
            "black_player_id": sample_user.id,
            "white_player_id": sample_user.id
        }
        
        response = await async_client.post("/api/v1/games/", json=game_data)
        
        assert response.status_code == 400
        assert "Black and white player cannot be the same" in response.json()["detail"]


class TestListGames:
    """Test GET /api/v1/games/ endpoint."""
    
    async def test_list_games_empty(self, async_client: AsyncClient):
        """Test listing games when database is empty."""
        response = await async_client.get("/api/v1/games/")
        
        assert response.status_code == 200
        assert response.json() == []
    
    async def test_list_games_with_data(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_user2, sample_ruleset):
        """Test listing games with existing data."""
        # Create multiple games
        game1 = Game.create_single_player_game(sample_user.id, sample_ruleset.id)
        game2 = Game.create_two_player_game(sample_user.id, sample_user2.id, sample_ruleset.id)
        db_session.add_all([game1, game2])
        await db_session.commit()
        
        response = await async_client.get("/api/v1/games/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Should include game details
        for game in data:
            assert "id" in game
            assert "status" in game
            assert "black_player" in game
            assert "ruleset" in game
    
    async def test_list_games_pagination(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_ruleset):
        """Test game list pagination."""
        # Create multiple games
        for i in range(5):
            game = Game.create_single_player_game(sample_user.id, sample_ruleset.id)
            db_session.add(game)
        await db_session.commit()
        
        # Test limit
        response = await async_client.get("/api/v1/games/?limit=3")
        assert response.status_code == 200
        assert len(response.json()) == 3
        
        # Test skip
        response = await async_client.get("/api/v1/games/?skip=2&limit=2")
        assert response.status_code == 200
        assert len(response.json()) == 2
    
    async def test_list_games_filter_by_status(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_ruleset):
        """Test filtering games by status."""
        # Create games with different statuses
        waiting_game = Game.create_single_player_game(sample_user.id, sample_ruleset.id)
        active_game = Game.create_single_player_game(sample_user.id, sample_ruleset.id)
        active_game.start_game()
        db_session.add_all([waiting_game, active_game])
        await db_session.commit()
        
        # Filter by WAITING status
        response = await async_client.get("/api/v1/games/?status=WAITING")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "waiting"
        
        # Filter by ACTIVE status
        response = await async_client.get("/api/v1/games/?status=ACTIVE")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "active"
    
    async def test_list_games_filter_by_player(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_user2, sample_ruleset):
        """Test filtering games by player ID."""
        # Create games with different players
        game1 = Game.create_single_player_game(sample_user.id, sample_ruleset.id)
        game2 = Game.create_single_player_game(sample_user2.id, sample_ruleset.id)
        game3 = Game.create_two_player_game(sample_user.id, sample_user2.id, sample_ruleset.id)
        db_session.add_all([game1, game2, game3])
        await db_session.commit()
        
        # Filter by sample_user.id (should get game1 and game3)
        response = await async_client.get(f"/api/v1/games/?player_id={sample_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Filter by sample_user2.id (should get game2 and game3)
        response = await async_client.get(f"/api/v1/games/?player_id={sample_user2.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestGetGame:
    """Test GET /api/v1/games/{game_id} endpoint."""
    
    async def test_get_game_success(self, async_client: AsyncClient, sample_game):
        """Test successful game retrieval."""
        response = await async_client.get(f"/api/v1/games/{sample_game.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_game.id
        assert data["black_player_id"] == sample_game.black_player_id
        assert data["status"] == sample_game.status.value
        assert "board_state" in data
        assert "black_player" in data
        assert "ruleset" in data
    
    async def test_get_game_not_found(self, async_client: AsyncClient):
        """Test game retrieval with non-existent ID."""
        response = await async_client.get("/api/v1/games/non-existent-uuid")
        
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]


class TestStartGame:
    """Test PUT /api/v1/games/{game_id}/start endpoint."""
    
    async def test_start_game_success(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_ruleset):
        """Test successful game start."""
        # Create a WAITING game
        game = Game.create_single_player_game(sample_user.id, sample_ruleset.id)
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        response = await async_client.put(f"/api/v1/games/{game.id}/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["started_at"] is not None
        assert data["current_player"] == "black"
    
    async def test_start_game_not_found(self, async_client: AsyncClient):
        """Test starting non-existent game."""
        response = await async_client.put("/api/v1/games/non-existent-uuid/start")
        
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]
    
    async def test_start_game_already_started(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_ruleset):
        """Test starting already active game."""
        # Create and start a game
        game = Game.create_single_player_game(sample_user.id, sample_ruleset.id)
        game.start_game()
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        response = await async_client.put(f"/api/v1/games/{game.id}/start")
        
        assert response.status_code == 400
        assert "Game cannot be started" in response.json()["detail"]


class TestUpdateGame:
    """Test PUT /api/v1/games/{game_id} endpoint."""
    
    async def test_update_game_end_with_winner(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_ruleset):
        """Test ending game with winner."""
        # Create and start game
        game = Game.create_single_player_game(sample_user.id, sample_ruleset.id)
        game.start_game()
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        update_data = {
            "status": "FINISHED",
            "winner_id": sample_user.id
        }
        
        response = await async_client.put(f"/api/v1/games/{game.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "finished"
        assert data["winner_id"] == sample_user.id
        assert data["finished_at"] is not None
        assert data["is_game_over"] is True
    
    async def test_update_game_abandon(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_ruleset):
        """Test abandoning game."""
        # Create and start game
        game = Game.create_single_player_game(sample_user.id, sample_ruleset.id)
        game.start_game()
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        update_data = {
            "status": "ABANDONED"
        }
        
        response = await async_client.put(f"/api/v1/games/{game.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "abandoned"
        assert data["winner_id"] is None
        assert data["finished_at"] is not None
        assert data["is_game_over"] is True
    
    async def test_update_game_not_found(self, async_client: AsyncClient):
        """Test updating non-existent game."""
        update_data = {"status": "FINISHED"}
        
        response = await async_client.put("/api/v1/games/non-existent-uuid", json=update_data)
        
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]


class TestMakeMove:
    """Test POST /api/v1/games/{game_id}/moves/ endpoint."""
    
    async def test_make_move_success(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_ruleset):
        """Test successful move creation."""
        # Create and start game
        game = Game.create_single_player_game(sample_user.id, sample_ruleset.id)
        game.start_game()
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        move_data = {
            "player_id": sample_user.id,
            "row": 7,
            "col": 7
        }
        
        response = await async_client.post(f"/api/v1/games/{game.id}/moves/", json=move_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["game_id"] == game.id
        assert data["player_id"] == sample_user.id
        assert data["move_number"] == 1
        assert data["row"] == 7
        assert data["col"] == 7
        assert data["player_color"] == "black"
        assert data["is_winning_move"] is False
    
    async def test_make_move_two_player_alternating(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_user2, sample_ruleset):
        """Test alternating moves in two-player game."""
        # Create and start two-player game
        game = Game.create_two_player_game(sample_user.id, sample_user2.id, sample_ruleset.id)
        game.start_game()
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        # First move (BLACK player)
        move1_data = {
            "player_id": sample_user.id,
            "row": 7,
            "col": 7
        }
        
        response1 = await async_client.post(f"/api/v1/games/{game.id}/moves/", json=move1_data)
        assert response1.status_code == 201
        assert response1.json()["player_color"] == "black"
        
        # Second move (WHITE player)
        move2_data = {
            "player_id": sample_user2.id,
            "row": 7,
            "col": 8
        }
        
        response2 = await async_client.post(f"/api/v1/games/{game.id}/moves/", json=move2_data)
        assert response2.status_code == 201
        assert response2.json()["player_color"] == "white"
    
    async def test_make_move_game_not_found(self, async_client: AsyncClient, sample_user):
        """Test making move in non-existent game."""
        move_data = {
            "player_id": sample_user.id,
            "row": 7,
            "col": 7
        }
        
        response = await async_client.post("/api/v1/games/non-existent-uuid/moves/", json=move_data)
        
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]
    
    async def test_make_move_game_not_active(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_ruleset):
        """Test making move in inactive game."""
        # Create game but don't start it
        game = Game.create_single_player_game(sample_user.id, sample_ruleset.id)
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        move_data = {
            "player_id": sample_user.id,
            "row": 7,
            "col": 7
        }
        
        response = await async_client.post(f"/api/v1/games/{game.id}/moves/", json=move_data)
        
        assert response.status_code == 400
        assert "Game is not active" in response.json()["detail"]
    
    async def test_make_move_wrong_player(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_user2, sample_ruleset):
        """Test making move with wrong player."""
        # Create two-player game
        game = Game.create_two_player_game(sample_user.id, sample_user2.id, sample_ruleset.id)
        game.start_game()
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        # Try to make first move as WHITE player (should be BLACK)
        move_data = {
            "player_id": sample_user2.id,  # WHITE player
            "row": 7,
            "col": 7
        }
        
        response = await async_client.post(f"/api/v1/games/{game.id}/moves/", json=move_data)
        
        assert response.status_code == 400
        assert "black player's turn" in response.json()["detail"]
    
    async def test_make_move_invalid_position(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_ruleset):
        """Test making move at invalid position."""
        # Create and start game
        game = Game.create_single_player_game(sample_user.id, sample_ruleset.id)
        game.start_game()
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        move_data = {
            "player_id": sample_user.id,
            "row": 20,  # Out of bounds
            "col": 7
        }
        
        response = await async_client.post(f"/api/v1/games/{game.id}/moves/", json=move_data)
        
        assert response.status_code == 422
        assert "less than or equal to 14" in str(response.json())
    
    async def test_make_move_occupied_position(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_user2, sample_ruleset):
        """Test making move at already occupied position."""
        # Create and start two-player game 
        game = Game.create_two_player_game(sample_user.id, sample_user2.id, sample_ruleset.id)
        game.start_game()
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        # First move (BLACK player)
        move1_data = {
            "player_id": sample_user.id,
            "row": 7,
            "col": 7
        }
        response1 = await async_client.post(f"/api/v1/games/{game.id}/moves/", json=move1_data)
        assert response1.status_code == 201
        
        # Try same position with WHITE player (should fail due to occupied position)
        move2_data = {
            "player_id": sample_user2.id,
            "row": 7,
            "col": 7  # Same position
        }
        response2 = await async_client.post(f"/api/v1/games/{game.id}/moves/", json=move2_data)
        assert response2.status_code == 400
        assert "already occupied" in response2.json()["detail"]


class TestGetGameMoves:
    """Test GET /api/v1/games/{game_id}/moves/ endpoint."""
    
    async def test_get_game_moves_empty(self, async_client: AsyncClient, sample_game):
        """Test getting moves for game with no moves."""
        response = await async_client.get(f"/api/v1/games/{sample_game.id}/moves/")
        
        assert response.status_code == 200
        assert response.json() == []
    
    async def test_get_game_moves_with_data(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_user2, sample_ruleset):
        """Test getting moves for game with existing moves."""
        # Create and start two-player game
        game = Game.create_two_player_game(sample_user.id, sample_user2.id, sample_ruleset.id)
        game.start_game()
        db_session.add(game)
        await db_session.commit()
        await db_session.refresh(game)
        
        # Make some moves via API
        move1_data = {"player_id": sample_user.id, "row": 7, "col": 7}
        move2_data = {"player_id": sample_user2.id, "row": 7, "col": 8}
        
        await async_client.post(f"/api/v1/games/{game.id}/moves/", json=move1_data)
        await async_client.post(f"/api/v1/games/{game.id}/moves/", json=move2_data)
        
        # Get moves
        response = await async_client.get(f"/api/v1/games/{game.id}/moves/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Should be ordered by move_number
        assert data[0]["move_number"] == 1
        assert data[1]["move_number"] == 2
        assert data[0]["player_color"] == "black"
        assert data[1]["player_color"] == "white"
    
    async def test_get_game_moves_not_found(self, async_client: AsyncClient):
        """Test getting moves for non-existent game."""
        response = await async_client.get("/api/v1/games/non-existent-uuid/moves/")
        
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]


class TestGameAPIIntegration:
    """Integration tests for game API workflows."""
    
    async def test_complete_game_workflow(self, async_client: AsyncClient, db_session: AsyncSession, sample_user, sample_user2, sample_ruleset):
        """Test complete game workflow: create -> start -> make moves -> finish."""
        # 1. Create two-player game
        game_data = {
            "ruleset_id": sample_ruleset.id,
            "black_player_id": sample_user.id,
            "white_player_id": sample_user2.id
        }
        
        create_response = await async_client.post("/api/v1/games/", json=game_data)
        assert create_response.status_code == 201
        game = create_response.json()
        game_id = game["id"]
        
        # 2. Start game
        start_response = await async_client.put(f"/api/v1/games/{game_id}/start")
        assert start_response.status_code == 200
        assert start_response.json()["status"] == "active"
        
        # 3. Make some moves
        moves = [
            {"player_id": sample_user.id, "row": 7, "col": 7},   # BLACK
            {"player_id": sample_user2.id, "row": 7, "col": 8},  # WHITE
            {"player_id": sample_user.id, "row": 8, "col": 8},   # BLACK
        ]
        
        for i, move_data in enumerate(moves):
            move_response = await async_client.post(f"/api/v1/games/{game_id}/moves/", json=move_data)
            assert move_response.status_code == 201
            assert move_response.json()["move_number"] == i + 1
        
        # 4. Get move history
        moves_response = await async_client.get(f"/api/v1/games/{game_id}/moves/")
        assert moves_response.status_code == 200
        assert len(moves_response.json()) == 3
        
        # 5. End game
        update_data = {
            "status": "FINISHED",
            "winner_id": sample_user.id
        }
        
        end_response = await async_client.put(f"/api/v1/games/{game_id}", json=update_data)
        assert end_response.status_code == 200
        assert end_response.json()["status"] == "finished"
        assert end_response.json()["winner_id"] == sample_user.id
    
    async def test_single_player_game_workflow(self, async_client: AsyncClient, sample_user, sample_ruleset):
        """Test single-player game workflow."""
        # 1. Create single-player game
        game_data = {
            "ruleset_id": sample_ruleset.id,
            "black_player_id": sample_user.id,
            "white_player_id": None
        }
        
        create_response = await async_client.post("/api/v1/games/", json=game_data)
        assert create_response.status_code == 201
        game = create_response.json()
        game_id = game["id"]
        assert game["is_single_player"] is True
        
        # 2. Start and make moves
        start_response = await async_client.put(f"/api/v1/games/{game_id}/start")
        assert start_response.status_code == 200
        
        move_response = await async_client.post(f"/api/v1/games/{game_id}/moves/", json={
            "player_id": sample_user.id,
            "row": 7,
            "col": 7
        })
        assert move_response.status_code == 201
        assert move_response.json()["player_color"] == "black"