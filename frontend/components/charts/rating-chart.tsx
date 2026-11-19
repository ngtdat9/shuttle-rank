"use client";

import { useId } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";

import { formatDate, formatRating } from "@/lib/format";
import { cn } from "@/lib/utils";

export type RatingPoint = {
  date: string;
  rating: number;
};

export type RatingSeries = {
  name: string;
  color?: string;
  points: RatingPoint[];
};

export type RatingChartProps = {
  series: RatingSeries[];
  className?: string;
  height?: number;
};

const SERIES_COLORS = ["#a6f36b", "#35d5d0", "#8ea196", "#d5f5b8", "#1f8a86"];

function seriesColor(series: RatingSeries, index: number): string {
  return series.color ?? SERIES_COLORS[index % SERIES_COLORS.length] ?? SERIES_COLORS[0];
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function RatingTooltip({
  active,
  payload,
  label,
}: Pick<TooltipContentProps<number, string>, "active" | "payload" | "label">) {
  if (!active || payload.length === 0) {
    return null;
  }

  const dateLabel =
    typeof label === "string" || typeof label === "number"
      ? formatDate(String(label), { month: "short", day: "numeric" })
      : "";

  return (
    <div className="rounded-2xl border border-border bg-elevated px-3 py-2 text-xs shadow-lg">
      {dateLabel ? <p className="mb-1 text-muted-foreground">{dateLabel}</p> : null}
      <ul className="flex flex-col gap-1">
        {payload.map((entry) => {
          const rating = asNumber(entry.value);
          return (
            <li key={String(entry.dataKey)} className="flex items-center gap-2">
              <span
                className="size-2 rounded-full"
                style={{ background: entry.color ?? "#a6f36b" }}
              />
              <span className="text-muted-foreground">{entry.name}</span>
              <span className="ml-auto font-medium tabular-nums">
                {rating === null ? "—" : formatRating(rating)}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

type ChartRow = { date: string } & Record<string, string | number | null>;

function buildRows(series: RatingSeries[]): ChartRow[] {
  const dates = new Set<string>();
  for (const item of series) {
    for (const point of item.points) {
      dates.add(point.date);
    }
  }

  return [...dates].sort().map((date) => {
    const row: ChartRow = { date };
    for (const item of series) {
      const point = item.points.find((entry) => entry.date === date);
      row[item.name] = point ? point.rating : null;
    }
    return row;
  });
}

export function RatingChart({ series, className, height = 256 }: RatingChartProps) {
  const gradientPrefix = useId().replace(/:/g, "");
  const rows = buildRows(series);
  const hasPoints = series.some((item) => item.points.length > 0);

  if (!hasPoints) {
    return (
      <div
        className={cn(
          "flex items-center justify-center rounded-[22px] bg-card text-sm text-muted-foreground ring-1 ring-foreground/10",
          className,
        )}
        style={{ height }}
      >
        No rating history yet
      </div>
    );
  }

  const ratings = series.flatMap((item) => item.points.map((point) => point.rating));
  const min = Math.min(...ratings);
  const max = Math.max(...ratings);
  const pad = Math.max(8, Math.round((max - min) * 0.18) || 8);

  return (
    <div className={cn("w-full", className)}>
      {series.length > 1 ? (
        <ul className="mb-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
          {series.map((item, index) => (
            <li key={item.name} className="inline-flex items-center gap-1.5">
              <span
                className="size-2 rounded-full"
                style={{ background: seriesColor(item, index) }}
              />
              {item.name}
            </li>
          ))}
        </ul>
      ) : null}
      <div style={{ height }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <defs>
              {series.map((item, index) => {
                const color = seriesColor(item, index);
                const id = `${gradientPrefix}-${index}`;
                return (
                  <linearGradient key={id} id={id} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={color} stopOpacity={0.28} />
                    <stop offset="100%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                );
              })}
            </defs>
            <CartesianGrid
              vertical={false}
              stroke="rgba(255,255,255,0.06)"
              strokeDasharray="3 6"
            />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "#a1aaa3", fontSize: 11 }}
              tickFormatter={(value: string) =>
                formatDate(value, { month: "short", day: "numeric" }, "en-US")
              }
              minTickGap={24}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={42}
              domain={[min - pad, max + pad]}
              tick={{ fill: "#a1aaa3", fontSize: 11 }}
              tickFormatter={(value: number) => formatRating(value, "en-US")}
            />
            <Tooltip
              content={(props) => (
                <RatingTooltip
                  active={props.active}
                  payload={props.payload}
                  label={props.label}
                />
              )}
              cursor={{ stroke: "rgba(255,255,255,0.16)", strokeWidth: 1 }}
            />
            {series.map((item, index) => {
              const color = seriesColor(item, index);
              return (
                <Area
                  key={item.name}
                  type="monotone"
                  dataKey={item.name}
                  name={item.name}
                  stroke={color}
                  strokeWidth={2}
                  fill={`url(#${gradientPrefix}-${index})`}
                  connectNulls
                  dot={{ r: 2.5, strokeWidth: 0, fill: color }}
                  activeDot={{ r: 4, strokeWidth: 0, fill: color }}
                />
              );
            })}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
