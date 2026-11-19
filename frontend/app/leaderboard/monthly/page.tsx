import { Suspense } from "react";

import { MonthlyBoard } from "@/components/club/monthly-board";
import { TableRowsSkeleton } from "@/components/loading-skeleton";

export const metadata = { title: "Monthly leaderboard" };

export default function MonthlyLeaderboardPage({
  searchParams,
}: PageProps<"/leaderboard/monthly">) {
  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <div>
        <h1 className="text-[28px] leading-[34px] font-semibold">Monthly leaderboard</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
          Ratings carry over. This is the standing at the end of the month.
        </p>
      </div>
      <Suspense fallback={<TableRowsSkeleton rows={8} />}>
        <MonthlyBoard searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
