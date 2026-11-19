"""Ranking, head-to-head, and rating-history responses."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from app.schemas.common import APISchema, FormResult, PlayerSummary
from app.schemas.matches import Match


class RankingEntry(APISchema):
    rank: int
    player: PlayerSummary
    rating: int
    highest_rating: int
    matches_played: int
    wins: int
    losses: int
    win_rate: float | None
    last_rating_change: int | None
    rating_change_30d: int
    recent_form: list[FormResult]


class RankingsResponse(APISchema):
    items: list[RankingEntry]
    last_updated: datetime | None


class MonthRef(APISchema):
    year: int
    month: int


class MonthlyRankingItem(APISchema):
    rank: int
    player: PlayerSummary
    rating: int
    rank_change: int | None
    wins: int
    losses: int
    matches_played: int
    rating_change_during_month: int


class MonthlyRankingsResponse(APISchema):
    available_months: list[MonthRef]
    year: int | None
    month: int | None
    items: list[MonthlyRankingItem]


class PlayerMonth(APISchema):
    year: int
    month: int
    rating: int
    rank: int
    wins: int
    losses: int
    matches_played: int
    rating_change_during_month: int


class PlayerMonthlyResponse(APISchema):
    items: list[PlayerMonth]


class RatingPoint(APISchema):
    match_id: UUID
    match_date: datetime
    old_rating: int
    new_rating: int
    rating_change: int
    opponent: PlayerSummary
    result: FormResult


class PlayerRatingHistory(APISchema):
    player_id: UUID
    starting_rating: Literal[1500] = 1500
    points: list[RatingPoint]


class HeadToHeadStreak(APISchema):
    player_id: UUID
    count: int


class HeadToHead(APISchema):
    player_a: PlayerSummary
    player_b: PlayerSummary
    total_matches: int
    player_a_wins: int
    player_b_wins: int
    player_a_win_rate: float | None
    player_b_win_rate: float | None
    current_streak: HeadToHeadStreak | None
    player_a_net_rating_change: int
    matches: list[Match]
