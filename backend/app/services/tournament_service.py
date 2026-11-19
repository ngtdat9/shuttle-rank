"""Tournament reads, admin writes, and the bracket hook for match changes.

Public mutators commit; the ``_``-prefixed inner functions flush only.
``record_match`` creates the rated match through ``match_service._create_match``
and updates the bracket in the same transaction, so Elo is identical to a
club match. ``on_match_changed`` keeps the bracket in step when such a match
is corrected, canceled, or deleted.
"""

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models.match import Match
from app.models.player import Player
from app.models.tournament import BracketMatch as BracketSlot
from app.models.tournament import Tournament, TournamentParticipant
from app.schemas.tournaments import (
    Bracket,
    BracketMatch,
    BracketRound,
    TournamentDetail,
    TournamentListResponse,
    TournamentSummary,
)
from app.schemas.tournaments import (
    TournamentParticipant as TournamentParticipantSchema,
)
from app.services.audit import write_audit
from app.services.bracket import bracket_size, loser_position, round_count, seed_order
from app.services.ordering import ensure_utc
from app.services.serialize import load_players, player_summary
from app.services.transactions import transaction

_STATUSES = {"draft", "in_progress", "completed", "canceled"}
_MATCH_CHANGES = {"correct", "cancel", "delete"}


def on_match_changed(
    db: Session,
    match: Match,
    before: dict[str, Any],
    *,
    change: Literal["correct", "cancel", "delete"],
) -> None:
    """Move a bracket with a changed match result. Does not commit.

    ``_correct_match``, ``_cancel_match``, and ``_delete_match`` call this
    after the match row has been updated and flushed, and before rating
    replay, in the caller's transaction. ``before`` is the snapshot from
    before the update. A raised ``BusinessRuleError`` makes the caller roll
    the whole change back.

    - Matches with no tournament are ignored.
    - A still-completed match whose winner changed swaps the winner in the
      bracket. A canceled, deleted, or no-longer-completed match clears the
      result, so the bracket match goes back to ``ready``.
    - Either change is refused (422) when the next bracket match already has
      a result. Players cannot change (``_apply_correction`` enforces that).
    - Correcting a canceled match back to ``completed`` re-attaches it to the
      open bracket match for the same two players, if there is one.
    """
    if not isinstance(before, dict):
        raise BusinessRuleError("Match snapshot is missing")
    if change not in _MATCH_CHANGES:
        raise BusinessRuleError("Unknown match change")
    if match.tournament_id is None:
        return
    tournament = db.get(Tournament, match.tournament_id)
    if tournament is None:
        return
    slot = db.scalar(select(BracketSlot).where(BracketSlot.match_id == match.id))
    still_completed = change == "correct" and match.status == "completed"
    if slot is None:
        if still_completed and before.get("status") != "completed":
            _reinstate(db, tournament, match)
        return
    if still_completed:
        if match.winner_id != slot.winner_id:
            _require_next_open(db, slot)
            slot.winner_id = match.winner_id
            db.flush()
            nxt = _next_slot(db, slot)
            if nxt is not None:
                _place(nxt, slot.position, match.winner_id)
            db.flush()
            if nxt is None:
                _set_final_positions(db, tournament)
        return
    _require_next_open(db, slot)
    _clear_result(db, tournament, slot)


def list_tournaments(db: Session, *, status: str | None = None) -> TournamentListResponse:
    if status is not None and status not in _STATUSES:
        raise BusinessRuleError("Invalid tournament status")
    tournaments = list(db.scalars(select(Tournament)).all())
    if status is not None:
        tournaments = [tournament for tournament in tournaments if tournament.status == status]
    tournaments.sort(key=_list_sort_key)
    context = _context(db, [tournament.id for tournament in tournaments])
    return TournamentListResponse(
        items=[_summary(tournament, context) for tournament in tournaments]
    )


