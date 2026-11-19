"""Public achievement reads."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.achievements import AchievementListResponse
from app.services.achievement_service import list_achievements

router = APIRouter()


@router.get("/achievements", response_model=AchievementListResponse)
def achievements(
    db: Session = Depends(get_db),
    include_inactive: bool = False,
) -> AchievementListResponse:
    return list_achievements(db, include_inactive=include_inactive)
