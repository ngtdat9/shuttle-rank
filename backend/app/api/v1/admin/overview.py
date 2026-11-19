"""Admin stats and the audit log."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import pagination
from app.db.session import get_db
from app.schemas.admin import AdminStats, AuditLogEntry
from app.schemas.common import Paginated
from app.services.admin_service import get_admin_stats, list_audit_logs

router = APIRouter()


@router.get("/stats", response_model=AdminStats)
def admin_stats(db: Session = Depends(get_db)) -> AdminStats:
    return get_admin_stats(db)


@router.get("/audit-logs", response_model=Paginated[AuditLogEntry])
def admin_audit_logs(
    db: Session = Depends(get_db),
    pages: tuple[int, int] = Depends(pagination),
    entity_type: str | None = None,
    action: str | None = None,
) -> Paginated[AuditLogEntry]:
    page, page_size = pages
    return list_audit_logs(
        db,
        page=page,
        page_size=page_size,
        entity_type=entity_type,
        action=action,
    )
