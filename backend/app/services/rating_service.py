"""Apply Elo results and replay them. This is the only code that writes ratings.

Public entry points:

- ``apply_match_rating(db, match)`` rates one completed match from current
  ratings. It does not commit. A second call raises ``ConflictError``.
- ``rate_new_match(db, match)`` picks the incremental path or a replay for a
  match that was just inserted. It does not commit.
- ``replay_from(db, cutoff, extra_player_ids=None)`` rebuilds history from an
  order key onward. It does not commit. Callers rebuild monthly snapshots.
- ``recalculate_all(db)`` rebuilds every rating from scratch, rebuilds monthly
  snapshots, and commits.
"""

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError
from app.models.match import Match
from app.models.player import Player
from app.models.rating_history import RatingHistory
from app.services.elo import STARTING_RATING, apply_result
from app.services.monthly_service import rebuild_monthly_snapshots
from app.services.ordering import is_rated, match_sort_key
from app.services.transactions import transaction

OrderKey = tuple[object, object, uuid.UUID]


def apply_match_rating(db: Session, match: Match) -> None:
    """Rate one completed match from the players' current ratings.

    Does not commit. Raises ``ConflictError`` when the match already has
    rating history, and leaves the session unchanged in that case.
    """
    if not is_rated(match):
        raise BusinessRuleError("Only completed, non-deleted matches are rated")
    players = _players_by_id(db, [match.player_a_id, match.player_b_id])
    ratings = {player_id: player.current_rating for player_id, player in players.items()}
    _write_match_ratings(db, match, ratings)
    for player_id, new_rating in ratings.items():
        player = players[player_id]
        player.current_rating = new_rating
        player.highest_rating = max(player.highest_rating, new_rating)
    db.flush()


def rate_new_match(db: Session, match: Match) -> None:
    """Rate a newly inserted completed match, replaying when it is backdated."""
    if not is_rated(match):
        return
    others = [
        row for row in db.scalars(select(Match)).all() if is_rated(row) and row.id != match.id
    ]
    own_key = match_sort_key(match)
    if not others or own_key > max(match_sort_key(row) for row in others):
        apply_match_rating(db, match)
        return
    replay_from(db, own_key, extra_player_ids={match.player_a_id, match.player_b_id})


def replay_from(
    db: Session,
    cutoff: OrderKey,
    extra_player_ids: Iterable[uuid.UUID] | None = None,
) -> None:
    """Rebuild rating history for every rated match at or after ``cutoff``.

    ``cutoff`` is a ``match_sort_key`` tuple. Players in ``extra_player_ids``
    are recomputed even if they are no longer on a match at the cutoff, which
    covers a correction that swaps a participant. Does not commit.
    """
    matches = list(db.scalars(select(Match)).all())
    histories = list(db.scalars(select(RatingHistory)).all())
    match_by_id = {match.id: match for match in matches}

    before: dict[uuid.UUID, tuple[OrderKey, int]] = {}
    affected: set[uuid.UUID] = set(extra_player_ids or [])
    doomed: list[RatingHistory] = []

    for history in histories:
        match = match_by_id.get(history.match_id)
        if match is None:
            continue
        key = match_sort_key(match)
        if key < cutoff:
            previous = before.get(history.player_id)
            if previous is None or key > previous[0]:
                before[history.player_id] = (key, history.new_rating)
        else:
            affected.add(history.player_id)
            doomed.append(history)

    for match in matches:
        if match_sort_key(match) >= cutoff:
            affected.add(match.player_a_id)
            affected.add(match.player_b_id)

    for history in doomed:
        db.delete(history)
    db.flush()

    ratings: dict[uuid.UUID, int] = {player_id: row[1] for player_id, row in before.items()}
    later = [match for match in matches if is_rated(match) and match_sort_key(match) >= cutoff]
    later.sort(key=match_sort_key)
    for match in later:
        _write_match_ratings(db, match, ratings)
    db.flush()
    _recompute_stored_ratings(db, affected)


