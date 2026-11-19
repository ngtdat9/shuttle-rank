"""Admin achievement writes and award management."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import AdminPrincipal, get_actor_id, require_admin
from app.api.v1.deps import pagination
from app.db.session import get_db
from app.schemas.achievements import (
    Achievement,
    AchievementAward,
    AchievementListResponse,
    AdminAchievementAward,
)
from app.schemas.admin import (
    AchievementAwardRequest,
    AchievementCreateRequest,
    AchievementUpdateRequest,
    DeletedResponse,
)
from app.schemas.common import Paginated
from app.services import achievement_service

router = APIRouter()


@router.get("/achievements", response_model=AchievementListResponse)
def admin_achievements(db: Session = Depends(get_db)) -> AchievementListResponse:
    return achievement_service.list_achievements(db, include_inactive=True)


@router.post("/achievements", response_model=Achievement, status_code=status.HTTP_201_CREATED)
def admin_create_achievement(
    body: AchievementCreateRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Achievement:
    row = achievement_service.create_achievement(
        db, actor=get_actor_id(principal), **body.model_dump()
    )
    return achievement_service.get_achievement(db, row.id)


@router.patch("/achievements/{achievement_id}", response_model=Achievement)
def admin_update_achievement(
    achievement_id: UUID,
    body: AchievementUpdateRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Achievement:
    achievement_service.update_achievement(
        db, achievement_id, actor=get_actor_id(principal), **body.model_dump(exclude_unset=True)
    )
    return achievement_service.get_achievement(db, achievement_id)


@router.get("/player-achievements", response_model=Paginated[AdminAchievementAward])
def admin_awards(
    db: Session = Depends(get_db),
    pages: tuple[int, int] = Depends(pagination),
) -> Paginated[AdminAchievementAward]:
    page, page_size = pages
    return achievement_service.list_awards(db, page=page, page_size=page_size)


@router.post(
    "/players/{player_id}/achievements",
    response_model=AchievementAward,
    status_code=status.HTTP_201_CREATED,
)
def admin_award_achievement(
    player_id: UUID,
    body: AchievementAwardRequest,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AchievementAward:
    row = achievement_service.award_achievement(
        db,
        player_id=player_id,
        achievement_id=body.achievement_id,
        actor=get_actor_id(principal),
        notes=body.notes,
    )
    return achievement_service.get_award(db, row.id)


@router.delete("/player-achievements/{award_id}", response_model=DeletedResponse)
def admin_revoke_award(
    award_id: UUID,
    principal: AdminPrincipal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DeletedResponse:
    achievement_service.revoke_award(db, award_id, actor=get_actor_id(principal))
    return DeletedResponse(id=award_id, deleted=True)
