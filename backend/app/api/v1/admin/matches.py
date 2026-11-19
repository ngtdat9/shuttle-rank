"""Admin match writes. Tournament results are recorded on the tournament routes."""

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import AdminPrincipal, get_actor_id, require_admin
from app.api.v1.deps import pagination
from app.db.session import get_db
from app.schemas.admin import (
    DeletedResponse,
    MatchCancelRequest,
    MatchCorrectRequest,
    MatchCreateRequest,
    MatchUpdateRequest,
)
from app.schemas.common import Paginated
from app.schemas.matches import Match
from app.services.match_service import (
    cancel_match,
    correct_match,
    create_match,
    delete_match,
    get_match,
    list_matches,
    update_match_metadata,
)

router = APIRouter()

MatchStatusFilter = Literal["completed", "canceled", "disputed", "all"]


def _scores(games: list[tuple[int, int]] | None) -> list[list[int]] | None:
    if games is None:
        return None
    return [list(game) for game in games]


@router.get("/matches", response_model=Paginated[Match])
def admin_matches(
    db: Session = Depends(get_db),
    pages: tuple[int, int] = Depends(pagination),
    player_id: UUID | None = None,
    status: MatchStatusFilter = "all",
    tournament_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    include_deleted: bool = False,
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
        include_deleted=include_deleted,
    )


@router.post("/matches", response_model=Match, status_code=status.HTTP_201_CREATED)
def admin_create_match(
    body: MatchCreateRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Match:
    match = create_match(
        db,
        player_a_id=body.player_a_id,
        player_b_id=body.player_b_id,
        winner_id=body.winner_id,
        match_date=body.match_date,
        status=body.status,
        game_scores=_scores(body.game_scores),
        notes=body.notes,
        created_by=get_actor_id(principal),
    )
    return get_match(db, match.id)


@router.patch("/matches/{match_id}", response_model=Match)
def admin_update_match(
    match_id: UUID,
    body: MatchUpdateRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Match:
    changes = body.model_dump(exclude_unset=True)
    if "game_scores" in changes:
        changes["game_scores"] = _scores(body.game_scores)
    update_match_metadata(db, match_id, actor=get_actor_id(principal), **changes)
    return get_match(db, match_id)


@router.post("/matches/{match_id}/correct", response_model=Match)
def admin_correct_match(
    match_id: UUID,
    body: MatchCorrectRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Match:
    changes = body.model_dump(exclude_unset=True)
    reason = changes.pop("reason")
    match = correct_match(db, match_id, reason=reason, actor=get_actor_id(principal), **changes)
    return get_match(db, match.id)


@router.post("/matches/{match_id}/cancel", response_model=Match)
def admin_cancel_match(
    match_id: UUID,
    body: MatchCancelRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Match:
    match = cancel_match(db, match_id, body.reason, get_actor_id(principal))
    return get_match(db, match.id)


@router.delete("/matches/{match_id}", response_model=DeletedResponse)
def admin_delete_match(
    match_id: UUID,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
    reason: str = Query(min_length=1, max_length=500),
) -> DeletedResponse:
    match = delete_match(db, match_id, reason, get_actor_id(principal))
    return DeletedResponse(id=match.id, deleted=True)
