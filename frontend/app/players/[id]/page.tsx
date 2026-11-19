import { Suspense } from "react";

import {
  ProfileAchievements,
  ProfileChart,
  ProfileHeader,
  ProfileMatches,
  ProfileMonthly,
} from "@/components/club/profile-sections";
import { CardsSkeleton, ChartSkeleton, TableRowsSkeleton } from "@/components/loading-skeleton";

export const metadata = { title: "Player" };

export default function PlayerPage({ params, searchParams }: PageProps<"/players/[id]">) {
  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <Suspense fallback={<CardsSkeleton count={1} />}>
        <ProfileHeader params={params} />
      </Suspense>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 lg:gap-5">
        <div className="lg:col-span-7">
          <Suspense fallback={<ChartSkeleton />}>
            <ProfileChart params={params} />
          </Suspense>
        </div>
        <div className="lg:col-span-5">
          <Suspense fallback={<CardsSkeleton count={2} className="sm:grid-cols-1" />}>
            <ProfileAchievements params={params} />
          </Suspense>
        </div>
      </div>
      <Suspense fallback={<TableRowsSkeleton rows={6} />}>
        <ProfileMatches params={params} searchParams={searchParams} />
      </Suspense>
      <Suspense fallback={<TableRowsSkeleton rows={4} />}>
        <ProfileMonthly params={params} />
      </Suspense>
    </div>
  );
}