def get_tournament(db: Session, tournament_id: uuid.UUID) -> TournamentDetail:
    tournament = _get(db, tournament_id)
    context = _context(db, [tournament.id])
    summary = _summary(tournament, context)
    participants = sorted(
        context.participants.get(tournament.id, []),
        key=lambda row: (
            row.seed is None,
            row.seed if row.seed is not None else 0,
            context.players[row.player_id].display_name.casefold(),
            context.players[row.player_id].display_name,
        ),
    )
    runner = next((row for row in participants if row.final_position == 2), None)
    bracket_count = db.scalar(
        select(func.count())
        .select_from(BracketSlot)
        .where(BracketSlot.tournament_id == tournament.id)
    )
    return TournamentDetail(
        **summary.model_dump(),
        participants=[
            TournamentParticipantSchema(
                player=player_summary(context.players[row.player_id]),
                seed=row.seed,
                final_position=row.final_position,
            )
            for row in participants
        ],
        bracket_generated=bool(bracket_count),
        runner_up=None if runner is None else player_summary(context.players[runner.player_id]),
        updated_at=tournament.updated_at,
    )


def get_bracket(db: Session, tournament_id: uuid.UUID) -> Bracket:
    _get(db, tournament_id)
    slots = list(
        db.scalars(select(BracketSlot).where(BracketSlot.tournament_id == tournament_id)).all()
    )
    if not slots:
        return Bracket(tournament_id=tournament_id, rounds=[])

    player_ids = {
        player_id
        for slot in slots
        for player_id in (slot.player_a_id, slot.player_b_id)
        if player_id is not None
    }
    players = load_players(db, player_ids)
    seeds = {
        row.player_id: row.seed
        for row in db.scalars(
            select(TournamentParticipant).where(
                TournamentParticipant.tournament_id == tournament_id
            )
        ).all()
    }
    match_ids = {slot.match_id for slot in slots if slot.match_id is not None}
    matches = {}
    if match_ids:
        matches = {
            match.id: match
            for match in db.scalars(select(Match).where(Match.id.in_(match_ids))).all()
        }
    max_round = max(slot.round for slot in slots)
    grouped: dict[int, list[BracketSlot]] = defaultdict(list)
    for slot in slots:
        grouped[slot.round].append(slot)
    rounds = []
    for round_number in sorted(grouped):
        rows = sorted(grouped[round_number], key=lambda slot: slot.position)
        rounds.append(
            BracketRound(
                round=round_number,
                name=round_name(round_number, max_round),
                matches=[_bracket_match(slot, players, seeds, matches) for slot in rows],
            )
        )
    return Bracket(tournament_id=tournament_id, rounds=rounds)


def select_active_tournament(db: Session) -> TournamentSummary | None:
    """In-progress tournament if one exists, otherwise the latest draft."""
    tournaments = list(db.scalars(select(Tournament)).all())
    in_progress = [tournament for tournament in tournaments if tournament.status == "in_progress"]
    drafts = [tournament for tournament in tournaments if tournament.status == "draft"]
    pool = in_progress or drafts
    if not pool:
        return None
    pool.sort(
        key=lambda tournament: (
            tournament.start_date or date.min,
            ensure_utc(tournament.created_at),
        ),
        reverse=True,
    )
    context = _context(db, [pool[0].id])
    return _summary(pool[0], context)


def round_name(round_number: int, max_round: int) -> str:
    """Name a round by how far it sits from the final."""
    distance = max_round - round_number
    if distance == 0:
        return "Final"
    if distance == 1:
        return "Semifinals"
    if distance == 2:
        return "Quarterfinals"
    return f"Round of {2 ** (distance + 1)}"


class _Context:
    def __init__(self) -> None:
        self.participants: dict[uuid.UUID, list[TournamentParticipant]] = defaultdict(list)
        self.players: dict[uuid.UUID, Player] = {}


def _context(db: Session, tournament_ids: list[uuid.UUID]) -> _Context:
    context = _Context()
    if not tournament_ids:
        return context
    rows = list(
        db.scalars(
            select(TournamentParticipant).where(
                TournamentParticipant.tournament_id.in_(tournament_ids)
            )
        ).all()
    )
    for row in rows:
        context.participants[row.tournament_id].append(row)
    context.players = load_players(db, {row.player_id for row in rows})
    return context


