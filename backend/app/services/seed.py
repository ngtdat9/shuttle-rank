"""Reproducible demo club for local development.

``seed_demo`` refuses to run when ``APP_ENV`` is production. It also refuses
when the database already has players, unless ``reset`` is set. Reset deletes
application rows in foreign-key order and leaves ``admin_users`` in place.
Players, matches, and awards go through the services, so ratings are
calculated. Pairings use ``random.Random`` with a fixed seed. Tournaments
are left for the tournament seed.
"""

import random
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.achievement import Achievement, PlayerAchievement
from app.models.audit_log import AuditLog
from app.models.match import Match
from app.models.monthly_ranking import MonthlyRanking
from app.models.player import Player
from app.models.rating_history import RatingHistory
from app.models.tournament import BracketMatch, Tournament, TournamentParticipant
from app.services.achievement_service import award_achievement
from app.services.audit import write_audit
from app.services.match_service import create_match
from app.services.ordering import ensure_utc, is_rated, match_sort_key
from app.services.player_service import create_player

_ACTOR = "seed-demo"
_RNG_SEED = 20261119
_NAMES = (
    "Linh Tran",
    "Marcus Chen",
    "Priya Shah",
    "Owen Blake",
    "Hana Suzuki",
    "Diego Alvarez",
    "Nora Berg",
    "Samir Khan",
)
# Hidden only from the pairing coin-flip. Ratings still come from Elo.
_STRENGTH = (0.64, 0.58, 0.55, 0.52, 0.48, 0.45, 0.42, 0.36)
_ACHIEVEMENTS = (
    ("First Win", "Win your first club match.", "trophy", "wins", 1),
    ("Giant Slayer", "Beat a player rated well above you.", "swords", "manual", None),
    ("Hot Streak", "Win three matches in a row.", "flame", "streak", 3),
    ("Club Champion", "Finish a period at the top of the club.", "crown", "manual", None),
    ("Century", "Reach 100 career wins.", "target", "wins", 100),
)
_DELETE_ORDER = (
    PlayerAchievement,
    RatingHistory,
    MonthlyRanking,
    BracketMatch,
    TournamentParticipant,
    Match,
    AuditLog,
    Achievement,
    Tournament,
    Player,
)


class SeedError(ValueError):
    """``seed-demo`` refused to change the database."""


@dataclass(frozen=True)
class SeedSummary:
    players: int
    matches: int
    completed: int
    disputed: int
    canceled: int
    achievements: int
    awards: int
    ratings: tuple[tuple[str, int], ...]

    def render(self) -> str:
        lines = [
            "Seeded demo club",
            f"players: {self.players}",
            (
                f"matches: {self.matches} "
                f"({self.completed} completed, {self.disputed} disputed, "
                f"{self.canceled} canceled)"
            ),
            f"achievements: {self.achievements} definitions, {self.awards} awards",
            "ratings:",
        ]
        lines.extend(f"  {name}: {rating}" for name, rating in self.ratings)
        return "\n".join(lines)


