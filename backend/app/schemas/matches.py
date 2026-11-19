"""Match responses."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from app.schemas.common import APISchema, FormResult, PlayerSummary, RatingChange


class TournamentRef(APISchema):
    id: UUID
    name: str


class Match(APISchema):
    id: UUID
    player_a: PlayerSummary
    player_b: PlayerSummary
    winner_id: UUID
    match_date: datetime
    status: Literal["completed", "canceled", "disputed"]
    tournament: TournamentRef | None
    game_scores: list[tuple[int, int]] | None
    notes: str | None
    rating_changes: list[RatingChange]
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PlayerMatch(Match):
    opponent: PlayerSummary
    result: FormResult
    rating_change: int | None
