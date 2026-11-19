import { Suspense } from "react";

import { TournamentList } from "@/components/club/tournament-list";
import { CardsSkeleton } from "@/components/loading-skeleton";

export const metadata = { title: "Tournaments" };

export default function TournamentsPage() {
  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <h1 className="text-[28px] leading-[34px] font-semibold">Tournaments</h1>
      <Suspense fallback={<CardsSkeleton count={4} className="md:grid-cols-2" />}>
        <TournamentList />
      </Suspense>
    </div>
  );
}
