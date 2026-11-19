"""Database constraint and UTC datetime tests on an isolated SQLite file."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Achievement, Match, Player, PlayerAchievement, RatingHistory


def _player(session: Session, name: str) -> Player:
    player = Player(display_name=name)
    session.add(player)
    session.flush()
    return player


def _match(session: Session, player_a: Player, player_b: Player, winner: Player) -> Match:
    match = Match(
        player_a_id=player_a.id,
        player_b_id=player_b.id,
        winner_id=winner.id,
        match_date=datetime.now(UTC),
        created_by="test-admin",
    )
    session.add(match)
    session.flush()
    return match


def test_sqlite_foreign_keys_are_enabled(session: Session) -> None:
    if session.get_bind().dialect.name != "sqlite":
        pytest.skip("SQLite-only PRAGMA; PostgreSQL always enforces foreign keys")
    assert session.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_utc_datetime_round_trips_as_aware_utc(session: Session) -> None:
    player = _player(session, "Ada")
    session.commit()
    session.refresh(player)
    assert player.created_at.tzinfo is not None
    assert player.created_at.utcoffset() == timedelta(0)
    assert player.updated_at.utcoffset() == timedelta(0)


def test_valid_match_is_stored(session: Session) -> None:
    ada = _player(session, "Ada")
    bob = _player(session, "Bob")
    match = _match(session, ada, bob, ada)
    session.commit()
    assert match.id is not None
    assert match.status == "completed"
    assert ada.current_rating == 1500
    assert ada.highest_rating == 1500


def test_player_cannot_play_themselves(session: Session) -> None:
    ada = _player(session, "Ada")
    session.add(
        Match(
            player_a_id=ada.id,
            player_b_id=ada.id,
            winner_id=ada.id,
            match_date=datetime.now(UTC),
            created_by="test-admin",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_winner_must_be_a_participant(session: Session) -> None:
    ada = _player(session, "Ada")
    bob = _player(session, "Bob")
    cara = _player(session, "Cara")
    session.add(
        Match(
            player_a_id=ada.id,
            player_b_id=bob.id,
            winner_id=cara.id,
            match_date=datetime.now(UTC),
            created_by="test-admin",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_foreign_key_rejects_unknown_player(session: Session) -> None:
    ada = _player(session, "Ada")
    session.add(
        Match(
            player_a_id=uuid.uuid4(),
            player_b_id=ada.id,
            winner_id=ada.id,
            match_date=datetime.now(UTC),
            created_by="test-admin",
        )
    )
    with pytest.raises(IntegrityError, match="(?i)foreign key"):
        session.commit()


def test_duplicate_rating_history_for_match_and_player_is_rejected(session: Session) -> None:
    ada = _player(session, "Ada")
    bob = _player(session, "Bob")
    match = _match(session, ada, bob, ada)
    session.add(
        RatingHistory(
            player_id=ada.id,
            match_id=match.id,
            old_rating=1500,
            new_rating=1516,
            rating_change=16,
        )
    )
    session.add(
        RatingHistory(
            player_id=ada.id,
            match_id=match.id,
            old_rating=1500,
            new_rating=1516,
            rating_change=16,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_duplicate_player_achievement_is_rejected(session: Session) -> None:
    ada = _player(session, "Ada")
    achievement = Achievement(name="First win", description="Won a match")
    session.add(achievement)
    session.flush()
    awarded_at = datetime.now(UTC)
    session.add(
        PlayerAchievement(
            player_id=ada.id,
            achievement_id=achievement.id,
            awarded_at=awarded_at,
            awarded_by="admin",
        )
    )
    session.add(
        PlayerAchievement(
            player_id=ada.id,
            achievement_id=achievement.id,
            awarded_at=awarded_at,
            awarded_by="admin",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
