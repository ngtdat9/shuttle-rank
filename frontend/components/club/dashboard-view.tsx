import Link from "next/link";

import { AchievementIcon } from "@/components/achievement-icon";
import { RatingChart, type RatingPoint, type RatingSeries } from "@/components/charts/rating-chart";
import { isWinner, ratingChangeFor } from "@/components/club/match-utils";
import { PlayerInline } from "@/components/club/player-inline";
import { cardClass, heroCardClass, QuietEmpty, textActionClass } from "@/components/club/styles";
import { FormGuide } from "@/components/form-guide";
import { LoadError } from "@/components/load-error";
import { LocalDateTime } from "@/components/local-time";
import { RankBadge } from "@/components/rank-badge";
import { RatingDelta } from "@/components/rating-delta";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getDashboard } from "@/lib/api/client";
import {
  formatDate,
  formatDelta,
  formatRank,
  formatRating,
  formatRecord,
  formatWinRate,
} from "@/lib/format";
import { errorCopy, loadData } from "@/lib/load";
import { cn } from "@/lib/utils";
import type { Match, RankingEntry, RatingProgressionSeries } from "@/types/api";

function timeKey(iso: string): string {
  const ms = Date.parse(iso);
  if (Number.isNaN(ms)) return iso;
  return String(ms).padStart(16, "0");
}

