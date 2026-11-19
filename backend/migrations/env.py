"""Alembic environment.

The database URL comes from ``DATABASE_URL`` or application settings, not from a
hard-coded value. SQLite migrations run in batch mode so later alterations can
rebuild tables.
"""

import os
from logging.config import fileConfig

from alembic import context

from app import models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.db.session import make_engine
from app.db.types import UTCDateTime

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def render_item(type_: str, obj: object, _autogen_context: object) -> str | bool:
    """Render the UTC type as a portable DateTime so migrations stay dialect-neutral."""
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    return False


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL") or settings.DATABASE_URL


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
        compare_type=True,
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_database_url()
    connectable = make_engine(url)
    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=url.startswith("sqlite"),
                compare_type=True,
                render_item=render_item,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
