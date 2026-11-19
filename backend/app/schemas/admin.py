"""Admin request bodies and responses that are not public schemas."""

from datetime import datetime
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.common import APISchema


def _trimmed_reason(value: str) -> str:
    text = value.strip()
    if not 1 <= len(text) <= 500:
        raise ValueError("Reason must be between 1 and 500 characters")
    return text


class PlayerCreateRequest(APISchema):
    display_name: str
    avatar_url: str | None = None

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str) -> str:
        name = value.strip()
        if not 1 <= len(name) <= 50:
            raise ValueError("Display name must be between 1 and 50 characters")
        return name


class PlayerUpdateRequest(APISchema):
    display_name: str | None = None
    avatar_url: str | None = None
    is_active: bool | None = None

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        if not 1 <= len(name) <= 50:
            raise ValueError("Display name must be between 1 and 50 characters")
        return name


class MatchCreateRequest(APISchema):
    player_a_id: UUID
    player_b_id: UUID
    winner_id: UUID
    match_date: datetime
    status: Literal["completed", "disputed"] = "completed"
    game_scores: list[tuple[int, int]] | None = None
    notes: str | None = None


class MatchUpdateRequest(APISchema):
    notes: str | None = None
    game_scores: list[tuple[int, int]] | None = None


class MatchCorrectRequest(APISchema):
    player_a_id: UUID | None = None
    player_b_id: UUID | None = None
    winner_id: UUID | None = None
    match_date: datetime | None = None
    status: Literal["completed", "disputed", "canceled"] | None = None
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return _trimmed_reason(value)

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        for name in ("player_a_id", "player_b_id", "winner_id", "match_date", "status"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class MatchCancelRequest(APISchema):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return _trimmed_reason(value)


class DeletedResponse(APISchema):
    id: UUID
    deleted: Literal[True]


class AdminStats(APISchema):
    players_total: int
    players_active: int
    matches_total: int
    matches_completed: int
    matches_canceled: int
    matches_disputed: int
    tournaments_total: int
    tournaments_in_progress: int
    achievements_awarded: int
    last_match_at: datetime | None


class AuditLogEntry(APISchema):
    id: UUID
    actor_id: str
    action: str
    entity_type: str
    entity_id: str | None
    before_data: dict[str, Any] | None
    after_data: dict[str, Any] | None
    created_at: datetime


class MonthlyRebuildResponse(APISchema):
    months_rebuilt: int
