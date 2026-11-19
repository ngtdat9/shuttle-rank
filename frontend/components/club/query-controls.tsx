"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { defaultRankingOrder } from "@/lib/query";
import { formatMonthLabel, isCurrentUtcMonth } from "@/lib/format";
import type { MonthRef, RankingSort } from "@/types/api";
import { cn } from "@/lib/utils";

const SORTS: { value: RankingSort; label: string }[] = [
  { value: "rank", label: "Rank" },
  { value: "rating", label: "Elo" },
  { value: "win_rate", label: "Win rate" },
  { value: "wins", label: "Wins" },
  { value: "losses", label: "Losses" },
  { value: "matches_played", label: "Matches" },
  { value: "highest_rating", label: "Highest" },
];

export function useQueryUpdate() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const update = useCallback(
    (changes: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(changes)) {
        if (value == null || value === "") next.delete(key);
        else next.set(key, value);
      }
      const qs = next.toString();
      router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  return { searchParams, update, pathname };
}

export const fieldLabelClass = "flex min-w-0 flex-col gap-1 text-xs font-medium text-muted-foreground";

export const nativeSelectClass =
  "h-11 rounded-full border border-input bg-transparent px-3 text-sm text-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none md:h-10";

export function SearchField({
  param = "q",
  label,
  placeholder,
  className,
}: {
  param?: string;
  label: string;
  placeholder?: string;
  className?: string;
}) {
  const { searchParams, update } = useQueryUpdate();
  const urlValue = searchParams.get(param) ?? "";
  const [value, setValue] = useState(urlValue);
  const [syncedUrl, setSyncedUrl] = useState(urlValue);

  if (syncedUrl !== urlValue) {
    setSyncedUrl(urlValue);
    setValue(urlValue);
  }

  useEffect(() => {
    if (value === urlValue) return;
    const handle = window.setTimeout(() => {
      update({ [param]: value.trim() ? value : null, page: null });
    }, 300);
    return () => window.clearTimeout(handle);
  }, [param, update, urlValue, value]);

  return (
    <form
      role="search"
      className={className}
      onSubmit={(event) => {
        event.preventDefault();
        update({ [param]: value.trim() ? value : null, page: null });
      }}
    >
      <label className={fieldLabelClass}>
        {label}
        <Input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={placeholder}
          className="h-11 w-full sm:w-56 md:h-10"
        />
      </label>
    </form>
  );
}

export function RankingSortSelect() {
  const { searchParams, update } = useQueryUpdate();
  const current = SORTS.some((item) => item.value === searchParams.get("sort"))
    ? (searchParams.get("sort") as RankingSort)
    : "rank";

  return (
    <label className={fieldLabelClass}>
      Sort
      <Select
        value={current}
        onValueChange={(value) => {
          const sort = value as RankingSort;
          const order = defaultRankingOrder(sort);
          update({
            sort: sort === "rank" ? null : sort,
            order: sort === "rank" ? null : order,
          });
        }}
      >
        <SelectTrigger className="h-11 w-full rounded-full sm:w-40 md:h-10" aria-label="Sort">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SORTS.map((item) => (
            <SelectItem key={item.value} value={item.value}>
              {item.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </label>
  );
}

export function SortButton({
  sortKey,
  label,
  activeSort,
  activeOrder,
}: {
  sortKey: RankingSort;
  label: string;
  activeSort: RankingSort;
  activeOrder: "asc" | "desc";
}) {
  const { update } = useQueryUpdate();
  const active = activeSort === sortKey;
  const nextOrder = active ? (activeOrder === "asc" ? "desc" : "asc") : defaultRankingOrder(sortKey);

  return (
    <button
      type="button"
      onClick={() => update({ sort: sortKey, order: nextOrder })}
      className={cn(
        "inline-flex items-center gap-1 rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        active ? "text-foreground" : "text-muted-foreground",
      )}
    >
      {label}
      <span aria-hidden="true">{active ? (activeOrder === "asc" ? "↑" : "↓") : ""}</span>
      <span className="sr-only">
        {active
          ? `, sorted ${activeOrder === "asc" ? "ascending" : "descending"}`
          : ", activate to sort"}
      </span>
    </button>
  );
}

export function MonthSelect({
  months,
  year,
  month,
}: {
  months: MonthRef[];
  year: number | null;
  month: number | null;
}) {
  const { update } = useQueryUpdate();
  const value = year != null && month != null ? `${year}-${month}` : "";

  return (
    <label className={cn(fieldLabelClass, "sm:w-56")}>
      Month
      <select
        className={nativeSelectClass}
        value={value}
        onChange={(event) => {
          const [nextYear, nextMonth] = event.target.value.split("-");
          update({ year: nextYear ?? null, month: nextMonth ?? null });
        }}
      >
        {months.map((item) => {
          const progress = isCurrentUtcMonth(item.year, item.month) ? " · in progress" : "";
          return (
            <option key={`${item.year}-${item.month}`} value={`${item.year}-${item.month}`}>
              {formatMonthLabel(item.year, item.month)}
              {progress}
            </option>
          );
        })}
      </select>
    </label>
  );
}
