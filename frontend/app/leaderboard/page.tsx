import { Suspense } from "react";
import Link from "next/link";

import { LeaderboardTable } from "@/components/club/leaderboard-table";
import { RankingSortSelect, SearchField } from "@/components/club/query-controls";
import { textActionClass } from "@/components/club/styles";
import { TableRowsSkeleton } from "@/components/loading-skeleton";

export const metadata = { title: "Leaderboard" };

export default function LeaderboardPage({ searchParams }: PageProps<"/leaderboard">) {
  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <h1 className="text-[28px] leading-[34px] font-semibold">Leaderboard</h1>
        <Suspense fallback={<div className="h-11" />}>
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
            <SearchField label="Name" placeholder="Filter by name" />
            <RankingSortSelect />
            <Link href="/leaderboard/monthly" className={textActionClass}>
              Monthly view
            </Link>
          </div>
        </Suspense>
      </div>
      <Suspense fallback={<TableRowsSkeleton rows={8} columns={6} />}>
        <LeaderboardTable searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
