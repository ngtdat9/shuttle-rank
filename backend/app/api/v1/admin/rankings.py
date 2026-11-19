"""Admin ranking maintenance."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AdminPrincipal, get_actor_id, require_admin
from app.db.session import get_db
from app.schemas.admin import MonthlyRebuildResponse
from app.services.admin_service import rebuild_monthly_rankings

router = APIRouter()


@router.post("/rankings/monthly/rebuild", response_model=MonthlyRebuildResponse)
def admin_rebuild_monthly(
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MonthlyRebuildResponse:
    months = rebuild_monthly_rankings(db, actor=get_actor_id(principal))
    return MonthlyRebuildResponse(months_rebuilt=months)
