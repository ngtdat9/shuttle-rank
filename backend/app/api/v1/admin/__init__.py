"""Admin API. Every route on ``admin_router`` depends on ``require_admin``.

Later admin routes should be an ``APIRouter`` included from this module. They
inherit that dependency. A handler that needs the caller can declare
``principal: AdminPrincipal = Depends(require_admin)``; FastAPI runs the
dependency once per request.
"""

from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.api.v1.admin.me import router as me_router

admin_router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(require_admin)],
    tags=["admin"],
)
admin_router.include_router(me_router)

__all__ = ["admin_router"]
