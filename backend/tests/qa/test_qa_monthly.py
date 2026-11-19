"""Monthly snapshots: month-end rating, in-month record, ties, and no reset."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.models.match import Match
from app.models.monthly_ranking import MonthlyRanking
from app.models.player import Player
from app.services.monthly_service import get_monthly_rankings, get_player_monthly
from app.services.player_service import deactivate_player
from tests.factories import make_match, make_player
from tests.qa.reference import monthly_snapshots

ACTOR = "qa"
NOW = datetime.now(UTC)


def _rows(db: Session) -> list[MonthlyRanking]:
    db.expire_all()
    return list(db.scalars(select(MonthlyRanking)).all())


def _indexed(snapshots: dict[tuple[int, int], list[dict[str, object]]]):
    return {
        (year, month, row["player_id"]): row
        for (year, month), rows in snapshots.items()
        for row in rows
    }


def test_monthly_values_carry_forward_through_the_current_month(db: Session) -> None:
    empty = get_monthly_rankings(db)
    assert empty.available_months == []
    assert empty.year is None and empty.month is None
    assert empty.items == []

    ann = make_player(db, "Ann")
    bob = make_player(db, "Bob")
    cal = make_player(db, "Cal")
    zed = make_player(db, "Zed")
    make_match(db, ann, bob, winner=ann, match_date=datetime(2026, 1, 10, 12, tzinfo=UTC))
    make_match(db, bob, ann, winner=bob, match_date=datetime(2026, 2, 10, 12, tzinfo=UTC))
    make_match(db, cal, ann, winner=cal, match_date=datetime(2026, 3, 10, 12, tzinfo=UTC))

    players = [ann, bob, cal, zed]
    expected = monthly_snapshots(players, list(db.scalars(select(Match)).all()), now=NOW)
    stored = _indexed(expected)
    january = stored[(2026, 1, ann.id)]
    assert january["rating"] == 1516
    assert january["wins"] == 1 and january["losses"] == 0
    assert january["matches_played"] == 1
    assert january["rating_change_during_month"] == 16
    assert january["rank"] == 1
    bob_jan = stored[(2026, 1, bob.id)]
    assert bob_jan["rating"] == 1484
    assert bob_jan["wins"] == 0 and bob_jan["losses"] == 1
    assert bob_jan["rating_change_during_month"] == -16
    assert bob_jan["rank"] == 2
    assert (2026, 1, cal.id) not in stored
    assert (2026, 1, zed.id) not in stored

    bob_feb = stored[(2026, 2, bob.id)]
    ann_feb = stored[(2026, 2, ann.id)]
    assert bob_feb["rating"] == 1501
    assert bob_feb["wins"] == 1 and bob_feb["losses"] == 0
    assert bob_feb["rating_change_during_month"] == 17
    assert bob_feb["rank"] == 1
    assert ann_feb["rating"] == 1499
    assert ann_feb["wins"] == 0 and ann_feb["losses"] == 1
    assert ann_feb["rating_change_during_month"] == -17
    assert ann_feb["rank"] == 2
    assert (2026, 2, cal.id) not in stored

    march_ratings = {
        ann.id: stored[(2026, 3, ann.id)]["rating"],
        bob.id: stored[(2026, 3, bob.id)]["rating"],
        cal.id: stored[(2026, 3, cal.id)]["rating"],
    }
    assert stored[(2026, 3, cal.id)]["wins"] == 1
    assert (2026, 3, zed.id) not in stored

    months = sorted(expected)
    assert months[0] == (2026, 1)
    assert months[-1] == (NOW.year, NOW.month)
    for previous, current in zip(months, months[1:], strict=False):
        assert _next(previous) == current
    for year, month in months:
        if (year, month) <= (2026, 2):
            continue
        for player_id, rating in march_ratings.items():
            row = stored[(year, month, player_id)]
            assert row["rating"] == rating
            if (year, month) != (2026, 3):
                assert row["wins"] == 0 and row["losses"] == 0
                assert row["matches_played"] == 0
                assert row["rating_change_during_month"] == 0
        assert (year, month, zed.id) not in stored

    db_rows = _rows(db)
    actual = {
        (row.year, row.month, row.player_id): (
            row.rating,
            row.rank,
            row.wins,
            row.losses,
            row.matches_played,
            row.rating_change_during_month,
        )
        for row in db_rows
    }
    wanted = {
        key: (
            row["rating"],
            row["rank"],
            row["wins"],
            row["losses"],
            row["matches_played"],
            row["rating_change_during_month"],
        )
        for key, row in stored.items()
    }
    assert actual == wanted

    february = get_monthly_rankings(db, year=2026, month=2)
    by_id = {item.player.id: item for item in february.items}
    assert by_id[bob.id].rank_change == 1
    assert by_id[ann.id].rank_change == -1
    assert by_id[bob.id].rating == 1501
    assert by_id[ann.id].rating_change_during_month == -17
    january_api = get_monthly_rankings(db, year=2026, month=1)
    assert all(item.rank_change is None for item in january_api.items)

    march = get_monthly_rankings(db, year=2026, month=3)
    march_by_id = {item.player.id: item for item in march.items}
    assert march_by_id[cal.id].rank_change is None
    assert set(march_by_id) == {ann.id, bob.id, cal.id}

    latest = get_monthly_rankings(db)
    assert (latest.year, latest.month) == (NOW.year, NOW.month)
    available = [(item.year, item.month) for item in latest.available_months]
    assert available == list(reversed(months))

    ann_months = get_player_monthly(db, ann.id)
    assert [(row.year, row.month) for row in ann_months] == months
    assert ann_months[0].rating == 1516
    assert ann_months[-1].rating == march_ratings[ann.id]

    db.expire_all()
    live = db.get(Player, ann.id)
    assert live is not None
    assert live.current_rating == march_ratings[ann.id]
    assert live.current_rating != 1500

    deactivate_player(db, ann.id, actor=ACTOR)
    still = get_monthly_rankings(db, year=2026, month=1)
    inactive = next(item for item in still.items if item.player.id == ann.id)
    assert inactive.player.is_active is False

    with pytest.raises(NotFoundError) as missing:
        get_monthly_rankings(db, year=1999, month=1)
    assert missing.value.status_code == 404
    with pytest.raises(BusinessRuleError):
        get_monthly_rankings(db, year=2026, month=None)


def test_monthly_equal_results_share_a_rank_and_skip(db: Session) -> None:
    mira = make_player(db, "Mira")
    nia = make_player(db, "Nia")
    otto = make_player(db, "Otto")
    pia = make_player(db, "Pia")
    played = datetime(2026, 1, 15, 12, tzinfo=UTC)
    make_match(db, mira, nia, winner=mira, match_date=played)
    make_match(db, otto, pia, winner=otto, match_date=played + timedelta(hours=1))
    expected = monthly_snapshots(
        [mira, nia, otto, pia],
        list(db.scalars(select(Match)).all()),
        now=NOW,
    )
    ranks = {row["player_id"]: row["rank"] for row in expected[(2026, 1)]}
    assert ranks == {mira.id: 1, otto.id: 1, nia.id: 3, pia.id: 3}
    db.expire_all()
    stored = {
        row.player_id: row.rank
        for row in db.scalars(select(MonthlyRanking).where(MonthlyRanking.month == 1))
    }
    assert stored == ranks


def test_monthly_equal_ratings_share_a_rank_when_wins_differ(db: Session) -> None:
    """R-LB-02: equal ratings share a rank even when the win counts differ."""
    ace = make_player(db, "Ace")
    bea = make_player(db, "Bea")
    cal = make_player(db, "Cal")
    day = datetime(2026, 1, 1, 12, tzinfo=UTC)
    make_match(db, ace, bea, winner=ace, match_date=day)
    make_match(db, cal, ace, winner=cal, match_date=day.replace(day=2))
    make_match(db, cal, ace, winner=cal, match_date=day.replace(day=3))
    players = [ace, bea, cal]
    expected = monthly_snapshots(players, list(db.scalars(select(Match)).all()), now=NOW)
    january = {row["player_id"]: row for row in expected[(2026, 1)]}
    assert january[cal.id]["rating"] == 1532
    assert january[ace.id]["rating"] == 1484
    assert january[bea.id]["rating"] == 1484
    assert january[cal.id]["wins"] == 2
    assert january[ace.id]["wins"] == 1
    assert january[bea.id]["wins"] == 0
    assert january[cal.id]["rank"] == 1
    assert january[ace.id]["rank"] == 2
    assert january[bea.id]["rank"] == 2

    db.expire_all()
    stored = {
        row.player_id: (row.rank, row.rating, row.wins, row.rating_change_during_month)
        for row in db.scalars(
            select(MonthlyRanking).where(MonthlyRanking.year == 2026, MonthlyRanking.month == 1)
        )
    }
    assert stored[cal.id] == (1, 1532, 2, 32)
    assert stored[ace.id] == (2, 1484, 1, -16)
    assert stored[bea.id] == (2, 1484, 0, -16)


def _next(month: tuple[int, int]) -> tuple[int, int]:
    year, value = month
    if value == 12:
        return year + 1, 1
    return year, value + 1
