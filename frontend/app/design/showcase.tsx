"use client";

import { useState, type ReactNode } from "react";
import { Eye } from "lucide-react";

import { BarStat } from "@/components/charts/bar-stat";
import { RatingChart } from "@/components/charts/rating-chart";
import { ConfirmDialog } from "@/components/confirm-dialog";
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeader,
  DataTableRow,
  dataTableIconButtonClass,
} from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { FormGuide, type FormResult } from "@/components/form-guide";
import {
  CardsSkeleton,
  ChartSkeleton,
  TableRowsSkeleton,
} from "@/components/loading-skeleton";
import { PageHeader } from "@/components/page-header";
import { PlayerAvatar } from "@/components/player-avatar";
import { RankBadge } from "@/components/rank-badge";
import { RatingDelta } from "@/components/rating-delta";
import { SectionCard } from "@/components/section-card";
import { StatCard } from "@/components/stat-card";
import { StatusBadge, type StatusKind } from "@/components/status-badge";
import { WinRate } from "@/components/win-rate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatDate, formatRating } from "@/lib/format";

/**
 * Rendered only by app/design/page.tsx.
 * Sample props below are for visual review. They are not club data.
 */

const SAMPLE_AVATAR = `data:image/svg+xml,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#1f7a76"/><text x="32" y="40" text-anchor="middle" fill="#f5f7f5" font-size="22" font-family="sans-serif">SR</text></svg>`,
)}`;

const SAMPLE_ROWS: {
  rank: number;
  name: string;
  rating: number;
  delta: number;
  winRate: number;
  form: FormResult[];
}[] = [
  {
    rank: 1,
    name: "Minh Tran",
    rating: 1284,
    delta: 16,
    winRate: 72.4,
    form: ["W", "W", "L", "W", "W"],
  },
  {
    rank: 2,
    name: "Kenji Sato",
    rating: 1240,
    delta: -8,
    winRate: 64.1,
    form: ["L", "W", "W", "L", "W"],
  },
  {
    rank: 3,
    name: "Luca Rossi",
    rating: 1211,
    delta: 4,
    winRate: 58,
    form: ["W", "L", "W", "W", "L"],
  },
  {
    rank: 4,
    name: "Omar Haddad",
    rating: 1176,
    delta: 0,
    winRate: 51.2,
    form: ["L", "L", "W", "L", "W"],
  },
  {
    rank: 5,
    name: "Theo Nguyen",
    rating: 1142,
    delta: -12,
    winRate: 46.7,
    form: ["L", "W", "L", "L", "W"],
  },
];

const STATUSES: StatusKind[] = [
  "completed",
  "canceled",
  "disputed",
  "draft",
  "in_progress",
];

const SWATCHES = [
  { name: "Background", className: "bg-background" },
  { name: "Surface", className: "bg-surface" },
  { name: "Elevated", className: "bg-elevated" },
  { name: "Lime", className: "bg-primary" },
  { name: "Cyan", className: "bg-secondary" },
  { name: "Coral", className: "bg-negative" },
  { name: "Amber", className: "bg-warning" },
];

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-xs font-medium tracking-[0.14em] text-muted-foreground uppercase">
        {title}
      </h2>
      {children}
    </section>
  );
}

export function DesignShowcase() {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  return (
    <div className="flex flex-col gap-10">
      <PageHeader
        title="Design system"
        subtitle="Component showcase for review. This route is not in the club navigation, and the figures below are sample props."
        actions={
          <Button type="button" className="rounded-full" onClick={() => setConfirmOpen(true)}>
            Open confirm
          </Button>
        }
      />

      <Block title="Tokens">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
          {SWATCHES.map((swatch) => (
            <div key={swatch.name} className="flex flex-col gap-2">
              <div
                className={`h-14 rounded-[20px] ring-1 ring-foreground/10 ${swatch.className}`}
              />
              <p className="text-xs text-muted-foreground">{swatch.name}</p>
            </div>
          ))}
        </div>
        <p className="text-sm text-muted-foreground">
          {formatDate("2026-03-01", undefined, "en-US")} · rating{" "}
          {formatRating(1284, "en-US")} · 72.4% · delta +16
        </p>
      </Block>

      <Block title="Controls">
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <Button type="button">Primary</Button>
          <Button type="button" variant="secondary">
            Secondary
          </Button>
          <Button type="button" variant="outline">
            Outline
          </Button>
          <Button type="button" variant="destructive">
            Destructive
          </Button>
          <Badge>Lime</Badge>
          <Badge variant="secondary">Cyan</Badge>
          <Badge variant="outline">Outline</Badge>
          <Input className="max-w-xs" placeholder="Player name" aria-label="Player name" />
          <Select defaultValue="singles">
            <SelectTrigger className="w-44 rounded-full" aria-label="Discipline">
              <SelectValue placeholder="Discipline" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="singles">Men&apos;s singles</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Block>

      <Block title="Stats">
        <div className="grid gap-3 sm:grid-cols-3">
          <StatCard label="Sample rating" value={formatRating(1284, "en-US")} delta={16} />
          <StatCard
            label="Sample change"
            value={formatRating(1176, "en-US")}
            delta={-8}
            subLabel="Last recorded match"
          />
          <StatCard label="Unchanged" value={formatRating(1211, "en-US")} delta={0} />
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <RatingDelta value={16} />
          <RatingDelta value={-16} />
          <RatingDelta value={0} />
        </div>
      </Block>

      <Block title="Players">
        <div className="flex flex-wrap items-center gap-4">
          <PlayerAvatar name="Minh Tran" size="lg" />
          <PlayerAvatar name="Kenji Sato" />
          <PlayerAvatar name="Luca Rossi" size="sm" />
          <PlayerAvatar name="Sample Photo" imageUrl={SAMPLE_AVATAR} />
          <RankBadge rank={1} />
          <RankBadge rank={2} />
          <RankBadge rank={3} />
          <RankBadge rank={4} />
          <RankBadge rank={12} />
        </div>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <FormGuide results={["W", "W", "L", "W", "L"]} />
          <WinRate percent={72.4} className="w-28" />
          <div className="flex flex-wrap gap-2">
            {STATUSES.map((status) => (
              <StatusBadge key={status} status={status} />
            ))}
          </div>
        </div>
      </Block>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Rating history" description="Sample series for the chart foundation">
          <RatingChart
            series={[
              {
                name: "Minh",
                points: [
                  { date: "2026-01-04", rating: 1180 },
                  { date: "2026-01-18", rating: 1204 },
                  { date: "2026-02-01", rating: 1196 },
                  { date: "2026-02-15", rating: 1232 },
                  { date: "2026-03-01", rating: 1284 },
                ],
              },
              {
                name: "Kenji",
                points: [
                  { date: "2026-01-04", rating: 1210 },
                  { date: "2026-01-18", rating: 1226 },
                  { date: "2026-02-01", rating: 1248 },
                  { date: "2026-02-15", rating: 1236 },
                  { date: "2026-03-01", rating: 1240 },
                ],
              },
            ]}
          />
        </SectionCard>
        <SectionCard title="Session bars" description="Optional bar chart">
          <BarStat
            data={[
              { label: "W1", value: 4 },
              { label: "W2", value: 6 },
              { label: "W3", value: 3 },
              { label: "W4", value: 7 },
              { label: "W5", value: 5 },
              { label: "W6", value: 8 },
            ]}
          />
        </SectionCard>
      </div>

      <SectionCard title="Comparison" description="Dense table styling">
        <DataTable>
          <DataTableHeader>
            <DataTableRow>
              <DataTableHead>Rk</DataTableHead>
              <DataTableHead>Player</DataTableHead>
              <DataTableHead>Rating</DataTableHead>
              <DataTableHead>Form</DataTableHead>
              <DataTableHead>Win rate</DataTableHead>
              <DataTableHead className="text-right">Action</DataTableHead>
            </DataTableRow>
          </DataTableHeader>
          <DataTableBody>
            {SAMPLE_ROWS.map((row) => (
              <DataTableRow key={row.name}>
                <DataTableCell>
                  <RankBadge rank={row.rank} />
                </DataTableCell>
                <DataTableCell>
                  <div className="flex items-center gap-2">
                    <PlayerAvatar name={row.name} size="sm" />
                    <span className="font-medium">{row.name}</span>
                  </div>
                </DataTableCell>
                <DataTableCell>
                  <div className="flex items-center gap-2">
                    <span className="tabular-nums">{formatRating(row.rating, "en-US")}</span>
                    <RatingDelta value={row.delta} />
                  </div>
                </DataTableCell>
                <DataTableCell>
                  <FormGuide results={row.form} />
                </DataTableCell>
                <DataTableCell>
                  <WinRate percent={row.winRate} />
                </DataTableCell>
                <DataTableCell className="text-right">
                  <button
                    type="button"
                    className={dataTableIconButtonClass}
                    aria-label={`View ${row.name}`}
                  >
                    <Eye className="size-3.5" aria-hidden />
                  </button>
                </DataTableCell>
              </DataTableRow>
            ))}
          </DataTableBody>
        </DataTable>
      </SectionCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <EmptyState
          title="No matches yet"
          description="Recorded games will show up here."
          action={
            <Button type="button" variant="outline" className="rounded-full">
              Sample action
            </Button>
          }
        />
        <ErrorState
          title="Could not load the board"
          message={
            retryCount === 0
              ? "The request failed. Retry is wired for the showcase."
              : `Retry clicked ${retryCount} time${retryCount === 1 ? "" : "s"}.`
          }
          onRetry={() => setRetryCount((count) => count + 1)}
        />
      </div>

      <Block title="Loading">
        <CardsSkeleton />
        <ChartSkeleton />
        <TableRowsSkeleton />
      </Block>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Cancel this match?"
        description="This changes ratings. The backend will replay Elo after you confirm. Nothing is submitted from this showcase."
        confirmLabel="Cancel match"
        destructive
        onConfirm={() => setConfirmOpen(false)}
      />
    </div>
  );
}
