"""Factories for tests and QA.

Player and match helpers go through the service layer, so ratings, history,
monthly snapshots, and audit rows stay consistent. Tournament and achievement
helpers insert rows directly because those write services are a later task.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.achievement import Achievement, PlayerAchievement
from app.models.match import Match
from app.models.player import Player
from app.models.tournament import BracketMatch, Tournament, TournamentParticipant
from app.services.match_service import create_match
from app.services.player_service import create_player


def make_player(
    db: Session,
    name: str,
    *,
    actor: str = "tester",
    avatar_url: str | None = None,
) -> Player:
    return create_player(db, display_name=name, actor=actor, avatar_url=avatar_url)


def make_match(
    db: Session,
    player_a: Player,
    player_b: Player,
    *,
    winner: Player | None = None,
    match_date: datetime | None = None,
    status: str = "completed",
    game_scores: list[list[int]] | None = None,
    notes: str | None = None,
    actor: str = "tester",
    tournament_id: uuid.UUID | None = None,
) -> Match:
    played_at = match_date or (datetime.now(UTC) - timedelta(days=1))
    return create_match(
        db,
        player_a_id=player_a.id,
        player_b_id=player_b.id,
        winner_id=(winner or player_a).id,
        match_date=played_at,
        status=status,
        game_scores=game_scores,
        notes=notes,
        created_by=actor,
        tournament_id=tournament_id,
    )


def make_tournament(
    db: Session,
    name: str,
    *,
    status: str = "draft",
    description: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> Tournament:
    tournament = Tournament(
        name=name,
        description=description,
        status=status,
        start_date=None
        if start_date is None
        else start_date.date()
        if isinstance(start_date, datetime)
        else start_date,
        end_date=None
        if end_date is None
        else end_date.date()
        if isinstance(end_date, datetime)
        else end_date,
    )
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    return tournament


def add_participant(
    db: Session,
    tournament: Tournament,
    player: Player,
    *,
    seed: int | None = None,
    final_position: int | None = None,
) -> TournamentParticipant:
    row = TournamentParticipant(
        tournament_id=tournament.id,
        player_id=player.id,
        seed=seed,
        final_position=final_position,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def add_bracket_slot(
    db: Session,
    tournament: Tournament,
    *,
    round_number: int,
    position: int,
    player_a: Player | None = None,
    player_b: Player | None = None,
    winner: Player | None = None,
    match: Match | None = None,
    is_bye: bool = False,
) -> BracketMatch:
    slot = BracketMatch(
        tournament_id=tournament.id,
        round=round_number,
        position=position,
        player_a_id=None if player_a is None else player_a.id,
        player_b_id=None if player_b is None else player_b.id,
        winner_id=None if winner is None else winner.id,
        match_id=None if match is None else match.id,
        is_bye=is_bye,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


def make_achievement(
    db: Session,
    name: str,
    *,
    description: str = "Club award",
    icon: str = "award",
    is_active: bool = True,
) -> Achievement:
    row = Achievement(name=name, description=description, icon=icon, is_active=is_active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def award(
    db: Session,
    player: Player,
    achievement: Achievement,
    *,
    awarded_at: datetime | None = None,
    notes: str | None = None,
    awarded_by: str = "tester",
) -> PlayerAchievement:
    row = PlayerAchievement(
        player_id=player.id,
        achievement_id=achievement.id,
        awarded_at=awarded_at or datetime.now(UTC),
        awarded_by=awarded_by,
        notes=notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
