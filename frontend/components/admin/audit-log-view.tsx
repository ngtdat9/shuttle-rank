"use client";

import { Fragment, useState, type ReactNode } from "react";

import { AdminQueryError, adminSelectClass } from "@/components/admin/ui";
import { useAdminQuery } from "@/components/admin/use-admin-query";
import { fieldLabelClass, useQueryUpdate } from "@/components/club/query-controls";
import { LocalDateTime } from "@/components/local-time";
import { Pager } from "@/components/pager";
import { getAdminAuditLogs } from "@/lib/api/admin";
import { AUDIT_ACTIONS, AUDIT_ENTITY_TYPES } from "@/lib/admin/labels";

const PAGE_SIZE = 20;

export function AuditLogView() {
  const { searchParams, update, pathname } = useQueryUpdate();
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const entityType = searchParams.get("entity_type") ?? "";
  const action = searchParams.get("action") ?? "";
  const [openId, setOpenId] = useState<string | null>(null);
  const logs = useAdminQuery(
    `admin-audit:${page}:${entityType}:${action}`,
    (token, signal) =>
      getAdminAuditLogs(
        token,
        {
          page,
          page_size: PAGE_SIZE,
          entity_type: entityType || undefined,
          action: action || undefined,
        },
        signal,
      ),
  );

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-[28px] leading-[34px] font-semibold">Audit log</h1>
      <div className="flex flex-wrap items-end gap-3">
        <label className={fieldLabelClass}>
          Entity type
          <select
            className={adminSelectClass}
            value={entityType}
            onChange={(event) =>
              update({ entity_type: event.target.value || null, page: null })
            }
          >
            <option value="">All</option>
            {AUDIT_ENTITY_TYPES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className={fieldLabelClass}>
          Action
          <select
            className={adminSelectClass}
            value={action}
            onChange={(event) =>
              update({ action: event.target.value || null, page: null })
            }
          >
            <option value="">All</option>
            {AUDIT_ACTIONS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </div>
      {logs.loading ? (
        <div aria-busy="true" className="h-64 animate-pulse rounded-[20px] bg-elevated">
          <span className="sr-only">Loading audit log</span>
        </div>
      ) : logs.error ? (
        <AdminQueryError
          thing="the audit log"
          error={logs.error}
          onRetry={logs.reload}
        />
      ) : logs.data && logs.data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No admin activity yet.</p>
      ) : (
        <>
          <div className="overflow-x-auto rounded-[20px] bg-card ring-1 ring-foreground/10">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="px-3 py-3 font-medium">Time</th>
                  <th className="px-3 py-3 font-medium">Actor</th>
                  <th className="px-3 py-3 font-medium">Action</th>
                  <th className="px-3 py-3 font-medium">Entity</th>
                  <th className="px-3 py-3 font-medium">Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.data?.items.map((entry) => {
                  const open = openId === entry.id;
                  const panelId = `audit-${entry.id}`;
                  return (
                    <AuditRows key={entry.id}>
                      <tr className="border-t border-border">
                        <td className="px-3 py-3 whitespace-nowrap">
                          <LocalDateTime value={entry.created_at} />
                        </td>
                        <td className="px-3 py-3 font-mono text-xs">
                          {entry.actor_id}
                        </td>
                        <td className="px-3 py-3">{entry.action}</td>
                        <td className="px-3 py-3">
                          {entry.entity_type}
                          <span className="mt-1 block font-mono text-xs text-muted-foreground">
                            {entry.entity_id ?? "—"}
                          </span>
                        </td>
                        <td className="px-3 py-3">
                          <button
                            type="button"
                            className="text-sm underline-offset-4 hover:underline focus-visible:rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            aria-expanded={open}
                            aria-controls={panelId}
                            onClick={() => setOpenId(open ? null : entry.id)}
                          >
                            {open ? "Hide" : "Show"}
                          </button>
                        </td>
                      </tr>
                      {open ? (
                        <tr className="border-t border-border">
                          <td id={panelId} colSpan={5} className="px-3 py-3">
                            <div className="grid gap-3 md:grid-cols-2">
                              <JsonBlock label="Before" value={entry.before_data} />
                              <JsonBlock label="After" value={entry.after_data} />
                            </div>
                          </td>
                        </tr>
                      ) : null}
                    </AuditRows>
                  );
                })}
              </tbody>
            </table>
          </div>
          {logs.data ? (
            <Pager
              page={logs.data.page}
              pageSize={logs.data.page_size}
              total={logs.data.total}
              pathname={pathname}
              query={{
                entity_type: entityType || undefined,
                action: action || undefined,
              }}
            />
          ) : null}
        </>
      )}
    </div>
  );
}

function AuditRows({ children }: { children: ReactNode }) {
  return <Fragment>{children}</Fragment>;
}

function JsonBlock({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <p className="mb-1 text-xs font-medium text-muted-foreground">{label}</p>
      <pre className="overflow-x-auto rounded-xl bg-elevated p-3 font-mono text-xs whitespace-pre-wrap">
        {formatJson(value)}
      </pre>
    </div>
  );
}

function formatJson(value: unknown): string {
  if (value == null) return "null";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return "Could not display this payload.";
  }
}
