"""Achievement reads and admin writes.

Public mutators (``create_achievement``, ``update_achievement``,
``award_achievement``, ``revoke_award``) commit. The ``_``-prefixed inner
functions flush only, so a caller can compose them in a larger transaction.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models.achievement import Achievement as AchievementRow
from app.models.achievement import PlayerAchievement as PlayerAchievementRow
from app.models.player import Player
from app.schemas.achievements import (
    Achievement,
    AchievementAward,
    AchievementListResponse,
    AdminAchievementAward,
    PlayerAchievement,
    PlayerAchievementListResponse,
)
from app.schemas.common import Paginated
from app.services.audit import write_audit
from app.services.ordering import ensure_utc
from app.services.serialize import load_players, player_summary
from app.services.transactions import transaction


def list_achievements(db: Session, *, include_inactive: bool = False) -> AchievementListResponse:
    rows = list(db.scalars(select(AchievementRow)).all())
    if not include_inactive:
        rows = [row for row in rows if row.is_active]
    rows.sort(key=lambda row: (row.name.casefold(), row.name))
    counts = _award_counts(db)
    return AchievementListResponse(items=[_achievement(row, counts.get(row.id, 0)) for row in rows])


def list_player_achievements(db: Session, player_id: uuid.UUID) -> PlayerAchievementListResponse:
    if db.get(Player, player_id) is None:
        raise NotFoundError("Player not found")
    awards = list(
        db.scalars(
            select(PlayerAchievementRow).where(PlayerAchievementRow.player_id == player_id)
        ).all()
    )
    awards.sort(key=lambda award: ensure_utc(award.awarded_at), reverse=True)
    achievements = _achievements_by_id(db, {award.achievement_id for award in awards})
    counts = _award_counts(db)
    return PlayerAchievementListResponse(
        items=[
            PlayerAchievement(
                id=award.id,
                achievement=_achievement(
                    achievements[award.achievement_id], counts.get(award.achievement_id, 0)
                ),
                awarded_at=award.awarded_at,
                notes=award.notes,
            )
            for award in awards
        ]
    )


def recent_awards(db: Session, *, limit: int = 5) -> list[AchievementAward]:
    awards = list(db.scalars(select(PlayerAchievementRow)).all())
    awards.sort(key=lambda award: ensure_utc(award.awarded_at), reverse=True)
    awards = awards[:limit]
    if not awards:
        return []
    players = load_players(db, {award.player_id for award in awards})
    achievements = _achievements_by_id(db, {award.achievement_id for award in awards})
    counts = _award_counts(db)
    return [
        AchievementAward(
            id=award.id,
            player=player_summary(players[award.player_id]),
            achievement=_achievement(
                achievements[award.achievement_id],
                counts.get(award.achievement_id, 0),
            ),
            awarded_at=award.awarded_at,
        )
        for award in awards
    ]


def award_achievement(
    db: Session,
    *,
    player_id: uuid.UUID,
    achievement_id: uuid.UUID,
    actor: str,
    notes: str | None = None,
    awarded_at: datetime | None = None,
) -> PlayerAchievementRow:
    """Award an achievement, write ``achievement.award``, and commit."""
    with transaction(db):
        row = _award_achievement(
            db,
            player_id=player_id,
            achievement_id=achievement_id,
            actor=actor,
            notes=notes,
            awarded_at=awarded_at,
        )
    db.refresh(row)
    return row


def _award_achievement(
    db: Session,
    *,
    player_id: uuid.UUID,
    achievement_id: uuid.UUID,
    actor: str,
    notes: str | None = None,
    awarded_at: datetime | None = None,
) -> PlayerAchievementRow:
    """Insert one award and flush. Does not commit or roll back."""
    actor_id = _require_actor(actor)
    if notes is not None and not isinstance(notes, str):
        raise BusinessRuleError("Notes must be a string")
    if db.get(Player, player_id) is None:
        raise NotFoundError("Player not found")
    achievement = db.get(AchievementRow, achievement_id)
    if achievement is None:
        raise NotFoundError("Achievement not found")
    if not achievement.is_active:
        raise BusinessRuleError("Inactive achievements cannot be awarded")
    existing = db.scalar(
        select(PlayerAchievementRow.id).where(
            PlayerAchievementRow.player_id == player_id,
            PlayerAchievementRow.achievement_id == achievement_id,
        )
    )
    if existing is not None:
        raise ConflictError("Player already has this achievement")
    when = datetime.now(UTC) if awarded_at is None else ensure_utc(awarded_at)
    row = PlayerAchievementRow(
        player_id=player_id,
        achievement_id=achievement_id,
        awarded_at=when,
        awarded_by=actor_id,
        notes=notes,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError("Player already has this achievement") from exc
    write_audit(
        db,
        actor_id=actor_id,
        action="achievement.award",
        entity_type="player_achievement",
        entity_id=row.id,
        before_data=None,
        after_data={
            "player_id": player_id,
            "achievement_id": achievement_id,
            "awarded_at": when,
            "notes": notes,
        },
    )
    db.flush()
    return row


def get_achievement(db: Session, achievement_id: uuid.UUID) -> Achievement:
    row = _get_achievement(db, achievement_id)
    return _achievement(row, _award_counts(db).get(row.id, 0))


def create_achievement(
    db: Session,
    *,
    name: str,
    description: str,
    actor: str,
    icon: str = "award",
    criteria_type: str = "manual",
    criteria_value: int | None = None,
) -> AchievementRow:
    """Insert an achievement definition and write ``achievement.create``. Commits."""
    with transaction(db):
        row = _create_achievement(
            db,
            name=name,
            description=description,
            actor=actor,
            icon=icon,
            criteria_type=criteria_type,
            criteria_value=criteria_value,
        )
    db.refresh(row)
    return row


def _create_achievement(
    db: Session,
    *,
    name: str,
    description: str,
    actor: str,
    icon: str = "award",
    criteria_type: str = "manual",
    criteria_value: int | None = None,
) -> AchievementRow:
    actor_id = _require_actor(actor)
    _ensure_name_free(db, name, exclude_id=None)
    row = AchievementRow(
        name=name,
        description=description,
        icon=icon,
        criteria_type=criteria_type,
        criteria_value=criteria_value,
        is_active=True,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError("An achievement with this name already exists") from exc
    write_audit(
        db,
        actor_id=actor_id,
        action="achievement.create",
        entity_type="achievement",
        entity_id=row.id,
        before_data=None,
        after_data=_definition_snapshot(row),
    )
    db.flush()
    return row


def update_achievement(
    db: Session, achievement_id: uuid.UUID, *, actor: str, **changes: Any
) -> AchievementRow:
    """Change an achievement definition (including ``is_active``). Commits."""
    with transaction(db):
        row = _update_achievement(db, achievement_id, actor=actor, **changes)
    db.refresh(row)
    return row


def _update_achievement(
    db: Session, achievement_id: uuid.UUID, *, actor: str, **changes: Any
) -> AchievementRow:
    actor_id = _require_actor(actor)
    allowed = {"name", "description", "icon", "criteria_type", "criteria_value", "is_active"}
    if not changes or set(changes) - allowed:
        raise BusinessRuleError("No valid achievement changes were provided")
    row = _get_achievement(db, achievement_id)
    before = _definition_snapshot(row)
    if "name" in changes and changes["name"] != row.name:
        _ensure_name_free(db, changes["name"], exclude_id=row.id)
    for key, value in changes.items():
        setattr(row, key, value)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError("An achievement with this name already exists") from exc
    write_audit(
        db,
        actor_id=actor_id,
        action="achievement.update",
        entity_type="achievement",
        entity_id=row.id,
        before_data=before,
        after_data=_definition_snapshot(row),
    )
    db.flush()
    return row


def list_awards(
    db: Session, *, page: int = 1, page_size: int = 20
) -> Paginated[AdminAchievementAward]:
    """All awards, newest first, with ``notes`` and ``awarded_by``."""
    if page < 1 or not 1 <= page_size <= 100:
        raise BusinessRuleError("Invalid pagination")
    total = int(db.scalar(select(func.count()).select_from(PlayerAchievementRow)) or 0)
    rows = list(
        db.scalars(
            select(PlayerAchievementRow)
            .order_by(PlayerAchievementRow.awarded_at.desc(), PlayerAchievementRow.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return Paginated(items=_admin_awards(db, rows), total=total, page=page, page_size=page_size)


def get_admin_award(db: Session, award_id: uuid.UUID) -> AdminAchievementAward:
    row = db.get(PlayerAchievementRow, award_id)
    if row is None:
        raise NotFoundError("Award not found")
    return _admin_awards(db, [row])[0]


def get_award(db: Session, award_id: uuid.UUID) -> AchievementAward:
    admin = get_admin_award(db, award_id)
    return AchievementAward(
        id=admin.id,
        player=admin.player,
        achievement=admin.achievement,
        awarded_at=admin.awarded_at,
    )


def revoke_award(db: Session, award_id: uuid.UUID, *, actor: str) -> uuid.UUID:
    """Delete an award and write ``achievement.revoke``. Commits."""
    with transaction(db):
        _revoke_award(db, award_id, actor=actor)
    return award_id


def _revoke_award(db: Session, award_id: uuid.UUID, *, actor: str) -> None:
    actor_id = _require_actor(actor)
    row = db.get(PlayerAchievementRow, award_id)
    if row is None:
        raise NotFoundError("Award not found")
    before = {
        "player_id": row.player_id,
        "achievement_id": row.achievement_id,
        "awarded_at": row.awarded_at,
        "awarded_by": row.awarded_by,
        "notes": row.notes,
    }
    db.delete(row)
    db.flush()
    write_audit(
        db,
        actor_id=actor_id,
        action="achievement.revoke",
        entity_type="player_achievement",
        entity_id=award_id,
        before_data=before,
        after_data=None,
    )
    db.flush()


def _admin_awards(db: Session, rows: list[PlayerAchievementRow]) -> list[AdminAchievementAward]:
    if not rows:
        return []
    players = load_players(db, {row.player_id for row in rows})
    achievements = _achievements_by_id(db, {row.achievement_id for row in rows})
    counts = _award_counts(db)
    return [
        AdminAchievementAward(
            id=row.id,
            player=player_summary(players[row.player_id]),
            achievement=_achievement(
                achievements[row.achievement_id], counts.get(row.achievement_id, 0)
            ),
            awarded_at=row.awarded_at,
            notes=row.notes,
            awarded_by=row.awarded_by,
        )
        for row in rows
    ]


def _get_achievement(db: Session, achievement_id: uuid.UUID) -> AchievementRow:
    row = db.get(AchievementRow, achievement_id)
    if row is None:
        raise NotFoundError("Achievement not found")
    return row


def _ensure_name_free(db: Session, name: str, *, exclude_id: uuid.UUID | None) -> None:
    wanted = name.strip().casefold()
    for other_id, other_name in db.execute(select(AchievementRow.id, AchievementRow.name)).all():
        if other_id != exclude_id and other_name.strip().casefold() == wanted:
            raise ConflictError("An achievement with this name already exists")


def _definition_snapshot(row: AchievementRow) -> dict[str, Any]:
    return {
        "name": row.name,
        "description": row.description,
        "icon": row.icon,
        "criteria_type": row.criteria_type,
        "criteria_value": row.criteria_value,
        "is_active": row.is_active,
    }


def _require_actor(actor: str) -> str:
    if not isinstance(actor, str) or not actor.strip():
        raise BusinessRuleError("Actor is required")
    return actor.strip()


def _achievement(row: AchievementRow, awarded_count: int) -> Achievement:
    return Achievement(
        id=row.id,
        name=row.name,
        description=row.description,
        icon=row.icon,
        criteria_type=row.criteria_type,
        criteria_value=row.criteria_value,
        is_active=row.is_active,
        awarded_count=awarded_count,
    )


def _achievements_by_id(db: Session, ids: set[uuid.UUID]) -> dict[uuid.UUID, AchievementRow]:
    if not ids:
        return {}
    return {
        row.id: row
        for row in db.scalars(select(AchievementRow).where(AchievementRow.id.in_(ids))).all()
    }


def _award_counts(db: Session) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(PlayerAchievementRow.achievement_id, func.count()).group_by(
            PlayerAchievementRow.achievement_id
        )
    ).all()
    return {achievement_id: int(count) for achievement_id, count in rows}
