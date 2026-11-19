"""Elo results checked against the documented formula, not the app's helper."""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.player import Player
from app.models.rating_history import RatingHistory
from tests.factories import make_match, make_player
from tests.qa.reference import STARTING_RATING, elo_delta, replay


def _refresh(db: Session) -> None:
    db.expire_all()


def _stage_ratings(db: Session, player: Player, rating: int) -> None:
    player.current_rating = rating
    player.highest_rating = rating
    db.commit()
    db.refresh(player)


def _history(db: Session, match_id: object) -> dict[object, RatingHistory]:
    rows = db.scalars(select(RatingHistory).where(RatingHistory.match_id == match_id)).all()
    return {row.player_id: row for row in rows}


def test_equal_ratings_award_sixteen_points(db: Session) -> None:
    ann = make_player(db, "Ann")
    bob = make_player(db, "Bob")
    match = make_match(
        db,
        ann,
        bob,
        winner=ann,
        match_date=datetime(2026, 1, 2, 12, tzinfo=UTC),
        game_scores=[[21, 15], [21, 19]],
        notes="scores do not matter",
    )
    _refresh(db)
    ann = db.get(Player, ann.id)
    bob = db.get(Player, bob.id)
    assert ann is not None and bob is not None
    assert ann.current_rating == 1516
    assert bob.current_rating == 1484
    assert ann.highest_rating == 1516
    assert bob.highest_rating == STARTING_RATING
    assert ann.current_rating + bob.current_rating == STARTING_RATING * 2
    rows = _history(db, match.id)
    assert rows[ann.id].old_rating == 1500
    assert rows[ann.id].new_rating == 1516
    assert rows[ann.id].rating_change == 16
    assert rows[bob.id].old_rating == 1500
    assert rows[bob.id].new_rating == 1484
    assert rows[bob.id].rating_change == -16
    assert rows[ann.id].rating_change + rows[bob.id].rating_change == 0
    assert all(
        isinstance(value, int)
        for value in (
            ann.current_rating,
            bob.current_rating,
            rows[ann.id].rating_change,
            rows[bob.id].rating_change,
        )
    )
    assert elo_delta(1500, 1500) == 16


def test_sixteen_hundred_beats_fourteen_hundred(db: Session) -> None:
    favorite = make_player(db, "Favorite")
    underdog = make_player(db, "Underdog")
    _stage_ratings(db, favorite, 1600)
    _stage_ratings(db, underdog, 1400)
    match = make_match(
        db,
        favorite,
        underdog,
        winner=favorite,
        match_date=datetime(2026, 2, 2, 12, tzinfo=UTC),
    )
    _refresh(db)
    favorite = db.get(Player, favorite.id)
    underdog = db.get(Player, underdog.id)
    assert favorite is not None and underdog is not None
    rows = _history(db, match.id)
    assert elo_delta(1600, 1400) == 8
    assert rows[favorite.id].old_rating == 1600
    assert rows[favorite.id].new_rating == 1608
    assert rows[favorite.id].rating_change == 8
    assert rows[underdog.id].old_rating == 1400
    assert rows[underdog.id].new_rating == 1392
    assert rows[underdog.id].rating_change == -8
    assert favorite.current_rating == 1608
    assert underdog.current_rating == 1392
    assert favorite.highest_rating == 1608
    assert underdog.highest_rating == 1400
    assert favorite.current_rating + underdog.current_rating == 3000


def test_fourteen_hundred_beats_sixteen_hundred(db: Session) -> None:
    underdog = make_player(db, "Upset Winner")
    favorite = make_player(db, "Upset Loser")
    _stage_ratings(db, underdog, 1400)
    _stage_ratings(db, favorite, 1600)
    match = make_match(
        db,
        underdog,
        favorite,
        winner=underdog,
        match_date=datetime(2026, 2, 3, 12, tzinfo=UTC),
    )
    _refresh(db)
    underdog = db.get(Player, underdog.id)
    favorite = db.get(Player, favorite.id)
    assert underdog is not None and favorite is not None
    rows = _history(db, match.id)
    assert elo_delta(1400, 1600) == 24
    assert rows[underdog.id].rating_change == 24
    assert rows[underdog.id].new_rating == 1424
    assert rows[favorite.id].rating_change == -24
    assert rows[favorite.id].new_rating == 1576
    assert underdog.current_rating == 1424
    assert favorite.current_rating == 1576
    assert underdog.highest_rating == 1424
    assert favorite.highest_rating == 1600
    assert rows[underdog.id].rating_change + rows[favorite.id].rating_change == 0


