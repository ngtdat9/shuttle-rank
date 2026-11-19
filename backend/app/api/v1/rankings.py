"""GET /rankings and GET /rankings/monthly."""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.rankings import MonthlyRankingsResponse, RankingsResponse
from app.services.monthly_service import get_monthly_rankings
from app.services.ranking_service import get_rankings

router = APIRouter()

SortField = Literal[
    "rank",
    "rating",
    "win_rate",
    "wins",
    "losses",
    "matches_played",
    "highest_rating",
]


@router.get("/rankings", response_model=RankingsResponse)
def rankings(
    db: Session = Depends(get_db),
    include_inactive: bool = False,
    sort: SortField = "rank",
    order: Literal["asc", "desc"] | None = None,
) -> RankingsResponse:
    return get_rankings(db, include_inactive=include_inactive, sort=sort, order=order)


@router.get("/rankings/monthly", response_model=MonthlyRankingsResponse)
def monthly_rankings(
    db: Session = Depends(get_db),
    year: int | None = Query(default=None, ge=1, le=9999),
    month: int | None = Query(default=None, ge=1, le=12),
) -> MonthlyRankingsResponse:
    return get_monthly_rankings(db, year=year, month=month)
