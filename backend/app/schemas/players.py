"""Player directory and profile responses."""

from datetime import datetime

from app.schemas.common import APISchema, PlayerStats, PlayerSummary


class PlayerListItem(PlayerSummary):
    highest_rating: int
    rank: int | None
    matches_played: int
    wins: int
    losses: int
    win_rate: float | None


class PlayerListResponse(APISchema):
    items: list[PlayerListItem]


class PlayerProfile(PlayerSummary):
    highest_rating: int
    rank: int | None
    stats: PlayerStats
    created_at: datetime
    updated_at: datetime
