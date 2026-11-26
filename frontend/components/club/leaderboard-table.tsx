import Link from "next/link";

import { PlayerProfileLink } from "@/components/club/player-inline";
import { cardClass, QuietEmpty } from "@/components/club/styles";
import { SortButton } from "@/components/club/query-controls";
import { FormGuide } from "@/components/form-guide";
import { LoadError } from "@/components/load-error";
import { LocalDateTime } from "@/components/local-time";
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
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getRankings } from "@/lib/api/client";
import { formatRank, formatRating, formatRecord, formatWinRate } from "@/lib/format";
import { errorCopy, loadData } from "@/lib/load";
import { readOne, readRankingSort, readSortOrder, type Query } from "@/lib/query";
import type { RankingEntry, RankingSort } from "@/types/api";

function ariaSort(active: boolean, order: "asc" | "desc"): "ascending" | "descending" | "none" {
  if (!active) return "none";
  return order === "asc" ? "ascending" : "descending";
}

function RankingCards({ items }: { items: RankingEntry[] }) {
  return (
    <ul className="flex flex-col gap-3 md:hidden">
      {items.map((entry) => (
        <li key={entry.player.id}>
          <Link
            href={`/players/${entry.player.id}`}
            className="sr-panel sr-lift block rounded-[24px] p-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <span className="flex items-center justify-between gap-3">
              <span className="flex min-w-0 items-center gap-2">
                <span className="text-muted-foreground tabular-nums">{formatRank(entry.rank)}</span>
                <span className="truncate font-medium">{entry.player.display_name}</span>
              </span>
              <span className="text-base tabular-nums">{formatRating(entry.rating)}</span>
            </span>
            <span className="mt-3 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="tabular-nums">{formatRecord(entry.wins, entry.losses)}</span>
              <span className="tabular-nums">{formatWinRate(entry.win_rate)}</span>
              <RatingDelta value={entry.last_rating_change} />
              <FormGuide results={entry.recent_form} order="newest-first" />
            </span>
            <span className="mt-2 block text-xs text-muted-foreground">
              Highest {formatRating(entry.highest_rating)}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export async function LeaderboardTable({ searchParams }: { searchParams: Promise<Query> }) {
  const params = await searchParams;
  const sort = readRankingSort(params.sort);
  const order = readSortOrder(params.order, sort);
  const query = readOne(params.q) ?? "";
  const result = await loadData(getRankings({ sort, order }));

  if (!result.ok) {
    const copy = errorCopy(result.error, "the leaderboard");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  if (result.data.items.length === 0) {
    return <QuietEmpty>No active players yet.</QuietEmpty>;
  }

  const needle = query.toLowerCase();
  const items = needle
    ? result.data.items.filter((entry) => entry.player.display_name.toLowerCase().includes(needle))
    : result.data.items;

  if (items.length === 0) {
    return <QuietEmpty>No players match “{query}”.</QuietEmpty>;
  }

  function head(sortKey: RankingSort, label: string, alignRight = false) {
    const active = sort === sortKey;
    return (
      <TableHead aria-sort={ariaSort(active, order)} className={alignRight ? "text-right" : undefined}>
        <SortButton sortKey={sortKey} label={label} activeSort={sort} activeOrder={order} />
      </TableHead>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {result.data.last_updated ? (
        <p className="text-xs text-muted-foreground">
          Updated <LocalDateTime value={result.data.last_updated} />
        </p>
      ) : null}
      <RankingCards items={items} />
      <div className={`${cardClass} hidden overflow-hidden p-0 md:block`}>
        <Table>
          <caption className="sr-only">
            Club leaderboard. Form chips read oldest on the left and newest on the right.
          </caption>
          <TableHeader>
            <TableRow>
              {head("rank", "Rank")}
              <TableHead>Player</TableHead>
              {head("rating", "Elo", true)}
              <TableHead className="text-right">W–L</TableHead>
              {head("win_rate", "Win rate", true)}
              <TableHead className="text-right">Last change</TableHead>
              <TableHead>
                <Tooltip>
                  <TooltipTrigger className="cursor-help underline decoration-dotted underline-offset-4">
                    Form
                  </TooltipTrigger>
                  <TooltipContent>Oldest on the left, newest on the right.</TooltipContent>
                </Tooltip>
              </TableHead>
              {head("highest_rating", "Highest", true)}
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((entry) => (
              <TableRow key={entry.player.id} className="relative">
                <TableCell className="text-muted-foreground tabular-nums">
                  {formatRank(entry.rank)}
                </TableCell>
                <TableCell>
                  <PlayerProfileLink player={entry.player} stretch />
                </TableCell>
                <TableCell className="text-right tabular-nums">{formatRating(entry.rating)}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatRecord(entry.wins, entry.losses)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatWinRate(entry.win_rate)}
                </TableCell>
                <TableCell className="text-right">
                  <RatingDelta value={entry.last_rating_change} />
                </TableCell>
                <TableCell>
                  <FormGuide results={entry.recent_form} order="newest-first" />
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatRating(entry.highest_rating)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <p className="text-xs text-muted-foreground">Form reads oldest to newest, left to right.</p>
    </div>
  );
}
