import { Suspense } from "react";

import { TournamentDetailSkeleton } from "@/components/tournaments/detail-skeleton";
import { TournamentDetail } from "@/components/tournaments/tournament-detail";

export const metadata = { title: "Tournament" };

export default function TournamentPage({ params }: PageProps<"/tournaments/[id]">) {
  return (
    <Suspense fallback={<TournamentDetailSkeleton />}>
      <TournamentDetail params={params} />
    </Suspense>
  );
}
