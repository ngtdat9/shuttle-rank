"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";

import { cn } from "@/lib/utils";

export type BarStatDatum = {
  label: string;
  value: number;
};

export type BarStatProps = {
  data: BarStatDatum[];
  className?: string;
  height?: number;
  color?: string;
};

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return null;
}

function BarTooltip({
  active,
  payload,
  label,
}: Pick<TooltipContentProps<number, string>, "active" | "payload" | "label">) {
  if (!active || payload.length === 0) {
    return null;
  }

  const value = asNumber(payload[0]?.value);

  return (
    <div className="glass glass-sm px-3 py-2 text-xs">
      <p className="text-muted-foreground">{label}</p>
      <p className="mt-0.5 font-medium tabular-nums text-positive">
        {value === null ? "—" : value}
      </p>
    </div>
  );
}

export function BarStat({
  data,
  className,
  height = 220,
  color = "#a6f36b",
}: BarStatProps) {
  if (data.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center rounded-[22px] text-sm text-muted-foreground",
          className,
        )}
        style={{ height }}
      >
        No values yet
      </div>
    );
  }

  return (
    <div className={cn("w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 4, left: 0, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            tick={{ fill: "rgba(235,245,238,0.66)", fontSize: 11 }}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            width={28}
            tick={{ fill: "rgba(235,245,238,0.66)", fontSize: 11 }}
          />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            content={(props) => (
              <BarTooltip
                active={props.active}
                payload={props.payload}
                label={props.label}
              />
            )}
          />
          <Bar dataKey="value" fill={color} radius={[8, 8, 4, 4]} maxBarSize={36} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
