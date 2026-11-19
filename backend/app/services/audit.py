"""Audit log writes. Callers commit; this helper only adds a row."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.services.ordering import ensure_utc


def to_jsonable(value: Any) -> Any:
    """Convert UUIDs and datetimes so audit JSON is portable."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return ensure_utc(value).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def write_audit(
    db: Session,
    *,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | str | None,
    before_data: dict[str, Any] | None,
    after_data: dict[str, Any] | None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=None if entity_id is None else str(entity_id),
            before_data=None if before_data is None else to_jsonable(before_data),
            after_data=None if after_data is None else to_jsonable(after_data),
        )
    )
