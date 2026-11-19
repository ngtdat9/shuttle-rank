"""Build API schemas from rows. No business rules live here."""

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.match import Match as MatchRow
from app.models.player import Player
from app.models.rating_history import RatingHistory
from app.models.tournament import Tournament
from app.schemas.common import PlayerSummary, RatingChange
from app.schemas.matches import Match, PlayerMatch, TournamentRef
from app.services.ordering import is_rated


def player_summary(player: Player) -> PlayerSummary:
    return PlayerSummary(
        id=player.id,
        display_name=player.display_name,
        avatar_url=player.avatar_url,
        current_rating=player.current_rating,
        is_active=player.is_active,
    )


def load_players(db: Session, player_ids: set[uuid.UUID]) -> dict[uuid.UUID, Player]:
    if not player_ids:
        return {}
    return {
        player.id: player
        for player in db.scalars(select(Player).where(Player.id.in_(player_ids))).all()
    }


def matches_to_read_models(db: Session, matches: list[MatchRow]) -> list[Match]:
    if not matches:
        return []
    prepared = _prepare_matches(db, matches)
    return [_build_match(match, prepared) for match in matches]


def player_matches_to_read_models(
    db: Session,
    matches: list[MatchRow],
    player_id: uuid.UUID,
) -> list[PlayerMatch]:
    read_models = matches_to_read_models(db, matches)
    items: list[PlayerMatch] = []
    for match, model in zip(matches, read_models, strict=True):
        opponent = model.player_b if match.player_a_id == player_id else model.player_a
        result = "W" if match.winner_id == player_id else "L"
        change = next(
            (row.rating_change for row in model.rating_changes if row.player_id == player_id),
            None,
        )
        if not is_rated(match):
            change = None
        items.append(
            PlayerMatch(
                **model.model_dump(),
                opponent=opponent,
                result=result,
                rating_change=change,
            )
        )
    return items


def _prepare_matches(db: Session, matches: list[MatchRow]) -> dict[str, object]:
    player_ids: set[uuid.UUID] = set()
    tournament_ids: set[uuid.UUID] = set()
    match_ids: list[uuid.UUID] = []
    for match in matches:
        player_ids.add(match.player_a_id)
        player_ids.add(match.player_b_id)
        match_ids.append(match.id)
        if match.tournament_id is not None:
            tournament_ids.add(match.tournament_id)
    players = load_players(db, player_ids)
    tournaments = {}
    if tournament_ids:
        tournaments = {
            tournament.id: tournament
            for tournament in db.scalars(
                select(Tournament).where(Tournament.id.in_(tournament_ids))
            ).all()
        }
    grouped: dict[uuid.UUID, list[RatingHistory]] = defaultdict(list)
    for history in db.scalars(
        select(RatingHistory).where(RatingHistory.match_id.in_(match_ids))
    ).all():
        grouped[history.match_id].append(history)
    return {"players": players, "tournaments": tournaments, "history": grouped}


def _build_match(match: MatchRow, prepared: dict[str, object]) -> Match:
    players = prepared["players"]
    tournaments = prepared["tournaments"]
    history = prepared["history"]
    assert isinstance(players, dict)
    assert isinstance(tournaments, dict)
    assert isinstance(history, dict)
    rows: list[RatingHistory] = list(history.get(match.id, []))
    order = {match.player_a_id: 0, match.player_b_id: 1}
    rows.sort(key=lambda row: order.get(row.player_id, 2))
    tournament = tournaments.get(match.tournament_id) if match.tournament_id else None
    return Match(
        id=match.id,
        player_a=player_summary(players[match.player_a_id]),
        player_b=player_summary(players[match.player_b_id]),
        winner_id=match.winner_id,
        match_date=match.match_date,
        status=match.status,  # type: ignore[arg-type]
        tournament=None
        if tournament is None
        else TournamentRef(id=tournament.id, name=tournament.name),
        game_scores=_scores(match.game_scores),
        notes=match.notes,
        rating_changes=[
            RatingChange(
                player_id=row.player_id,
                old_rating=row.old_rating,
                new_rating=row.new_rating,
                rating_change=row.rating_change,
            )
            for row in rows
        ],
        deleted_at=match.deleted_at,
        created_at=match.created_at,
        updated_at=match.updated_at,
    )


def _scores(value: object) -> list[tuple[int, int]] | None:
    if not value:
        return None
    if not isinstance(value, list):
        return None
    return [(int(game[0]), int(game[1])) for game in value]
