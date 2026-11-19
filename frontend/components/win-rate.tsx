import { formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

type WinRateProps = {
  /** Percentage from 0 to 100. */
  percent: number;
  className?: string;
};

export function WinRate({ percent, className }: WinRateProps) {
  const safe = Number.isFinite(percent) ? Math.min(100, Math.max(0, percent)) : 0;

  return (
    <div className={cn("min-w-16", className)}>
      <p className="text-sm font-medium tabular-nums">{formatPercent(safe)}</p>
      <div
        className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-foreground/10"
        role="meter"
        aria-label="Win rate"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(safe)}
      >
        <div
          className="h-full rounded-full bg-primary"
          style={{ width: `${safe}%` }}
        />
      </div>
    </div>
  );
}
