import type { MatchListStatus, RankingSort, SortOrder } from "@/types/api";

export type Query = Record<string, string | string[] | undefined>;

const RANKING_SORTS: readonly RankingSort[] = [
  "rank",
  "rating",
  "win_rate",
  "wins",
  "losses",
  "matches_played",
  "highest_rating",
];

const MATCH_STATUSES: readonly MatchListStatus[] = ["completed", "canceled", "disputed", "all"];

export function readOne(value: string | string[] | undefined): string | undefined {
  const raw = Array.isArray(value) ? value[0] : value;
  const trimmed = raw?.trim();
  return trimmed ? trimmed : undefined;
}

export function readPage(value: string | string[] | undefined): number {
  const raw = readOne(value);
  if (!raw) return 1;
  const page = Number(raw);
  if (!Number.isInteger(page) || page < 1) return 1;
  return page;
}

export function defaultRankingOrder(sort: RankingSort): SortOrder {
  return sort === "rank" ? "asc" : "desc";
}

export function readRankingSort(value: string | string[] | undefined): RankingSort {
  const raw = readOne(value);
  if (raw && RANKING_SORTS.includes(raw as RankingSort)) {
    return raw as RankingSort;
  }
  return "rank";
}

export function readSortOrder(
  value: string | string[] | undefined,
  sort: RankingSort,
): SortOrder {
  const raw = readOne(value);
  if (raw === "asc" || raw === "desc") return raw;
  return defaultRankingOrder(sort);
}

export function readMatchStatus(value: string | string[] | undefined): MatchListStatus {
  const raw = readOne(value);
  if (raw && MATCH_STATUSES.includes(raw as MatchListStatus)) {
    return raw as MatchListStatus;
  }
  return "completed";
}

export function readDateParam(value: string | string[] | undefined): string | undefined {
  const raw = readOne(value);
  if (!raw || !/^\d{4}-\d{2}-\d{2}$/.test(raw)) return undefined;
  return raw;
}

export function readMonthPart(value: string | string[] | undefined): number | undefined {
  const raw = readOne(value);
  if (!raw || !/^\d+$/.test(raw)) return undefined;
  const number = Number(raw);
  return Number.isInteger(number) ? number : undefined;
}
