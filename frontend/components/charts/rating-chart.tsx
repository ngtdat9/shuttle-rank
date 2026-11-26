"use client";

import { useEffect, useId, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";

import { formatDate, formatDelta, formatRating } from "@/lib/format";
import { SERIES_COLORS } from "@/lib/series-colors";
import { cn } from "@/lib/utils";

export type RatingPoint = {
  date: string;
  rating: number;
  /** Axis and tooltip label. Use "Start" for the 1500 point. */
  label?: string;
  /** Sort key. Defaults to `date`. The 1500 start should sort first. */
  sortKey?: string;
  opponent?: string;
  result?: "W" | "L";
  ratingChange?: number | null;
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

const AXIS_TEXT = "rgba(235,245,238,0.66)";
const GRID = "rgba(255,255,255,0.1)";

type PointMeta = {
  opponent?: string;
  result?: "W" | "L";
  ratingChange?: number | null;
};

type ChartRow = {
  key: string;
  label: string;
} & Record<string, string | number | null>;

function seriesColor(series: RatingSeries, index: number): string {
  return (
    series.color ?? SERIES_COLORS[index % SERIES_COLORS.length] ?? SERIES_COLORS[0]
  );
}

function seriesDataKey(index: number): string {
  return `s${index}`;
}

function asNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  return null;
}

function displayLabel(label: string, timeZone?: string): string {
  if (label === "Start") return "Start";
  if (/^\d{4}-\d{2}-\d{2}/.test(label)) {
    return formatDate(label, { month: "short", day: "numeric", timeZone }, "en-US");
  }
  return label;
}

function buildChart(series: RatingSeries[]): {
  rows: ChartRow[];
  meta: Map<string, PointMeta>;
} {
  const keys = new Set<string>();
  const labels = new Map<string, string>();
  const meta = new Map<string, PointMeta>();

  series.forEach((item, index) => {
    const dataKey = seriesDataKey(index);
    item.points.forEach((point) => {
      const key = point.sortKey ?? point.date;
      keys.add(key);
      if (!labels.has(key)) labels.set(key, point.label ?? point.date);
      if (point.opponent || point.result || point.ratingChange != null) {
        meta.set(`${dataKey}\0${key}`, {
          opponent: point.opponent,
          result: point.result,
          ratingChange: point.ratingChange,
        });
      }
    });
  });

  const rows = [...keys].sort().map((key) => {
    const row: ChartRow = { key, label: labels.get(key) ?? key };
    series.forEach((item, index) => {
      const point = item.points.find((entry) => (entry.sortKey ?? entry.date) === key);
      row[seriesDataKey(index)] = point ? point.rating : null;
    });
    return row;
  });

  return { rows, meta };
}

function RatingTooltip({
  active,
  payload,
  label,
  meta,
  series,
  timeZone,
}: Pick<TooltipContentProps<number, string>, "active" | "payload" | "label"> & {
  timeZone?: string;
  meta: Map<string, PointMeta>;
  series: RatingSeries[];
}) {
  if (!active || payload.length === 0) return null;

  const row = payload[0]?.payload as ChartRow | undefined;
  const dateLabel = displayLabel(
    row?.label ?? (typeof label === "string" ? label : ""),
    timeZone,
  );

  return (
    <div className="glass glass-sm rounded-xl px-3 py-2 text-xs">
      {dateLabel ? <p className="mb-1 text-foreground/80">{dateLabel}</p> : null}
      <ul className="flex flex-col gap-1">
        {payload.map((entry) => {
          const rating = asNumber(entry.value);
          const dataKey = String(entry.dataKey ?? "");
          const detail = meta.get(`${dataKey}\0${row?.key ?? ""}`);
          const name =
            series.find((_, index) => seriesDataKey(index) === dataKey)?.name ??
            entry.name;
          return (
            <li key={dataKey} className="flex flex-col gap-0.5">
              <span className="flex items-center gap-2">
                <span
                  className="size-2 rounded-full"
                  style={{ background: entry.color ?? "#A6F36B" }}
                />
                <span className="text-muted-foreground">{name}</span>
                <span className="ml-auto font-mono font-medium tabular-nums">
                  {rating === null ? "—" : formatRating(rating)}
                </span>
              </span>
              {detail?.opponent ? (
                <span className="pl-4 text-muted-foreground">
                  {detail.result
                    ? `${detail.result} vs ${detail.opponent}`
                    : detail.opponent}
                  {detail.ratingChange != null
                    ? ` · ${formatDelta(detail.ratingChange)}`
                    : ""}
                </span>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function RatingChart({ series, className, height = 256 }: RatingChartProps) {
  const gradientPrefix = useId().replace(/:/g, "");
  const [hidden, setHidden] = useState<string[]>([]);
  // UTC on server and first paint; the viewer's zone after mount (no hydration mismatch).
  const [timeZone, setTimeZone] = useState<string | undefined>(undefined);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTimeZone(Intl.DateTimeFormat().resolvedOptions().timeZone);
  }, []);
  const { rows, meta } = buildChart(series);
  const hasPoints = series.some((item) => item.points.length > 0);
  const visible = series
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => !hidden.includes(item.name));

  if (!hasPoints) {
    return (
      <div
        className={cn(
          "flex items-center justify-center text-sm text-muted-foreground",
          className,
        )}
        style={{ height }}
      >
        No rating history yet
      </div>
    );
  }

  const ratings = visible.flatMap(({ item }) =>
    item.points.map((point) => point.rating),
  );
  const min = ratings.length > 0 ? Math.min(...ratings) : 1500;
  const max = ratings.length > 0 ? Math.max(...ratings) : 1500;
  const pad = Math.max(8, Math.round((max - min) * 0.18) || 8);
  const showDots = rows.length === 1;

  function toggle(name: string) {
    setHidden((current) =>
      current.includes(name)
        ? current.filter((item) => item !== name)
        : [...current, name],
    );
  }

  return (
    <div className={cn("w-full", className)}>
      {series.length > 1 ? (
        <ul className="mb-3 flex flex-wrap gap-2 text-xs">
          {series.map((item, index) => {
            const on = !hidden.includes(item.name);
            return (
              <li key={`${item.name}-${index}`}>
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => toggle(item.name)}
                  className={cn(
                    "inline-flex h-9 items-center gap-2 rounded-full px-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    on ? "text-foreground/90" : "text-muted-foreground line-through",
                  )}
                >
                  <span
                    className="size-2.5 rounded-[3px]"
                    style={{ background: on ? seriesColor(item, index) : "rgba(255,255,255,0.3)" }}
                  />
                  {item.name}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
      {visible.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Turn a player back on in the legend.
        </p>
      ) : (
        <div style={{ height }} className="w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rows} margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis
                dataKey="key"
                tickLine={false}
                axisLine={false}
                tick={{ fill: AXIS_TEXT, fontSize: 12, fontFamily: "var(--font-geist-mono)" }}
                tickFormatter={(value: string) => {
                  const row = rows.find((entry) => entry.key === value);
                  return displayLabel(row?.label ?? value, timeZone);
                }}
                minTickGap={24}
                padding={{ left: 8, right: 32 }}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                width={44}
                domain={[min - pad, max + pad]}
                tick={{ fill: AXIS_TEXT, fontSize: 12, fontFamily: "var(--font-geist-mono)" }}
                tickFormatter={(value: number) => formatRating(value)}
              />
              <Tooltip
                content={(props) => (
                  <RatingTooltip
                    active={props.active}
                    payload={props.payload}
                    label={props.label}
                    meta={meta}
                    series={series}
                    timeZone={timeZone}
                  />
                )}
                cursor={{ stroke: "rgba(255,255,255,0.3)", strokeWidth: 1 }}
              />
              {visible.map(({ item, index }) => {
                const color = seriesColor(item, index);
                return (
                  <Line
                    key={`${gradientPrefix}-${item.name}-${index}`}
                    type="monotone"
                    dataKey={seriesDataKey(index)}
                    name={item.name}
                    stroke={color}
                    strokeWidth={series.length > 1 && index === 0 ? 3.5 : 2.5}
                    strokeLinecap="round"
                    connectNulls
                    dot={showDots ? { r: 3, strokeWidth: 0, fill: color } : false}
                    activeDot={{ r: 4, strokeWidth: 0, fill: color }}
                    isAnimationActive={false}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
