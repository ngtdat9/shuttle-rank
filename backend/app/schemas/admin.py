"""Admin request bodies and responses that are not public schemas."""

from datetime import date, datetime
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
    notes: str | None = Field(default=None, max_length=500)


class MatchUpdateRequest(APISchema):
    notes: str | None = Field(default=None, max_length=500)
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


def _trimmed(value: str, low: int, high: int, label: str) -> str:
    text = value.strip()
    if not low <= len(text) <= high:
        raise ValueError(f"{label} must be between {low} and {high} characters")
    return text


class TournamentCreateRequest(APISchema):
    name: str
    description: str | None = Field(default=None, max_length=2000)
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        return _trimmed(value, 1, 100, "Name")


class TournamentUpdateRequest(APISchema):
    name: str | None = None
    description: str | None = Field(default=None, max_length=2000)
    start_date: date | None = None
    end_date: date | None = None
    status: Literal["canceled"] | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        return None if value is None else _trimmed(value, 1, 100, "Name")

    @model_validator(mode="after")
    def reject_null_name_or_status(self) -> Self:
        for name in ("name", "status"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class ParticipantInput(APISchema):
    player_id: UUID
    seed: int | None = Field(default=None, ge=1, le=1024)


class ParticipantsAddRequest(APISchema):
    participants: list[ParticipantInput] = Field(min_length=1, max_length=256)


class BracketGenerateRequest(APISchema):
    seeding: Literal["rating", "manual"] = "rating"


class TournamentMatchRequest(APISchema):
    bracket_match_id: UUID
    winner_id: UUID
    match_date: datetime
    game_scores: list[tuple[int, int]] | None = None
    notes: str | None = Field(default=None, max_length=500)


class AchievementCreateRequest(APISchema):
    name: str
    description: str
    icon: str = Field(default="award", min_length=1, max_length=64)
    criteria_type: str = Field(default="manual", min_length=1, max_length=64)
    criteria_value: int | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        return _trimmed(value, 1, 80, "Name")

    @field_validator("description")
    @classmethod
    def trim_description(cls, value: str) -> str:
        return _trimmed(value, 1, 300, "Description")


class AchievementUpdateRequest(APISchema):
    name: str | None = None
    description: str | None = None
    icon: str | None = Field(default=None, min_length=1, max_length=64)
    criteria_type: str | None = Field(default=None, min_length=1, max_length=64)
    criteria_value: int | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        return None if value is None else _trimmed(value, 1, 80, "Name")

    @field_validator("description")
    @classmethod
    def trim_description(cls, value: str | None) -> str | None:
        return None if value is None else _trimmed(value, 1, 300, "Description")

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> Self:
        for name in ("name", "description", "icon", "criteria_type", "is_active"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class AchievementAwardRequest(APISchema):
    achievement_id: UUID
    notes: str | None = Field(default=None, max_length=500)
