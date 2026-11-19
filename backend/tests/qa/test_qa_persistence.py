"""Writes through the services survive a new engine on the same SQLite file."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import make_engine
from app.models.match import Match
from app.models.monthly_ranking import MonthlyRanking
from app.models.player import Player
from app.models.rating_history import RatingHistory
from tests.factories import make_match, make_player


def test_service_writes_survive_a_new_session_on_the_same_file(tmp_path) -> None:
    database_path = tmp_path / "club.db"
    url = f"sqlite:///{database_path}"
    assert ":memory:" not in url

    engine = make_engine(url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    ann = make_player(session, "Persist Ann")
    bob = make_player(session, "Persist Bob")
    match = make_match(
        session,
        ann,
        bob,
        winner=ann,
        match_date=datetime(2026, 1, 4, 12, tzinfo=UTC),
        notes="kept",
    )
    ids = (ann.id, bob.id, match.id)
    session.close()
    engine.dispose()
    assert database_path.is_file()
    assert database_path.stat().st_size > 0

    reopened = make_engine(url)
    again = sessionmaker(bind=reopened, autoflush=False, autocommit=False)()
    try:
        stored_ann = again.get(Player, ids[0])
        stored_bob = again.get(Player, ids[1])
        stored_match = again.get(Match, ids[2])
        assert stored_ann is not None and stored_bob is not None and stored_match is not None
        assert stored_ann.display_name == "Persist Ann"
        assert stored_ann.current_rating == 1516
        assert stored_ann.highest_rating == 1516
        assert stored_bob.current_rating == 1484
        assert stored_bob.highest_rating == 1500
        assert stored_match.winner_id == ids[0]
        assert stored_match.notes == "kept"
        assert stored_match.status == "completed"
        history = list(
            again.scalars(select(RatingHistory).where(RatingHistory.match_id == ids[2])).all()
        )
        assert len(history) == 2
        assert {row.player_id: row.rating_change for row in history} == {ids[0]: 16, ids[1]: -16}
        months = list(again.scalars(select(MonthlyRanking)).all())
        assert months
        assert any(row.player_id == ids[0] and row.rating == 1516 for row in months)
    finally:
        again.close()
        reopened.dispose()
