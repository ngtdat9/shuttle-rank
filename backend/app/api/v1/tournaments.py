"""Public tournament reads."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.tournaments import Bracket, TournamentDetail, TournamentListResponse
from app.services.tournament_service import get_bracket, get_tournament, list_tournaments

router = APIRouter()

TournamentStatus = Literal["draft", "in_progress", "completed", "canceled"]


@router.get("/tournaments", response_model=TournamentListResponse)
def tournaments(
    db: Session = Depends(get_db),
    status: TournamentStatus | None = None,
) -> TournamentListResponse:
    return list_tournaments(db, status=status)


@router.get("/tournaments/{tournament_id}", response_model=TournamentDetail)
def tournament_detail(tournament_id: UUID, db: Session = Depends(get_db)) -> TournamentDetail:
    return get_tournament(db, tournament_id)


@router.get("/tournaments/{tournament_id}/bracket", response_model=Bracket)
def tournament_bracket(tournament_id: UUID, db: Session = Depends(get_db)) -> Bracket:
    return get_bracket(db, tournament_id)
