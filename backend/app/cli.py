"""Admin maintenance commands.

Run from the ``backend`` directory, after ``alembic upgrade head``:

    python -m app.cli create-admin --auth-user-id <uuid> --email <email> [--display-name NAME]
    python -m app.cli list-admins
    python -m app.cli deactivate-admin --auth-user-id <uuid>
    python -m app.cli seed-demo [--reset]

Add a later subcommand by registering another parser in ``build_parser`` and
pointing it at a handler.
"""

import argparse
import logging
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal, make_engine
from app.models.admin_user import AdminUser
from app.services.seed import seed_demo

logger = logging.getLogger(__name__)

_DISPLAY_NAME_MAX = 120
_EMAIL_MAX = 255


def _clean_auth_user_id(value: str) -> str:
    """Canonical lowercase UUID text, matching a Supabase JWT ``sub``."""
    try:
        return str(uuid.UUID(value.strip()))
    except ValueError as exc:
        raise ValueError("auth_user_id must be a UUID") from exc


def _clean_email(email: str) -> str:
    cleaned = email.strip()
    local, separator, domain = cleaned.partition("@")
    if (
        separator != "@"
        or not local
        or not domain
        or "@" in domain
        or " " in cleaned
        or len(cleaned) > _EMAIL_MAX
    ):
        raise ValueError("email must be a valid email address")
    return cleaned


def _clean_display_name(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > _DISPLAY_NAME_MAX:
        raise ValueError("display name must be at most 120 characters")
    return cleaned


def upsert_active_admin(
    session: Session,
    *,
    auth_user_id: str,
    email: str,
    display_name: str | None = None,
    update_display_name: bool = False,
) -> tuple[AdminUser, bool]:
    """Insert an active admin or refresh the existing row. Returns ``(row, created)``."""
    existing = session.scalar(select(AdminUser).where(AdminUser.auth_user_id == auth_user_id))
    email_owner = session.scalar(select(AdminUser).where(AdminUser.email == email))
    if email_owner is not None and (existing is None or email_owner.id != existing.id):
        raise ValueError("email is already used by another admin")
    if existing is None:
        admin = AdminUser(
            auth_user_id=auth_user_id,
            email=email,
            display_name=display_name,
            is_active=True,
        )
        session.add(admin)
        return admin, True
    existing.email = email
    existing.is_active = True
    if update_display_name:
        existing.display_name = display_name
    return existing, False


@contextmanager
def _session_scope() -> Iterator[Session]:
    """Short-lived engine so the CLI honours the current ``DATABASE_URL``."""
    engine = make_engine(settings.DATABASE_URL)
    session = Session(bind=engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


def bootstrap_admin() -> None:
    """Upsert one active admin from the bootstrap settings.

    Returns without raising when the settings are blank, invalid, or the
    ``admin_users`` table does not exist yet. Startup can continue before the
    first migration.
    """
    raw_id = settings.ADMIN_BOOTSTRAP_USER_ID.strip()
    raw_email = settings.ADMIN_BOOTSTRAP_EMAIL.strip()
    if not raw_id and not raw_email:
        return
    if not raw_id or not raw_email:
        logger.warning(
            "Admin bootstrap skipped; set both ADMIN_BOOTSTRAP_USER_ID and ADMIN_BOOTSTRAP_EMAIL"
        )
        return
    try:
        auth_user_id = _clean_auth_user_id(raw_id)
        email = _clean_email(raw_email)
    except ValueError:
        logger.warning(
            "Admin bootstrap skipped; ADMIN_BOOTSTRAP_USER_ID or ADMIN_BOOTSTRAP_EMAIL is invalid"
        )
        return

    session = SessionLocal()
    try:
        upsert_active_admin(
            session,
            auth_user_id=auth_user_id,
            email=email,
            update_display_name=False,
        )
        session.commit()
    except ValueError:
        session.rollback()
        logger.warning("Admin bootstrap skipped; email is already used by another admin")
    except SQLAlchemyError:
        session.rollback()
        logger.warning(
            "Admin bootstrap skipped; admin_users is not available yet",
            exc_info=True,
        )
    else:
        logger.info("Bootstrapped admin %s", auth_user_id)
    finally:
        session.close()


def _cmd_create_admin(args: argparse.Namespace) -> int:
    auth_user_id = _clean_auth_user_id(args.auth_user_id)
    email = _clean_email(args.email)
    update_display_name = args.display_name is not None
    display_name = _clean_display_name(args.display_name)
    with _session_scope() as session:
        _admin, created = upsert_active_admin(
            session,
            auth_user_id=auth_user_id,
            email=email,
            display_name=display_name,
            update_display_name=update_display_name,
        )
    verb = "Created" if created else "Updated"
    print(f"{verb} admin {auth_user_id} {email}")
    return 0


def _cmd_list_admins(_args: argparse.Namespace) -> int:
    with _session_scope() as session:
        admins = session.scalars(
            select(AdminUser).order_by(AdminUser.email, AdminUser.auth_user_id)
        ).all()
        # Copy columns before commit expires the instances.
        rendered = [
            (
                admin.auth_user_id,
                admin.email,
                admin.display_name or "-",
                "active" if admin.is_active else "inactive",
            )
            for admin in admins
        ]
    if not rendered:
        print("No admins.")
        return 0
    for auth_user_id, email, name, state in rendered:
        print(f"{auth_user_id}\t{email}\t{name}\t{state}")
    return 0


def _cmd_deactivate_admin(args: argparse.Namespace) -> int:
    auth_user_id = _clean_auth_user_id(args.auth_user_id)
    with _session_scope() as session:
        admin = session.scalar(select(AdminUser).where(AdminUser.auth_user_id == auth_user_id))
        if admin is None:
            raise ValueError(f"No admin with auth_user_id {auth_user_id}")
        admin.is_active = False
    print(f"Deactivated {auth_user_id}")
    return 0


def _cmd_seed_demo(args: argparse.Namespace) -> int:
    with _session_scope() as session:
        summary = seed_demo(session, reset=args.reset)
    print(summary.render())
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Subcommand parser. New commands are another ``add_parser`` block."""
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-admin", help="Create or update an active admin")
    create.add_argument("--auth-user-id", required=True)
    create.add_argument("--email", required=True)
    create.add_argument("--display-name", default=None)
    create.set_defaults(handler=_cmd_create_admin)

    listing = subparsers.add_parser("list-admins", help="Print admin allowlist rows")
    listing.set_defaults(handler=_cmd_list_admins)

    deactivate = subparsers.add_parser("deactivate-admin", help="Mark an admin inactive")
    deactivate.add_argument("--auth-user-id", required=True)
    deactivate.set_defaults(handler=_cmd_deactivate_admin)

    seed = subparsers.add_parser("seed-demo", help="Load a reproducible demo club")
    seed.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing app data first (refused in production)",
    )
    seed.set_defaults(handler=_cmd_seed_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except SQLAlchemyError as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
