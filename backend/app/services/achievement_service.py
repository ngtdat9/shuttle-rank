"""Read-only achievement queries. Awarding stays in a later task."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.achievement import Achievement as AchievementRow
from app.models.achievement import PlayerAchievement as PlayerAchievementRow
from app.models.player import Player
from app.schemas.achievements import (
    Achievement,
    AchievementAward,
    AchievementListResponse,
    PlayerAchievement,
    PlayerAchievementListResponse,
)
from app.services.ordering import ensure_utc
from app.services.serialize import load_players, player_summary


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