def test_upset_gains_more_than_a_favorite_win(db: Session) -> None:
    """The same rating gap pays the underdog more than the favorite."""
    strong = make_player(db, "Strong")
    weak = make_player(db, "Weak")
    _stage_ratings(db, strong, 1600)
    _stage_ratings(db, weak, 1400)
    favorite_win = make_match(
        db,
        strong,
        weak,
        winner=strong,
        match_date=datetime(2026, 3, 1, 12, tzinfo=UTC),
    )
    other_strong = make_player(db, "Other Strong")
    other_weak = make_player(db, "Other Weak")
    _stage_ratings(db, other_strong, 1600)
    _stage_ratings(db, other_weak, 1400)
    upset = make_match(
        db,
        other_weak,
        other_strong,
        winner=other_weak,
        match_date=datetime(2026, 3, 2, 12, tzinfo=UTC),
    )
    _refresh(db)
    favorite_rows = _history(db, favorite_win.id)
    upset_rows = _history(db, upset.id)
    favorite_gain = favorite_rows[strong.id].rating_change
    upset_gain = upset_rows[other_weak.id].rating_change
    assert favorite_gain == 8
    assert upset_gain == 24
    assert upset_gain > favorite_gain


def test_game_scores_do_not_change_the_delta(db: Session) -> None:
    plain_a = make_player(db, "Plain A")
    plain_b = make_player(db, "Plain B")
    scored_a = make_player(db, "Scored A")
    scored_b = make_player(db, "Scored B")
    played_at = datetime(2026, 4, 1, 12, tzinfo=UTC)
    plain = make_match(db, plain_a, plain_b, winner=plain_a, match_date=played_at)
    scored = make_match(
        db,
        scored_a,
        scored_b,
        winner=scored_a,
        match_date=played_at,
        game_scores=[[21, 0], [0, 99], [21, 19], [19, 21], [21, 18]],
        notes="x" * 500,
    )
    _refresh(db)
    assert _history(db, plain.id)[plain_a.id].rating_change == 16
    assert _history(db, scored.id)[scored_a.id].rating_change == 16


def test_random_sequences_conserve_points_history_and_peaks(db: Session) -> None:
    for seed in range(6):
        local = random.Random(seed)
        players = [make_player(db, f"S{seed}P{index}") for index in range(4)]
        dates = [
            datetime(2025, 1, 1, tzinfo=UTC)
            + timedelta(days=local.randrange(0, 200), minutes=index)
            for index in range(12)
        ]
        local.shuffle(dates)
        for when in dates:
            left, right = local.sample(players, 2)
            winner = local.choice([left, right])
            make_match(db, left, right, winner=winner, match_date=when)
            _assert_invariants(db)


def _assert_invariants(db: Session) -> None:
    _refresh(db)
    players = list(db.scalars(select(Player)).all())
    match_rows = list(db.scalars(select(Match)).all())
    histories = list(db.scalars(select(RatingHistory)).all())
    assert sum(player.current_rating for player in players) == STARTING_RATING * len(players)
    by_player: dict[object, list[RatingHistory]] = {}
    by_match: dict[object, list[RatingHistory]] = {}
    for row in histories:
        assert isinstance(row.old_rating, int)
        assert isinstance(row.new_rating, int)
        assert isinstance(row.rating_change, int)
        assert row.new_rating == row.old_rating + row.rating_change
        by_player.setdefault(row.player_id, []).append(row)
        by_match.setdefault(row.match_id, []).append(row)
    for rows in by_match.values():
        assert len(rows) == 2
        assert rows[0].rating_change + rows[1].rating_change == 0
    expected = replay(players, match_rows)
    assert {player.id: player.current_rating for player in players} == expected["current"]
    assert {player.id: player.highest_rating for player in players} == expected["highest"]
    for player in players:
        news = [row.new_rating for row in by_player.get(player.id, [])]
        assert player.highest_rating == max([STARTING_RATING, *news])
        assert isinstance(player.current_rating, int)
        assert isinstance(player.highest_rating, int)