def _summary(tournament: Tournament, context: _Context) -> TournamentSummary:
    participants = context.participants.get(tournament.id, [])
    champion_row = next((row for row in participants if row.final_position == 1), None)
    champion = None
    if champion_row is not None:
        champion = player_summary(context.players[champion_row.player_id])
    return TournamentSummary(
        id=tournament.id,
        name=tournament.name,
        description=tournament.description,
        format=tournament.format,  # type: ignore[arg-type]
        status=tournament.status,  # type: ignore[arg-type]
        start_date=tournament.start_date,
        end_date=tournament.end_date,
        participant_count=len(participants),
        champion=champion,
        created_at=tournament.created_at,
    )


def _bracket_match(
    slot: BracketSlot,
    players: dict[uuid.UUID, Player],
    seeds: dict[uuid.UUID, int | None],
    matches: dict[uuid.UUID, Match],
) -> BracketMatch:
    linked = matches.get(slot.match_id) if slot.match_id is not None else None
    return BracketMatch(
        id=slot.id,
        round=slot.round,
        position=slot.position,
        player_a=None if slot.player_a_id is None else player_summary(players[slot.player_a_id]),
        player_b=None if slot.player_b_id is None else player_summary(players[slot.player_b_id]),
        seed_a=None if slot.player_a_id is None else seeds.get(slot.player_a_id),
        seed_b=None if slot.player_b_id is None else seeds.get(slot.player_b_id),
        winner_id=slot.winner_id,
        is_bye=slot.is_bye,
        status=_bracket_status(slot),  # type: ignore[arg-type]
        match_id=slot.match_id,
        match_date=None if linked is None else linked.match_date,
        game_scores=None
        if linked is None or not linked.game_scores
        else _scores(linked.game_scores),
    )


def _bracket_status(slot: BracketSlot) -> str:
    if slot.is_bye:
        return "bye"
    if slot.winner_id is not None:
        return "completed"
    if slot.player_a_id is None or slot.player_b_id is None:
        return "pending"
    return "ready"


def _scores(value: object) -> list[tuple[int, int]]:
    assert isinstance(value, list)
    return [(int(game[0]), int(game[1])) for game in value]


def _get(db: Session, tournament_id: uuid.UUID) -> Tournament:
    tournament = db.get(Tournament, tournament_id)
    if tournament is None:
        raise NotFoundError("Tournament not found")
    return tournament


def _list_sort_key(tournament: Tournament) -> tuple[int, int, float]:
    in_progress_first = 0 if tournament.status == "in_progress" else 1
    if tournament.start_date is None:
        start_rank = 0
    else:
        start_rank = -tournament.start_date.toordinal()
    return (in_progress_first, start_rank, -ensure_utc(tournament.created_at).timestamp())


# ---------------------------------------------------------------------------
# Admin writes
# ---------------------------------------------------------------------------


