import { ArrowDown, ArrowUp, Minus } from "lucide-react";

import { formatDelta } from "@/lib/format";
import { cn } from "@/lib/utils";

type RatingDeltaProps = {
  value: number;
  className?: string;
};

export function RatingDelta({ value, className }: RatingDeltaProps) {
  const direction = value > 0 ? "up" : value < 0 ? "down" : "flat";
  const Icon = direction === "up" ? ArrowUp : direction === "down" ? ArrowDown : Minus;
  const label =
    direction === "up"
      ? "Rating up"
      : direction === "down"
        ? "Rating down"
        : "Rating unchanged";

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
      <Icon className="size-3.5" aria-hidden />
      <span>{formatDelta(value)}</span>
      <span className="sr-only">{label}</span>
    </span>
  );
}
