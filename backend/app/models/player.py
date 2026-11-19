"""Club players. Ratings change only through match processing, never by hand."""

import uuid

from sqlalchemy import Boolean, Integer, String, Uuid, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Player(Base, TimestampMixin):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    current_rating: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1500, server_default="1500"
    )
    highest_rating: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1500, server_default="1500"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
