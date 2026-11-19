import { Suspense } from "react";

import { HeadToHeadChooserSection, HeadToHeadResult } from "@/components/club/h2h-view";
import { CardsSkeleton } from "@/components/loading-skeleton";

export const metadata = { title: "Head-to-head" };

export default function HeadToHeadPage({ searchParams }: PageProps<"/head-to-head">) {
  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <h1 className="text-[28px] leading-[34px] font-semibold">Head-to-head</h1>
      <Suspense fallback={<div className="h-16" />}>
        <HeadToHeadChooserSection />
      </Suspense>
      <Suspense fallback={<CardsSkeleton count={1} className="sm:grid-cols-1" />}>
        <HeadToHeadResult searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
