import { Suspense } from "react";

import { MatchDetail } from "@/components/club/match-detail";
import { CardsSkeleton } from "@/components/loading-skeleton";

export const metadata = { title: "Match" };

export default function MatchPage({ params }: PageProps<"/matches/[id]">) {
  return (
    <Suspense fallback={<CardsSkeleton count={1} className="mx-auto max-w-[720px] sm:grid-cols-1" />}>
      <MatchDetail params={params} />
    </Suspense>
  );
}
