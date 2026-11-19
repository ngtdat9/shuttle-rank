"""Transaction boundary for mutating services.

Convention: each public mutator commits on success and rolls back on any
exception. The matching inner function (``_create_match``, ``_correct_match``,
``_cancel_match``, ``_delete_match``, ``_update_match_metadata``,
``_create_player``, ``_update_player``, ``_deactivate_player``,
``_award_achievement``) flushes and does not commit, so a caller can compose
several of them and commit once. ``recalculate_all`` commits on success.
Rating application, replay, and ``rebuild_monthly_snapshots`` also flush
only. Read functions do not commit. ``get_db`` rolls back a request that
raises and does not commit, because the public services already did.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session


@contextmanager
def transaction(db: Session) -> Iterator[None]:
    """Commit when the block finishes; roll back and re-raise on any exception."""
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise
