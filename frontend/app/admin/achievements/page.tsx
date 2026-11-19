import { Suspense } from "react";

import { AchievementsView } from "@/components/admin/achievements-view";

export const metadata = { title: "Achievements" };

export default function AdminAchievementsPage() {
  return (
    <Suspense
      fallback={
        <div
          className="h-40 animate-pulse rounded-[20px] bg-elevated"
          aria-busy="true"
        />
      }
    >
      <AchievementsView />
    </Suspense>
  );
}
