"""Corrections, cancels, and deletes replay to the same result as a full recalculation."""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.player import Player
from app.models.rating_history import RatingHistory
from app.services.match_service import cancel_match, correct_match, delete_match
from app.services.rating_service import recalculate_all
from tests.factories import make_match, make_player
from tests.qa.reference import STARTING_RATING, is_rated, match_key, replay

ACTOR = "qa"
REASON = "qa correction"


def assert_matches_independent_replay(db: Session, label: str) -> None:
    """Compare stored ratings and history with a from-scratch replay, then recalculate_all."""
    db.expire_all()
    players = list(db.scalars(select(Player)).all())
    matches = list(db.scalars(select(Match)).all())
    histories = list(db.scalars(select(RatingHistory)).all())
    expected = replay(players, matches)
    expected_rows = {
        (match_id, player_id): (old, new, change)
        for match_id, player_id, old, new, change in expected["rows"]  # type: ignore[union-attr]
    }
    matches_by_id = {match.id: match for match in matches}
    actual_rows = {
        (row.match_id, row.player_id): (row.old_rating, row.new_rating, row.rating_change)
        for row in histories
    }
    actual_current = {player.id: player.current_rating for player in players}
    actual_highest = {player.id: player.highest_rating for player in players}
    assert actual_current == expected["current"], label
    assert actual_highest == expected["highest"], label
    assert actual_rows == expected_rows, label
    assert sum(actual_current.values()) == STARTING_RATING * len(players), label

    rated_ids = {match.id for match in matches if is_rated(match)}
    history_matches = {match_id for match_id, _player_id in actual_rows}
    assert history_matches == rated_ids, label
    for player in players:
        chain = [row for row in histories if row.player_id == player.id]
        chain.sort(key=lambda row: match_key(matches_by_id[row.match_id]))
        previous = None
        news: list[int] = []
        for row in chain:
            assert row.new_rating == row.old_rating + row.rating_change, label
            assert row.old_rating == (STARTING_RATING if previous is None else previous), label
            previous = row.new_rating
            news.append(row.new_rating)
        assert player.highest_rating == max([STARTING_RATING, *news]), label
        if chain:
            assert player.current_rating == chain[-1].new_rating, label
        else:
            assert player.current_rating == STARTING_RATING, label

    recalculate_all(db)
    db.expire_all()
    players = list(db.scalars(select(Player)).all())
    histories = list(db.scalars(select(RatingHistory)).all())
    rebuilt_current = {player.id: player.current_rating for player in players}
    rebuilt_highest = {player.id: player.highest_rating for player in players}
    rebuilt_rows = {
        (row.match_id, row.player_id): (row.old_rating, row.new_rating, row.rating_change)
        for row in histories
    }
    assert rebuilt_current == expected["current"], f"{label} after recalculate_all"
    assert rebuilt_highest == expected["highest"], f"{label} after recalculate_all"
    assert rebuilt_rows == expected_rows, f"{label} after recalculate_all"


def _change(db: Session, match_id: object, player_id: object) -> int:
    row = db.scalar(
        select(RatingHistory).where(
            RatingHistory.match_id == match_id,
            RatingHistory.player_id == player_id,
        )
    )
    assert row is not None
    return row.rating_change


def test_documented_correction_replays_the_later_match(db: Session) -> None:
    """January 2 A beats B, January 3 A beats B again, then January 2 is reversed."""
    ann = make_player(db, "Replay Ann")
    bob = make_player(db, "Replay Bob")
    first = make_match(
        db,
        ann,
        bob,
        winner=ann,
        match_date=datetime(2026, 1, 2, 12, tzinfo=UTC),
    )
    second = make_match(
        db,
        ann,
        bob,
        winner=ann,
        match_date=datetime(2026, 1, 3, 12, tzinfo=UTC),
    )
    db.expire_all()
    ann_row = db.get(Player, ann.id)
    bob_row = db.get(Player, bob.id)
    assert ann_row is not None and bob_row is not None
    assert ann_row.current_rating == 1531
    assert bob_row.current_rating == 1469
    assert ann_row.highest_rating == 1531
    assert bob_row.highest_rating == STARTING_RATING
    assert _change(db, first.id, ann.id) == 16
    assert _change(db, second.id, ann.id) == 15

    correct_match(db, first.id, reason=REASON, actor=ACTOR, winner_id=bob.id)
    db.expire_all()
    ann_row = db.get(Player, ann.id)
    bob_row = db.get(Player, bob.id)
    assert ann_row is not None and bob_row is not None
    assert _change(db, first.id, bob.id) == 16
    assert _change(db, first.id, ann.id) == -16
    assert _change(db, second.id, ann.id) == 17
    assert ann_row.current_rating == 1501
    assert bob_row.current_rating == 1499
    assert ann_row.highest_rating == 1501
    assert bob_row.highest_rating == 1516
    assert_matches_independent_replay(db, "documented winner flip")