def seed_demo(db: Session, *, reset: bool = False, now: datetime | None = None) -> SeedSummary:
    """Load the demo club into ``db``. Raises ``SeedError`` when refused."""
    if settings.APP_ENV == "production":
        raise SeedError("seed-demo cannot run when APP_ENV=production")
    moment = ensure_utc(now or datetime.now(UTC))
    existing = int(db.scalar(select(func.count()).select_from(Player)) or 0)
    if existing and not reset:
        raise SeedError("Database already has players. Re-run with --reset to replace them.")
    if reset:
        _delete_app_data(db)

    rng = random.Random(_RNG_SEED)
    players = [create_player(db, display_name=name, actor=_ACTOR) for name in _NAMES]
    strength = {player.id: _STRENGTH[index] for index, player in enumerate(players)}
    nights = _club_nights(moment)
    for night in nights:
        count = rng.randint(2, 4)
        for slot, (player_a, player_b) in enumerate(_pick_pairs(rng, players, count)):
            winner_is_a = rng.random() < (
                strength[player_a.id] / (strength[player_a.id] + strength[player_b.id])
            )
            winner = player_a if winner_is_a else player_b
            create_match(
                db,
                player_a_id=player_a.id,
                player_b_id=player_b.id,
                winner_id=winner.id,
                match_date=_played_at(night, slot, moment),
                status="completed",
                game_scores=_match_scores(rng, winner_is_a),
                created_by=_ACTOR,
            )

    extras = _pick_pairs(rng, players, 2)
    _create_special(
        db,
        extras[0],
        status="disputed",
        match_date=_in_the_past(nights[3] + timedelta(hours=3), moment),
        rng=rng,
    )
    _create_special(
        db,
        extras[1],
        status="canceled",
        match_date=_in_the_past(nights[8] + timedelta(hours=3), moment),
        rng=rng,
    )

    definitions = _insert_achievements(db)
    awards = _award_demo(db, players, definitions, moment)
    return _summary(db, awards)


def _create_special(
    db: Session,
    pair: tuple[Player, Player],
    *,
    status: str,
    match_date: datetime,
    rng: random.Random,
) -> None:
    player_a, player_b = pair
    winner_is_a = rng.random() < 0.5
    winner = player_a if winner_is_a else player_b
    create_match(
        db,
        player_a_id=player_a.id,
        player_b_id=player_b.id,
        winner_id=winner.id,
        match_date=match_date,
        status=status,
        game_scores=_match_scores(rng, winner_is_a),
        created_by=_ACTOR,
    )


def _delete_app_data(db: Session) -> None:
    """Remove club rows. ``admin_users`` stays. Flushes and does not commit."""
    for model in _DELETE_ORDER:
        db.execute(delete(model))
    db.flush()


def _insert_achievements(db: Session) -> dict[str, Achievement]:
    created: dict[str, Achievement] = {}
    for name, description, icon, criteria_type, criteria_value in _ACHIEVEMENTS:
        row = Achievement(
            name=name,
            description=description,
            icon=icon,
            criteria_type=criteria_type,
            criteria_value=criteria_value,
            is_active=True,
        )
        db.add(row)
        db.flush()
        write_audit(
            db,
            actor_id=_ACTOR,
            action="achievement.create",
            entity_type="achievement",
            entity_id=row.id,
            before_data=None,
            after_data={"name": name, "icon": icon, "criteria_type": criteria_type},
        )
        created[name] = row
    db.commit()
    return created


def _award_demo(
    db: Session,
    players: list[Player],
    definitions: dict[str, Achievement],
    now: datetime,
) -> int:
    matches = [match for match in db.scalars(select(Match)).all() if is_rated(match)]
    matches.sort(key=match_sort_key)
    if not matches:
        return 0
    awarded = 0
    names = {player.id: player.display_name for player in players}
    strength = {player.id: _STRENGTH[index] for index, player in enumerate(players)}

    award_achievement(
        db,
        player_id=matches[0].winner_id,
        achievement_id=definitions["First Win"].id,
        actor=_ACTOR,
        notes="Won the first recorded club match",
        awarded_at=now - timedelta(days=1),
    )
    awarded += 1

    for match in matches:
        loser_id = match.player_b_id if match.winner_id == match.player_a_id else match.player_a_id
        if strength[match.winner_id] < strength[loser_id]:
            award_achievement(
                db,
                player_id=match.winner_id,
                achievement_id=definitions["Giant Slayer"].id,
                actor=_ACTOR,
                notes="Won against a higher-rated opponent",
                awarded_at=now - timedelta(days=1),
            )
            awarded += 1
            break

    results: dict[uuid.UUID, list[bool]] = defaultdict(list)
    for match in matches:
        results[match.player_a_id].append(match.winner_id == match.player_a_id)
        results[match.player_b_id].append(match.winner_id == match.player_b_id)
    streak_ids = [player_id for player_id, flags in results.items() if _has_win_streak(flags, 3)]
    streak_ids.sort(key=lambda player_id: names[player_id])
    if streak_ids:
        award_achievement(
            db,
            player_id=streak_ids[0],
            achievement_id=definitions["Hot Streak"].id,
            actor=_ACTOR,
            notes="Three wins in a row",
            awarded_at=now - timedelta(hours=12),
        )
        awarded += 1

    champion_achievement_id = definitions["Club Champion"].id
    db.expire_all()
    ranked = list(db.scalars(select(Player)).all())
    ranked.sort(key=lambda player: (-player.current_rating, player.display_name.casefold()))
    award_achievement(
        db,
        player_id=ranked[0].id,
        achievement_id=champion_achievement_id,
        actor=_ACTOR,
        notes="Highest rating after the demo matches",
        awarded_at=now - timedelta(hours=6),
    )
    return awarded + 1


