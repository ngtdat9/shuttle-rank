"""Monthly snapshots, ranking ties, head-to-head, and player stats."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.services.elo import apply_result
from app.services.monthly_service import get_monthly_rankings, rebuild_monthly_snapshots
from app.services.player_service import deactivate_player, get_player_profile, list_players
from app.services.ranking_service import get_head_to_head, get_rankings, load_player_stats
from tests.factories import make_match, make_player


def _shift(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def _at(year: int, month: int) -> datetime:
    return datetime(year, month, 15, 12, tzinfo=UTC)


def test_monthly_snapshots_span_months_and_share_ranks(db: Session) -> None:
    now = datetime.now(UTC)
    older = _shift(now.year, now.month, -2)
    previous = _shift(now.year, now.month, -1)
    amy = make_player(db, "Amy")
    cara = make_player(db, "Cara")
    bob = make_player(db, "Bob")
    dee = make_player(db, "Dee")
    eve = make_player(db, "Eve")
    finn = make_player(db, "Finn")
    make_match(db, amy, bob, winner=amy, match_date=_at(*older))
    make_match(db, cara, dee, winner=cara, match_date=_at(*older))
    make_match(db, eve, finn, winner=eve, match_date=_at(*previous))

    months = rebuild_monthly_snapshots(db)
    db.commit()
    assert months == 3

    september = get_monthly_rankings(db, year=older[0], month=older[1])
    by_name = {item.player.display_name: item for item in september.items}
    assert [item.player.display_name for item in september.items] == ["Amy", "Cara", "Bob", "Dee"]
    assert by_name["Amy"].rank == 1
    assert by_name["Cara"].rank == 1
    assert by_name["Bob"].rank == 3
    assert by_name["Amy"].rating == 1516
    assert by_name["Bob"].rating == 1484
    assert by_name["Amy"].wins == 1
    assert by_name["Amy"].rating_change_during_month == 16
    assert by_name["Amy"].rank_change is None

    october = get_monthly_rankings(db, year=previous[0], month=previous[1])
    october_names = {item.player.display_name: item for item in october.items}
    assert october_names["Eve"].rank == 1
    assert october_names["Eve"].rank_change is None
    assert october_names["Amy"].rank == 2
    assert october_names["Cara"].rank == 2
    assert october_names["Amy"].rank_change == -1
    assert october_names["Amy"].wins == 0
    assert october_names["Amy"].matches_played == 0
    assert october_names["Amy"].rating == 1516
    assert october_names["Eve"].wins == 1
    assert october_names["Bob"].rank == 4

    current = get_monthly_rankings(db, year=now.year, month=now.month)
    current_names = {item.player.display_name: item for item in current.items}
    assert current_names["Amy"].rank == 1
    assert current_names["Cara"].rank == 1
    assert current_names["Eve"].rank == 1
    assert current_names["Amy"].rank_change == 1
    assert current_names["Eve"].rank_change == 0
    assert current_names["Amy"].matches_played == 0
    assert current_names["Bob"].rank == 4

    default = get_monthly_rankings(db)
    assert (default.year, default.month) == (now.year, now.month)
    assert [(month.year, month.month) for month in default.available_months] == [
        (now.year, now.month),
        previous,
        older,
    ]
    with pytest.raises(NotFoundError):
        get_monthly_rankings(db, year=1999, month=1)
    with pytest.raises(BusinessRuleError):
        get_monthly_rankings(db, year=2026)


def test_rankings_use_shared_ranks_and_hide_inactive_players(db: Session) -> None:
    amy = make_player(db, "Amy")
    cara = make_player(db, "Cara")
    bob = make_player(db, "Bob")
    dee = make_player(db, "Dee")
    make_player(db, "Zoe")
    gina = make_player(db, "Gina")
    deactivate_player(db, gina.id, actor="tester")
    day = datetime(2026, 7, 1, tzinfo=UTC)
    make_match(db, amy, bob, winner=amy, match_date=day)
    make_match(db, cara, dee, winner=cara, match_date=day)

    board = get_rankings(db)
    assert [item.player.display_name for item in board.items] == [
        "Amy",
        "Cara",
        "Zoe",
        "Bob",
        "Dee",
    ]
    assert [item.rank for item in board.items] == [1, 1, 3, 4, 4]
    assert board.items[2].win_rate is None
    assert board.items[2].matches_played == 0
    assert board.last_updated is not None

    by_wins = get_rankings(db, sort="wins", order="desc")
    assert by_wins.items[0].wins >= by_wins.items[-1].wins
    assert by_wins.items[0].rank == 1

    with_inactive = get_rankings(db, include_inactive=True)
    assert any(item.player.display_name == "Gina" for item in with_inactive.items)
    hidden = get_rankings(db, include_inactive=False)
    assert all(item.player.display_name != "Gina" for item in hidden.items)

    profile = get_player_profile(db, amy.id)
    assert profile.rank == 1
    assert profile.stats.wins == 1
    assert profile.stats.recent_form == ["W"]
    assert profile.stats.current_streak is not None
    assert profile.stats.current_streak.type == "W"
    inactive_profile = get_player_profile(db, gina.id)
    assert inactive_profile.rank is None

    directory = list_players(db, include_inactive=True, search="gi")
    assert [item.display_name for item in directory.items] == ["Gina"]
    assert directory.items[0].rank is None


def test_head_to_head_and_recent_form(db: Session) -> None:
    amy = make_player(db, "Amy")
    bob = make_player(db, "Bob")
    now = datetime.now(UTC)
    make_match(db, amy, bob, winner=amy, match_date=now - timedelta(days=40))
    make_match(db, amy, bob, winner=bob, match_date=now - timedelta(days=1))
    make_match(db, amy, bob, winner=bob, match_date=now - timedelta(days=2), status="canceled")

    second_delta = apply_result(1484, 1516).delta
    report = get_head_to_head(db, amy.id, bob.id)
    assert report.total_matches == 2
    assert report.player_a_wins == 1
    assert report.player_b_wins == 1
    assert report.player_a_win_rate == 0.5
    assert report.current_streak is not None
    assert report.current_streak.player_id == bob.id
    assert report.current_streak.count == 1
    assert report.player_a_net_rating_change == 16 - second_delta
    assert report.matches[0].winner_id == bob.id

    stats = load_player_stats(db)[amy.id]
    assert stats.recent_form == ["L", "W"]
    assert stats.current_streak == ("L", 1)
    assert stats.matches_played == 2
    assert stats.last_rating_change == -second_delta
    assert stats.rating_change_30d == -second_delta

    with pytest.raises(BusinessRuleError):
        get_head_to_head(db, amy.id, amy.id)
    with pytest.raises(NotFoundError):
        get_head_to_head(db, amy.id, uuid.uuid4())