def test_cancel_and_delete_of_the_only_match_return_both_players_to_1500(db: Session) -> None:
    left = make_player(db, "Only Left")
    right = make_player(db, "Only Right")
    canceled = make_match(
        db,
        left,
        right,
        winner=left,
        match_date=datetime(2026, 3, 1, 12, tzinfo=UTC),
    )
    cancel_match(db, canceled.id, REASON, ACTOR)
    db.expire_all()
    left_row = db.get(Player, left.id)
    right_row = db.get(Player, right.id)
    stored = db.get(Match, canceled.id)
    assert left_row is not None and right_row is not None and stored is not None
    assert stored.status == "canceled"
    assert left_row.current_rating == STARTING_RATING
    assert right_row.current_rating == STARTING_RATING
    assert left_row.highest_rating == STARTING_RATING
    assert right_row.highest_rating == STARTING_RATING
    assert db.scalars(select(RatingHistory)).all() == []

    other_a = make_player(db, "Delete Left")
    other_b = make_player(db, "Delete Right")
    removed = make_match(
        db,
        other_a,
        other_b,
        winner=other_b,
        match_date=datetime(2026, 3, 2, 12, tzinfo=UTC),
    )
    delete_match(db, removed.id, REASON, ACTOR)
    db.expire_all()
    other_a = db.get(Player, other_a.id)
    other_b = db.get(Player, other_b.id)
    removed_row = db.get(Match, removed.id)
    assert other_a is not None and other_b is not None and removed_row is not None
    assert removed_row.deleted_at is not None
    assert other_a.current_rating == STARTING_RATING
    assert other_b.current_rating == STARTING_RATING
    assert other_a.highest_rating == STARTING_RATING
    assert other_b.highest_rating == STARTING_RATING
    remaining = db.scalars(select(RatingHistory)).all()
    assert remaining == []
    assert_matches_independent_replay(db, "only match removed")


def test_canceling_the_earlier_match_replays_the_later_one_from_1500(db: Session) -> None:
    ann = make_player(db, "Chain Ann")
    bob = make_player(db, "Chain Bob")
    first = make_match(db, ann, bob, winner=ann, match_date=datetime(2026, 4, 1, 12, tzinfo=UTC))
    second = make_match(db, ann, bob, winner=ann, match_date=datetime(2026, 4, 2, 12, tzinfo=UTC))
    cancel_match(db, first.id, REASON, ACTOR)
    db.expire_all()
    ann_row = db.get(Player, ann.id)
    bob_row = db.get(Player, bob.id)
    assert ann_row is not None and bob_row is not None
    assert ann_row.current_rating == 1516
    assert bob_row.current_rating == 1484
    assert _change(db, second.id, ann.id) == 16
    assert db.scalar(select(RatingHistory).where(RatingHistory.match_id == first.id)) is None
    assert_matches_independent_replay(db, "cancel earliest")


def test_seeded_random_operations_match_a_full_replay(db: Session) -> None:
    rng = random.Random(20261119)
    players = [make_player(db, f"P{index}") for index in range(6)]
    dates = [
        datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=rng.randrange(0, 500), minutes=index)
        for index in range(40)
    ]
    rng.shuffle(dates)
    match_ids: list[object] = []
    for index, when in enumerate(dates):
        left, right = rng.sample(players, 2)
        winner = rng.choice([left, right])
        created = make_match(db, left, right, winner=winner, match_date=when)
        match_ids.append(created.id)
        assert_matches_independent_replay(db, f"create {index}")

    def match(index: int) -> Match:
        db.expire_all()
        row = db.get(Match, match_ids[index])
        assert row is not None
        return row

    first = match(0)
    flipped = first.player_b_id if first.winner_id == first.player_a_id else first.player_a_id
    correct_match(db, first.id, reason=REASON, actor=ACTOR, winner_id=flipped)
    assert_matches_independent_replay(db, "flip winner")

    correct_match(
        db,
        match(3).id,
        reason=REASON,
        actor=ACTOR,
        match_date=datetime(2023, 6, 1, 9, tzinfo=UTC),
    )
    assert_matches_independent_replay(db, "move date earlier")

    correct_match(
        db,
        match(5).id,
        reason=REASON,
        actor=ACTOR,
        match_date=datetime(2026, 8, 1, 18, tzinfo=UTC),
    )
    assert_matches_independent_replay(db, "move date later")

    swapped = match(7)
    replacement = next(
        player for player in players if player.id not in (swapped.player_a_id, swapped.player_b_id)
    )
    correct_match(
        db,
        swapped.id,
        reason=REASON,
        actor=ACTOR,
        player_b_id=replacement.id,
        winner_id=swapped.player_a_id,
    )
    assert_matches_independent_replay(db, "swap player")

    cancel_match(db, match(9).id, REASON, ACTOR)
    assert_matches_independent_replay(db, "cancel")

    delete_match(db, match(11).id, REASON, ACTOR)
    assert_matches_independent_replay(db, "delete")

    disputed = match(13)
    correct_match(db, disputed.id, reason=REASON, actor=ACTOR, status="disputed")
    assert_matches_independent_replay(db, "completed to disputed")
    correct_match(db, disputed.id, reason=REASON, actor=ACTOR, status="completed")
    assert_matches_independent_replay(db, "disputed to completed")

    later = match(2)
    later_winner = later.player_b_id if later.winner_id == later.player_a_id else later.player_a_id
    correct_match(db, later.id, reason=REASON, actor=ACTOR, winner_id=later_winner)
    assert_matches_independent_replay(db, "flip a later match")

    make_match(
        db,
        players[0],
        players[1],
        winner=players[1],
        match_date=datetime(2024, 6, 15, 12, tzinfo=UTC),
    )
    assert_matches_independent_replay(db, "backdated insert")

    cancel_match(db, match(15).id, REASON, ACTOR)
    assert_matches_independent_replay(db, "second cancel")
    delete_match(db, match(17).id, REASON, ACTOR)
    assert_matches_independent_replay(db, "second delete")
