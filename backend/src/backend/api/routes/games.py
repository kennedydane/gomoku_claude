"""
Game management API endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...db.database import get_db
from ...db.models import Game, GameMove, GameStatus, Player, RuleSet, User
from ...schemas.game import GameCreate, GameResponse, GameUpdate
from ...schemas.gamemove import GameMoveCreate, GameMoveResponse

router = APIRouter(prefix="/games", tags=["games"])


@router.post("/", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
async def create_game(
    game: GameCreate,
    db: AsyncSession = Depends(get_db)
) -> GameResponse:
    """
    Create a new game.
    
    - **ruleset_id**: ID of the ruleset to use
    - **black_player_id**: ID of the player who plays black
    - **white_player_id**: ID of the white player
    """
    # Verify ruleset exists
    result = await db.execute(select(RuleSet).where(RuleSet.id == game.ruleset_id))
    ruleset = result.scalar_one_or_none()
    if not ruleset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ruleset not found"
        )
    
    # Verify black player exists
    result = await db.execute(select(User).where(User.id == game.black_player_id))
    black_player = result.scalar_one_or_none()
    if not black_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Black player not found"
        )
    
    # Verify white player exists
    result = await db.execute(select(User).where(User.id == game.white_player_id))
    white_player = result.scalar_one_or_none()
    if not white_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="White player not found"
        )
    
    if game.black_player_id == game.white_player_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Black and white player cannot be the same"
        )
    
    # Create the game
    db_game = Game.create_game(
        black_player_id=game.black_player_id,
        white_player_id=game.white_player_id,
        ruleset_id=game.ruleset_id
    )
    
    # Initialize board based on ruleset size
    db_game.initialize_board(ruleset.board_size)
    
    db.add(db_game)
    await db.commit()
    await db.refresh(db_game)
    
    return await _get_game_response(db_game, db)


@router.get("/", response_model=List[GameResponse])
async def list_games(
    skip: int = Query(0, ge=0, description="Number of games to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of games to return"),
    status: Optional[str] = Query(None, description="Filter by game status"),
    player_id: Optional[int] = Query(None, description="Filter by player ID"),
    db: AsyncSession = Depends(get_db)
) -> List[GameResponse]:
    """
    List games with optional filtering.
    
    - **skip**: Number of games to skip (default: 0)
    - **limit**: Maximum number of games to return (default: 50, max: 100)
    - **status**: Optional filter by game status
    - **player_id**: Optional filter by player ID (either black or white)
    """
    query = select(Game)
    
    if status:
        try:
            status_enum = GameStatus(status.lower())
            query = query.where(Game.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status value. Must be one of: {[s.value for s in GameStatus]}"
            )
    
    if player_id:
        query = query.where(
            (Game.black_player_id == player_id) | 
            (Game.white_player_id == player_id)
        )
    
    query = query.offset(skip).limit(limit).order_by(Game.created_at.desc())
    
    result = await db.execute(query)
    games = result.scalars().all()
    
    responses = []
    for game in games:
        response = await _get_game_response(game, db)
        responses.append(response)
    
    return responses


@router.get("/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: str,
    db: AsyncSession = Depends(get_db)
) -> GameResponse:
    """
    Get a specific game by ID.
    
    - **game_id**: Game UUID to retrieve
    """
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    
    return await _get_game_response(game, db)


@router.put("/{game_id}/start", response_model=GameResponse)
async def start_game(
    game_id: str,
    db: AsyncSession = Depends(get_db)
) -> GameResponse:
    """
    Start a game (change status from WAITING to ACTIVE).
    
    - **game_id**: Game UUID to start
    """
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    
    if not game.can_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game cannot be started"
        )
    
    game.start_game()
    await db.commit()
    await db.refresh(game)
    
    return await _get_game_response(game, db)


@router.put("/{game_id}", response_model=GameResponse)
async def update_game(
    game_id: str,
    game_update: GameUpdate,
    db: AsyncSession = Depends(get_db)
) -> GameResponse:
    """
    Update game information.
    
    - **game_id**: Game UUID to update
    - **status**: New game status
    - **winner_id**: Winner player ID (for finished games)
    """
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    
    # Update only provided fields
    update_data = game_update.model_dump(exclude_unset=True)
    
    if "status" in update_data:
        new_status_str = update_data["status"]
        if new_status_str == "FINISHED":
            winner_id = update_data.get("winner_id")
            game.end_game(winner_id)
        elif new_status_str == "ABANDONED":
            game.abandon_game()
    
    await db.commit()
    await db.refresh(game)
    
    return await _get_game_response(game, db)


@router.post("/{game_id}/moves/", response_model=GameMoveResponse, status_code=status.HTTP_201_CREATED)
async def make_move(
    game_id: str,
    move: GameMoveCreate,
    db: AsyncSession = Depends(get_db)
) -> GameMoveResponse:
    """
    Make a move in a game.
    
    - **game_id**: Game UUID to make move in
    - **player_id**: ID of player making the move
    - **row**: Board row position (0-based)
    - **col**: Board column position (0-based)
    """
    # Get the game
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    
    if game.status != GameStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game is not active"
        )
    
    # Verify player is in this game
    if move.player_id not in [game.black_player_id, game.white_player_id]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is not in this game"
        )
    
    # Determine player color based on move number
    move_count = await GameMove.get_move_count(db, game_id)
    expected_move_number = move_count + 1
    expected_color = Player.BLACK if expected_move_number % 2 == 1 else Player.WHITE
    
    # Check if it's the correct player's turn
    expected_player_id = game.black_player_id if expected_color == Player.BLACK else game.white_player_id
    
    if move.player_id != expected_player_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"It's {expected_color.value} player's turn"
        )
    
    # Create the move
    db_move = GameMove(
        game_id=game_id,
        player_id=move.player_id,
        move_number=expected_move_number,
        row=move.row,
        col=move.col,
        player_color=expected_color
    )
    
    # Validate the move
    try:
        await db_move.validate_before_insert(db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Make the move in the game board
    if not game.is_valid_position(move.row, move.col):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid move position"
        )
    
    # Add move to database
    db.add(db_move)
    
    # Update game board state
    success = game.make_move(move.row, move.col)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Move failed"
        )
    
    await db.commit()
    await db.refresh(db_move)
    
    return GameMoveResponse.model_validate(db_move)


@router.get("/{game_id}/moves/", response_model=List[GameMoveResponse])
async def get_game_moves(
    game_id: str,
    db: AsyncSession = Depends(get_db)
) -> List[GameMoveResponse]:
    """
    Get all moves for a game.
    
    - **game_id**: Game UUID to get moves for
    """
    # Verify game exists
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    
    # Get moves
    moves = await GameMove.get_moves_by_game(db, game_id)
    
    return [GameMoveResponse.model_validate(move) for move in moves]


async def _get_game_response(game: Game, db: AsyncSession) -> GameResponse:
    """Helper function to create GameResponse with related data."""
    
    # Load relationships
    await db.refresh(game, [
        "black_player", "white_player", "winner", "ruleset"
    ])
    
    # Convert board_state to GameState format
    board_state = {
        "board": game.board_state["board"],
        "size": game.board_state["size"]
    }
    
    return GameResponse(
        id=game.id,
        black_player_id=game.black_player_id,
        white_player_id=game.white_player_id,
        ruleset_id=game.ruleset_id,
        status=game.status,
        current_player=game.current_player,
        board_state=board_state,
        winner_id=game.winner_id,
        move_count=game.move_count,
        started_at=game.started_at,
        finished_at=game.finished_at,
        created_at=game.created_at,
        updated_at=game.updated_at,
        is_game_over=game.is_game_over,
        can_start=game.can_start,
        black_player={
            "id": game.black_player.id,
            "username": game.black_player.username,
            "display_name": game.black_player.display_name
        } if game.black_player else None,
        white_player={
            "id": game.white_player.id,
            "username": game.white_player.username, 
            "display_name": game.white_player.display_name
        },
        winner={
            "id": game.winner.id,
            "username": game.winner.username,
            "display_name": game.winner.display_name
        } if game.winner else None,
        ruleset={
            "id": game.ruleset.id,
            "name": game.ruleset.name,
            "board_size": game.ruleset.board_size,
            "allow_overlines": game.ruleset.allow_overlines
        } if game.ruleset else None
    )