"use client";

import type { ReactNode } from "react";
import Link from "next/link";

import { AdminQueryError } from "@/components/admin/ui";
import { useAdminQuery } from "@/components/admin/use-admin-query";
import { LocalDateTime } from "@/components/local-time";
import { textActionClass } from "@/components/club/styles";
import { getAdminAuditLogs, getAdminStats } from "@/lib/api/admin";

export function OverviewView() {
  const statsQuery = useAdminQuery("admin-stats", (token, signal) =>
    getAdminStats(token, signal),
  );
  const auditQuery = useAdminQuery("admin-audit-preview", (token, signal) =>
    getAdminAuditLogs(token, { page: 1, page_size: 10 }, signal),
  );

  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <h1 className="text-[28px] leading-[34px] font-semibold">Overview</h1>
      {statsQuery.loading ? (
        <div
          aria-busy="true"
          aria-live="polite"
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          <span className="sr-only">Loading overview</span>
          {Array.from({ length: 4 }, (_, index) => (
            <div
              key={index}
              className="h-32 animate-pulse rounded-[20px] bg-elevated"
            />
          ))}
        </div>
      ) : statsQuery.error ? (
        <AdminQueryError
          thing="overview"
          error={statsQuery.error}
          onRetry={statsQuery.reload}
        />
      ) : statsQuery.data ? (
        <section
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
          aria-label="Club counts"
        >
          <Stat
            label="Players"
            value={statsQuery.data.players_active}
            detail="active"
            muted={`${statsQuery.data.players_total} total`}
          />
          <Stat
            label="Matches"
            value={statsQuery.data.matches_completed}
            detail="completed"
            muted={`${statsQuery.data.matches_canceled} canceled · ${statsQuery.data.matches_disputed} disputed`}
            footer={
              statsQuery.data.last_match_at ? (
                <>
                  Last match <LocalDateTime value={statsQuery.data.last_match_at} />
                </>
              ) : (
                "No matches yet."
              )
            }
          />
          <Stat
            label="Tournaments"
            value={statsQuery.data.tournaments_in_progress}
            detail="in progress"
            muted={`${statsQuery.data.tournaments_total} total`}
          />
          <Stat
            label="Achievements"
            value={statsQuery.data.achievements_awarded}
            detail="awarded"
          />
        </section>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-12 lg:gap-5">
        <section className="rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 md:p-5 lg:col-span-7">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Recent activity</h2>
            <Link href="/admin/audit-log" className={textActionClass}>
              Full log
            </Link>
          </div>
          {auditQuery.loading ? (
            <div
              aria-busy="true"
              className="mt-4 h-40 animate-pulse rounded-xl bg-elevated"
            >
              <span className="sr-only">Loading recent activity</span>
            </div>
          ) : auditQuery.error ? (
            <div className="mt-4">
              <AdminQueryError
                thing="recent activity"
                error={auditQuery.error}
                onRetry={auditQuery.reload}
              />
            </div>
          ) : auditQuery.data && auditQuery.data.items.length > 0 ? (
            <ul className="mt-3 divide-y divide-border">
              {auditQuery.data.items.map((entry) => (
                <li
                  key={entry.id}
                  className="flex flex-wrap items-baseline justify-between gap-2 py-3 text-sm"
                >
                  <span>
                    <span className="font-medium">{entry.action}</span>
                    <span className="text-muted-foreground">
                      {" "}
                      · {entry.entity_type}
                    </span>
                  </span>
                  <span className="text-xs text-muted-foreground">
                    <LocalDateTime value={entry.created_at} />
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-muted-foreground">No admin activity yet.</p>
          )}
        </section>
        <section className="rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 md:p-5 lg:col-span-5">
          <h2 className="text-lg font-semibold">Shortcuts</h2>
          <div className="mt-3 flex flex-col items-start gap-1">
            <Link href="/admin/matches?record=1" className={textActionClass}>
              Record match
            </Link>
            <Link href="/admin/players?new=1" className={textActionClass}>
              Add player
            </Link>
            <Link href="/admin/tournaments?new=1" className={textActionClass}>
              New tournament
            </Link>
            <Link href="/admin/players" className={textActionClass}>
              Players
            </Link>
            <Link href="/admin/matches" className={textActionClass}>
              Matches
            </Link>
            <Link href="/admin/tournaments" className={textActionClass}>
              Tournaments
            </Link>
            <Link href="/admin/achievements" className={textActionClass}>
              Achievements
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  detail,
  muted,
  footer,
}: {
  label: string;
  value: number;
  detail: string;
  muted?: string;
  footer?: ReactNode;
}) {
  return (
    <article className="rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 md:p-5">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-2 text-[28px] leading-none font-semibold tabular-nums">
        {value}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
      {muted ? (
        <p className="mt-2 text-xs text-muted-foreground tabular-nums">{muted}</p>
      ) : null}
      {footer ? <p className="mt-2 text-xs text-muted-foreground">{footer}</p> : null}
    </article>
  );
}
