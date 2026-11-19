"""Spec-derived Elo, replay, and monthly oracles for QA.

The formulas come from docs/ELO_ALGORITHM.md and docs/API.md. This module does
not call the application rating code.
"""

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

STARTING_RATING = 1500
K_FACTOR = 32


class _Player(Protocol):
    id: UUID
    display_name: str


class _Match(Protocol):
    id: UUID
    player_a_id: UUID
    player_b_id: UUID
    winner_id: UUID
    match_date: datetime
    created_at: datetime
    status: str
    deleted_at: datetime | None


def elo_delta(winner_rating: int, loser_rating: int) -> int:
    """delta = floor(32 * (1 - E_winner) + 0.5)."""
    expected = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    return math.floor(K_FACTOR * (1 - expected) + 0.5)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def match_key(match: _Match) -> tuple[datetime, datetime, UUID]:
    return (ensure_utc(match.match_date), ensure_utc(match.created_at), match.id)


def is_rated(match: _Match) -> bool:
    return match.status == "completed" and match.deleted_at is None


def rated_matches(matches: Iterable[_Match]) -> list[_Match]:
    rated = [match for match in matches if is_rated(match)]
    rated.sort(key=match_key)
    return rated


def replay(players: Sequence[_Player], matches: Iterable[_Match]) -> dict[str, object]:
    """Replay every currently rated match from 1500 in processing order."""
    current = {player.id: STARTING_RATING for player in players}
    highest = {player.id: STARTING_RATING for player in players}
    rows: list[tuple[UUID, UUID, int, int, int]] = []
    for match in rated_matches(matches):
        old_a = current[match.player_a_id]
        old_b = current[match.player_b_id]
        if match.winner_id == match.player_a_id:
            delta = elo_delta(old_a, old_b)
            new_a, new_b = old_a + delta, old_b - delta
            change_a, change_b = delta, -delta
        elif match.winner_id == match.player_b_id:
            delta = elo_delta(old_b, old_a)
            new_b, new_a = old_b + delta, old_a - delta
            change_b, change_a = delta, -delta
        else:
            raise AssertionError(f"winner is not a participant on match {match.id}")
        current[match.player_a_id] = new_a
        current[match.player_b_id] = new_b
        for player_id, old, new, change in (
            (match.player_a_id, old_a, new_a, change_a),
            (match.player_b_id, old_b, new_b, change_b),
        ):
            rows.append((match.id, player_id, old, new, change))
            highest[player_id] = max(highest[player_id], STARTING_RATING, new)
    return {"current": current, "highest": highest, "rows": rows}


def month_span(start: datetime, end: datetime) -> list[tuple[int, int]]:
    year, month = start.year, start.month
    months: list[tuple[int, int]] = []
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return months


def _month_start(year: int, month: int) -> datetime:
    return datetime(year, month, 1, tzinfo=UTC)


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def competition_ranks(rows: list[dict[str, object]]) -> None:
    """Equal ratings share a rank. The next rank skips (1, 2, 2, 4)."""
    last_rating = object()
    rank = 0
    for index, row in enumerate(rows):
        if row["rating"] != last_rating:
            rank = index + 1
            last_rating = row["rating"]
        row["rank"] = rank


def monthly_snapshots(
    players: Sequence[_Player],
    matches: Iterable[_Match],
    *,
    now: datetime,
) -> dict[tuple[int, int], list[dict[str, object]]]:
    """Month-end rating, in-month record, and competition ranks. No monthly reset."""
    names = {player.id: player.display_name for player in players}
    rated = rated_matches(matches)
    if not rated:
        return {}
    played = replay(players, rated)
    history = {
        (player_id, match_id): (old, new, change)
        for match_id, player_id, old, new, change in played["rows"]  # type: ignore[union-attr]
    }
    first = ensure_utc(rated[0].match_date)
    snapshots: dict[tuple[int, int], list[dict[str, object]]] = {}
    for year, month in month_span(first, ensure_utc(now)):
        start = _month_start(year, month)
        end = _month_start(*_next_month(year, month))
        debuted: set[UUID] = set()
        latest: dict[UUID, tuple[tuple[datetime, datetime, UUID], int]] = {}
        wins: dict[UUID, int] = defaultdict(int)
        losses: dict[UUID, int] = defaultdict(int)
        played_count: dict[UUID, int] = defaultdict(int)
        change: dict[UUID, int] = defaultdict(int)
        for match in rated:
            played_at = ensure_utc(match.match_date)
            if played_at >= end:
                break
            key = match_key(match)
            for player_id in (match.player_a_id, match.player_b_id):
                debuted.add(player_id)
                _old, new, _change = history[(player_id, match.id)]
                previous = latest.get(player_id)
                if previous is None or key > previous[0]:
                    latest[player_id] = (key, new)
            if start <= played_at < end:
                for player_id in (match.player_a_id, match.player_b_id):
                    played_count[player_id] += 1
                    _old, _new, delta = history[(player_id, match.id)]
                    change[player_id] += delta
                    if match.winner_id == player_id:
                        wins[player_id] += 1
                    else:
                        losses[player_id] += 1
        rows = [
            {
                "player_id": player_id,
                "rating": latest[player_id][1],
                "wins": wins[player_id],
                "losses": losses[player_id],
                "matches_played": played_count[player_id],
                "rating_change_during_month": change[player_id],
                "name": names[player_id],
            }
            for player_id in debuted
        ]
        rows.sort(
            key=lambda row: (
                -int(row["rating"]),
                -int(row["wins"]),
                str(row["name"]).casefold(),
                str(row["name"]),
            )
        )
        competition_ranks(rows)
        snapshots[(year, month)] = rows
    return snapshots
