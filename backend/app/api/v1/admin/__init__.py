"""Admin API. Every route on ``admin_router`` depends on ``require_admin``.

Later admin routes should be an ``APIRouter`` included from this module. They
inherit that dependency. A handler that needs the caller can declare
``principal: AdminPrincipal = Depends(require_admin)``; FastAPI runs the
dependency once per request.
"""

from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.api.v1.admin.achievements import router as achievements_router
from app.api.v1.admin.matches import router as matches_router
from app.api.v1.admin.me import router as me_router
from app.api.v1.admin.overview import router as overview_router
from app.api.v1.admin.players import router as players_router
from app.api.v1.admin.rankings import router as rankings_router
from app.api.v1.admin.tournaments import router as tournaments_router

admin_router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(require_admin)],
    tags=["admin"],
)
admin_router.include_router(me_router)
admin_router.include_router(overview_router)
admin_router.include_router(players_router)
admin_router.include_router(matches_router)
admin_router.include_router(rankings_router)
admin_router.include_router(tournaments_router)
admin_router.include_router(achievements_router)

__all__ = ["admin_router"]
