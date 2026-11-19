import { formatPercent, formatWinRate } from "@/lib/format";
import { cn } from "@/lib/utils";

type WinRateProps = {
  /** Percentage from 0 to 100. Used by the design showcase. */
  percent?: number;
  /** API win rate from 0 to 1, or null when there are no matches. */
  rate?: number | null;
  className?: string;
  showBar?: boolean;
};

export function WinRate({ percent, rate, className, showBar = true }: WinRateProps) {
  if (rate === null) {
    return (
      <span className={cn("text-sm text-muted-foreground tabular-nums", className)}>—</span>
    );
  }

  const fromRate = rate !== undefined;
  const safe = fromRate
    ? Math.min(100, Math.max(0, rate * 100))
    : Number.isFinite(percent)
      ? Math.min(100, Math.max(0, percent ?? 0))
      : 0;
  const label = fromRate ? formatWinRate(rate) : formatPercent(safe);

  return (
    <div className={cn("min-w-16", className)}>
      <p className="text-sm font-medium tabular-nums">{label}</p>
      {showBar ? (
        <div
          className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-foreground/10"
          role="meter"
          aria-label="Win rate"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(safe)}
        >
          <div className="h-full rounded-full bg-primary" style={{ width: `${safe}%` }} />
        </div>
      ) : null}
    </div>
  );
}
