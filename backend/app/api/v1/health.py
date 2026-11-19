"""Liveness probe. Confirms the process can run ``SELECT 1``."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse | JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check database probe failed")
        db.rollback()
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "error"},
        )
    return HealthResponse(status="ok", database="ok")
