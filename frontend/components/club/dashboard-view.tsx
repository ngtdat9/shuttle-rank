import Link from "next/link";
import { ArrowRight, Trophy } from "lucide-react";

import { AchievementIcon } from "@/components/achievement-icon";
import { RatingChart, type RatingPoint, type RatingSeries } from "@/components/charts/rating-chart";
import { isWinner, ratingChangeFor } from "@/components/club/match-utils";
import { PlayerAvatar } from "@/components/player-avatar";
import { cardClass, heroCardClass, QuietEmpty, textActionClass } from "@/components/club/styles";
import { FormGuide } from "@/components/form-guide";
import { LoadError } from "@/components/load-error";
import { LocalDateTime } from "@/components/local-time";
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
  formatGameScores,
  formatRank,
  formatRating,
  formatRecord,
  formatWinRate,
} from "@/lib/format";
import { errorCopy, loadData } from "@/lib/load";
import { SERIES_COLORS } from "@/lib/series-colors";
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

function StatTile({ value, label }: { value: number; label: string }) {
  return (
    <div className="sr-panel flex flex-col justify-between gap-4 rounded-[24px] p-4 md:gap-[18px] md:rounded-[28px] md:p-6">
      <p className="text-[11px] font-medium tracking-wider text-muted-foreground uppercase md:text-xs">
        {label}
      </p>
      <p className="font-mono text-4xl leading-none font-semibold tracking-tight tabular-nums md:text-5xl">
        {value}
      </p>
    </div>
  );
}

function LeaderCard({
  leader,
  updatedAt,
  accent,
}: {
  leader: RankingEntry | null;
  updatedAt: string | null;
  accent: string;
}) {
  if (!leader) {
    return (
      <section className={cn(heroCardClass, "flex min-h-[200px] flex-col gap-3")}>
        <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
          Club leader
        </p>
        <p className="text-sm text-muted-foreground">No players yet.</p>
        {updatedAt ? (
          <p className="text-xs text-muted-foreground">
            Updated <LocalDateTime value={updatedAt} />
          </p>
        ) : null}
      </section>
    );
  }

  return (
    <section
      aria-label="Club leader"
      className={cn(heroCardClass, "flex min-h-[340px] flex-col justify-between gap-6 md:gap-6")}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="inline-flex h-7 items-center gap-1.5 rounded-full border border-primary/45 bg-primary/20 px-3 text-xs font-semibold tracking-wide text-[#d4ffb0]">
          <Trophy className="size-3.5" aria-hidden />
          Club leader
        </span>
        {updatedAt ? (
          <span className="inline-flex h-7 items-center rounded-full border border-white/20 bg-white/10 px-3 text-xs font-semibold">
            Updated&nbsp;
            <LocalDateTime value={updatedAt} />
          </span>
        ) : null}
      </div>

      <div className="flex flex-wrap items-end justify-between gap-6">
        <div className="flex min-w-0 flex-col gap-3">
          <div className="flex min-w-0 items-center gap-3.5">
            <PlayerAvatar
              name={leader.player.display_name}
              imageUrl={leader.player.avatar_url}
              size="lg"
              accent={accent}
              className="data-[size=lg]:size-12 md:data-[size=lg]:size-14"
            />
            <h2 className="min-w-0 text-[28px] leading-[1.1] font-bold tracking-tight text-balance md:text-[40px]">
              {leader.player.display_name}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {leader.recent_form.length > 0 ? (
              <FormGuide results={leader.recent_form} order="newest-first" />
            ) : null}
            <span className="text-sm text-foreground/85 md:ml-1.5">
              <span className="tabular-nums">{formatRecord(leader.wins, leader.losses)}</span>
              {" · "}
              <span className="tabular-nums">{formatWinRate(leader.win_rate)}</span> win rate
              {" · Highest "}
              <span className="tabular-nums">{formatRating(leader.highest_rating)}</span>
            </span>
          </div>
        </div>
        <div className="flex flex-col gap-1 md:items-end">
          <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
            Elo rating
          </p>
          <p className="font-mono text-[60px] leading-[0.9] font-semibold tracking-[-0.04em] tabular-nums md:text-[76px]">
            {formatRating(leader.rating)}
          </p>
          <p className="flex flex-wrap items-center gap-x-1.5 text-sm font-semibold md:justify-end">
            <RatingDelta value={leader.last_rating_change} />
            <span className="font-normal text-muted-foreground">last match ·</span>
            <RatingDelta value={leader.rating_change_30d} />
            <span className="font-normal text-muted-foreground">in 30 days</span>
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2.5">
        <Button asChild className="h-12 px-5 text-[15px] font-semibold md:h-11 md:text-sm">
          <Link href={`/players/${leader.player.id}`}>
            View profile
            <ArrowRight aria-hidden />
          </Link>
        </Button>
        <Button
          asChild
          variant="outline"
          className="h-12 px-5 text-[15px] font-semibold md:h-11 md:text-sm"
        >
          <Link href="/leaderboard">Full leaderboard</Link>
        </Button>
      </div>
    </section>
  );
}

