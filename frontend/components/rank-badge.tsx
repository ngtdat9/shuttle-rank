import { cn } from "@/lib/utils";

type RankBadgeProps = {
  rank: number;
  className?: string;
};

export function RankBadge({ rank, className }: RankBadgeProps) {
  const label = String(Math.max(0, Math.trunc(rank))).padStart(2, "0");

  return (
    <span
      aria-label={`Rank ${rank}`}
      className={cn(
        "inline-flex min-w-8 items-center justify-center rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums",
        rank === 1 && "bg-primary text-primary-foreground",
        rank === 2 && "bg-secondary text-secondary-foreground",
        rank === 3 && "bg-muted text-foreground",
        rank > 3 && "text-muted-foreground",
        className,
      )}
    >
      {label}
    </span>
  );
}
