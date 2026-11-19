import { Suspense } from "react";

import { MatchHistory } from "@/components/club/match-history";
import { TableRowsSkeleton } from "@/components/loading-skeleton";

export const metadata = { title: "Matches" };

export default function MatchesPage({ searchParams }: PageProps<"/matches">) {
  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <h1 className="text-[28px] leading-[34px] font-semibold">Matches</h1>
      <Suspense fallback={<TableRowsSkeleton rows={8} />}>
        <MatchHistory searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
