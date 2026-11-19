"""Admin overview: club counts, the audit log, and monthly rebuild."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError
from app.models.achievement import PlayerAchievement
from app.models.audit_log import AuditLog
from app.models.match import Match
from app.models.player import Player
from app.models.tournament import Tournament
from app.schemas.admin import AdminStats, AuditLogEntry
from app.schemas.common import Paginated
from app.services.audit import write_audit
from app.services.monthly_service import rebuild_monthly_snapshots
from app.services.transactions import transaction


def get_admin_stats(db: Session) -> AdminStats:
    """Counts for the admin overview. Deleted matches are excluded."""
    players_total = _count(db, select(func.count()).select_from(Player))
    players_active = _count(
        db, select(func.count()).select_from(Player).where(Player.is_active.is_(True))
    )
    status_rows = db.execute(
        select(Match.status, func.count()).where(Match.deleted_at.is_(None)).group_by(Match.status)
    ).all()
    by_status = {status: int(count) for status, count in status_rows}
    completed = by_status.get("completed", 0)
    canceled = by_status.get("canceled", 0)
    disputed = by_status.get("disputed", 0)
    latest = db.scalars(
        select(Match)
        .where(Match.deleted_at.is_(None))
        .order_by(Match.match_date.desc(), Match.id.desc())
        .limit(1)
    ).first()
    return AdminStats(
        players_total=players_total,
        players_active=players_active,
        matches_total=completed + canceled + disputed,
        matches_completed=completed,
        matches_canceled=canceled,
        matches_disputed=disputed,
        tournaments_total=_count(db, select(func.count()).select_from(Tournament)),
        tournaments_in_progress=_count(
            db,
            select(func.count()).select_from(Tournament).where(Tournament.status == "in_progress"),
        ),
        achievements_awarded=_count(db, select(func.count()).select_from(PlayerAchievement)),
        last_match_at=None if latest is None else latest.match_date,
    )


def list_audit_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    entity_type: str | None = None,
    action: str | None = None,
) -> Paginated[AuditLogEntry]:
    """Audit rows newest first. ``entity_type`` and ``action`` match exactly."""
    if page < 1 or not 1 <= page_size <= 100:
        raise BusinessRuleError("Invalid pagination")
    statement = select(AuditLog)
    if entity_type is not None:
        statement = statement.where(AuditLog.entity_type == entity_type)
    if action is not None:
        statement = statement.where(AuditLog.action == action)
    statement = statement.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    total = int(
        db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    )
    rows = list(db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all())
    return Paginated(
        items=[_audit_entry(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def rebuild_monthly_rankings(db: Session, *, actor: str) -> int:
    """Rebuild every monthly snapshot and record ``rankings.monthly_rebuild``. Commits."""
    actor_id = _require_actor(actor)
    with transaction(db):
        months = rebuild_monthly_snapshots(db)
        write_audit(
            db,
            actor_id=actor_id,
            action="rankings.monthly_rebuild",
            entity_type="rankings",
            entity_id=None,
            before_data=None,
            after_data={"months_rebuilt": months},
        )
    return months


def _audit_entry(row: AuditLog) -> AuditLogEntry:
    return AuditLogEntry(
        id=row.id if isinstance(row.id, uuid.UUID) else uuid.UUID(str(row.id)),
        actor_id=row.actor_id,
        action=row.action,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        before_data=row.before_data,
        after_data=row.after_data,
        created_at=row.created_at,
    )


def _count(db: Session, statement) -> int:
    return int(db.scalar(statement) or 0)


def _require_actor(actor: str) -> str:
    if not isinstance(actor, str) or not actor.strip():
        raise BusinessRuleError("Actor is required")
    return actor.strip()
