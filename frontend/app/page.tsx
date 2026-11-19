import { Suspense } from "react";

import { DashboardView } from "@/components/club/dashboard-view";
import { CardsSkeleton, ChartSkeleton, TableRowsSkeleton } from "@/components/loading-skeleton";

export default function HomePage() {
  return (
    <Suspense fallback={<DashboardFallback />}>
      <DashboardView />
    </Suspense>
  );
}

function DashboardFallback() {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
      <div className="lg:col-span-7">
        <CardsSkeleton count={1} />
      </div>
      <div className="lg:col-span-5">
        <CardsSkeleton count={1} />
      </div>
      <div className="lg:col-span-5">
        <ChartSkeleton />
      </div>
      <div className="lg:col-span-7">
        <TableRowsSkeleton rows={5} />
      </div>
      <div className="lg:col-span-7">
        <TableRowsSkeleton rows={5} />
      </div>
      <div className="lg:col-span-5">
        <CardsSkeleton count={2} className="sm:grid-cols-1" />
      </div>
    </div>
  );
}
