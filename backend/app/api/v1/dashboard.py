"""GET /dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import Dashboard
from app.services.ranking_service import get_dashboard

router = APIRouter()


@router.get("/dashboard", response_model=Dashboard)
def dashboard(db: Session = Depends(get_db)) -> Dashboard:
    return get_dashboard(db)
