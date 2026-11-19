"""Tournaments, entrants, and single-elimination bracket slots."""

import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, TimestampMixin


class Tournament(Base, TimestampMixin):
    __tablename__ = "tournaments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'in_progress', 'completed', 'canceled')",
            name="status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="single_elimination",
        server_default="single_elimination",
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft", server_default="draft"
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class TournamentParticipant(Base, CreatedAtMixin):
    __tablename__ = "tournament_participants"
    __table_args__ = (UniqueConstraint("tournament_id", "player_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tournament_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tournaments.id"), nullable=False
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("players.id"), nullable=False, index=True
    )
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_position: Mapped[int | None] = mapped_column(Integer, nullable=True)


class BracketMatch(Base, TimestampMixin):
    __tablename__ = "bracket_matches"
    __table_args__ = (UniqueConstraint("tournament_id", "round", "position"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tournament_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tournaments.id"), nullable=False
    )
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    player_a_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("players.id"), nullable=True
    )
    player_b_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("players.id"), nullable=True
    )
    winner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("players.id"), nullable=True
    )
    match_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("matches.id"), nullable=True, unique=True
    )
    is_bye: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
