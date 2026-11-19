import { CardsSkeleton, ChartSkeleton, TableRowsSkeleton } from "@/components/loading-skeleton";

export default function Loading() {
  return (
    <div className="flex flex-col gap-4">
      <CardsSkeleton count={2} />
      <ChartSkeleton />
      <TableRowsSkeleton rows={5} />
    </div>
  );
}
