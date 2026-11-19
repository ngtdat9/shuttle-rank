"""Dashboard aggregate response."""

from datetime import datetime

from app.schemas.achievements import AchievementAward
from app.schemas.common import APISchema, PlayerSummary
from app.schemas.matches import Match
from app.schemas.rankings import RankingEntry
from app.schemas.tournaments import TournamentSummary


class DashboardTotals(APISchema):
    active_players: int
    total_matches: int
    matches_this_month: int
    tournaments_completed: int


class ProgressionPoint(APISchema):
    match_date: datetime | None
    rating: int


class RatingProgression(APISchema):
    player: PlayerSummary
    points: list[ProgressionPoint]


class Dashboard(APISchema):
    leader: RankingEntry | None
    top_players: list[RankingEntry]
    totals: DashboardTotals
    recent_matches: list[Match]
    rating_progression: list[RatingProgression]
    active_tournament: TournamentSummary | None
    recent_achievements: list[AchievementAward]
    last_updated: datetime | None
