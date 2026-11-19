"""Standings, head-to-head, and the dashboard. Stats are computed here, not stored."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.models.match import Match
from app.models.player import Player
from app.models.rating_history import RatingHistory
from app.models.tournament import Tournament
from app.schemas.common import PlayerStats, Streak
from app.schemas.dashboard import Dashboard, DashboardTotals, ProgressionPoint, RatingProgression
from app.schemas.rankings import HeadToHead, HeadToHeadStreak, RankingEntry, RankingsResponse
from app.services.achievement_service import recent_awards
from app.services.elo import STARTING_RATING
from app.services.ordering import ensure_utc, is_rated, match_sort_key
from app.services.serialize import matches_to_read_models, player_summary
from app.services.tournament_service import select_active_tournament

SORT_FIELDS = (
    "rank",
    "rating",
    "win_rate",
    "wins",
    "losses",
    "matches_played",
    "highest_rating",
)


@dataclass
class ComputedStats:
    matches_played: int
    wins: int
    losses: int
    win_rate: float | None
    current_streak: tuple[str, int] | None
    recent_form: list[str]
    last_rating_change: int | None
    rating_change_30d: int

    def as_schema(self) -> PlayerStats:
        streak = None
        if self.current_streak is not None:
            kind, count = self.current_streak
            streak = Streak(type=kind, count=count)  # type: ignore[arg-type]
        return PlayerStats(
            matches_played=self.matches_played,
            wins=self.wins,
            losses=self.losses,
            win_rate=self.win_rate,
            current_streak=streak,
            recent_form=self.recent_form,  # type: ignore[arg-type]
            last_rating_change=self.last_rating_change,
            rating_change_30d=self.rating_change_30d,
        )


@dataclass
class Standing:
    player: Player
    rank: int
    stats: ComputedStats


def load_player_stats(
    db: Session, *, now: datetime | None = None
) -> dict[uuid.UUID, ComputedStats]:
    """Stats for every player, including those who have not played."""
    moment = ensure_utc(now or datetime.now(UTC))
    cutoff = moment - timedelta(days=30)
    players = list(db.scalars(select(Player)).all())
    matches = [match for match in db.scalars(select(Match)).all() if is_rated(match)]
    matches.sort(key=match_sort_key, reverse=True)
    changes = {
        (history.player_id, history.match_id): history.rating_change
        for history in db.scalars(select(RatingHistory)).all()
    }
    grouped: dict[uuid.UUID, list[Match]] = {player.id: [] for player in players}
    for match in matches:
        if match.player_a_id in grouped:
            grouped[match.player_a_id].append(match)
        if match.player_b_id in grouped:
            grouped[match.player_b_id].append(match)

    stats: dict[uuid.UUID, ComputedStats] = {}
    for player in players:
        played = grouped.get(player.id, [])
        wins = sum(1 for match in played if match.winner_id == player.id)
        losses = len(played) - wins
        form = ["W" if match.winner_id == player.id else "L" for match in played[:5]]
        streak = _streak(["W" if match.winner_id == player.id else "L" for match in played])
        last_change = None
        if played:
            last_change = changes.get((player.id, played[0].id))
        change_30d = sum(
            changes.get((player.id, match.id), 0)
            for match in played
            if ensure_utc(match.match_date) >= cutoff
        )
        stats[player.id] = ComputedStats(
            matches_played=len(played),
            wins=wins,
            losses=losses,
            win_rate=None if not played else wins / len(played),
            current_streak=streak,
            recent_form=form,
            last_rating_change=last_change,
            rating_change_30d=change_30d,
        )
    return stats


def compute_standings(db: Session, *, include_inactive: bool) -> list[Standing]:
    """Competition ranks: rating desc, wins desc, name asc. Equal ratings share a rank."""
    stats = load_player_stats(db)
    players = list(db.scalars(select(Player)).all())
    if not include_inactive:
        players = [player for player in players if player.is_active]
    players.sort(
        key=lambda player: (
            -player.current_rating,
            -stats[player.id].wins,
            player.display_name.casefold(),
            player.display_name,
        )
    )
    standings: list[Standing] = []
    last_key: int | None = None
    rank = 0
    for index, player in enumerate(players):
        key = player.current_rating
        if key != last_key:
            rank = index + 1
            last_key = key
        standings.append(Standing(player=player, rank=rank, stats=stats[player.id]))
    return standings


def get_rankings(
    db: Session,
    *,
    include_inactive: bool = False,
    sort: str = "rank",
    order: str | None = None,
) -> RankingsResponse:
    if sort not in SORT_FIELDS:
        raise BusinessRuleError("Unknown rankings sort")
    if order not in (None, "asc", "desc"):
        raise BusinessRuleError("Unknown rankings order")
    standings = compute_standings(db, include_inactive=include_inactive)
    entries = [_entry(row) for row in standings]
    _sort_entries(entries, sort, "asc" if order is None and sort == "rank" else (order or "desc"))
    return RankingsResponse(items=entries, last_updated=latest_rated_at(db))


def get_head_to_head(db: Session, player_a_id: uuid.UUID, player_b_id: uuid.UUID) -> HeadToHead:
    if player_a_id == player_b_id:
        raise BusinessRuleError("A player cannot be compared with themselves")
    player_a = db.get(Player, player_a_id)
    player_b = db.get(Player, player_b_id)
    if player_a is None or player_b is None:
        raise NotFoundError("Player not found")

    matches = list(
        db.scalars(
            select(Match).where(
                Match.deleted_at.is_(None),
                Match.status == "completed",
                or_(
                    and_(Match.player_a_id == player_a_id, Match.player_b_id == player_b_id),
                    and_(Match.player_a_id == player_b_id, Match.player_b_id == player_a_id),
                ),
            )
        ).all()
    )
    matches.sort(key=match_sort_key, reverse=True)
    total = len(matches)
    player_a_wins = sum(1 for match in matches if match.winner_id == player_a_id)
    player_b_wins = total - player_a_wins
    changes = _changes_for(db, [match.id for match in matches])
    net = sum(changes.get((player_a_id, match.id), 0) for match in matches)
    streak = None
    if matches:
        winner_id = matches[0].winner_id
        count = 1
        for match in matches[1:]:
            if match.winner_id != winner_id:
                break
            count += 1
        streak = HeadToHeadStreak(player_id=winner_id, count=count)
    return HeadToHead(
        player_a=player_summary(player_a),
        player_b=player_summary(player_b),
        total_matches=total,
        player_a_wins=player_a_wins,
        player_b_wins=player_b_wins,
        player_a_win_rate=None if total == 0 else player_a_wins / total,
        player_b_win_rate=None if total == 0 else player_b_wins / total,
        current_streak=streak,
        player_a_net_rating_change=net,
        matches=matches_to_read_models(db, matches),
    )


def get_dashboard(db: Session) -> Dashboard:
    standings = compute_standings(db, include_inactive=False)
    entries = [_entry(row) for row in standings]
    rated = _rated_matches(db)
    now = datetime.now(UTC)
    month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
    if now.month == 12:
        month_end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
    else:
        month_end = datetime(now.year, now.month + 1, 1, tzinfo=UTC)
    active_players = db.scalar(
        select(func.count()).select_from(Player).where(Player.is_active.is_(True))
    )
    completed_tournaments = db.scalar(
        select(func.count()).select_from(Tournament).where(Tournament.status == "completed")
    )
    return Dashboard(
        leader=entries[0] if entries else None,
        top_players=entries[:5],
        totals=DashboardTotals(
            active_players=int(active_players or 0),
            total_matches=len(rated),
            matches_this_month=sum(
                1 for match in rated if month_start <= ensure_utc(match.match_date) < month_end
            ),
            tournaments_completed=int(completed_tournaments or 0),
        ),
        recent_matches=matches_to_read_models(db, list(reversed(rated[-5:]))),
        rating_progression=_progression(db, standings[:5]),
        active_tournament=select_active_tournament(db),
        recent_achievements=recent_awards(db, limit=5),
        last_updated=None if not rated else ensure_utc(rated[-1].match_date),
    )


def latest_rated_at(db: Session) -> datetime | None:
    rated = _rated_matches(db)
    if not rated:
        return None
    return ensure_utc(rated[-1].match_date)


def _rated_matches(db: Session) -> list[Match]:
    matches = [match for match in db.scalars(select(Match)).all() if is_rated(match)]
    matches.sort(key=match_sort_key)
    return matches


def _progression(db: Session, standings: list[Standing]) -> list[RatingProgression]:
    if not standings:
        return []
    player_ids = [row.player.id for row in standings]
    rows = db.execute(
        select(RatingHistory, Match)
        .join(Match, RatingHistory.match_id == Match.id)
        .where(RatingHistory.player_id.in_(player_ids))
    ).all()
    grouped: dict[uuid.UUID, list[tuple[RatingHistory, Match]]] = {
        player_id: [] for player_id in player_ids
    }
    for history, match in rows:
        if history.player_id in grouped and is_rated(match):
            grouped[history.player_id].append((history, match))
    series: list[RatingProgression] = []
    for standing in standings:
        points = [ProgressionPoint(match_date=None, rating=STARTING_RATING)]
        history_rows = grouped.get(standing.player.id, [])
        history_rows.sort(key=lambda pair: match_sort_key(pair[1]))
        for history, match in history_rows:
            points.append(ProgressionPoint(match_date=match.match_date, rating=history.new_rating))
        series.append(RatingProgression(player=player_summary(standing.player), points=points))
    return series


def _entry(standing: Standing) -> RankingEntry:
    stats = standing.stats
    return RankingEntry(
        rank=standing.rank,
        player=player_summary(standing.player),
        rating=standing.player.current_rating,
        highest_rating=standing.player.highest_rating,
        matches_played=stats.matches_played,
        wins=stats.wins,
        losses=stats.losses,
        win_rate=stats.win_rate,
        last_rating_change=stats.last_rating_change,
        rating_change_30d=stats.rating_change_30d,
        recent_form=stats.recent_form,  # type: ignore[arg-type]
    )


def _sort_entries(entries: list[RankingEntry], sort: str, order: str) -> None:
    reverse = order == "desc"
    if sort == "win_rate":

        def win_rate_key(entry: RankingEntry) -> tuple[int, float]:
            if entry.win_rate is None:
                return (1, 0.0)
            value = -entry.win_rate if reverse else entry.win_rate
            return (0, value)

        entries.sort(key=win_rate_key)
        return
    if sort == "rank":
        entries.sort(key=lambda entry: entry.rank, reverse=reverse)
        return
    entries.sort(key=lambda entry: getattr(entry, sort), reverse=reverse)


def _streak(results: list[str]) -> tuple[str, int] | None:
    if not results:
        return None
    first = results[0]
    count = 1
    for result in results[1:]:
        if result != first:
            break
        count += 1
    return first, count


def _changes_for(db: Session, match_ids: list[uuid.UUID]) -> dict[tuple[uuid.UUID, uuid.UUID], int]:
    if not match_ids:
        return {}
    return {
        (history.player_id, history.match_id): history.rating_change
        for history in db.scalars(
            select(RatingHistory).where(RatingHistory.match_id.in_(match_ids))
        ).all()
    }
