"""Shared match ordering. Rated matches sort by (match_date, created_at, id)."""

import uuid
from datetime import UTC, datetime

from app.models.match import Match


def ensure_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC and convert aware ones to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def match_sort_key(match: Match) -> tuple[datetime, datetime, uuid.UUID]:
    """Chronological processing key from decision D-014."""
    return (ensure_utc(match.match_date), ensure_utc(match.created_at), match.id)


def is_rated(match: Match) -> bool:
    """Completed matches that have not been soft-deleted affect ratings."""
    return match.status == "completed" and match.deleted_at is None
