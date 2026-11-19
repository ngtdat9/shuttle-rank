"""Shared timestamp columns. Values are UTC on insert and update."""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import UTCDateTime, utcnow


def _created_at_column() -> Mapped[datetime]:
    return mapped_column(
        UTCDateTime,
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )


class CreatedAtMixin:
    created_at: Mapped[datetime] = _created_at_column()


class TimestampMixin:
    created_at: Mapped[datetime] = _created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )
