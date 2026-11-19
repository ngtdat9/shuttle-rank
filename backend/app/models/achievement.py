"""Achievement definitions and one award per player."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime
from app.models.mixins import TimestampMixin


class Achievement(Base, TimestampMixin):
    __tablename__ = "achievements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str] = mapped_column(
        String(64), nullable=False, default="award", server_default="award"
    )
    criteria_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default="manual", server_default="manual"
    )
    criteria_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class PlayerAchievement(Base):
    __tablename__ = "player_achievements"
    __table_args__ = (UniqueConstraint("player_id", "achievement_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("players.id"), nullable=False
    )
    achievement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("achievements.id"), nullable=False
    )
    awarded_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    awarded_by: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
