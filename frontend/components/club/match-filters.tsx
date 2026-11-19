"use client";

import { Button } from "@/components/ui/button";
import { SearchField, nativeSelectClass, fieldLabelClass, useQueryUpdate } from "@/components/club/query-controls";
import type { PlayerListItem, TournamentSummary } from "@/types/api";

const STATUSES = [
  { value: "completed", label: "Completed" },
  { value: "canceled", label: "Canceled" },
  { value: "disputed", label: "Disputed" },
  { value: "all", label: "All" },
] as const;

export function MatchFilters({
  players,
  tournaments,
}: {
  players: PlayerListItem[];
  tournaments: TournamentSummary[];
}) {
  const { searchParams, update } = useQueryUpdate();
  const status = searchParams.get("status") ?? "completed";
  const playerId = searchParams.get("player_id") ?? "";
  const tournamentId = searchParams.get("tournament_id") ?? "";
  const dateFrom = searchParams.get("date_from") ?? "";
  const dateTo = searchParams.get("date_to") ?? "";

  return (
    <div className="flex flex-wrap items-end gap-3">
      <SearchField param="search" label="Player name" placeholder="Search players" />
      <label className={fieldLabelClass}>
        Player
        <select
          className={nativeSelectClass}
          value={playerId}
          onChange={(event) => update({ player_id: event.target.value || null, page: null })}
        >
          <option value="">Any player</option>
          {players.map((player) => (
            <option key={player.id} value={player.id}>
              {player.display_name}
              {player.is_active ? "" : " · Inactive"}
            </option>
          ))}
        </select>
      </label>
      <label className={fieldLabelClass}>
        Status
        <select
          className={nativeSelectClass}
          value={STATUSES.some((item) => item.value === status) ? status : "completed"}
          onChange={(event) =>
            update({
              status: event.target.value === "completed" ? null : event.target.value,
              page: null,
            })
          }
        >
          {STATUSES.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <label className={fieldLabelClass}>
        Tournament
        <select
          className={nativeSelectClass}
          value={tournamentId}
          onChange={(event) => update({ tournament_id: event.target.value || null, page: null })}
        >
          <option value="">Any tournament</option>
          {tournaments.map((tournament) => (
            <option key={tournament.id} value={tournament.id}>
              {tournament.name}
            </option>
          ))}
        </select>
      </label>
      <label className={fieldLabelClass}>
        From (UTC)
        <input
          type="date"
          className={nativeSelectClass}
          value={dateFrom}
          onChange={(event) => update({ date_from: event.target.value || null, page: null })}
        />
      </label>
      <label className={fieldLabelClass}>
        To (UTC)
        <input
          type="date"
          className={nativeSelectClass}
          value={dateTo}
          onChange={(event) => update({ date_to: event.target.value || null, page: null })}
        />
      </label>
      <Button
        type="button"
        variant="outline"
        className="h-11 px-4 md:h-10"
        onClick={() =>
          update({
            search: null,
            player_id: null,
            status: null,
            tournament_id: null,
            date_from: null,
            date_to: null,
            page: null,
          })
        }
      >
        Clear
      </Button>
    </div>
  );
}
