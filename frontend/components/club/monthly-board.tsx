import Link from "next/link";

import { MonthSelect } from "@/components/club/query-controls";
import { PlayerProfileLink } from "@/components/club/player-inline";
import { cardClass, QuietEmpty, textActionClass } from "@/components/club/styles";
import { LoadError } from "@/components/load-error";
import { RankChange } from "@/components/rank-change";
import { RatingDelta } from "@/components/rating-delta";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getMonthlyRankings } from "@/lib/api/client";
import { formatMonthLabel, formatRank, formatRating, formatRecord, isCurrentUtcMonth } from "@/lib/format";
import { errorCopy, loadData } from "@/lib/load";
import { readMonthPart, type Query } from "@/lib/query";
import type { MonthlyRankingsResponse } from "@/types/api";

function MonthTable({ data }: { data: MonthlyRankingsResponse }) {
  if (data.items.length === 0) {
    return <QuietEmpty>No completed matches yet.</QuietEmpty>;
  }

  return (
    <>
      <ul className="flex flex-col gap-3 md:hidden">
        {data.items.map((item) => (
          <li key={item.player.id}>
            <Link
              href={`/players/${item.player.id}`}
              className="block rounded-[20px] bg-card p-4 ring-1 ring-foreground/10"
            >
              <span className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2">
                  <span className="text-muted-foreground tabular-nums">{formatRank(item.rank)}</span>
                  <RankChange value={item.rank_change} />
                  <span className="font-medium">{item.player.display_name}</span>
                </span>
                <span className="tabular-nums">{formatRating(item.rating)}</span>
              </span>
              <span className="mt-2 flex flex-wrap gap-3 text-sm text-muted-foreground">
                <span className="tabular-nums">{formatRecord(item.wins, item.losses)}</span>
                <RatingDelta value={item.rating_change_during_month} />
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <div className={`${cardClass} hidden overflow-hidden p-0 md:block`}>
        <Table>
          <caption className="sr-only">Monthly standings. Ratings are not reset.</caption>
          <TableHeader>
            <TableRow>
              <TableHead>Position</TableHead>
              <TableHead>Move</TableHead>
              <TableHead>Player</TableHead>
              <TableHead className="text-right">Rating</TableHead>
              <TableHead className="text-right">W–L</TableHead>
              <TableHead className="text-right">Month change</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((item) => (
              <TableRow key={item.player.id} className="relative">
                <TableCell className="text-muted-foreground tabular-nums">
                  {formatRank(item.rank)}
                </TableCell>
                <TableCell>
                  <RankChange value={item.rank_change} />
                </TableCell>
                <TableCell>
                  <PlayerProfileLink player={item.player} stretch />
                </TableCell>
                <TableCell className="text-right tabular-nums">{formatRating(item.rating)}</TableCell>
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
  );
}

export async function MonthlyBoard({ searchParams }: { searchParams: Promise<Query> }) {
  const params = await searchParams;
  const year = readMonthPart(params.year);
  const month = readMonthPart(params.month);
  const requested = year != null && month != null && month >= 1 && month <= 12;

  let result = await loadData(
    requested ? getMonthlyRankings(year, month) : getMonthlyRankings(),
  );

  let missingMonth = false;
  if (!result.ok && result.error.status === 404 && requested) {
    missingMonth = true;
    result = await loadData(getMonthlyRankings());
  }

  if (!result.ok) {
    const copy = errorCopy(result.error, "the monthly leaderboard");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  const data = result.data;
  const inProgress =
    data.year != null && data.month != null && isCurrentUtcMonth(data.year, data.month);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        {data.available_months.length > 0 ? (
          <MonthSelect months={data.available_months} year={data.year} month={data.month} />
        ) : null}
        <Link href="/leaderboard" className={textActionClass}>
          Current leaderboard
        </Link>
      </div>
      {inProgress ? (
        <p className="text-sm text-muted-foreground">
          {formatMonthLabel(data.year ?? 0, data.month ?? 1)} · in progress
        </p>
      ) : null}
      {missingMonth ? (
        <QuietEmpty>No standings for that month.</QuietEmpty>
      ) : data.available_months.length === 0 ? (
        <QuietEmpty>No completed matches yet.</QuietEmpty>
      ) : (
        <MonthTable data={data} />
      )}
    </div>
  );
}