def _summary(db: Session, awards: int) -> SeedSummary:
    db.expire_all()
    players = list(db.scalars(select(Player)).all())
    players.sort(key=lambda player: (-player.current_rating, player.display_name.casefold()))
    matches = list(db.scalars(select(Match)).all())
    by_status = {status: 0 for status in ("completed", "disputed", "canceled")}
    for match in matches:
        by_status[match.status] = by_status.get(match.status, 0) + 1
    return SeedSummary(
        players=len(players),
        matches=len(matches),
        completed=by_status["completed"],
        disputed=by_status["disputed"],
        canceled=by_status["canceled"],
        achievements=len(_ACHIEVEMENTS),
        awards=awards,
        ratings=tuple((player.display_name, player.current_rating) for player in players),
    )


def _club_nights(now: datetime) -> list[datetime]:
    """Ten weekly sessions. The last one falls in the current week, in the past."""
    moment = ensure_utc(now).replace(second=0, microsecond=0)
    monday = moment.date() - timedelta(days=moment.weekday())
    wednesday = datetime(monday.year, monday.month, monday.day, 18, 0, tzinfo=UTC) + timedelta(
        days=2
    )
    if wednesday <= moment:
        last = wednesday
    else:
        last = moment - timedelta(minutes=1)
        week_start = datetime(monday.year, monday.month, monday.day, tzinfo=UTC)
        if last < week_start:
            last = week_start
    return [last - timedelta(weeks=9 - index) for index in range(10)]


def _played_at(night: datetime, slot: int, now: datetime) -> datetime:
    played = night + timedelta(minutes=40 * slot)
    if played <= now:
        return played
    return now - timedelta(minutes=5 * (4 - slot))


def _in_the_past(stamp: datetime, now: datetime) -> datetime:
    if stamp <= now:
        return stamp
    return now - timedelta(minutes=1)


def _pick_pairs(
    rng: random.Random, players: list[Player], count: int
) -> list[tuple[Player, Player]]:
    order = players[:]
    rng.shuffle(order)
    pairs: list[tuple[Player, Player]] = []
    while len(pairs) < count and len(order) >= 2:
        pairs.append((order.pop(), order.pop()))
    return pairs


def _match_scores(rng: random.Random, winner_is_a: bool) -> list[list[int]]:
    if rng.random() < 0.55:
        games = (True, True)
    else:
        games = rng.choice(((True, False, True), (False, True, True)))
    return [_game(rng, winner_is_a if flag else not winner_is_a) for flag in games]


def _game(rng: random.Random, winner_is_a: bool) -> list[int]:
    roll = rng.random()
    if roll < 0.7:
        winner_score = 21
        loser_score = rng.randint(8, 19)
    elif roll < 0.95:
        loser_score = rng.randint(20, 28)
        winner_score = loser_score + 2
    else:
        winner_score = 30
        loser_score = 29
    if winner_is_a:
        return [winner_score, loser_score]
    return [loser_score, winner_score]


def _has_win_streak(flags: list[bool], length: int) -> bool:
    run = 0
    for won in flags:
        run = run + 1 if won else 0
        if run >= length:
            return True
    return False
