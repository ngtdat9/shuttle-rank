"""Admin player writes. Ratings are not accepted on these bodies."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import AdminPrincipal, get_actor_id, require_admin
from app.db.session import get_db
from app.schemas.admin import PlayerCreateRequest, PlayerUpdateRequest
from app.schemas.players import PlayerListResponse, PlayerProfile
from app.services.player_service import (
    create_player,
    deactivate_player,
    get_player_profile,
    list_players,
    update_player,
)

router = APIRouter()


@router.get("/players", response_model=PlayerListResponse)
def admin_players(db: Session = Depends(get_db)) -> PlayerListResponse:
    return list_players(db, include_inactive=True)


@router.post("/players", response_model=PlayerProfile, status_code=status.HTTP_201_CREATED)
def admin_create_player(
    body: PlayerCreateRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PlayerProfile:
    player = create_player(
        db,
        display_name=body.display_name,
        avatar_url=body.avatar_url,
        actor=get_actor_id(principal),
    )
    return get_player_profile(db, player.id)


@router.patch("/players/{player_id}", response_model=PlayerProfile)
def admin_update_player(
    player_id: UUID,
    body: PlayerUpdateRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PlayerProfile:
    changes = body.model_dump(exclude_unset=True)
    update_player(db, player_id, actor=get_actor_id(principal), **changes)
    return get_player_profile(db, player_id)


@router.delete("/players/{player_id}", response_model=PlayerProfile)
def admin_deactivate_player(
    player_id: UUID,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PlayerProfile:
    deactivate_player(db, player_id, actor=get_actor_id(principal))
    return get_player_profile(db, player_id)
