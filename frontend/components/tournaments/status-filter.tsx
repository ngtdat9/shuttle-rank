"use client";

import {
  fieldLabelClass,
  nativeSelectClass,
  useQueryUpdate,
} from "@/components/club/query-controls";
import {
  isTournamentStatus,
  TOURNAMENT_STATUSES,
} from "@/components/tournaments/statuses";

export function TournamentStatusFilter() {
  const { searchParams, update } = useQueryUpdate();
  const raw = searchParams.get("status") ?? "";
  const value = isTournamentStatus(raw) ? raw : "";

  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className={fieldLabelClass}>
        Status
        <select
          className={nativeSelectClass}
          value={value}
          onChange={(event) => update({ status: event.target.value || null })}
        >
          <option value="">All</option>
          {TOURNAMENT_STATUSES.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
