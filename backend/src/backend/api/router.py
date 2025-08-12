"""
Main API router aggregating all route modules.
"""

from fastapi import APIRouter

from .routes.users import router as users_router
from .routes.rulesets import router as rulesets_router  
from .routes.games import router as games_router

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_router.include_router(users_router)
api_router.include_router(rulesets_router)
api_router.include_router(games_router)