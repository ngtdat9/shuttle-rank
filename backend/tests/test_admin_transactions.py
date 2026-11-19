"""Inner match writes share one transaction, and tournament results stop at the hook."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError
from app.models.match import Match
from app.models.player import Player
from app.services.match_service import (
    _create_match,
    correct_match,
    get_rating_history,
)
from app.services.player_service import _create_player as create_player_inner
from app.services.player_service import create_player
from app.services.transactions import transaction
from tests.factories import make_match, make_player, make_tournament


def test_inner_writes_flush_without_committing(db: Session) -> None:
    player = create_player_inner(db, display_name="Ada", actor="tester")
    player_id = player.id
    db.rollback()
    assert db.get(Player, player_id) is None

    ada = create_player(db, display_name="Ada", actor="tester")
    bob = create_player(db, display_name="Bob", actor="tester")
    with pytest.raises(RuntimeError, match="stop"):
        with transaction(db):
            _create_match(
                db,
                player_a_id=ada.id,
                player_b_id=bob.id,
                winner_id=ada.id,
                match_date=datetime(2026, 10, 1, tzinfo=UTC),
                created_by="tester",
            )
            raise RuntimeError("stop")
    assert db.scalar(select(func.count()).select_from(Match)) == 0


def test_backdated_match_replays_inside_the_callers_transaction(db: Session) -> None:
    ada = create_player(db, display_name="Ada", actor="tester")
    bob = create_player(db, display_name="Bob", actor="tester")
    with transaction(db):
        _create_match(
            db,
            player_a_id=ada.id,
            player_b_id=bob.id,
            winner_id=ada.id,
            match_date=datetime(2026, 11, 1, tzinfo=UTC),
            created_by="tester",
        )
        _create_match(
            db,
            player_a_id=ada.id,
            player_b_id=bob.id,
            winner_id=bob.id,
            match_date=datetime(2026, 10, 1, tzinfo=UTC),
            created_by="tester",
        )
    history = get_rating_history(db, ada.id)
    assert len(history.points) == 2
    assert history.points[0].old_rating == 1500
    assert history.points[0].result == "L"
    assert history.points[1].old_rating == history.points[0].new_rating
    assert history.points[1].result == "W"


def test_tournament_result_changes_roll_back(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    cara = make_player(db, "Cara")
    city = make_tournament(db, "City Open", status="in_progress")
    match = make_match(db, ada, bob, winner=ada, tournament_id=city.id)
    rating = ada.current_rating

    with pytest.raises(BusinessRuleError, match="cannot be changed"):
        correct_match(db, match.id, reason="swap the draw", actor="tester", player_a_id=cara.id)

    db.expire_all()
    reloaded = db.get(Match, match.id)
    assert reloaded is not None
    assert reloaded.winner_id == ada.id
    assert reloaded.player_a_id == ada.id
    assert reloaded.status == "completed"
    assert reloaded.deleted_at is None
    reloaded_player = db.get(Player, ada.id)
    assert reloaded_player is not None
    assert reloaded_player.current_rating == rating
