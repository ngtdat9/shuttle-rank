import { Skeleton } from "@/components/ui/skeleton";

export function TournamentDetailSkeleton() {
  return (
    <div className="flex flex-col gap-4 lg:gap-5" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading tournament</span>
      <div className="rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 md:p-5">
        <Skeleton className="h-5 w-24 rounded-full" />
        <Skeleton className="mt-3 h-8 w-2/3 max-w-sm rounded-full" />
        <Skeleton className="mt-3 h-4 w-48 rounded-full" />
        <Skeleton className="mt-3 h-4 w-full max-w-md rounded-full" />
      </div>
      <div className="flex gap-6 overflow-hidden">
        {Array.from({ length: 3 }, (_, column) => (
          <div key={column} className="flex w-56 shrink-0 flex-col gap-3">
            <Skeleton className="h-3 w-24 rounded-full" />
            <Skeleton className="h-28 rounded-2xl" />
            <Skeleton className="h-28 rounded-2xl" />
          </div>
        ))}
      </div>
    </div>
  );
}
