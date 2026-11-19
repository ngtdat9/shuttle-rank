import { Suspense } from "react";

import { MatchesView } from "@/components/admin/matches-view";
import { TableRowsSkeleton } from "@/components/loading-skeleton";

export const metadata = { title: "Matches" };

export default function AdminMatchesPage() {
  return (
    <Suspense fallback={<TableRowsSkeleton rows={8} />}>
      <MatchesView />
    </Suspense>
  );
}
