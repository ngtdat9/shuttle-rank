"""Tournament and bracket responses."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from app.schemas.common import APISchema, PlayerSummary
from app.schemas.matches import Match


class TournamentSummary(APISchema):
    id: UUID
    name: str
    description: str | None
    format: Literal["single_elimination"]
    status: Literal["draft", "in_progress", "completed", "canceled"]
    start_date: date | None
    end_date: date | None
    participant_count: int
    champion: PlayerSummary | None
    created_at: datetime


class TournamentParticipant(APISchema):
    player: PlayerSummary
    seed: int | None
    final_position: int | None


class TournamentDetail(TournamentSummary):
    participants: list[TournamentParticipant]
    bracket_generated: bool
    runner_up: PlayerSummary | None
    updated_at: datetime


class TournamentListResponse(APISchema):
    items: list[TournamentSummary]


class BracketMatch(APISchema):
    id: UUID
    round: int
    position: int
    player_a: PlayerSummary | None
    player_b: PlayerSummary | None
    seed_a: int | None
    seed_b: int | None
    winner_id: UUID | None
    is_bye: bool
    status: Literal["pending", "ready", "completed", "bye"]
    match_id: UUID | None
    match_date: datetime | None
    game_scores: list[tuple[int, int]] | None


class BracketRound(APISchema):
    round: int
    name: str
    matches: list[BracketMatch]


class Bracket(APISchema):
    tournament_id: UUID
    rounds: list[BracketRound]


class TournamentMatchResult(APISchema):
    match: Match
    bracket: Bracket
