"""Admin tournament writes. Results go through the tournament, not /admin/matches."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import AdminPrincipal, get_actor_id, require_admin
from app.db.session import get_db
from app.schemas.admin import (
    BracketGenerateRequest,
    ParticipantsAddRequest,
    TournamentCreateRequest,
    TournamentMatchRequest,
    TournamentUpdateRequest,
)
from app.schemas.tournaments import (
    Bracket,
    TournamentDetail,
    TournamentListResponse,
    TournamentMatchResult,
)
from app.services import tournament_service
from app.services.match_service import get_match

router = APIRouter()


@router.get("/tournaments", response_model=TournamentListResponse)
def admin_tournaments(db: Session = Depends(get_db)) -> TournamentListResponse:
    return tournament_service.list_tournaments(db)


@router.post("/tournaments", response_model=TournamentDetail, status_code=status.HTTP_201_CREATED)
def admin_create_tournament(
    body: TournamentCreateRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TournamentDetail:
    tournament = tournament_service.create_tournament(
        db,
        name=body.name,
        description=body.description,
        start_date=body.start_date,
        end_date=body.end_date,
        actor=get_actor_id(principal),
    )
    return tournament_service.get_tournament(db, tournament.id)


@router.patch("/tournaments/{tournament_id}", response_model=TournamentDetail)
def admin_update_tournament(
    tournament_id: UUID,
    body: TournamentUpdateRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TournamentDetail:
    changes = body.model_dump(exclude_unset=True)
    tournament_service.update_tournament(
        db, tournament_id, actor=get_actor_id(principal), **changes
    )
    return tournament_service.get_tournament(db, tournament_id)


@router.post("/tournaments/{tournament_id}/participants", response_model=TournamentDetail)
def admin_add_participants(
    tournament_id: UUID,
    body: ParticipantsAddRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TournamentDetail:
    tournament_service.add_participants(
        db,
        tournament_id,
        [(entry.player_id, entry.seed) for entry in body.participants],
        actor=get_actor_id(principal),
    )
    return tournament_service.get_tournament(db, tournament_id)


@router.delete(
    "/tournaments/{tournament_id}/participants/{player_id}", response_model=TournamentDetail
)
def admin_remove_participant(
    tournament_id: UUID,
    player_id: UUID,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TournamentDetail:
    tournament_service.remove_participant(
        db, tournament_id, player_id, actor=get_actor_id(principal)
    )
    return tournament_service.get_tournament(db, tournament_id)


@router.post("/tournaments/{tournament_id}/generate-bracket", response_model=Bracket)
def admin_generate_bracket(
    tournament_id: UUID,
    body: BracketGenerateRequest | None = None,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Bracket:
    seeding = "rating" if body is None else body.seeding
    tournament_service.generate_bracket(
        db, tournament_id, seeding=seeding, actor=get_actor_id(principal)
    )
    return tournament_service.get_bracket(db, tournament_id)


@router.post(
    "/tournaments/{tournament_id}/matches",
    response_model=TournamentMatchResult,
    status_code=status.HTTP_201_CREATED,
)
def admin_record_tournament_match(
    tournament_id: UUID,
    body: TournamentMatchRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> TournamentMatchResult:
    scores = None if body.game_scores is None else [list(game) for game in body.game_scores]
    match = tournament_service.record_match(
        db,
        tournament_id,
        bracket_match_id=body.bracket_match_id,
        winner_id=body.winner_id,
        match_date=body.match_date,
        game_scores=scores,
        notes=body.notes,
        actor=get_actor_id(principal),
    )
    return TournamentMatchResult(
        match=get_match(db, match.id),
        bracket=tournament_service.get_bracket(db, tournament_id),
    )
