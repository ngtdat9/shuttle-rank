import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type TableRowsSkeletonProps = {
  rows?: number;
  columns?: number;
  className?: string;
};

type CardsSkeletonProps = {
  count?: number;
  className?: string;
};

type ChartSkeletonProps = {
  className?: string;
};

export function TableRowsSkeleton({
  rows = 5,
  columns = 5,
  className,
}: TableRowsSkeletonProps) {
  return (
    <div
      className={cn(
        "sr-panel flex flex-col gap-2 rounded-[24px] in-[.sr-public]:p-4",
        className,
      )}
      aria-hidden
      role="presentation"
    >
      <span className="sr-only">Loading table</span>
      {Array.from({ length: rows }, (_, row) => (
        <div key={row} className="flex items-center gap-3">
          {Array.from({ length: columns }, (_, column) => (
            <Skeleton
              key={column}
              className={cn("h-8 flex-1 rounded-full", column === 0 && "max-w-10")}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export function CardsSkeleton({ count = 3, className }: CardsSkeletonProps) {
  return (
    <div
      className={cn("grid gap-3 sm:grid-cols-3", className)}
      aria-busy="true"
      aria-live="polite"
    >
      <span className="sr-only">Loading</span>
      {Array.from({ length: count }, (_, index) => (
        <div
          key={index}
          className="flex flex-col gap-3 sr-panel rounded-[24px] bg-card p-4 ring-1 ring-foreground/10"
        >
          <Skeleton className="h-3 w-20 rounded-full" />
          <Skeleton className="h-9 w-24 rounded-full" />
          <Skeleton className="h-3 w-16 rounded-full" />
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton({ className }: ChartSkeletonProps) {
  return (
    <div
      className={cn(
        "sr-panel flex h-64 flex-col justify-end gap-3 rounded-[24px] bg-card p-4 ring-1 ring-foreground/10",
        className,
      )}
      aria-busy="true"
      aria-live="polite"
    >
      <span className="sr-only">Loading chart</span>
      <Skeleton className="h-40 w-full rounded-xl" />
      <div className="flex gap-2">
        <Skeleton className="h-3 w-16 rounded-full" />
        <Skeleton className="h-3 w-16 rounded-full" />
      </div>
    </div>
  );
}
