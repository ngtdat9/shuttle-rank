"""Match writes and public match reads.

Transaction convention
----------------------
Public mutators commit on success and roll back on any exception. Each one
is a thin wrapper around an inner function that does the work and flushes
but does not commit or roll back:

- ``create_match`` calls ``_create_match``
- ``correct_match`` calls ``_correct_match``
- ``cancel_match`` calls ``_cancel_match``
- ``delete_match`` calls ``_delete_match``
- ``update_match_metadata`` calls ``_update_match_metadata``

Call an inner function when several writes must share one transaction. A
tournament result is the case this exists for: create or correct a rated
match, update the bracket slots, and write the tournament audit row, then
commit once. Do not call the public wrapper from inside that transaction.
It would commit early and leave the bracket update on its own.

``_correct_match``, ``_cancel_match``, and ``_delete_match`` call
``tournament_service.on_match_changed(db, match, before, change=...)`` after
the match row is updated and flushed, and before rating replay. ``before``
is the pre-change snapshot. ``change`` is ``correct``, ``cancel``, or
``delete``. The hook ignores matches with no ``tournament_id``. For a tournament match it
moves the bracket with the result, or raises ``BusinessRuleError`` (the next
bracket match already has a result), and the caller's transaction rolls the
match change back. Tournament results are created by
``tournament_service.record_match``, which calls ``_create_match`` itself.

Player writes use the same split in ``player_service``: ``_create_player``,
``_update_player``, and ``_deactivate_player``. Read functions do not
commit. See also ``app.services.transactions``.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.errors import BusinessRuleError, NotFoundError
from app.models.match import Match
from app.models.player import Player
from app.models.rating_history import RatingHistory
from app.models.tournament import Tournament
from app.schemas.common import Paginated
from app.schemas.matches import Match as MatchSchema
from app.schemas.matches import PlayerMatch
from app.schemas.rankings import PlayerRatingHistory, RatingPoint
from app.services.audit import write_audit
from app.services.monthly_service import rebuild_monthly_snapshots
from app.services.ordering import ensure_utc, is_rated, match_sort_key
from app.services.rating_service import rate_new_match, replay_from
from app.services.serialize import (
    load_players,
    matches_to_read_models,
    player_matches_to_read_models,
    player_summary,
)
from app.services.transactions import transaction

_UNSET: Any = object()
_STATUSES = {"completed", "canceled", "disputed"}
_STATUS_FILTERS = _STATUSES | {"all"}


def create_match(
    db: Session,
    *,
    player_a_id: uuid.UUID,
    player_b_id: uuid.UUID,
    winner_id: uuid.UUID,
    match_date: datetime,
    status: str = "completed",
    game_scores: list[list[int]] | None = None,
    notes: str | None = None,
    created_by: str,
    tournament_id: uuid.UUID | None = None,
) -> Match:
    """Insert a match and, when it is rated, update Elo. Commits."""
    with transaction(db):
        match = _create_match(
            db,
            player_a_id=player_a_id,
            player_b_id=player_b_id,
            winner_id=winner_id,
            match_date=match_date,
            status=status,
            game_scores=game_scores,
            notes=notes,
            created_by=created_by,
            tournament_id=tournament_id,
        )
    db.refresh(match)
    return match


def _create_match(
    db: Session,
    *,
    player_a_id: uuid.UUID,
    player_b_id: uuid.UUID,
    winner_id: uuid.UUID,
    match_date: datetime,
    status: str = "completed",
    game_scores: list[list[int]] | None = None,
    notes: str | None = None,
    created_by: str,
    tournament_id: uuid.UUID | None = None,
) -> Match:
    """Insert a match and flush. Does not commit or roll back.

    A rated match updates Elo and monthly snapshots in this same session.
    The caller commits, or rolls back when this function raises.
    """
    actor = _require_actor(created_by)
    checked_status = _validate_status(status)
    _validate_participants(player_a_id, player_b_id, winner_id)
    played_at = _validate_match_date(match_date)
    scores = _validate_game_scores(game_scores)
    _validate_notes(notes)
    _ensure_players(db, [player_a_id, player_b_id], require_active=True)
    if tournament_id is not None and db.get(Tournament, tournament_id) is None:
        raise BusinessRuleError("Unknown tournament")
    match = Match(
        player_a_id=player_a_id,
        player_b_id=player_b_id,
        winner_id=winner_id,
        match_date=played_at,
        status=checked_status,
        tournament_id=tournament_id,
        game_scores=scores,
        notes=notes,
        created_by=actor,
    )
    db.add(match)
    db.flush()
    if is_rated(match):
        rate_new_match(db, match)
        rebuild_monthly_snapshots(db)
    write_audit(
        db,
        actor_id=actor,
        action="match.create",
        entity_type="match",
        entity_id=match.id,
        before_data=None,
        after_data=_snapshot(match),
    )
    db.flush()
    return match


def correct_match(
    db: Session,
    match_id: uuid.UUID,
    *,
    reason: str,
    actor: str,
    player_a_id: Any = _UNSET,
    player_b_id: Any = _UNSET,
    winner_id: Any = _UNSET,
    match_date: Any = _UNSET,
    status: Any = _UNSET,
) -> Match:
    """Apply a correction and replay from the earlier of the old and new positions.

    Commits on success. Tournament matches go through ``on_match_changed``
    before replay so the bracket can move with the result.
    """
    with transaction(db):
        match = _correct_match(
            db,
            match_id,
            reason=reason,
            actor=actor,
            player_a_id=player_a_id,
            player_b_id=player_b_id,
            winner_id=winner_id,
            match_date=match_date,
            status=status,
        )
    db.refresh(match)
    return match


def _correct_match(
    db: Session,
    match_id: uuid.UUID,
    *,
    reason: str,
    actor: str,
    player_a_id: Any = _UNSET,
    player_b_id: Any = _UNSET,
    winner_id: Any = _UNSET,
    match_date: Any = _UNSET,
    status: Any = _UNSET,
) -> Match:
    """Correct a match and flush. Does not commit or roll back."""
    actor_id = _require_actor(actor)
    reason_text = _require_reason(reason)
    match = _get_match(db, match_id)
    before = _snapshot(match)
    old_key = match_sort_key(match)
    old_players = {match.player_a_id, match.player_b_id}
    _apply_correction(
        db,
        match,
        player_a_id=player_a_id,
        player_b_id=player_b_id,
        winner_id=winner_id,
        match_date=match_date,
        status=status,
    )
    db.flush()
    _notify_match_changed(db, match, before, "correct")
    new_key = match_sort_key(match)
    replay_from(
        db,
        old_key if old_key <= new_key else new_key,
        extra_player_ids=old_players | {match.player_a_id, match.player_b_id},
    )
    rebuild_monthly_snapshots(db)
    after = _snapshot(match)
    after["reason"] = reason_text
    write_audit(
        db,
        actor_id=actor_id,
        action="match.correct",
        entity_type="match",
        entity_id=match.id,
        before_data=before,
        after_data=after,
    )
    db.flush()
    return match


def cancel_match(db: Session, match_id: uuid.UUID, reason: str, actor: str) -> Match:
    """Set status to canceled and replay ratings from this match. Commits."""
    with transaction(db):
        match = _cancel_match(db, match_id, reason, actor)
    db.refresh(match)
    return match


def _cancel_match(db: Session, match_id: uuid.UUID, reason: str, actor: str) -> Match:
    """Cancel a match and flush. Does not commit or roll back."""
    actor_id = _require_actor(actor)
    reason_text = _require_reason(reason)
    match = _get_match(db, match_id)
    before = _snapshot(match)
    cutoff = match_sort_key(match)
    players = {match.player_a_id, match.player_b_id}
    match.status = "canceled"
    db.flush()
    _notify_match_changed(db, match, before, "cancel")
    replay_from(db, cutoff, extra_player_ids=players)
    rebuild_monthly_snapshots(db)
    after = _snapshot(match)
    after["reason"] = reason_text
    write_audit(
        db,
        actor_id=actor_id,
        action="match.cancel",
        entity_type="match",
        entity_id=match.id,
        before_data=before,
        after_data=after,
    )
    db.flush()
    return match


def delete_match(db: Session, match_id: uuid.UUID, reason: str, actor: str) -> Match:
    """Soft-delete a match and replay ratings. The row stays in the database."""
    with transaction(db):
        match = _delete_match(db, match_id, reason, actor)
    db.refresh(match)
    return match


def _delete_match(db: Session, match_id: uuid.UUID, reason: str, actor: str) -> Match:
    """Soft-delete a match and flush. Does not commit or roll back."""
    actor_id = _require_actor(actor)
    reason_text = _require_reason(reason)
    match = _get_match(db, match_id)
    before = _snapshot(match)
    cutoff = match_sort_key(match)
    players = {match.player_a_id, match.player_b_id}
    match.deleted_at = datetime.now(UTC)
    db.flush()
    _notify_match_changed(db, match, before, "delete")
    replay_from(db, cutoff, extra_player_ids=players)
    rebuild_monthly_snapshots(db)
    after = _snapshot(match)
    after["reason"] = reason_text
    after["deleted"] = True
    write_audit(
        db,
        actor_id=actor_id,
        action="match.delete",
        entity_type="match",
        entity_id=match.id,
        before_data=before,
        after_data=after,
    )
    db.flush()
    return match


def update_match_metadata(
    db: Session,
    match_id: uuid.UUID,
    *,
    actor: str,
    notes: Any = _UNSET,
    game_scores: Any = _UNSET,
) -> Match:
    """Change notes or game scores. Ratings are not replayed. Commits."""
    with transaction(db):
        match = _update_match_metadata(
            db,
            match_id,
            actor=actor,
            notes=notes,
            game_scores=game_scores,
        )
    db.refresh(match)
    return match


def _update_match_metadata(
    db: Session,
    match_id: uuid.UUID,
    *,
    actor: str,
    notes: Any = _UNSET,
    game_scores: Any = _UNSET,
) -> Match:
    """Change notes or game scores and flush. Does not commit or roll back."""
    actor_id = _require_actor(actor)
    if notes is _UNSET and game_scores is _UNSET:
        raise BusinessRuleError("No match changes were provided")
    match = _get_match(db, match_id)
    before = _snapshot(match)
    if notes is not _UNSET:
        _validate_notes(notes)
        match.notes = notes
    if game_scores is not _UNSET:
        match.game_scores = _validate_game_scores(game_scores)
    db.flush()
    write_audit(
        db,
        actor_id=actor_id,
        action="match.update",
        entity_type="match",
        entity_id=match.id,
        before_data=before,
        after_data=_snapshot(match),
    )
    db.flush()
    return match


def list_matches(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    player_id: uuid.UUID | None = None,
    status: str = "completed",
    tournament_id: uuid.UUID | None = None,
    date_from: Any = None,
    date_to: Any = None,
    search: str | None = None,
    include_deleted: bool = False,
) -> Paginated[MatchSchema]:
    total, rows = _query_matches(
        db,
        page=page,
        page_size=page_size,
        player_id=player_id,
        status=status,
        tournament_id=tournament_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        include_deleted=include_deleted,
    )
    return Paginated(
        items=matches_to_read_models(db, rows),
        total=total,
        page=page,
        page_size=page_size,
    )


def get_match(db: Session, match_id: uuid.UUID) -> MatchSchema:
    match = _get_match(db, match_id)
    return matches_to_read_models(db, [match])[0]


def list_player_matches(
    db: Session,
    player_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    status: str = "completed",
) -> Paginated[PlayerMatch]:
    if db.get(Player, player_id) is None:
        raise NotFoundError("Player not found")
    total, rows = _query_matches(
        db,
        page=page,
        page_size=page_size,
        player_id=player_id,
        status=status,
        tournament_id=None,
        date_from=None,
        date_to=None,
        search=None,
    )
    return Paginated(
        items=player_matches_to_read_models(db, rows, player_id),
        total=total,
        page=page,
        page_size=page_size,
    )


def get_rating_history(db: Session, player_id: uuid.UUID) -> PlayerRatingHistory:
    if db.get(Player, player_id) is None:
        raise NotFoundError("Player not found")
    pairs = [
        (history, match)
        for history, match in db.execute(
            select(RatingHistory, Match)
            .join(Match, RatingHistory.match_id == Match.id)
            .where(RatingHistory.player_id == player_id, Match.deleted_at.is_(None))
        ).all()
        if is_rated(match)
    ]
    pairs.sort(key=lambda pair: match_sort_key(pair[1]))
    opponent_ids = {
        match.player_b_id if match.player_a_id == player_id else match.player_a_id
        for _, match in pairs
    }
    opponents = load_players(db, opponent_ids)
    points = []
    for history, match in pairs:
        opponent_id = match.player_b_id if match.player_a_id == player_id else match.player_a_id
        points.append(
            RatingPoint(
                match_id=match.id,
                match_date=match.match_date,
                old_rating=history.old_rating,
                new_rating=history.new_rating,
                rating_change=history.rating_change,
                opponent=player_summary(opponents[opponent_id]),
                result="W" if match.winner_id == player_id else "L",
            )
        )
    return PlayerRatingHistory(player_id=player_id, points=points)


def _query_matches(
    db: Session,
    *,
    page: int,
    page_size: int,
    player_id: uuid.UUID | None,
    status: str,
    tournament_id: uuid.UUID | None,
    date_from: Any,
    date_to: Any,
    search: str | None,
    include_deleted: bool = False,
) -> tuple[int, list[Match]]:
    if status not in _STATUS_FILTERS:
        raise BusinessRuleError("Invalid match status")
    if page < 1 or not 1 <= page_size <= 100:
        raise BusinessRuleError("Invalid pagination")
    if date_from is not None and date_to is not None and date_from > date_to:
        raise BusinessRuleError("date_from cannot be after date_to")

    player_a = aliased(Player)
    player_b = aliased(Player)
    statement = (
        select(Match)
        .join(player_a, Match.player_a_id == player_a.id)
        .join(player_b, Match.player_b_id == player_b.id)
    )
    if not include_deleted:
        statement = statement.where(Match.deleted_at.is_(None))
    if status != "all":
        statement = statement.where(Match.status == status)
    if player_id is not None:
        statement = statement.where(
            or_(Match.player_a_id == player_id, Match.player_b_id == player_id)
        )
    if tournament_id is not None:
        statement = statement.where(Match.tournament_id == tournament_id)
    if date_from is not None:
        start = datetime(date_from.year, date_from.month, date_from.day, tzinfo=UTC)
        statement = statement.where(Match.match_date >= start)
    if date_to is not None:
        end = datetime(date_to.year, date_to.month, date_to.day, tzinfo=UTC) + timedelta(days=1)
        statement = statement.where(Match.match_date < end)
    if search and search.strip():
        term = search.strip().lower()
        statement = statement.where(
            or_(
                func.lower(player_a.display_name).contains(term, autoescape=True),
                func.lower(player_b.display_name).contains(term, autoescape=True),
            )
        )
    statement = statement.order_by(
        Match.match_date.desc(), Match.created_at.desc(), Match.id.desc()
    )
    total = int(
        db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    )
    rows = list(db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all())
    return total, rows


def _notify_match_changed(
    db: Session,
    match: Match,
    before: dict[str, Any],
    change: str,
) -> None:
    """Ask the tournament service to update a bracket in this same transaction."""
    from app.services.tournament_service import on_match_changed

    on_match_changed(db, match, before, change=change)


def _apply_correction(db: Session, match: Match, **changes: Any) -> None:
    old_players = {match.player_a_id, match.player_b_id}
    player_a_id = match.player_a_id if changes["player_a_id"] is _UNSET else changes["player_a_id"]
    player_b_id = match.player_b_id if changes["player_b_id"] is _UNSET else changes["player_b_id"]
    winner_id = match.winner_id if changes["winner_id"] is _UNSET else changes["winner_id"]
    status = match.status if changes["status"] is _UNSET else _validate_status(changes["status"])
    if match.tournament_id is not None and (
        player_a_id != match.player_a_id or player_b_id != match.player_b_id
    ):
        raise BusinessRuleError("Players in a tournament match cannot be changed")
    _validate_participants(player_a_id, player_b_id, winner_id)
    players = _ensure_players(db, [player_a_id, player_b_id], require_active=False)
    added = {player_a_id, player_b_id} - old_players
    inactive = [player_id for player_id in added if not players[player_id].is_active]
    if inactive:
        raise BusinessRuleError(
            "Inactive players cannot be added to a match",
            details={"player_ids": sorted(str(player_id) for player_id in inactive)},
        )
    match.player_a_id = player_a_id
    match.player_b_id = player_b_id
    match.winner_id = winner_id
    match.status = status
    if changes["match_date"] is not _UNSET:
        match.match_date = _validate_match_date(changes["match_date"])


def _get_match(db: Session, match_id: uuid.UUID) -> Match:
    match = db.get(Match, match_id)
    if match is None or match.deleted_at is not None:
        raise NotFoundError("Match not found")
    return match


def _ensure_players(
    db: Session,
    player_ids: list[uuid.UUID],
    *,
    require_active: bool,
) -> dict[uuid.UUID, Player]:
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
    if require_active:
        inactive = [player.id for player in found.values() if not player.is_active]
        if inactive:
            raise BusinessRuleError(
                "Inactive players cannot be added to a match",
                details={"player_ids": sorted(str(player_id) for player_id in inactive)},
            )
    return found


def _validate_participants(
    player_a_id: uuid.UUID,
    player_b_id: uuid.UUID,
    winner_id: uuid.UUID,
) -> None:
    if player_a_id == player_b_id:
        raise BusinessRuleError("A player cannot play themselves")
    if winner_id not in (player_a_id, player_b_id):
        raise BusinessRuleError("Winner is not a participant")


def _validate_status(status: str) -> str:
    if status not in _STATUSES:
        raise BusinessRuleError("Invalid match status")
    return status


def _validate_match_date(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise BusinessRuleError("Match date must be a datetime")
    match_date = ensure_utc(value)
    if match_date > datetime.now(UTC) + timedelta(days=1):
        raise BusinessRuleError("Match date cannot be more than one day in the future")
    return match_date


def _validate_game_scores(game_scores: object) -> list[list[int]] | None:
    if game_scores is None:
        return None
    if not isinstance(game_scores, list) or not 1 <= len(game_scores) <= 5:
        raise BusinessRuleError("game_scores must contain between 1 and 5 games")
    cleaned: list[list[int]] = []
    for game in game_scores:
        if not isinstance(game, (list, tuple)) or len(game) != 2:
            raise BusinessRuleError("Each game score must be a pair of integers")
        pair: list[int] = []
        for score in game:
            if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 99:
                raise BusinessRuleError("Game scores must be integers between 0 and 99")
            pair.append(score)
        cleaned.append(pair)
    return cleaned


def _validate_notes(notes: object) -> None:
    if notes is not None and not isinstance(notes, str):
        raise BusinessRuleError("Notes must be a string")
    if notes is not None and len(notes) > 500:
        raise BusinessRuleError("Notes must be at most 500 characters")


def _require_actor(actor: str) -> str:
    if not isinstance(actor, str) or not actor.strip():
        raise BusinessRuleError("Actor is required")
    return actor.strip()


def _require_reason(reason: str) -> str:
    if not isinstance(reason, str):
        raise BusinessRuleError("Reason must be a string")
    text = reason.strip()
    if not 1 <= len(text) <= 500:
        raise BusinessRuleError("Reason must be between 1 and 500 characters")
    return text


def _snapshot(match: Match) -> dict[str, Any]:
    return {
        "id": match.id,
        "player_a_id": match.player_a_id,
        "player_b_id": match.player_b_id,
        "winner_id": match.winner_id,
        "match_date": match.match_date,
        "status": match.status,
        "tournament_id": match.tournament_id,
        "game_scores": match.game_scores,
        "notes": match.notes,
        "created_by": match.created_by,
        "deleted_at": match.deleted_at,
    }
