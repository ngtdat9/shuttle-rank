import { Suspense } from "react";

import { TournamentsView } from "@/components/admin/tournaments-view";

export const metadata = { title: "Tournaments" };

export default function AdminTournamentsPage() {
  return (
    <Suspense
      fallback={
        <div
          className="h-40 animate-pulse rounded-[20px] bg-elevated"
          aria-busy="true"
        />
      }
    >
      <TournamentsView />
    </Suspense>
  );
}
