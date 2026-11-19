import Link from "next/link";

import { AchievementIcon } from "@/components/achievement-icon";
import { RatingChart, type RatingPoint } from "@/components/charts/rating-chart";
import { PlayerAvatar } from "@/components/player-avatar";
import { cardClass, heroCardClass, QuietEmpty, textActionClass } from "@/components/club/styles";
import { FormGuide } from "@/components/form-guide";
import { InactiveBadge } from "@/components/inactive-badge";
import { LoadError } from "@/components/load-error";
import { LocalDateTime } from "@/components/local-time";
import { Pager } from "@/components/pager";
import { RankBadge } from "@/components/rank-badge";
import { RatingDelta } from "@/components/rating-delta";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  getPlayer,
  getPlayerAchievements,
  getPlayerMatches,
  getPlayerMonthly,
  getPlayerRatingHistory,
} from "@/lib/api/client";
import {
  formatDelta,
  formatMonthLabel,
  formatRank,
  formatRating,
  formatRecord,
  formatWinRate,
} from "@/lib/format";
import { errorCopy, loadData } from "@/lib/load";
import { readPage, type Query } from "@/lib/query";
import type { FormResult } from "@/types/api";

const PAGE_SIZE = 20;

function timeKey(iso: string): string {
  const ms = Date.parse(iso);
  if (Number.isNaN(ms)) return iso;
  return String(ms).padStart(16, "0");
}

function streakLabel(type: FormResult, count: number): string {
  if (type === "W") return count === 1 ? "1 win" : `${count} wins`;
  return count === 1 ? "1 loss" : `${count} losses`;
}

