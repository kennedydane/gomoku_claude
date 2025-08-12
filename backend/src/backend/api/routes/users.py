"""
User management API endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from ...db.database import get_db
from ...db.models import User
from ...schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Create a new user.
    
    - **username**: Unique username (3-50 characters)
    - **email**: Optional email address
    - **display_name**: Optional display name
    """
    try:
        db_user = User(
            username=user.username,
            email=user.email,
            display_name=user.display_name
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return UserResponse.model_validate(db_user)
    except IntegrityError as e:
        await db.rollback()
        if "username" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        elif "email" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User creation failed"
            )


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of users to return"),
    active_only: bool = Query(True, description="Only return active users"),
    db: AsyncSession = Depends(get_db)
) -> List[UserResponse]:
    """
    List users with pagination.
    
    - **skip**: Number of users to skip (default: 0)
    - **limit**: Maximum number of users to return (default: 50, max: 100)
    - **active_only**: Only return active users (default: True)
    """
    query = select(User)
    
    if active_only:
        query = query.where(User.is_active == True)
    
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [UserResponse.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Get a specific user by ID.
    
    - **user_id**: User ID to retrieve
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.model_validate(user)


@router.get("/username/{username}", response_model=UserResponse)
async def get_user_by_username(
    username: str,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Get a specific user by username.
    
    - **username**: Username to search for
    """
    result = await db.execute(select(User).where(User.username == username.lower()))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Update a user's information.
    
    - **user_id**: User ID to update
    - **email**: New email address
    - **display_name**: New display name
    - **is_active**: Active status
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update only provided fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    try:
        await db.commit()
        await db.refresh(user)
        return UserResponse.model_validate(user)
    except IntegrityError as e:
        await db.rollback()
        if "email" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User update failed"
            )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Soft delete a user (sets is_active = False).
    
    - **user_id**: User ID to delete
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    await db.commit()
    
    # Return 204 No Content (empty response)