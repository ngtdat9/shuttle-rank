"""Achievement responses."""

from datetime import datetime
from uuid import UUID

from app.schemas.common import APISchema, PlayerSummary


class Achievement(APISchema):
    id: UUID
    name: str
    description: str
    icon: str
    criteria_type: str
    criteria_value: int | None
    is_active: bool
    awarded_count: int


class PlayerAchievement(APISchema):
    id: UUID
    achievement: Achievement
    awarded_at: datetime
    notes: str | None


class AchievementAward(APISchema):
    id: UUID
    player: PlayerSummary
    achievement: Achievement
    awarded_at: datetime


class AchievementListResponse(APISchema):
    items: list[Achievement]


class PlayerAchievementListResponse(APISchema):
    items: list[PlayerAchievement]
