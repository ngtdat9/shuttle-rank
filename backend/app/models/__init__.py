"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from app.models.achievement import Achievement, PlayerAchievement
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.match import Match
from app.models.monthly_ranking import MonthlyRanking
from app.models.player import Player
from app.models.rating_history import RatingHistory
from app.models.tournament import BracketMatch, Tournament, TournamentParticipant

__all__ = [
    "Achievement",
    "AdminUser",
    "AuditLog",
    "BracketMatch",
    "Match",
    "MonthlyRanking",
    "Player",
    "PlayerAchievement",
    "RatingHistory",
    "Tournament",
    "TournamentParticipant",
]
