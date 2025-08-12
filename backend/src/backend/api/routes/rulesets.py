"""
RuleSet management API endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from ...db.database import get_db
from ...db.models import RuleSet
from ...schemas.ruleset import RuleSetCreate, RuleSetResponse

router = APIRouter(prefix="/rulesets", tags=["rulesets"])


@router.post("/", response_model=RuleSetResponse, status_code=status.HTTP_201_CREATED)
async def create_ruleset(
    ruleset: RuleSetCreate,
    db: AsyncSession = Depends(get_db)
) -> RuleSetResponse:
    """
    Create a new custom ruleset.
    
    - **name**: Unique name for the ruleset
    - **board_size**: Board size (typically 15 or 19)
    - **allow_overlines**: Whether 6+ stones in a row count as wins
    - **forbidden_moves**: JSON object with rule configurations
    - **description**: Optional description of the rules
    """
    try:
        db_ruleset = RuleSet(
            name=ruleset.name,
            board_size=ruleset.board_size,
            allow_overlines=ruleset.allow_overlines,
            forbidden_moves=ruleset.forbidden_moves,
            description=ruleset.description
        )
        db.add(db_ruleset)
        await db.commit()
        await db.refresh(db_ruleset)
        return RuleSetResponse.model_validate(db_ruleset)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ruleset with this name already exists"
        )


@router.get("/", response_model=List[RuleSetResponse])
async def list_rulesets(
    skip: int = Query(0, ge=0, description="Number of rulesets to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of rulesets to return"),
    board_size: int = Query(None, ge=5, le=19, description="Filter by board size"),
    db: AsyncSession = Depends(get_db)
) -> List[RuleSetResponse]:
    """
    List rulesets with optional filtering.
    
    - **skip**: Number of rulesets to skip (default: 0)
    - **limit**: Maximum number of rulesets to return (default: 50, max: 100)
    - **board_size**: Optional filter by board size
    """
    query = select(RuleSet)
    
    if board_size:
        query = query.where(RuleSet.board_size == board_size)
    
    query = query.offset(skip).limit(limit).order_by(RuleSet.name)
    
    result = await db.execute(query)
    rulesets = result.scalars().all()
    
    return [RuleSetResponse.model_validate(ruleset) for ruleset in rulesets]


@router.get("/standard", response_model=RuleSetResponse)
async def get_standard_ruleset(
    db: AsyncSession = Depends(get_db)
) -> RuleSetResponse:
    """
    Get the standard Gomoku ruleset, creating it if it doesn't exist.
    """
    result = await db.execute(select(RuleSet).where(RuleSet.name == "Standard"))
    ruleset = result.scalar_one_or_none()
    
    if not ruleset:
        # Create standard ruleset if it doesn't exist
        ruleset = RuleSet.create_standard_ruleset()
        db.add(ruleset)
        await db.commit()
        await db.refresh(ruleset)
    
    return RuleSetResponse.model_validate(ruleset)


@router.get("/presets", response_model=List[RuleSetResponse])
async def get_preset_rulesets(
    db: AsyncSession = Depends(get_db)
) -> List[RuleSetResponse]:
    """
    Get all preset rulesets (Standard, Renju, Freestyle, Caro, Swap2).
    Creates them if they don't exist.
    """
    preset_names = ["Standard", "Renju", "Freestyle", "Caro", "Swap2"]
    rulesets = []
    
    for name in preset_names:
        result = await db.execute(select(RuleSet).where(RuleSet.name == name))
        ruleset = result.scalar_one_or_none()
        
        if not ruleset:
            # Create the preset ruleset based on name
            if name == "Standard":
                ruleset = RuleSet.create_standard_ruleset()
            elif name == "Renju":
                ruleset = RuleSet.create_renju_ruleset()
            elif name == "Freestyle":
                ruleset = RuleSet.create_freestyle_ruleset()
            elif name == "Caro":
                ruleset = RuleSet.create_caro_ruleset()
            elif name == "Swap2":
                ruleset = RuleSet.create_swap2_ruleset()
            
            db.add(ruleset)
            rulesets.append(ruleset)
        else:
            rulesets.append(ruleset)
    
    if rulesets:  # Only commit if we created new rulesets
        try:
            await db.commit()
            for ruleset in rulesets:
                await db.refresh(ruleset)
        except IntegrityError:
            await db.rollback()
            # If there was a race condition, re-fetch from database
            result = await db.execute(
                select(RuleSet).where(RuleSet.name.in_(preset_names))
            )
            rulesets = result.scalars().all()
    
    return [RuleSetResponse.model_validate(ruleset) for ruleset in rulesets]


@router.get("/{ruleset_id}", response_model=RuleSetResponse)
async def get_ruleset(
    ruleset_id: int,
    db: AsyncSession = Depends(get_db)
) -> RuleSetResponse:
    """
    Get a specific ruleset by ID.
    
    - **ruleset_id**: RuleSet ID to retrieve
    """
    result = await db.execute(select(RuleSet).where(RuleSet.id == ruleset_id))
    ruleset = result.scalar_one_or_none()
    
    if not ruleset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ruleset not found"
        )
    
    return RuleSetResponse.model_validate(ruleset)


@router.get("/name/{name}", response_model=RuleSetResponse) 
async def get_ruleset_by_name(
    name: str,
    db: AsyncSession = Depends(get_db)
) -> RuleSetResponse:
    """
    Get a specific ruleset by name.
    
    - **name**: Ruleset name to search for
    """
    result = await db.execute(select(RuleSet).where(RuleSet.name == name))
    ruleset = result.scalar_one_or_none()
    
    if not ruleset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ruleset not found"
        )
    
    return RuleSetResponse.model_validate(ruleset)