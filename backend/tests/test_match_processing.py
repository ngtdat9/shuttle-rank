"""Match processing, replay, and the rules that protect ratings."""

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models.audit_log import AuditLog
from app.models.match import Match
from app.models.player import Player
from app.models.rating_history import RatingHistory
from app.services.elo import apply_result
from app.services.match_service import (
    cancel_match,
    correct_match,
    create_match,
    delete_match,
    update_match_metadata,
)
from app.services.ordering import match_sort_key
from app.services.player_service import deactivate_player
from app.services.rating_service import apply_match_rating, recalculate_all
from tests.factories import make_match, make_player


def _reload_players(db: Session) -> dict[str, Player]:
    db.expire_all()
    return {player.display_name: player for player in db.scalars(select(Player)).all()}


def _history(db: Session) -> list[tuple[uuid.UUID, uuid.UUID, int, int, int]]:
    db.expire_all()
    rows = []
    for history, match in db.execute(
        select(RatingHistory, Match).join(Match, RatingHistory.match_id == Match.id)
    ).all():
        rows.append(
            (
                match.id,
                history.player_id,
                history.old_rating,
                history.new_rating,
                history.rating_change,
            )
        )
    return sorted(rows, key=lambda row: (row[0].hex, row[1].hex))


def _ratings(db: Session) -> dict[str, tuple[int, int]]:
    players = _reload_players(db)
    return {
        name: (player.current_rating, player.highest_rating) for name, player in players.items()
    }


