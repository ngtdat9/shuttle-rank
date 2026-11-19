"""Player create, update, and deactivate. Ratings are never written here.

Each public function commits on success and rolls back on failure.
"""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models.player import Player
from app.schemas.players import PlayerListItem, PlayerListResponse, PlayerProfile
from app.services.audit import write_audit
from app.services.elo import STARTING_RATING
from app.services.monthly_service import get_player_monthly
from app.services.ranking_service import compute_standings, load_player_stats
from app.services.serialize import player_summary
from app.services.transactions import transaction

_UNSET: Any = object()
_MAX_NAME = 50
_MAX_AVATAR = 2048


def create_player(
    db: Session,
    *,
    display_name: str,
    actor: str,
    avatar_url: str | None = None,
) -> Player:
    """Create a player at the starting rating. Names are unique ignoring case."""
    actor_id = _require_actor(actor)
    name = _clean_name(display_name)
    avatar = _clean_avatar(avatar_url)
    with transaction(db):
        _ensure_name_available(db, name)
        player = Player(
            display_name=name,
            avatar_url=avatar,
            current_rating=STARTING_RATING,
            highest_rating=STARTING_RATING,
            is_active=True,
        )
        db.add(player)
        try:
            db.flush()
        except IntegrityError as exc:
            raise ConflictError("A player with this name already exists") from exc
        write_audit(
            db,
            actor_id=actor_id,
            action="player.create",
            entity_type="player",
            entity_id=player.id,
            before_data=None,
            after_data=_snapshot(player),
        )
    db.refresh(player)
    return player


def update_player(
    db: Session,
    player_id: uuid.UUID,
    *,
    actor: str,
    display_name: Any = _UNSET,
    avatar_url: Any = _UNSET,
    is_active: Any = _UNSET,
) -> Player:
    """Change name, avatar, or active flag. Omitted arguments are left as they are."""
    actor_id = _require_actor(actor)
    if display_name is _UNSET and avatar_url is _UNSET and is_active is _UNSET:
        raise BusinessRuleError("No player changes were provided")
    with transaction(db):
        player = _get_player(db, player_id)
        before = _snapshot(player)
        if display_name is not _UNSET:
            name = _clean_name(display_name)
            _ensure_name_available(db, name, exclude_id=player.id)
            player.display_name = name
        if avatar_url is not _UNSET:
            player.avatar_url = _clean_avatar(avatar_url)
        if is_active is not _UNSET:
            if not isinstance(is_active, bool):
                raise BusinessRuleError("is_active must be true or false")
            player.is_active = is_active
        try:
            db.flush()
        except IntegrityError as exc:
            raise ConflictError("A player with this name already exists") from exc
        write_audit(
            db,
            actor_id=actor_id,
            action="player.update",
            entity_type="player",
            entity_id=player.id,
            before_data=before,
            after_data=_snapshot(player),
        )
    db.refresh(player)
    return player


def deactivate_player(db: Session, player_id: uuid.UUID, *, actor: str) -> Player:
    """Mark a player inactive. History and ratings stay. The row is not deleted."""
    actor_id = _require_actor(actor)
    with transaction(db):
        player = _get_player(db, player_id)
        before = _snapshot(player)
        player.is_active = False
        db.flush()
        write_audit(
            db,
            actor_id=actor_id,
            action="player.deactivate",
            entity_type="player",
            entity_id=player.id,
            before_data=before,
            after_data=_snapshot(player),
        )
    db.refresh(player)
    return player


def list_players(
    db: Session,
    *,
    include_inactive: bool = False,
    search: str | None = None,
) -> PlayerListResponse:
    """Directory ordered by the active-player rank. Inactive players have a null rank."""
    standings = compute_standings(db, include_inactive=False)
    rank_by_id = {row.player.id: row.rank for row in standings}
    players = [row.player for row in standings]
    if include_inactive:
        inactive = list(db.scalars(select(Player).where(Player.is_active.is_(False))).all())
        inactive.sort(key=lambda player: (player.display_name.casefold(), player.display_name))
        players.extend(inactive)
    needle = (search or "").strip().casefold()
    if needle:
        players = [player for player in players if needle in player.display_name.casefold()]

    stats_by_id = load_player_stats(db)
    items: list[PlayerListItem] = []
    for player in players:
        stats = stats_by_id[player.id]
        summary = player_summary(player)
        items.append(
            PlayerListItem(
                **summary.model_dump(),
                highest_rating=player.highest_rating,
                rank=rank_by_id.get(player.id) if player.is_active else None,
                matches_played=stats.matches_played,
                wins=stats.wins,
                losses=stats.losses,
                win_rate=stats.win_rate,
            )
        )
    return PlayerListResponse(items=items)


def get_player_profile(db: Session, player_id: uuid.UUID) -> PlayerProfile:
    player = _get_player(db, player_id)
    rank = None
    if player.is_active:
        for row in compute_standings(db, include_inactive=False):
            if row.player.id == player.id:
                rank = row.rank
                break
    stats = load_player_stats(db)[player.id].as_schema()
    summary = player_summary(player)
    return PlayerProfile(
        **summary.model_dump(),
        highest_rating=player.highest_rating,
        rank=rank,
        stats=stats,
        created_at=player.created_at,
        updated_at=player.updated_at,
    )


def get_player_or_404(db: Session, player_id: uuid.UUID) -> Player:
    return _get_player(db, player_id)


def player_monthly_items(db: Session, player_id: uuid.UUID):
    _get_player(db, player_id)
    return get_player_monthly(db, player_id)


def _get_player(db: Session, player_id: uuid.UUID) -> Player:
    player = db.get(Player, player_id)
    if player is None:
        raise NotFoundError("Player not found")
    return player


def _ensure_name_available(
    db: Session,
    name: str,
    exclude_id: uuid.UUID | None = None,
) -> None:
    statement = select(Player.id).where(func.lower(Player.display_name) == name.casefold())
    if exclude_id is not None:
        statement = statement.where(Player.id != exclude_id)
    if db.scalar(statement.limit(1)) is not None:
        raise ConflictError("A player with this name already exists")


def _clean_name(display_name: str) -> str:
    if not isinstance(display_name, str):
        raise BusinessRuleError("Display name must be a string")
    name = display_name.strip()
    if not 1 <= len(name) <= _MAX_NAME:
        raise BusinessRuleError("Display name must be between 1 and 50 characters")
    return name


def _clean_avatar(avatar_url: str | None) -> str | None:
    if avatar_url is None:
        return None
    if not isinstance(avatar_url, str):
        raise BusinessRuleError("Avatar URL must be a string")
    cleaned = avatar_url.strip()
    if not cleaned:
        return None
    if len(cleaned) > _MAX_AVATAR:
        raise BusinessRuleError("Avatar URL is too long")
    return cleaned


def _require_actor(actor: str) -> str:
    if not isinstance(actor, str) or not actor.strip():
        raise BusinessRuleError("Actor is required")
    return actor.strip()


def _snapshot(player: Player) -> dict[str, Any]:
    return {
        "id": player.id,
        "display_name": player.display_name,
        "avatar_url": player.avatar_url,
        "is_active": player.is_active,
        "current_rating": player.current_rating,
        "highest_rating": player.highest_rating,
    }
