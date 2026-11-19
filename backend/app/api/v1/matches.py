"""Public match and head-to-head reads."""

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import pagination
from app.db.session import get_db
from app.schemas.common import Paginated
from app.schemas.matches import Match
from app.schemas.rankings import HeadToHead
from app.services.match_service import get_match, list_matches
from app.services.ranking_service import get_head_to_head

router = APIRouter()

MatchStatusFilter = Literal["completed", "canceled", "disputed", "all"]


@router.get("/matches", response_model=Paginated[Match])
def matches(
    db: Session = Depends(get_db),
    pages: tuple[int, int] = Depends(pagination),
    player_id: UUID | None = None,
    status: MatchStatusFilter = "completed",
    tournament_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
) -> Paginated[Match]:
    page, page_size = pages
    return list_matches(
        db,
        page=page,
        page_size=page_size,
        player_id=player_id,
        status=status,
        tournament_id=tournament_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )


@router.get("/matches/{match_id}", response_model=Match)
def match_detail(match_id: UUID, db: Session = Depends(get_db)) -> Match:
    return get_match(db, match_id)


@router.get("/head-to-head/{player_a}/{player_b}", response_model=HeadToHead)
def head_to_head(
    player_a: UUID,
    player_b: UUID,
    db: Session = Depends(get_db),
) -> HeadToHead:
    return get_head_to_head(db, player_a, player_b)
