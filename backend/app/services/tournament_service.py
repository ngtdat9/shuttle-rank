"""Tournament reads, and the hook match corrections call before replay.

Bracket writes arrive in a later task. ``on_match_changed`` is the extension
point those writes will replace: it ignores club matches and rejects
tournament matches until the bracket can move with the result.
"""

import uuid
from collections import defaultdict
from datetime import date
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
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
from app.services.ordering import ensure_utc
from app.services.serialize import load_players, player_summary

_STATUSES = {"draft", "in_progress", "completed", "canceled"}
_MATCH_CHANGES = {"correct", "cancel", "delete"}


def on_match_changed(
    db: Session,
    match: Match,
    before: dict[str, Any],
    *,
    change: Literal["correct", "cancel", "delete"],
) -> None:
    """Update a bracket after a match result changes. Does not commit.

    ``_correct_match``, ``_cancel_match``, and ``_delete_match`` call this
    after the match row has been updated and flushed, and before rating
    replay. ``before`` is the snapshot from before that update. ``change``
    is ``correct``, ``cancel``, or ``delete``. ``db`` is the caller's session.

    Matches with no tournament are ignored. A tournament match raises until
    this function updates advancement and enforces the next-slot rule. The
    caller then rolls the match change back.
    """
    if not isinstance(before, dict):
        raise BusinessRuleError("Match snapshot is missing")
    if change not in _MATCH_CHANGES:
        raise BusinessRuleError("Unknown match change")
    if match.tournament_id is None:
        return
    raise BusinessRuleError("Tournament match results are managed through the tournament bracket")


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