function progressionSeries(series: RatingProgressionSeries[]): RatingSeries[] {
  return series.map((entry) => ({
    name: entry.player.display_name,
    points: entry.points.map((point): RatingPoint =>
      point.match_date
        ? {
            date: point.match_date,
            rating: point.rating,
            label: point.match_date,
            sortKey: timeKey(point.match_date),
          }
        : { date: "start", rating: point.rating, label: "Start", sortKey: "0" },
    ),
  }));
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <div>
      <p className="text-[28px] leading-none font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function LeaderCard({ leader }: { leader: RankingEntry | null }) {
  if (!leader) {
    return (
      <section className={heroCardClass}>
        <p className="text-xs text-muted-foreground">Leader</p>
        <p className="mt-3 text-sm text-muted-foreground">No players yet.</p>
      </section>
    );
  }

  return (
    <section className={heroCardClass}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex h-5 items-center rounded-full bg-primary/15 px-2 text-xs font-medium text-positive">
          Leader
        </span>
        <RankBadge rank={leader.rank} />
        {leader.recent_form.length > 0 ? (
          <FormGuide results={leader.recent_form} order="newest-first" />
        ) : null}
      </div>
      <div className="mt-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold">{leader.player.display_name}</h2>
          <p className="mt-3 text-[56px] leading-none font-semibold tabular-nums">
            {formatRating(leader.rating)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">Elo</p>
        </div>
        <PlayerInline player={leader.player} size="lg" showInactive={false} />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-muted-foreground">W–L</dt>
          <dd className="tabular-nums">{formatRecord(leader.wins, leader.losses)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Win rate</dt>
          <dd className="tabular-nums">{formatWinRate(leader.win_rate)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Highest</dt>
          <dd className="tabular-nums">{formatRating(leader.highest_rating)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Last change</dt>
          <dd>
            <RatingDelta value={leader.last_rating_change} />
          </dd>
        </div>
      </dl>
      <Button asChild className="mt-5 h-11 px-4 md:h-10">
        <Link href={`/players/${leader.player.id}`}>View profile</Link>
      </Button>
    </section>
  );
}

function LatestResult({ match }: { match: Match }) {
  const winner = isWinner(match, match.player_a.id) ? match.player_a : match.player_b;
  const loser = winner.id === match.player_a.id ? match.player_b : match.player_a;
  return (
    <p className="mt-4 text-sm">
      <span className="font-medium">{winner.display_name}</span> beat{" "}
      <span className="text-muted-foreground">{loser.display_name}</span>
      <span className="mt-1 block text-muted-foreground">
        <LocalDateTime value={match.match_date} />
      </span>
      <span className="mt-2 flex flex-wrap gap-3">
        <span>
          {winner.display_name} <RatingDelta value={ratingChangeFor(match, winner.id)} />
        </span>
        <span>
          {loser.display_name} <RatingDelta value={ratingChangeFor(match, loser.id)} />
        </span>
      </span>
    </p>
  );
}

export async function DashboardView() {
  const result = await loadData(getDashboard());
  if (!result.ok) {
    const copy = errorCopy(result.error, "the dashboard");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  const data = result.data;
  const latest = data.recent_matches[0];
  const series = progressionSeries(data.rating_progression);
  const leader = data.leader;
  const leaderSummary = leader
    ? `${leader.player.display_name} is at ${formatRating(leader.rating)}, last change ${formatDelta(leader.last_rating_change)}.`
    : "No leader yet.";

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-5">
      <section className={cn(heroCardClass, "lg:col-span-7")}>
        <p className="text-xs text-muted-foreground">Club</p>
        <h1 className="mt-2 text-[28px] leading-[34px] font-semibold">Shuttle Rank</h1>
        <p className="mt-1 text-sm text-muted-foreground">Men&apos;s singles</p>
        {latest ? <LatestResult match={latest} /> : (
          <p className="mt-4 text-sm text-muted-foreground">No completed matches yet.</p>
        )}
        <div className="mt-6 grid grid-cols-3 gap-3">
          <Stat value={data.totals.active_players} label="Players" />
          <Stat value={data.totals.total_matches} label="Matches" />
          <Stat value={data.totals.matches_this_month} label="This month" />
        </div>
        {data.last_updated ? (
          <p className="mt-4 text-xs text-muted-foreground">
            Updated <LocalDateTime value={data.last_updated} />
          </p>
        ) : null}
      </section>

      <div className="lg:col-span-5">
        <LeaderCard leader={leader} />
      </div>

      <section className={cn(cardClass, "lg:col-span-5")}>
        <h2 className="text-lg font-semibold">Elo rating progression</h2>
        <p className="mt-1 text-xs text-muted-foreground">From the 1500 start.</p>
        <div className="mt-4">
          {series.length === 0 ? (
            <QuietEmpty>Ratings show up after the first completed match.</QuietEmpty>
          ) : (
            <RatingChart series={series} />
          )}
        </div>
        <p className="sr-only">{leaderSummary}</p>
      </section>

      <section className={cn(cardClass, "lg:col-span-7")}>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Club leaderboard</h2>
          <Link href="/leaderboard" className={textActionClass}>
            View all
          </Link>
        </div>
        {data.top_players.length === 0 ? (
          <QuietEmpty className="mt-4">No players yet.</QuietEmpty>
        ) : (
          <>
            <div className="mt-4 hidden md:block">
              <Table>
                <caption className="sr-only">Top five players</caption>
                <TableHeader>
                  <TableRow>
                    <TableHead>Rank</TableHead>
                    <TableHead>Player</TableHead>
                    <TableHead className="text-right">Elo</TableHead>
                    <TableHead className="text-right">W–L</TableHead>
                    <TableHead className="text-right">Win rate</TableHead>
                    <TableHead className="text-right">Last change</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.top_players.map((entry) => (
                    <TableRow key={entry.player.id} className="relative">
                      <TableCell className="text-muted-foreground tabular-nums">
                        {formatRank(entry.rank)}
                      </TableCell>
                      <TableCell>
                        <Link
                          href={`/players/${entry.player.id}`}
                          className="static rounded-full after:absolute after:inset-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <PlayerInline player={entry.player} showInactive={false} />
                        </Link>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatRating(entry.rating)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatRecord(entry.wins, entry.losses)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatWinRate(entry.win_rate)}
                      </TableCell>
                      <TableCell className="text-right">
                        <RatingDelta value={entry.last_rating_change} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <ul className="mt-4 flex flex-col gap-2 md:hidden">
              {data.top_players.map((entry) => (
                <li key={entry.player.id}>
                  <Link
                    href={`/players/${entry.player.id}`}
                    className="block rounded-2xl bg-elevated/40 px-3 py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className="flex items-center justify-between gap-3">
                      <span className="flex min-w-0 items-center gap-2">
                        <span className="text-muted-foreground tabular-nums">
                          {formatRank(entry.rank)}
                        </span>
                        <PlayerInline player={entry.player} showInactive={false} />
                      </span>
                      <span className="tabular-nums">{formatRating(entry.rating)}</span>
                    </span>
                    <span className="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                      <span className="tabular-nums">{formatRecord(entry.wins, entry.losses)}</span>
                      <span className="tabular-nums">{formatWinRate(entry.win_rate)}</span>
                      <RatingDelta value={entry.last_rating_change} />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className={cn(cardClass, "lg:col-span-7")}>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Recent matches</h2>
          <Link href="/matches" className={textActionClass}>
            All matches
          </Link>
        </div>
        {data.recent_matches.length === 0 ? (
          <QuietEmpty className="mt-4">No completed matches yet.</QuietEmpty>
        ) : (
          <ul className="mt-3 divide-y divide-border">
            {data.recent_matches.map((match) => {
              const aWins = isWinner(match, match.player_a.id);
              return (
                <li key={match.id}>
                  <Link
                    href={`/matches/${match.id}`}
                    className="flex flex-col gap-1 rounded-xl py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className="text-xs text-muted-foreground">
                      <LocalDateTime value={match.match_date} withTime={false} />
                      {match.tournament ? ` · ${match.tournament.name}` : ""}
                    </span>
                    <span className="text-sm">
                      <span className={aWins ? "text-foreground" : "text-muted-foreground"}>
                        {match.player_a.display_name}
                      </span>
                      <span className="text-muted-foreground"> vs </span>
                      <span className={!aWins ? "text-foreground" : "text-muted-foreground"}>
                        {match.player_b.display_name}
                      </span>
                    </span>
                    <span className="flex flex-wrap gap-3 text-sm">
                      <RatingDelta value={ratingChangeFor(match, match.player_a.id)} />
                      <RatingDelta value={ratingChangeFor(match, match.player_b.id)} />
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <div className="flex flex-col gap-4 lg:col-span-5 lg:gap-5">
        <section className={cardClass}>
          <h2 className="text-lg font-semibold">Tournament</h2>
          {data.active_tournament ? (
            <div className="mt-3 flex flex-col gap-2">
              <StatusBadge status={data.active_tournament.status} />
              <p className="font-medium">{data.active_tournament.name}</p>
              <p className="text-sm text-muted-foreground">
                {data.active_tournament.status === "draft"
                  ? "Not started"
                  : data.active_tournament.status === "in_progress"
                    ? "In progress"
                    : data.active_tournament.status}
                {data.active_tournament.start_date
                  ? ` · ${formatDate(data.active_tournament.start_date, undefined, "en-US")}`
                  : ""}
              </p>
              <p className="text-sm">{data.active_tournament.participant_count} players</p>
              <Link href={`/tournaments/${data.active_tournament.id}`} className={textActionClass}>
                View tournament
              </Link>
            </div>
          ) : (
            <div className="mt-3 flex flex-col gap-2">
              <QuietEmpty>No tournament in progress</QuietEmpty>
              <Link href="/tournaments" className={textActionClass}>
                All tournaments
              </Link>
            </div>
          )}
          <p className="mt-3 text-xs text-muted-foreground">
            {data.totals.tournaments_completed} completed
          </p>
        </section>

        <section className={cardClass}>
          <h2 className="text-lg font-semibold">Recent achievements</h2>
          {data.recent_achievements.length === 0 ? (
            <QuietEmpty className="mt-3">No achievements yet.</QuietEmpty>
          ) : (
            <ul className="mt-3 divide-y divide-border">
              {data.recent_achievements.map((award) => (
                <li key={award.id}>
                  <Link
                    href={`/players/${award.player.id}`}
                    className="flex items-center gap-3 py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className="grid size-8 place-items-center rounded-full bg-elevated text-foreground">
                      <AchievementIcon name={award.achievement.icon} />
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium">
                        {award.achievement.name}
                      </span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {award.player.display_name} · <LocalDateTime value={award.awarded_at} withTime={false} />
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