def create_tournament(
    db: Session,
    *,
    name: str,
    actor: str,
    description: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> Tournament:
    """Create a draft tournament and write ``tournament.create``. Commits."""
    with transaction(db):
        _check_dates(start_date, end_date)
        tournament = Tournament(
            name=name,
            description=description,
            status="draft",
            start_date=start_date,
            end_date=end_date,
        )
        db.add(tournament)
        db.flush()
        _audit(db, actor, "tournament.create", tournament, None, _snapshot(tournament))
    db.refresh(tournament)
    return tournament


def update_tournament(
    db: Session, tournament_id: uuid.UUID, *, actor: str, **changes: Any
) -> Tournament:
    """Edit details or cancel (from draft or in_progress). Commits."""
    with transaction(db):
        tournament = _get(db, tournament_id)
        allowed = {"name", "description", "start_date", "end_date", "status"}
        if not changes or set(changes) - allowed:
            raise BusinessRuleError("No valid tournament changes were provided")
        before = _snapshot(tournament)
        if "status" in changes:
            if changes["status"] != "canceled":
                raise BusinessRuleError("Status can only be changed to canceled")
            if tournament.status not in ("draft", "in_progress"):
                raise ConflictError("Only draft or in-progress tournaments can be canceled")
        start = changes.get("start_date", tournament.start_date)
        end = changes.get("end_date", tournament.end_date)
        _check_dates(start, end)
        for key, value in changes.items():
            setattr(tournament, key, value)
        db.flush()
        _audit(db, actor, "tournament.update", tournament, before, _snapshot(tournament))
    db.refresh(tournament)
    return tournament


def add_participants(
    db: Session,
    tournament_id: uuid.UUID,
    entries: list[tuple[uuid.UUID, int | None]],
    *,
    actor: str,
) -> Tournament:
    """Add entrants to a draft tournament. Commits."""
    with transaction(db):
        tournament = _get(db, tournament_id)
        _require_draft(tournament)
        if not entries:
            raise BusinessRuleError("At least one participant is required")
        ids = [player_id for player_id, _ in entries]
        if len(set(ids)) != len(ids):
            raise ConflictError("A player appears more than once in the request")
        players = load_players(db, set(ids))
        missing = [str(player_id) for player_id in ids if player_id not in players]
        if missing:
            raise BusinessRuleError("Unknown player", details={"player_ids": sorted(missing)})
        inactive = [str(player.id) for player in players.values() if not player.is_active]
        if inactive:
            raise BusinessRuleError(
                "Inactive players cannot join a tournament",
                details={"player_ids": sorted(inactive)},
            )
        existing = list(
            db.scalars(
                select(TournamentParticipant).where(
                    TournamentParticipant.tournament_id == tournament.id
                )
            ).all()
        )
        taken = {row.player_id for row in existing}
        duplicates = [str(player_id) for player_id in ids if player_id in taken]
        if duplicates:
            raise ConflictError(
                "Player is already a participant", details={"player_ids": sorted(duplicates)}
            )
        seeds = [row.seed for row in existing if row.seed is not None]
        seeds += [seed for _, seed in entries if seed is not None]
        if len(set(seeds)) != len(seeds):
            raise BusinessRuleError("Seeds must be unique within a tournament")
        for player_id, seed in entries:
            db.add(
                TournamentParticipant(tournament_id=tournament.id, player_id=player_id, seed=seed)
            )
        tournament.updated_at = datetime.now(UTC)
        db.flush()
        _audit(
            db,
            actor,
            "tournament.participants_add",
            tournament,
            None,
            {"added": [{"player_id": player_id, "seed": seed} for player_id, seed in entries]},
        )
    db.refresh(tournament)
    return tournament


def remove_participant(
    db: Session, tournament_id: uuid.UUID, player_id: uuid.UUID, *, actor: str
) -> Tournament:
    """Remove an entrant from a draft tournament. Commits."""
    with transaction(db):
        tournament = _get(db, tournament_id)
        _require_draft(tournament)
        row = db.scalar(
            select(TournamentParticipant).where(
                TournamentParticipant.tournament_id == tournament.id,
                TournamentParticipant.player_id == player_id,
            )
        )
        if row is None:
            raise NotFoundError("Participant not found")
        removed = {"player_id": row.player_id, "seed": row.seed}
        db.delete(row)
        tournament.updated_at = datetime.now(UTC)
        db.flush()
        _audit(db, actor, "tournament.participant_remove", tournament, removed, None)
    db.refresh(tournament)
    return tournament


def generate_bracket(
    db: Session,
    tournament_id: uuid.UUID,
    *,
    seeding: str = "rating",
    actor: str,
) -> Tournament:
    """Build (or rebuild) the bracket and start the tournament. Commits."""
    with transaction(db):
        tournament = _get(db, tournament_id)
        if seeding not in ("rating", "manual"):
            raise BusinessRuleError("Seeding must be rating or manual")
        if tournament.status not in ("draft", "in_progress"):
            raise ConflictError(
                "A bracket can only be generated for draft or in-progress tournaments"
            )
        participants = list(
            db.scalars(
                select(TournamentParticipant).where(
                    TournamentParticipant.tournament_id == tournament.id
                )
            ).all()
        )
        if len(participants) < 2:
            raise BusinessRuleError("At least 2 participants are required")
        old_slots = list(
            db.scalars(select(BracketSlot).where(BracketSlot.tournament_id == tournament.id)).all()
        )
        if any(slot.match_id is not None for slot in old_slots):
            raise ConflictError("The bracket cannot be regenerated after a result is recorded")
        players = load_players(db, {row.player_id for row in participants})

        def by_rating(row: TournamentParticipant) -> tuple[Any, ...]:
            player = players[row.player_id]
            return (-player.current_rating, player.display_name.casefold(), str(row.player_id))

        if seeding == "rating":
            ranked = sorted(participants, key=by_rating)
        else:
            ranked = sorted(
                participants,
                key=lambda row: (row.seed is None, row.seed or 0, *by_rating(row)),
            )
        before = {
            "seeds": {str(row.player_id): row.seed for row in participants},
            "bracket_generated": bool(old_slots),
        }
        for rank, row in enumerate(ranked, start=1):
            row.seed = rank
        for slot in old_slots:
            db.delete(slot)
        db.flush()

        size = bracket_size(len(ranked))
        rounds = round_count(size)
        slots: dict[tuple[int, int], BracketSlot] = {}
        for round_number in range(1, rounds + 1):
            for position in range(size // 2**round_number):
                slot = BracketSlot(
                    tournament_id=tournament.id, round=round_number, position=position
                )
                db.add(slot)
                slots[(round_number, position)] = slot
        order = seed_order(size)
        by_seed = {rank: row.player_id for rank, row in enumerate(ranked, start=1)}
        for position in range(size // 2):
            first = slots[(1, position)]
            seed_a, seed_b = order[2 * position], order[2 * position + 1]
            first.player_a_id = by_seed.get(seed_a)
            first.player_b_id = by_seed.get(seed_b)
            if first.player_b_id is None:
                first.is_bye = True
                first.winner_id = first.player_a_id
                if rounds > 1:
                    _place(slots[(2, position // 2)], position, first.winner_id)
        tournament.status = "in_progress"
        db.flush()
        _audit(
            db,
            actor,
            "tournament.bracket_generate",
            tournament,
            before,
            {
                "seeding": seeding,
                "bracket_size": size,
                "rounds": rounds,
                "byes": size - len(ranked),
                "seeds": {str(row.player_id): row.seed for row in ranked},
                "status": tournament.status,
            },
        )
    db.refresh(tournament)
    return tournament


def record_match(
    db: Session,
    tournament_id: uuid.UUID,
    *,
    bracket_match_id: uuid.UUID,
    winner_id: uuid.UUID,
    match_date: datetime,
    game_scores: list[list[int]] | None = None,
    notes: str | None = None,
    actor: str,
) -> Match:
    """Record a bracket result as a normal rated match and advance the winner. Commits."""
    from app.services.match_service import _create_match

    with transaction(db):
        tournament = _get(db, tournament_id)
        if tournament.status != "in_progress":
            raise ConflictError("Results can only be recorded for in-progress tournaments")
        slot = db.get(BracketSlot, bracket_match_id)
        if slot is None or slot.tournament_id != tournament.id:
            raise NotFoundError("Bracket match not found")
        if (
            slot.is_bye
            or slot.winner_id is not None
            or slot.player_a_id is None
            or slot.player_b_id is None
        ):
            raise BusinessRuleError("Bracket match is not ready")
        if winner_id not in (slot.player_a_id, slot.player_b_id):
            raise BusinessRuleError("Winner must be one of the bracket match players")
        before = _slot_state(slot) | {"tournament_status": tournament.status}
        match = _create_match(
            db,
            player_a_id=slot.player_a_id,
            player_b_id=slot.player_b_id,
            winner_id=winner_id,
            match_date=match_date,
            status="completed",
            game_scores=game_scores,
            notes=notes,
            created_by=actor,
            tournament_id=tournament.id,
        )
        _apply_result(db, tournament, slot, match.id, winner_id)
        _audit(
            db,
            actor,
            "tournament.match_record",
            tournament,
            before,
            _slot_state(slot) | {"tournament_status": tournament.status},
        )
    db.refresh(match)
    return match


# ---------------------------------------------------------------------------
# Bracket helpers (flush only)
# ---------------------------------------------------------------------------


def _next_slot(db: Session, slot: BracketSlot) -> BracketSlot | None:
    return db.scalar(
        select(BracketSlot).where(
            BracketSlot.tournament_id == slot.tournament_id,
            BracketSlot.round == slot.round + 1,
            BracketSlot.position == slot.position // 2,
        )
    )


def _place(target: BracketSlot, from_position: int, player_id: uuid.UUID | None) -> None:
    """Put a winner into the next match: slot A from even positions, slot B from odd."""
    if from_position % 2 == 0:
        target.player_a_id = player_id
    else:
        target.player_b_id = player_id


def _require_next_open(db: Session, slot: BracketSlot) -> None:
    nxt = _next_slot(db, slot)
    if nxt is not None and nxt.winner_id is not None:
        raise BusinessRuleError("The next bracket match already has a result")


def _apply_result(
    db: Session,
    tournament: Tournament,
    slot: BracketSlot,
    match_id: uuid.UUID,
    winner_id: uuid.UUID,
) -> None:
    slot.match_id = match_id
    slot.winner_id = winner_id
    db.flush()
    nxt = _next_slot(db, slot)
    if nxt is not None:
        _place(nxt, slot.position, winner_id)
        db.flush()
        return
    if tournament.status == "in_progress":
        tournament.status = "completed"
    _set_final_positions(db, tournament)


def _clear_result(db: Session, tournament: Tournament, slot: BracketSlot) -> None:
    slot.winner_id = None
    slot.match_id = None
    db.flush()
    nxt = _next_slot(db, slot)
    if nxt is not None:
        _place(nxt, slot.position, None)
        db.flush()
        return
    if tournament.status == "completed":
        tournament.status = "in_progress"
    _set_final_positions(db, tournament)


def _reinstate(db: Session, tournament: Tournament, match: Match) -> None:
    pair = {match.player_a_id, match.player_b_id}
    candidates = db.scalars(
        select(BracketSlot).where(
            BracketSlot.tournament_id == tournament.id,
            BracketSlot.match_id.is_(None),
            BracketSlot.winner_id.is_(None),
        )
    ).all()
    slot = next(
        (row for row in candidates if {row.player_a_id, row.player_b_id} == pair),
        None,
    )
    if slot is None:
        raise BusinessRuleError("The bracket has no open match for these players")
    _apply_result(db, tournament, slot, match.id, match.winner_id)


def _set_final_positions(db: Session, tournament: Tournament) -> None:
    """Recompute positions from recorded results. All cleared unless the final is decided."""
    slots = list(
        db.scalars(select(BracketSlot).where(BracketSlot.tournament_id == tournament.id)).all()
    )
    rows = {
        row.player_id: row
        for row in db.scalars(
            select(TournamentParticipant).where(
                TournamentParticipant.tournament_id == tournament.id
            )
        ).all()
    }
    for row in rows.values():
        row.final_position = None
    if slots:
        max_round = max(slot.round for slot in slots)
        final = next(slot for slot in slots if slot.round == max_round)
        if final.winner_id is not None:
            rows[final.winner_id].final_position = 1
            for slot in slots:
                if slot.is_bye or slot.winner_id is None:
                    continue
                loser = slot.player_b_id if slot.winner_id == slot.player_a_id else slot.player_a_id
                if loser in rows:
                    rows[loser].final_position = loser_position(slot.round, max_round)
    db.flush()


def _slot_state(slot: BracketSlot) -> dict[str, Any]:
    return {
        "bracket_match_id": slot.id,
        "round": slot.round,
        "position": slot.position,
        "player_a_id": slot.player_a_id,
        "player_b_id": slot.player_b_id,
        "winner_id": slot.winner_id,
        "match_id": slot.match_id,
    }


def _snapshot(tournament: Tournament) -> dict[str, Any]:
    return {
        "name": tournament.name,
        "description": tournament.description,
        "format": tournament.format,
        "status": tournament.status,
        "start_date": tournament.start_date,
        "end_date": tournament.end_date,
    }


def _audit(
    db: Session,
    actor: str,
    action: str,
    tournament: Tournament,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> None:
    if not isinstance(actor, str) or not actor.strip():
        raise BusinessRuleError("Actor is required")
    write_audit(
        db,
        actor_id=actor.strip(),
        action=action,
        entity_type="tournament",
        entity_id=tournament.id,
        before_data=before,
        after_data=after,
    )
    db.flush()


def _require_draft(tournament: Tournament) -> None:
    if tournament.status != "draft":
        raise ConflictError("Participants can only be changed while the tournament is a draft")


def _check_dates(start: date | None, end: date | None) -> None:
    if start is not None and end is not None and end < start:
        raise BusinessRuleError("end_date cannot be before start_date")
