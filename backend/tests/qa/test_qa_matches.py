"""Match validation and the rule that a match is rated at most once."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError
from app.models.match import Match
from app.models.player import Player
from app.models.rating_history import RatingHistory
from app.services.match_service import create_match
from app.services.player_service import deactivate_player
from app.services.rating_service import apply_match_rating
from tests.factories import make_player

ACTOR = "qa"


def _ratings(db: Session) -> dict[uuid.UUID, tuple[int, int]]:
    db.expire_all()
    players = db.scalars(select(Player)).all()
    return {player.id: (player.current_rating, player.highest_rating) for player in players}


def _match_count(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(Match)) or 0)


def _history_count(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(RatingHistory)) or 0)


def _reject(call) -> None:
    with pytest.raises(BusinessRuleError) as caught:
        call()
    assert caught.value.status_code == 422
    assert caught.value.code == "business_rule_violation"


def test_valid_match_is_stored_and_rated(db: Session) -> None:
    ann = make_player(db, "Valid Ann")
    bob = make_player(db, "Valid Bob")
    played_at = datetime(2026, 5, 1, 15, 30, tzinfo=UTC)
    match = create_match(
        db,
        player_a_id=ann.id,
        player_b_id=bob.id,
        winner_id=bob.id,
        match_date=played_at,
        game_scores=[[19, 21], [21, 18], [18, 21]],
        notes="club night",
        created_by=ACTOR,
    )
    db.expire_all()
    stored = db.get(Match, match.id)
    ann = db.get(Player, ann.id)
    bob = db.get(Player, bob.id)
    assert stored is not None and ann is not None and bob is not None
    assert stored.status == "completed"
    assert stored.winner_id == bob.id
    assert stored.player_a_id == ann.id
    assert stored.game_scores == [[19, 21], [21, 18], [18, 21]]
    assert stored.notes == "club night"
    assert stored.deleted_at is None
    assert bob.current_rating == 1516
    assert ann.current_rating == 1484
    assert _history_count(db) == 2


def test_self_match_is_rejected(db: Session) -> None:
    ann = make_player(db, "Self Ann")
    before = _ratings(db)

    def create() -> None:
        create_match(
            db,
            player_a_id=ann.id,
            player_b_id=ann.id,
            winner_id=ann.id,
            match_date=datetime(2026, 5, 2, tzinfo=UTC),
            created_by=ACTOR,
        )

    _reject(create)
    assert _ratings(db) == before
    assert _match_count(db) == 0
    assert _history_count(db) == 0


def test_winner_who_is_not_a_participant_is_rejected(db: Session) -> None:
    ann = make_player(db, "Pair Ann")
    bob = make_player(db, "Pair Bob")
    outsider = make_player(db, "Outsider")
    before = _ratings(db)

    def create() -> None:
        create_match(
            db,
            player_a_id=ann.id,
            player_b_id=bob.id,
            winner_id=outsider.id,
            match_date=datetime(2026, 5, 3, tzinfo=UTC),
            created_by=ACTOR,
        )

    _reject(create)
    assert _ratings(db) == before
    assert _match_count(db) == 0


def test_unknown_player_is_rejected(db: Session) -> None:
    ann = make_player(db, "Known Ann")
    before = _ratings(db)

    def create() -> None:
        create_match(
            db,
            player_a_id=ann.id,
            player_b_id=uuid.uuid4(),
            winner_id=ann.id,
            match_date=datetime(2026, 5, 4, tzinfo=UTC),
            created_by=ACTOR,
        )

    _reject(create)
    assert _ratings(db) == before
    assert _match_count(db) == 0
    assert _history_count(db) == 0


def test_inactive_player_is_rejected(db: Session) -> None:
    ann = make_player(db, "Active Ann")
    bob = make_player(db, "Inactive Bob")
    deactivate_player(db, bob.id, actor=ACTOR)
    before = _ratings(db)

    def create() -> None:
        create_match(
            db,
            player_a_id=ann.id,
            player_b_id=bob.id,
            winner_id=ann.id,
            match_date=datetime(2026, 5, 5, tzinfo=UTC),
            created_by=ACTOR,
        )

    _reject(create)
    assert _ratings(db) == before
    assert _match_count(db) == 0


def test_match_more_than_one_day_in_the_future_is_rejected(db: Session) -> None:
    ann = make_player(db, "Future Ann")
    bob = make_player(db, "Future Bob")
    before = _ratings(db)
    too_late = datetime.now(UTC) + timedelta(days=1, minutes=5)

    def create() -> None:
        create_match(
            db,
            player_a_id=ann.id,
            player_b_id=bob.id,
            winner_id=ann.id,
            match_date=too_late,
            created_by=ACTOR,
        )

    _reject(create)
    assert _ratings(db) == before
    assert _match_count(db) == 0

    allowed = datetime.now(UTC) + timedelta(hours=23)
    create_match(
        db,
        player_a_id=ann.id,
        player_b_id=bob.id,
        winner_id=ann.id,
        match_date=allowed,
        created_by=ACTOR,
    )
    assert _match_count(db) == 1


@pytest.mark.parametrize(
    "scores",
    [
        [[21, 19]] * 6,
        [[-1, 21]],
        pytest.param(
            [[21, 100]],
            marks=pytest.mark.xfail(
                reason="BUG-P2-03-01: game score >99 accepted (R-MA-02 says 0-99)", strict=True
            ),
        ),
        pytest.param(
            [[100, 0]],
            marks=pytest.mark.xfail(
                reason="BUG-P2-03-01: game score >99 accepted (R-MA-02 says 0-99)", strict=True
            ),
        ),
        [[21]],
        [[21, 19, 3]],
        [[21, True]],
        "21-19",
        [[21, 19.5]],
    ],
)
def test_invalid_game_scores_are_rejected(db: Session, scores: object) -> None:
    ann = make_player(db, f"Score Ann {scores!r}"[:50])
    bob = make_player(db, f"Score Bob {scores!r}"[:50])
    before = _ratings(db)

    def create() -> None:
        create_match(
            db,
            player_a_id=ann.id,
            player_b_id=bob.id,
            winner_id=ann.id,
            match_date=datetime(2026, 5, 6, tzinfo=UTC),
            game_scores=scores,  # type: ignore[arg-type]
            created_by=ACTOR,
        )

    _reject(create)
    assert _ratings(db) == before
    assert _match_count(db) == 0


@pytest.mark.xfail(
    reason="BUG-P2-03-02: create_match accepts notes over 500 chars (R-MA-02)", strict=True
)
def test_notes_longer_than_500_characters_are_rejected(db: Session) -> None:
    ann = make_player(db, "Notes Ann")
    bob = make_player(db, "Notes Bob")

    def create() -> None:
        create_match(
            db,
            player_a_id=ann.id,
            player_b_id=bob.id,
            winner_id=ann.id,
            match_date=datetime(2026, 5, 7, tzinfo=UTC),
            notes="n" * 501,
            created_by=ACTOR,
        )

    _reject(create)
    assert _match_count(db) == 0


@pytest.mark.parametrize("status", ["canceled", "disputed"])
def test_canceled_and_disputed_matches_do_not_change_ratings(db: Session, status: str) -> None:
    ann = make_player(db, f"{status.title()} Ann")
    bob = make_player(db, f"{status.title()} Bob")
    before = _ratings(db)
    match = create_match(
        db,
        player_a_id=ann.id,
        player_b_id=bob.id,
        winner_id=ann.id,
        match_date=datetime(2026, 5, 8, tzinfo=UTC),
        status=status,
        created_by=ACTOR,
    )
    db.expire_all()
    stored = db.get(Match, match.id)
    assert stored is not None
    assert stored.status == status
    assert _ratings(db) == before
    assert _history_count(db) == 0
    assert all(rating == (1500, 1500) for rating in before.values())


def test_apply_match_rating_twice_conflicts_and_leaves_state_unchanged(db: Session) -> None:
    ann = make_player(db, "Once Ann")
    bob = make_player(db, "Once Bob")
    match = Match(
        player_a_id=ann.id,
        player_b_id=bob.id,
        winner_id=ann.id,
        match_date=datetime(2026, 5, 9, 12, tzinfo=UTC),
        status="completed",
        created_by=ACTOR,
    )
    db.add(match)
    db.commit()
    apply_match_rating(db, match)
    db.commit()
    db.expire_all()
    before_players = _ratings(db)
    before_rows = [
        (row.player_id, row.old_rating, row.new_rating, row.rating_change)
        for row in db.scalars(select(RatingHistory).where(RatingHistory.match_id == match.id))
    ]
    assert before_players[ann.id] == (1516, 1516)
    assert before_players[bob.id] == (1484, 1500)
    assert len(before_rows) == 2

    with pytest.raises(ConflictError) as caught:
        apply_match_rating(db, match)
    assert caught.value.status_code == 409
    assert caught.value.code == "conflict"
    db.rollback()

    assert _ratings(db) == before_players
    after_rows = [
        (row.player_id, row.old_rating, row.new_rating, row.rating_change)
        for row in db.scalars(select(RatingHistory).where(RatingHistory.match_id == match.id))
    ]
    assert after_rows == before_rows
    assert sum(change for _, _, _, change in after_rows) == 0
