import { Suspense } from "react";

import { PlayerDirectory } from "@/components/club/player-directory";
import { SearchField } from "@/components/club/query-controls";
import { CardsSkeleton } from "@/components/loading-skeleton";

export const metadata = { title: "Players" };

export default function PlayersPage({ searchParams }: PageProps<"/players">) {
  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <h1 className="text-[28px] leading-[34px] font-semibold">Players</h1>
        <Suspense fallback={<div className="h-11 w-56" />}>
          <SearchField param="search" label="Search" placeholder="Search by name" />
        </Suspense>
      </div>
      <Suspense fallback={<CardsSkeleton count={6} className="md:grid-cols-2 lg:grid-cols-3" />}>
        <PlayerDirectory searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
