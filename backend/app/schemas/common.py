"""Schemas shared by public responses."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

FormResult = Literal["W", "L"]


class APISchema(BaseModel):
    """Response models reject unexpected constructor fields."""

    model_config = ConfigDict(extra="forbid")


class PlayerSummary(APISchema):
    id: UUID
    display_name: str
    avatar_url: str | None
    current_rating: int
    is_active: bool


class Streak(APISchema):
    type: FormResult
    count: int


class PlayerStats(APISchema):
    matches_played: int
    wins: int
    losses: int
    win_rate: float | None
    current_streak: Streak | None
    recent_form: list[FormResult]
    last_rating_change: int | None
    rating_change_30d: int


class RatingChange(APISchema):
    player_id: UUID
    old_rating: int
    new_rating: int
    rating_change: int


class Paginated[T](APISchema):
    items: list[T]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
