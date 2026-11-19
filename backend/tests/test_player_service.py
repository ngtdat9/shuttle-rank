"""Player service rules and audit rows."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError
from app.models.audit_log import AuditLog
from app.models.player import Player
from app.services.player_service import create_player, deactivate_player, update_player
from tests.factories import make_match, make_player


def test_create_trims_and_rejects_duplicate_names(db: Session) -> None:
    created = create_player(db, display_name="  Ada  ", actor="tester")
    assert created.display_name == "Ada"
    assert created.current_rating == 1500
    assert created.highest_rating == 1500
    with pytest.raises(ConflictError):
        create_player(db, display_name="ada", actor="tester")
    assert db.scalar(select(Player).where(Player.display_name == "ada")) is None
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "player.create")).one()
    assert audit.after_data["display_name"] == "Ada"
    assert audit.before_data is None


def test_name_length_is_enforced(db: Session) -> None:
    with pytest.raises(BusinessRuleError):
        create_player(db, display_name="   ", actor="tester")
    with pytest.raises(BusinessRuleError):
        create_player(db, display_name="A" * 51, actor="tester")


def test_update_and_deactivate_do_not_touch_ratings(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    make_match(db, ada, bob, winner=ada)
    updated = update_player(
        db,
        ada.id,
        actor="tester",
        display_name="Ada Lovelace",
        avatar_url="https://example.com/a.png",
    )
    assert updated.display_name == "Ada Lovelace"
    assert updated.current_rating == 1516
    deactivated = deactivate_player(db, ada.id, actor="tester")
    assert deactivated.is_active is False
    assert deactivated.current_rating == 1516
    assert deactivated.highest_rating == 1516
    reactivated = update_player(db, ada.id, actor="tester", is_active=True)
    assert reactivated.is_active is True
    actions = set(db.scalars(select(AuditLog.action).where(AuditLog.entity_type == "player")).all())
    assert {"player.create", "player.update", "player.deactivate"} <= actions