def test_equal_ratings_are_persisted(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    match = make_match(db, ada, bob, winner=ada)

    players = _reload_players(db)
    assert players["Ada"].current_rating == 1516
    assert players["Bob"].current_rating == 1484
    assert players["Ada"].highest_rating == 1516
    assert players["Bob"].highest_rating == 1500

    history = list(
        db.scalars(select(RatingHistory).where(RatingHistory.match_id == match.id)).all()
    )
    assert len(history) == 2
    by_player = {row.player_id: row for row in history}
    assert by_player[ada.id].old_rating == 1500
    assert by_player[ada.id].new_rating == 1516
    assert by_player[ada.id].rating_change == 16
    assert by_player[bob.id].rating_change == -16
    assert sum(row.rating_change for row in history) == 0

    audit = db.scalars(select(AuditLog).where(AuditLog.action == "match.create")).one()
    assert audit.entity_id == str(match.id)
    assert audit.before_data is None
    assert audit.after_data["winner_id"] == str(ada.id)


def test_many_matches_stay_zero_sum(db: Session) -> None:
    names = ["Ada", "Bob", "Cara", "Dee"]
    players = [make_player(db, name) for name in names]
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    for index in range(12):
        left = players[index % 4]
        right = players[(index + 1) % 4]
        winner = left if index % 2 == 0 else right
        make_match(db, left, right, winner=winner, match_date=moment + timedelta(days=index))

    ratings = _reload_players(db)
    assert sum(player.current_rating for player in ratings.values()) == 1500 * 4


def test_highest_rating_tracks_the_peak(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    first = datetime(2026, 2, 1, tzinfo=UTC)
    make_match(db, ada, bob, winner=ada, match_date=first)
    second_result = apply_result(1516, 1484)
    make_match(db, ada, bob, winner=ada, match_date=first + timedelta(days=1))
    peak = 1516 + second_result.delta
    players = _reload_players(db)
    assert players["Ada"].current_rating == peak
    assert players["Ada"].highest_rating == peak

    make_match(db, ada, bob, winner=bob, match_date=first + timedelta(days=2))
    players = _reload_players(db)
    assert players["Ada"].current_rating < peak
    assert players["Ada"].highest_rating == peak


def test_canceled_and_disputed_matches_write_no_history(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    make_match(db, ada, bob, status="canceled")
    make_match(db, ada, bob, status="disputed")
    assert db.scalar(select(func.count()).select_from(RatingHistory)) == 0
    players = _reload_players(db)
    assert players["Ada"].current_rating == 1500
    assert players["Bob"].highest_rating == 1500


@pytest.mark.parametrize(
    ("builder", "message"),
    [
        ("self", "themselves"),
        ("winner", "participant"),
        ("unknown", "Unknown"),
        ("inactive", "Inactive"),
        ("future", "future"),
        ("status", "status"),
        ("scores", "Game scores"),
    ],
)
def test_create_match_rejects_invalid_input(db: Session, builder: str, message: str) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    cara = make_player(db, "Cara")
    deactivate_player(db, cara.id, actor="tester")
    kwargs = {
        "player_a_id": ada.id,
        "player_b_id": bob.id,
        "winner_id": ada.id,
        "match_date": datetime.now(UTC) - timedelta(hours=1),
        "created_by": "tester",
    }
    if builder == "self":
        kwargs["player_b_id"] = ada.id
        kwargs["winner_id"] = ada.id
    elif builder == "winner":
        kwargs["winner_id"] = cara.id
    elif builder == "unknown":
        kwargs["player_b_id"] = uuid.uuid4()
    elif builder == "inactive":
        kwargs["player_b_id"] = cara.id
    elif builder == "future":
        kwargs["match_date"] = datetime.now(UTC) + timedelta(days=2)
    elif builder == "status":
        kwargs["status"] = "postponed"
    else:
        kwargs["game_scores"] = [[21, -1]]

    with pytest.raises(BusinessRuleError, match=message):
        create_match(db, **kwargs)
    assert db.scalar(select(func.count()).select_from(Match)) == 0


def test_game_score_shape_is_rejected(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    base = {
        "player_a_id": ada.id,
        "player_b_id": bob.id,
        "winner_id": ada.id,
        "match_date": datetime.now(UTC) - timedelta(hours=1),
        "created_by": "tester",
    }
    for scores in ([], [[21, 18]] * 6, [[21]], [[True, 1]], [[1.5, 2]]):
        with pytest.raises(BusinessRuleError):
            create_match(db, game_scores=scores, **base)
    assert db.scalar(select(func.count()).select_from(Match)) == 0


def test_duplicate_processing_changes_nothing(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    match = make_match(db, ada, bob, winner=ada)
    before_ratings = _ratings(db)
    before_history = _history(db)

    with pytest.raises(ConflictError):
        apply_match_rating(db, match)

    assert _ratings(db) == before_ratings
    assert _history(db) == before_history


def test_failure_mid_transaction_rolls_back(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")

    def explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("snapshot failed")

    monkeypatch.setattr("app.services.match_service.rebuild_monthly_snapshots", explode)
    with pytest.raises(RuntimeError, match="snapshot failed"):
        make_match(db, ada, bob, winner=ada)

    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Match)) == 0
    assert db.scalar(select(func.count()).select_from(RatingHistory)) == 0
    assert (
        db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.entity_type == "match"))
        == 0
    )
    players = _reload_players(db)
    assert players["Ada"].current_rating == 1500
    assert players["Bob"].highest_rating == 1500


def _simulate(
    matches: list[Match],
) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, int], set[tuple]]:
    ratings: dict[uuid.UUID, int] = defaultdict(lambda: 1500)
    highest: dict[uuid.UUID, int] = defaultdict(lambda: 1500)
    history: set[tuple] = set()
    for match in sorted(matches, key=match_sort_key):
        if match.status != "completed" or match.deleted_at is not None:
            continue
        old_a = ratings[match.player_a_id]
        old_b = ratings[match.player_b_id]
        if match.winner_id == match.player_a_id:
            result = apply_result(old_a, old_b)
            new_a, new_b = result.winner_new, result.loser_new
            change_a, change_b = result.delta, -result.delta
        else:
            result = apply_result(old_b, old_a)
            new_b, new_a = result.winner_new, result.loser_new
            change_b, change_a = result.delta, -result.delta
        ratings[match.player_a_id] = new_a
        ratings[match.player_b_id] = new_b
        highest[match.player_a_id] = max(highest[match.player_a_id], new_a)
        highest[match.player_b_id] = max(highest[match.player_b_id], new_b)
        history.add((match.id, match.player_a_id, old_a, new_a, change_a))
        history.add((match.id, match.player_b_id, old_b, new_b, change_b))
    return ratings, highest, history


def _assert_matches_simulation(db: Session, matches: list[Match]) -> None:
    ratings, highest, history = _simulate(matches)
    stored = _reload_players(db)
    for match in matches:
        for player_id in (match.player_a_id, match.player_b_id):
            player = next(row for row in stored.values() if row.id == player_id)
            assert player.current_rating == ratings[player_id]
            assert player.highest_rating == highest[player_id]
    assert set(_history(db)) == history


