"""Public player reads."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import pagination
from app.db.session import get_db
from app.schemas.achievements import PlayerAchievementListResponse
from app.schemas.common import Paginated
from app.schemas.matches import PlayerMatch
from app.schemas.players import PlayerListResponse, PlayerProfile
from app.schemas.rankings import PlayerMonthlyResponse, PlayerRatingHistory
from app.services.achievement_service import list_player_achievements
from app.services.match_service import get_rating_history, list_player_matches
from app.services.player_service import get_player_profile, list_players, player_monthly_items

router = APIRouter()

MatchStatusFilter = Literal["completed", "canceled", "disputed", "all"]


@router.get("/players", response_model=PlayerListResponse)
def players(
    db: Session = Depends(get_db),
    include_inactive: bool = False,
    search: str | None = None,
) -> PlayerListResponse:
    return list_players(db, include_inactive=include_inactive, search=search)


@router.get("/players/{player_id}", response_model=PlayerProfile)
def player_profile(player_id: UUID, db: Session = Depends(get_db)) -> PlayerProfile:
    return get_player_profile(db, player_id)


@router.get("/players/{player_id}/matches", response_model=Paginated[PlayerMatch])
def player_matches(
    player_id: UUID,
    db: Session = Depends(get_db),
    pages: tuple[int, int] = Depends(pagination),
    status: MatchStatusFilter = "completed",
) -> Paginated[PlayerMatch]:
    page, page_size = pages
    return list_player_matches(db, player_id, page=page, page_size=page_size, status=status)


@router.get("/players/{player_id}/rating-history", response_model=PlayerRatingHistory)
def player_rating_history(player_id: UUID, db: Session = Depends(get_db)) -> PlayerRatingHistory:
    return get_rating_history(db, player_id)


@router.get("/players/{player_id}/monthly", response_model=PlayerMonthlyResponse)
def player_monthly(player_id: UUID, db: Session = Depends(get_db)) -> PlayerMonthlyResponse:
    return PlayerMonthlyResponse(items=player_monthly_items(db, player_id))


@router.get("/players/{player_id}/achievements", response_model=PlayerAchievementListResponse)
def player_achievements(
    player_id: UUID,
    db: Session = Depends(get_db),
) -> PlayerAchievementListResponse:
    return list_player_achievements(db, player_id)
