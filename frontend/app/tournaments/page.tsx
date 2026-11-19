import { Suspense } from "react";

import { CardsSkeleton } from "@/components/loading-skeleton";
import { TournamentStatusFilter } from "@/components/tournaments/status-filter";
import { TournamentList } from "@/components/tournaments/tournament-list";

export const metadata = { title: "Tournaments" };

export default function TournamentsPage({ searchParams }: PageProps<"/tournaments">) {
  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <h1 className="text-[28px] leading-[34px] font-semibold">Tournaments</h1>
      <Suspense fallback={<div className="h-16 w-48" aria-hidden />}>
        <TournamentStatusFilter />
      </Suspense>
      <Suspense fallback={<CardsSkeleton count={4} className="lg:grid-cols-2" />}>
        <TournamentList searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
