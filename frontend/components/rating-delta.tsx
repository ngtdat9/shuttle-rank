import { TrendingDown, TrendingUp } from "lucide-react";

import { formatDelta } from "@/lib/format";
import { cn } from "@/lib/utils";

type RatingDeltaProps = {
  value: number | null;
  className?: string;
};

export function RatingDelta({ value, className }: RatingDeltaProps) {
  if (value == null || !Number.isFinite(value)) {
    return (
      <span className={cn("text-sm font-medium text-muted-foreground tabular-nums", className)}>
        —
      </span>
    );
  }

  const direction = value > 0 ? "up" : value < 0 ? "down" : "flat";
  const label =
    direction === "up" ? "Rating up" : direction === "down" ? "Rating down" : "Rating unchanged";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-sm font-medium tabular-nums",
        direction === "up" && "text-positive",
        direction === "down" && "text-negative",
        direction === "flat" && "text-muted-foreground",
        className,
      )}
    >
      {direction === "up" ? <TrendingUp className="size-3.5" aria-hidden /> : null}
      {direction === "down" ? <TrendingDown className="size-3.5" aria-hidden /> : null}
      <span>{formatDelta(value)}</span>
      <span className="sr-only">{label}</span>
    </span>
  );
}
