"""Singles matches. Only rows with status ``completed`` and no ``deleted_at`` affect ratings."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime
from app.models.mixins import TimestampMixin


class Match(Base, TimestampMixin):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint("player_a_id != player_b_id", name="player_a_ne_player_b"),
        CheckConstraint(
            "winner_id IN (player_a_id, player_b_id)",
            name="winner_is_participant",
        ),
        CheckConstraint(
            "status IN ('completed', 'canceled', 'disputed')",
            name="status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_a_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("players.id"), nullable=False, index=True
    )
    player_b_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("players.id"), nullable=False, index=True
    )
    winner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("players.id"), nullable=False
    )
    match_date: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="completed", server_default="completed"
    )
    tournament_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tournaments.id"), nullable=True, index=True
    )
    game_scores: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    # Soft-deleted matches are hidden publicly and never affect ratings.
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
