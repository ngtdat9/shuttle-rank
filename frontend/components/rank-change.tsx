import { cn } from "@/lib/utils";

export function RankChange({ value }: { value: number | null }) {
  if (value == null) {
    return <span className="text-sm text-muted-foreground">New</span>;
  }
  if (value === 0) {
    return <span className="text-sm text-muted-foreground">—</span>;
  }
  if (value > 0) {
    return (
      <span className={cn("text-sm font-medium text-positive tabular-nums")} aria-label={`up ${value}`}>
        ▲{value}
      </span>
    );
  }
  const steps = Math.abs(value);
  return (
    <span className="text-sm font-medium text-negative tabular-nums" aria-label={`down ${steps}`}>
      ▼{steps}
    </span>
  );
}
