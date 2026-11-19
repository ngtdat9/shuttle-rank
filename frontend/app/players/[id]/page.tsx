import { Suspense } from "react";

import {
  ProfileAchievements,
  ProfileChart,
  ProfileHeader,
  ProfileMatches,
  ProfileMonthly,
  loadProfile,
} from "@/components/club/profile-sections";
import { LoadError } from "@/components/load-error";
import { errorCopy } from "@/lib/load";
import {
  CardsSkeleton,
  ChartSkeleton,
  TableRowsSkeleton,
} from "@/components/loading-skeleton";

export const metadata = { title: "Player" };

export default async function PlayerPage({
  params,
  searchParams,
}: PageProps<"/players/[id]">) {
  const profile = await loadProfile(params);
  if (!profile.ok) {
    const copy = errorCopy(profile.error, "this player");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <ProfileHeader player={profile.data} />
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
