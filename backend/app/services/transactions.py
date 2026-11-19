"""Transaction boundary for mutating services.

Convention: public mutating functions (``create_match``, ``correct_match``,
``cancel_match``, ``delete_match``, ``update_match_metadata``, ``create_player``,
``update_player``, ``deactivate_player``, ``recalculate_all``) commit on success
and roll back on any exception. Helpers they call — rating application, replay,
and ``rebuild_monthly_snapshots`` — flush but do not commit, so one operation
stays in a single transaction. Read functions do not commit. ``get_db`` rolls
back a request that raises and does not commit, because these services already did.
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
