import { Suspense } from "react";

import { PlayersView } from "@/components/admin/players-view";
import { TableRowsSkeleton } from "@/components/loading-skeleton";

export const metadata = { title: "Players" };

export default function AdminPlayersPage() {
  return (
    <Suspense fallback={<TableRowsSkeleton rows={8} />}>
      <PlayersView />
    </Suspense>
  );
}