/** Game scores read player A first in the API; show them winner first for the "def." line. */
function winnerFirstScores(match: Match, aWins: boolean): string | null {
  const scores = match.game_scores;
  if (!scores || scores.length === 0) return null;
  return formatGameScores(aWins ? scores : scores.map(([a, b]): [number, number] => [b, a]));
}

export async function DashboardView() {
  const result = await loadData(getDashboard());
  if (!result.ok) {
    const copy = errorCopy(result.error, "the dashboard");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  const data = result.data;
  const series = progressionSeries(data.rating_progression);
  const leader = data.leader;
  const leaderSummary = leader
    ? `${leader.player.display_name} is at ${formatRating(leader.rating)}, last change ${formatDelta(leader.last_rating_change)}.`
    : "No leader yet.";
  // Same palette as the chart lines, so an avatar matches its line.
  const accentById = new Map<string, string>();
  data.rating_progression.forEach((entry, index) => {
    accentById.set(entry.player.id, SERIES_COLORS[index % SERIES_COLORS.length] ?? SERIES_COLORS[0]);
  });
  const accentFor = (id: string, fallbackIndex: number) =>
    accentById.get(id) ?? SERIES_COLORS[fallbackIndex % SERIES_COLORS.length] ?? SERIES_COLORS[0];

  return (
    <div className="flex flex-col gap-4 md:gap-5">
      <h1 className="sr-only">Shuttle Rank dashboard</h1>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] md:gap-5">
        <LeaderCard
          leader={leader}
          updatedAt={data.last_updated}
          accent={leader ? accentFor(leader.player.id, 0) : SERIES_COLORS[0]}
        />
        <section aria-label="Club totals" className="grid grid-cols-2 gap-4 md:gap-5">
          <StatTile value={data.totals.active_players} label="Active players" />
          <StatTile value={data.totals.total_matches} label="Matches played" />
          <StatTile value={data.totals.matches_this_month} label="This month" />
          <StatTile value={data.totals.tournaments_completed} label="Tournaments completed" />
        </section>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] md:gap-5">
        <section className={cn(cardClass, "md:p-7")}>
          <h2 className="text-lg font-semibold md:text-xl">Elo rating progression</h2>
          <p className="mt-1 text-xs text-muted-foreground">From the 1500 start.</p>
          <div className="mt-4">
            {series.length === 0 ? (
              <QuietEmpty>Ratings show up after the first completed match.</QuietEmpty>
            ) : (
              <RatingChart series={series} height={340} />
            )}
          </div>
          <p className="sr-only">{leaderSummary}</p>
        </section>

        <section className={cn(cardClass, "md:p-7")}>
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold md:text-xl">Recent matches</h2>
            <Link href="/matches" className={textActionClass}>
              View all
            </Link>
          </div>
          {data.recent_matches.length === 0 ? (
            <QuietEmpty className="mt-4">No completed matches yet.</QuietEmpty>
          ) : (
            <ul className="mt-3 flex flex-col gap-2.5">
              {data.recent_matches.map((match) => {
                const aWins = isWinner(match, match.player_a.id);
                const winner = aWins ? match.player_a : match.player_b;
                const loser = aWins ? match.player_b : match.player_a;
                const scores = winnerFirstScores(match, aWins);
                return (
                  <li key={match.id}>
                    <Link
                      href={`/matches/${match.id}`}
                      className="sr-inset sr-lift flex flex-col gap-1.5 rounded-[18px] px-4 py-3.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <span className="text-xs text-muted-foreground">
                        <LocalDateTime value={match.match_date} withTime={false} />
                        {match.tournament ? ` · ${match.tournament.name}` : ""}
                      </span>
                      <span className="flex items-center justify-between gap-2 text-sm">
                        <span className="min-w-0 truncate font-semibold">{winner.display_name}</span>
                        <RatingDelta value={ratingChangeFor(match, winner.id)} className="font-semibold" />
                      </span>
                      <span className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-[13px] text-muted-foreground">
                        <span className="flex min-w-0 items-center gap-2">
                          <span className="truncate">def. {loser.display_name}</span>
                          <RatingDelta value={ratingChangeFor(match, loser.id)} className="text-[13px]" />
                        </span>
                        {scores ? <span className="tabular-nums">{scores}</span> : null}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] md:gap-5">
        <section className={cn(cardClass, "p-3 pt-5 md:p-4 md:pt-6")}>
          <div className="flex flex-wrap items-center justify-between gap-3 px-2 pb-3 md:px-3">
            <h2 className="text-lg font-semibold md:text-xl">Club leaderboard</h2>
            <Button asChild variant="outline" className="h-10 px-4 text-sm font-semibold">
              <Link href="/leaderboard">
                View all<span className="hidden sm:inline">&nbsp;{data.totals.active_players} players</span>
              </Link>
            </Button>
          </div>
          {data.top_players.length === 0 ? (
            <QuietEmpty className="px-2 pb-2">No players yet.</QuietEmpty>
          ) : (
            <>
              <div className="hidden md:block">
                <Table>
                  <caption className="sr-only">Top five players</caption>
                  <TableHeader>
                    <TableRow className="border-0 hover:bg-transparent">
                      <TableHead className="text-xs tracking-wider uppercase">Rank</TableHead>
                      <TableHead className="text-xs tracking-wider uppercase">Player</TableHead>
                      <TableHead className="text-right text-xs tracking-wider uppercase">W–L</TableHead>
                      <TableHead className="text-right text-xs tracking-wider uppercase">Win rate</TableHead>
                      <TableHead className="text-right text-xs tracking-wider uppercase">Last change</TableHead>
                      <TableHead className="text-right text-xs tracking-wider uppercase">Elo</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.top_players.map((entry, index) => {
                      const isLeader = leader?.player.id === entry.player.id;
                      return (
                        <TableRow
                          key={entry.player.id}
                          className={cn(
                            "relative h-[60px] border-0",
                            isLeader && "bg-primary/10 shadow-[inset_0_0_0_1px_rgba(166,243,107,0.3)] hover:bg-primary/15",
                          )}
                        >
                          <TableCell
                            className={cn(
                              "rounded-l-2xl px-3 font-semibold tabular-nums",
                              isLeader ? "text-[#c6ff9a]" : "text-foreground",
                            )}
                          >
                            {formatRank(entry.rank)}
                          </TableCell>
                          <TableCell>
                            <Link
                              href={`/players/${entry.player.id}`}
                              className="static inline-flex min-w-0 items-center gap-3 rounded-full font-semibold after:absolute after:inset-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                              <PlayerAvatar
                                name={entry.player.display_name}
                                imageUrl={entry.player.avatar_url}
                                accent={accentFor(entry.player.id, index)}
                                className="size-9"
                              />
                              <span className="truncate">{entry.player.display_name}</span>
                            </Link>
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
                          <TableCell className="rounded-r-2xl px-3 text-right text-lg font-semibold tabular-nums">
                            {formatRating(entry.rating)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
              <ul className="flex flex-col gap-0.5 md:hidden">
                {data.top_players.map((entry, index) => {
                  const isLeader = leader?.player.id === entry.player.id;
                  return (
                    <li key={entry.player.id}>
                      <Link
                        href={`/players/${entry.player.id}`}
                        className={cn(
                          "sr-lift grid min-h-14 grid-cols-[30px_minmax(0,1fr)_auto] items-center gap-2.5 rounded-[14px] px-3 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                          isLeader && "bg-primary/10 shadow-[inset_0_0_0_1px_rgba(166,243,107,0.3)]",
                        )}
                      >
                        <span
                          className={cn(
                            "font-semibold tabular-nums",
                            isLeader && "text-[#c6ff9a]",
                          )}
                        >
                          {formatRank(entry.rank)}
                        </span>
                        <span className="flex min-w-0 items-center gap-2.5">
                          <PlayerAvatar
                            name={entry.player.display_name}
                            imageUrl={entry.player.avatar_url}
                            accent={accentFor(entry.player.id, index)}
                          />
                          <span className="truncate text-[15px] font-semibold">
                            {entry.player.display_name}
                          </span>
                        </span>
                        <span className="text-[17px] font-semibold tabular-nums">
                          {formatRating(entry.rating)}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </>
          )}
        </section>

        <div className="flex flex-col gap-4 md:gap-5">
          <section className={cn(cardClass, "flex flex-auto flex-col gap-3.5 md:p-7")}>
            <h2 className="text-lg font-semibold md:text-xl">Tournament</h2>
            {data.active_tournament ? (
              <div className="flex flex-col gap-2">
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
                <Button asChild variant="outline" className="h-11 self-start px-5 text-sm font-semibold">
                  <Link href={`/tournaments/${data.active_tournament.id}`}>View tournament</Link>
                </Button>
              </div>
            ) : (
              <div className="flex flex-col gap-3.5">
                <div className="flex items-center gap-3.5">
                  <span className="grid size-12 shrink-0 place-items-center rounded-2xl border border-white/20 bg-white/10 text-[#ffd36b]">
                    <Trophy className="size-[22px]" aria-hidden />
                  </span>
                  <QuietEmpty>No tournament in progress</QuietEmpty>
                </div>
                <Button asChild variant="outline" className="h-11 self-start px-5 text-sm font-semibold">
                  <Link href="/tournaments">All tournaments</Link>
                </Button>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              {data.totals.tournaments_completed} completed
            </p>
          </section>

          <section className={cn(cardClass, "flex-auto md:p-7")}>
            <h2 className="text-lg font-semibold md:text-xl">Recent achievements</h2>
            {data.recent_achievements.length === 0 ? (
              <QuietEmpty className="mt-3">No achievements yet.</QuietEmpty>
            ) : (
              <ul className="mt-3 divide-y divide-white/10">
                {data.recent_achievements.map((award) => (
                  <li key={award.id}>
                    <Link
                      href={`/players/${award.player.id}`}
                      className="sr-lift flex min-h-14 items-center gap-3 rounded-xl py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <span className="grid size-9 shrink-0 place-items-center rounded-full border border-white/20 bg-white/10 text-foreground">
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
    </div>
  );
}
