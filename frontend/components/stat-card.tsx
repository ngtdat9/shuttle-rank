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
    <Card className={cn("rounded-[22px] bg-card ring-foreground/10", className)}>
      <CardContent className="flex flex-col gap-2">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-4xl font-semibold tracking-tight tabular-nums">{value}</p>
        {delta !== undefined ? <RatingDelta value={delta} /> : null}
        {subLabel ? <p className="text-xs text-muted-foreground">{subLabel}</p> : null}
      </CardContent>
    </Card>
  );
}