def recalculate_all(db: Session) -> None:
    """Delete all rating history and rebuild it in order. Commits on success."""
    with transaction(db):
        for history in db.scalars(select(RatingHistory)).all():
            db.delete(history)
        db.flush()
        for player in db.scalars(select(Player)).all():
            player.current_rating = STARTING_RATING
            player.highest_rating = STARTING_RATING
        db.flush()
        rated = [match for match in db.scalars(select(Match)).all() if is_rated(match)]
        rated.sort(key=match_sort_key)
        for match in rated:
            apply_match_rating(db, match)
        rebuild_monthly_snapshots(db)


def _write_match_ratings(db: Session, match: Match, ratings: dict[uuid.UUID, int]) -> None:
    """Insert both history rows from ``ratings`` and store the new ratings there.

    ``ratings`` may omit a player; the missing value is the starting rating.
    The dict is updated in place. Does not change ``Player`` rows.
    """
    if not is_rated(match):
        raise BusinessRuleError("Only completed, non-deleted matches are rated")
    db.flush()
    existing = db.scalar(
        select(RatingHistory.id).where(RatingHistory.match_id == match.id).limit(1)
    )
    if existing is not None:
        raise ConflictError("Match has already been processed")

    old_a = ratings.get(match.player_a_id, STARTING_RATING)
    old_b = ratings.get(match.player_b_id, STARTING_RATING)
    if match.winner_id == match.player_a_id:
        result = apply_result(old_a, old_b)
        new_a, new_b = result.winner_new, result.loser_new
        change_a, change_b = result.delta, -result.delta
    elif match.winner_id == match.player_b_id:
        result = apply_result(old_b, old_a)
        new_b, new_a = result.winner_new, result.loser_new
        change_b, change_a = result.delta, -result.delta
    else:
        raise BusinessRuleError("Winner is not a participant")

    db.add(
        RatingHistory(
            player_id=match.player_a_id,
            match_id=match.id,
            old_rating=old_a,
            new_rating=new_a,
            rating_change=change_a,
        )
    )
    db.add(
        RatingHistory(
            player_id=match.player_b_id,
            match_id=match.id,
            old_rating=old_b,
            new_rating=new_b,
            rating_change=change_b,
        )
    )
    ratings[match.player_a_id] = new_a
    ratings[match.player_b_id] = new_b
    try:
        db.flush()
    except IntegrityError as exc:
        raise ConflictError("Match has already been processed") from exc


def _recompute_stored_ratings(db: Session, player_ids: set[uuid.UUID]) -> None:
    """Set current and highest ratings from the history that remains."""
    if not player_ids:
        return
    players = list(db.scalars(select(Player).where(Player.id.in_(player_ids))).all())
    histories = list(
        db.scalars(select(RatingHistory).where(RatingHistory.player_id.in_(player_ids))).all()
    )
    match_ids = {history.match_id for history in histories}
    matches = {}
    if match_ids:
        matches = {
            match.id: match
            for match in db.scalars(select(Match).where(Match.id.in_(match_ids))).all()
        }
    grouped: dict[uuid.UUID, list[RatingHistory]] = {player_id: [] for player_id in player_ids}
    for history in histories:
        grouped.setdefault(history.player_id, []).append(history)

    for player in players:
        rows = grouped.get(player.id, [])
        if not rows:
            player.current_rating = STARTING_RATING
            player.highest_rating = STARTING_RATING
            continue
        rows.sort(key=lambda history: match_sort_key(matches[history.match_id]))
        player.current_rating = rows[-1].new_rating
        player.highest_rating = max(STARTING_RATING, *(row.new_rating for row in rows))
    db.flush()


def _players_by_id(db: Session, player_ids: list[uuid.UUID]) -> dict[uuid.UUID, Player]:
    unique_ids = set(player_ids)
    found = {
        player.id: player
        for player in db.scalars(select(Player).where(Player.id.in_(unique_ids))).all()
    }
    missing = unique_ids - set(found)
    if missing:
        raise BusinessRuleError(
            "Unknown player",
            details={"player_ids": sorted(str(player_id) for player_id in missing)},
        )
    return found
