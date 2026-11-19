"""End-of-month ranking snapshots.

``rebuild_monthly_snapshots`` deletes and rewrites every row. It flushes and
does not commit; the match service calls it inside the same transaction as the
rating change. Months run from the first rated match's UTC month through the
current UTC month. A player appears in a month once they have at least one
rated match at or before that month ends. Rank is by month-end rating, then
wins in that month, then name. Equal ratings share a rank (1, 2, 2, 4).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.models.match import Match
from app.models.monthly_ranking import MonthlyRanking
from app.models.player import Player
from app.models.rating_history import RatingHistory
from app.schemas.rankings import MonthlyRankingItem, MonthlyRankingsResponse, MonthRef, PlayerMonth
from app.services.ordering import ensure_utc, is_rated, match_sort_key
from app.services.serialize import player_summary


def rebuild_monthly_snapshots(db: Session) -> int:
    """Replace every monthly snapshot. Returns how many months were written."""
    db.flush()
    db.execute(delete(MonthlyRanking))

    matches = [match for match in db.scalars(select(Match)).all() if is_rated(match)]
    matches.sort(key=match_sort_key)
    if not matches:
        db.flush()
        return 0

    histories = {
        (history.player_id, history.match_id): history
        for history in db.scalars(select(RatingHistory)).all()
    }
    players = {player.id: player for player in db.scalars(select(Player)).all()}
    first = ensure_utc(matches[0].match_date)
    now = datetime.now(UTC)
    months = list(iter_months((first.year, first.month), (now.year, now.month)))

    for year, month in months:
        start = _month_start(year, month)
        end = _month_start(*_next_month(year, month))
        wins: dict[uuid.UUID, int] = {}
        losses: dict[uuid.UUID, int] = {}
        played: dict[uuid.UUID, int] = {}
        change: dict[uuid.UUID, int] = {}
        latest: dict[uuid.UUID, tuple[object, int]] = {}
        debuted: set[uuid.UUID] = set()

        for match in matches:
            played_at = ensure_utc(match.match_date)
            if played_at >= end:
                break
            key = match_sort_key(match)
            for player_id in (match.player_a_id, match.player_b_id):
                debuted.add(player_id)
                history = histories[(player_id, match.id)]
                previous = latest.get(player_id)
                if previous is None or key > previous[0]:
                    latest[player_id] = (key, history.new_rating)
                if start <= played_at < end:
                    played[player_id] = played.get(player_id, 0) + 1
                    change[player_id] = change.get(player_id, 0) + history.rating_change
                    if match.winner_id == player_id:
                        wins[player_id] = wins.get(player_id, 0) + 1
                    else:
                        losses[player_id] = losses.get(player_id, 0) + 1

        rows = [
            {
                "player_id": player_id,
                "rating": latest[player_id][1],
                "wins": wins.get(player_id, 0),
                "losses": losses.get(player_id, 0),
                "matches_played": played.get(player_id, 0),
                "rating_change_during_month": change.get(player_id, 0),
                "name": players[player_id].display_name,
            }
            for player_id in debuted
        ]
        rows.sort(key=lambda row: (-row["rating"], -row["wins"], _name_key(row["name"])))
        _assign_ranks(rows)
        for row in rows:
            db.add(
                MonthlyRanking(
                    player_id=row["player_id"],
                    year=year,
                    month=month,
                    rating=row["rating"],
                    rank=row["rank"],
                    wins=row["wins"],
                    losses=row["losses"],
                    matches_played=row["matches_played"],
                    rating_change_during_month=row["rating_change_during_month"],
                )
            )
    db.flush()
    return len(months)


def get_monthly_rankings(
    db: Session,
    *,
    year: int | None = None,
    month: int | None = None,
) -> MonthlyRankingsResponse:
    """Return one month of snapshots. The default is the newest month."""
    if (year is None) != (month is None):
        raise BusinessRuleError("Year and month must be provided together")

    available = _available_months(db)
    if year is None:
        if not available:
            return MonthlyRankingsResponse(available_months=[], year=None, month=None, items=[])
        year, month = available[0].year, available[0].month
    assert year is not None and month is not None

    rows = list(
        db.scalars(
            select(MonthlyRanking).where(
                MonthlyRanking.year == year,
                MonthlyRanking.month == month,
            )
        ).all()
    )
    if not rows:
        raise NotFoundError("No monthly ranking for that month")

    previous_year, previous_month = _previous_month(year, month)
    previous_ranks = {
        row.player_id: row.rank
        for row in db.scalars(
            select(MonthlyRanking).where(
                MonthlyRanking.year == previous_year,
                MonthlyRanking.month == previous_month,
            )
        ).all()
    }
    players = {
        player.id: player
        for player in db.scalars(
            select(Player).where(Player.id.in_([row.player_id for row in rows]))
        ).all()
    }
    rows.sort(key=lambda row: (row.rank, _name_key(players[row.player_id].display_name)))
    items = [
        MonthlyRankingItem(
            rank=row.rank,
            player=player_summary(players[row.player_id]),
            rating=row.rating,
            rank_change=_rank_change(previous_ranks, row.player_id, row.rank),
            wins=row.wins,
            losses=row.losses,
            matches_played=row.matches_played,
            rating_change_during_month=row.rating_change_during_month,
        )
        for row in rows
    ]
    return MonthlyRankingsResponse(
        available_months=available,
        year=year,
        month=month,
        items=items,
    )


def get_player_monthly(db: Session, player_id: uuid.UUID) -> list[PlayerMonth]:
    rows = list(
        db.scalars(
            select(MonthlyRanking)
            .where(MonthlyRanking.player_id == player_id)
            .order_by(MonthlyRanking.year, MonthlyRanking.month)
        ).all()
    )
    return [
        PlayerMonth(
            year=row.year,
            month=row.month,
            rating=row.rating,
            rank=row.rank,
            wins=row.wins,
            losses=row.losses,
            matches_played=row.matches_played,
            rating_change_during_month=row.rating_change_during_month,
        )
        for row in rows
    ]


def iter_months(start: tuple[int, int], end: tuple[int, int]):
    if start > end:
        return
    year, month = start
    while (year, month) <= end:
        yield year, month
        year, month = _next_month(year, month)


def _available_months(db: Session) -> list[MonthRef]:
    pairs = {
        (row.year, row.month)
        for row in db.execute(select(MonthlyRanking.year, MonthlyRanking.month)).all()
    }
    ordered = sorted(pairs, reverse=True)
    return [MonthRef(year=year, month=month) for year, month in ordered]


def _rank_change(
    previous_ranks: dict[uuid.UUID, int],
    player_id: uuid.UUID,
    rank: int,
) -> int | None:
    previous = previous_ranks.get(player_id)
    if previous is None:
        return None
    return previous - rank


def _assign_ranks(rows: list[dict[str, object]]) -> None:
    last_key: object | None = None
    rank = 0
    for index, row in enumerate(rows):
        key = row["rating"]
        if key != last_key:
            rank = index + 1
            last_key = key
        row["rank"] = rank


def _name_key(name: str) -> tuple[str, str]:
    return (name.casefold(), name)


def _month_start(year: int, month: int) -> datetime:
    return datetime(year, month, 1, tzinfo=UTC)


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1
