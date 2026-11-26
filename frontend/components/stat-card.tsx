import type { ReactNode } from "react";

import { RatingDelta } from "@/components/rating-delta";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type StatCardProps = {
  label: string;
  value: ReactNode;
  delta?: number;
  subLabel?: string;
  className?: string;
};

export function StatCard({ label, value, delta, subLabel, className }: StatCardProps) {
  return (
    <Card className={cn("sr-panel rounded-[24px] [--card-spacing:--spacing(5)]", className)}>
      <CardContent className="flex flex-col gap-2">
        <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase">{label}</p>
        <p className="font-mono text-4xl font-semibold tracking-tight tabular-nums">{value}</p>
        {delta !== undefined ? <RatingDelta value={delta} /> : null}
        {subLabel ? <p className="text-xs text-muted-foreground">{subLabel}</p> : null}
      </CardContent>
    </Card>
  );
}
