"""Aggregate ``/api/v1`` routers. Write routes will live under ``/admin`` later."""

from fastapi import APIRouter

from app.api.v1.achievements import router as achievements_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.health import router as health_router
from app.api.v1.matches import router as matches_router
from app.api.v1.players import router as players_router
from app.api.v1.rankings import router as rankings_router
from app.api.v1.tournaments import router as tournaments_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(dashboard_router, tags=["dashboard"])
api_router.include_router(rankings_router, tags=["rankings"])
api_router.include_router(players_router, tags=["players"])
api_router.include_router(matches_router, tags=["matches"])
api_router.include_router(tournaments_router, tags=["tournaments"])
api_router.include_router(achievements_router, tags=["achievements"])