export async function ProfileHeader({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const result = await loadData(getPlayer(id), { notFoundOn404: true });
  if (!result.ok) {
    const copy = errorCopy(result.error, "this player");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  const player = result.data;
  const stats = player.stats;

  return (
    <section className={heroCardClass}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <PlayerAvatar name={player.display_name} imageUrl={player.avatar_url} size="lg" />
          <div className="min-w-0">
            <h1 className="truncate text-[28px] leading-[34px] font-semibold">
              {player.display_name}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {player.rank == null ? <InactiveBadge /> : <RankBadge rank={player.rank} />}
            </div>
          </div>
        </div>
        {stats.current_streak ? (
          <span className="inline-flex h-6 items-center rounded-full bg-elevated px-2 text-xs font-medium">
            {streakLabel(stats.current_streak.type, stats.current_streak.count)}
          </span>
        ) : null}
      </div>
      <p className="mt-4 text-[56px] leading-none font-semibold tabular-nums">
        {formatRating(player.current_rating)}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Elo · Highest {formatRating(player.highest_rating)}
      </p>
      <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <div>
          <dt className="text-xs text-muted-foreground">Matches</dt>
          <dd className="text-lg font-semibold tabular-nums">{stats.matches_played}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">W–L</dt>
          <dd className="text-lg font-semibold tabular-nums">
            {formatRecord(stats.wins, stats.losses)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Win rate</dt>
          <dd className="text-lg font-semibold tabular-nums">{formatWinRate(stats.win_rate)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Streak</dt>
          <dd className="text-lg font-semibold">
            {stats.current_streak
              ? streakLabel(stats.current_streak.type, stats.current_streak.count)
              : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Last change</dt>
          <dd>
            <RatingDelta value={stats.last_rating_change} />
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Last 30 days</dt>
          <dd>
            <RatingDelta value={stats.rating_change_30d} />
          </dd>
        </div>
      </dl>
      {stats.recent_form.length > 0 ? (
        <div className="mt-4">
          <FormGuide results={stats.recent_form} order="newest-first" />
        </div>
      ) : null}
    </section>
  );
}

export async function ProfileChart({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const result = await loadData(getPlayerRatingHistory(id));
  if (!result.ok) {
    const copy = errorCopy(result.error, "rating history");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  const history = result.data;
  const points: RatingPoint[] = [
    {
      date: "start",
      rating: history.starting_rating,
      label: "Start",
      sortKey: "0",
    },
    ...history.points.map((point, index) => ({
      date: point.match_date,
      rating: point.new_rating,
      label: point.match_date,
      sortKey: `${timeKey(point.match_date)}-${String(index).padStart(4, "0")}`,
      opponent: point.opponent.display_name,
      result: point.result,
      ratingChange: point.rating_change,
    })),
  ];
  const latest = history.points.at(-1);

  return (
    <section className={cardClass}>
      <h2 className="text-lg font-semibold">Elo rating progression</h2>
      <div className="mt-4">
        <RatingChart series={[{ name: "Elo", points }]} />
      </div>
      {history.points.length === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">
          No completed matches yet. Rating is the 1500 start.
        </p>
      ) : null}
      <p className="sr-only">
        {latest
          ? `Latest rating ${formatRating(latest.new_rating)}, change ${formatDelta(latest.rating_change)}.`
          : `Rating is the ${formatRating(history.starting_rating)} start.`}
      </p>
    </section>
  );
}

export async function ProfileAchievements({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const result = await loadData(getPlayerAchievements(id));
  if (!result.ok) {
    const copy = errorCopy(result.error, "achievements");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  return (
    <section className={cardClass}>
      <h2 className="text-lg font-semibold">Achievements</h2>
      {result.data.items.length === 0 ? (
        <QuietEmpty className="mt-3">No achievements yet.</QuietEmpty>
      ) : (
        <ul className="mt-3 grid gap-3">
          {result.data.items.map((award) => (
            <li key={award.id} className="flex gap-3">
              <span className="grid size-8 shrink-0 place-items-center rounded-full bg-elevated">
                <AchievementIcon name={award.achievement.icon} />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium">{award.achievement.name}</span>
                <span className="block text-xs text-muted-foreground">
                  <LocalDateTime value={award.awarded_at} withTime={false} />
                </span>
                {award.notes ? (
                  <span className="mt-1 block text-sm text-muted-foreground">{award.notes}</span>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export async function ProfileMatches({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Query>;
}) {
  const { id } = await params;
  const query = await searchParams;
  const page = readPage(query.page);
  const result = await loadData(
    getPlayerMatches(id, { page, page_size: PAGE_SIZE, status: "completed" }),
  );
  if (!result.ok) {
    const copy = errorCopy(result.error, "matches");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  const data = result.data;

  return (
    <section className={cardClass}>
      <h2 className="text-lg font-semibold">Matches</h2>
      {data.items.length === 0 ? (
        <QuietEmpty className="mt-3">No completed matches yet.</QuietEmpty>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <Table>
            <caption className="sr-only">Completed matches, newest first</caption>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Opponent</TableHead>
                <TableHead>Result</TableHead>
                <TableHead className="text-right">Change</TableHead>
                <TableHead>Match</TableHead>
                <TableHead>Compare</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((match) => (
                <TableRow key={match.id}>
                  <TableCell>
                    <LocalDateTime value={match.match_date} />
                  </TableCell>
                  <TableCell>
                    <Link href={`/players/${match.opponent.id}`} className={textActionClass}>
                      {match.opponent.display_name}
                    </Link>
                  </TableCell>
                  <TableCell className={match.result === "W" ? "text-positive" : "text-negative"}>
                    {match.result}
                  </TableCell>
                  <TableCell className="text-right">
                    <RatingDelta value={match.rating_change} />
                  </TableCell>
                  <TableCell>
                    <Link href={`/matches/${match.id}`} className={textActionClass}>
                      Match
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Link
                      href={`/head-to-head?a=${id}&b=${match.opponent.id}`}
                      className={textActionClass}
                    >
                      Compare
                    </Link>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <div className="mt-4">
        <Pager
          page={data.page}
          pageSize={data.page_size}
          total={data.total}
          pathname={`/players/${id}`}
          query={{}}
        />
      </div>
    </section>
  );
}

export async function ProfileMonthly({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const result = await loadData(getPlayerMonthly(id));
  if (!result.ok) {
    const copy = errorCopy(result.error, "monthly record");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  const items = result.data.items;
  const points: RatingPoint[] = items.map((item) => ({
    date: `${item.year}-${String(item.month).padStart(2, "0")}`,
    rating: item.rating,
    label: formatMonthLabel(item.year, item.month),
    sortKey: `${item.year}-${String(item.month).padStart(2, "0")}`,
  }));

  return (
    <section className={cardClass}>
      <h2 className="text-lg font-semibold">By month</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        Ratings carry over. Each row is the standing at the end of that month.
      </p>
      {items.length === 0 ? (
        <QuietEmpty className="mt-3">No monthly record yet.</QuietEmpty>
      ) : (
        <>
          <div className="mt-4">
            <RatingChart series={[{ name: "Month-end Elo", points }]} height={180} />
          </div>
          <div className="mt-4 overflow-x-auto">
            <Table>
              <caption className="sr-only">Month by month, oldest first</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Month</TableHead>
                  <TableHead>Rank</TableHead>
                  <TableHead className="text-right">Rating</TableHead>
                  <TableHead className="text-right">W–L</TableHead>
                  <TableHead className="text-right">Month change</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={`${item.year}-${item.month}`}>
                    <TableCell>{formatMonthLabel(item.year, item.month)}</TableCell>
                    <TableCell className="tabular-nums">{formatRank(item.rank)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatRating(item.rating)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatRecord(item.wins, item.losses)}
                    </TableCell>
                    <TableCell className="text-right">
                      <RatingDelta value={item.rating_change_during_month} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </section>
  );
}