def test_backdated_insert_replays_later_matches(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    later = make_match(db, ada, bob, winner=ada, match_date=datetime(2026, 3, 3, tzinfo=UTC))
    earlier = make_match(db, ada, bob, winner=bob, match_date=datetime(2026, 3, 1, tzinfo=UTC))
    _assert_matches_simulation(db, [later, earlier])
    players = _reload_players(db)
    # The March 3 match is no longer a 1500-vs-1500 result.
    assert players["Ada"].current_rating != 1516


def test_correcting_an_old_winner_matches_full_recalculation(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    cara = make_player(db, "Cara")
    day = datetime(2026, 4, 1, tzinfo=UTC)
    first = make_match(db, ada, bob, winner=ada, match_date=day)
    second = make_match(db, bob, cara, winner=bob, match_date=day + timedelta(days=1))
    third = make_match(db, cara, ada, winner=cara, match_date=day + timedelta(days=2))
    corrected = correct_match(
        db,
        first.id,
        reason="wrong winner",
        actor="tester",
        winner_id=bob.id,
    )
    assert corrected.winner_id == bob.id
    matches = [first, second, third]
    for match in matches:
        db.refresh(match)
    _assert_matches_simulation(db, matches)

    before_players = _ratings(db)
    before_history = _history(db)
    recalculate_all(db)
    assert _ratings(db) == before_players
    assert _history(db) == before_history

    audit = db.scalars(select(AuditLog).where(AuditLog.action == "match.correct")).one()
    assert audit.before_data["winner_id"] == str(ada.id)
    assert audit.after_data["winner_id"] == str(bob.id)
    assert audit.after_data["reason"] == "wrong winner"


def test_cancel_and_delete_restore_ratings(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    match = make_match(db, ada, bob, winner=ada, match_date=datetime(2026, 5, 1, tzinfo=UTC))
    cancel_match(db, match.id, "rain", "tester")
    players = _reload_players(db)
    assert players["Ada"].current_rating == 1500
    assert players["Bob"].current_rating == 1500
    assert players["Ada"].highest_rating == 1500
    assert db.scalar(select(func.count()).select_from(RatingHistory)) == 0
    assert (
        db.scalar(select(AuditLog).where(AuditLog.action == "match.cancel")).action
        == "match.cancel"
    )

    rematch = make_match(db, ada, bob, winner=ada, match_date=datetime(2026, 5, 2, tzinfo=UTC))
    deleted = delete_match(db, rematch.id, "entered twice", "tester")
    assert deleted.deleted_at is not None
    players = _reload_players(db)
    assert players["Ada"].current_rating == 1500
    assert players["Bob"].highest_rating == 1500
    assert db.scalar(select(func.count()).select_from(RatingHistory)) == 0
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "match.delete")).one()
    assert audit.after_data["deleted"] is True


def test_deleting_the_earlier_match_replays_the_later_one(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    day = datetime(2026, 6, 1, tzinfo=UTC)
    first = make_match(db, ada, bob, winner=ada, match_date=day)
    second = make_match(db, ada, bob, winner=ada, match_date=day + timedelta(days=1))
    delete_match(db, first.id, "void", "tester")
    db.refresh(second)
    _assert_matches_simulation(db, [second])
    players = _reload_players(db)
    assert players["Ada"].current_rating == 1516
    assert players["Bob"].current_rating == 1484


def test_metadata_update_does_not_change_ratings(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    match = make_match(db, ada, bob, winner=ada)
    before = _ratings(db)
    update_match_metadata(
        db,
        match.id,
        actor="tester",
        notes="close third game",
        game_scores=[[21, 18], [19, 21], [21, 15]],
    )
    assert _ratings(db) == before
    db.refresh(match)
    assert match.notes == "close third game"
    assert match.game_scores == [[21, 18], [19, 21], [21, 15]]
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "match.update")).one()
    assert audit.after_data["notes"] == "close third game"


def test_deleted_match_cannot_be_corrected(db: Session) -> None:
    ada = make_player(db, "Ada")
    bob = make_player(db, "Bob")
    match = make_match(db, ada, bob)
    delete_match(db, match.id, "void", "tester")
    with pytest.raises(NotFoundError):
        correct_match(db, match.id, reason="too late", actor="tester", winner_id=bob.id)
