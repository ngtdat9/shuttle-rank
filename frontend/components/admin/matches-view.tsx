"use client";

import { useState } from "react";
import Link from "next/link";

import {
  CancelMatchDialog,
  CorrectMatchDialog,
  DeleteMatchDialog,
  NotesMatchDialog,
  RecordMatchDialog,
} from "@/components/admin/match-dialogs";
import {
  AdminQueryError,
  adminOutlineButtonClass,
  adminPrimaryButtonClass,
  adminSelectClass,
} from "@/components/admin/ui";
import { useAdminQuery } from "@/components/admin/use-admin-query";
import {
  fieldLabelClass,
  SearchField,
  useQueryUpdate,
} from "@/components/club/query-controls";
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeader,
  DataTableRow,
} from "@/components/data-table";
import { LocalDateTime } from "@/components/local-time";
import { Pager } from "@/components/pager";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  getAdminMatches,
  getAdminPlayers,
  getAdminTournaments,
  matchDeletedAt,
  type AdminMatch,
} from "@/lib/api/admin";
import type { MatchListStatus } from "@/types/api";

const headClass = "normal-case tracking-normal";
const PAGE_SIZE = 20;

export function MatchesView() {
  const { searchParams, update, pathname } = useQueryUpdate();
  const wantRecord = searchParams.get("record") === "1";
  const [recordOpen, setRecordOpen] = useState(false);
  const [seenRecord, setSeenRecord] = useState(false);
  const [notesMatch, setNotesMatch] = useState<AdminMatch | null>(null);
  const [correctMatch, setCorrectMatch] = useState<AdminMatch | null>(null);
  const [cancelMatch, setCancelMatch] = useState<AdminMatch | null>(null);
  const [deleteMatch, setDeleteMatch] = useState<AdminMatch | null>(null);

  if (wantRecord && !seenRecord) {
    setSeenRecord(true);
    setRecordOpen(true);
  }
  if (!wantRecord && seenRecord) setSeenRecord(false);

  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const status = (searchParams.get("status") ?? "all") as MatchListStatus;
  const playerId = searchParams.get("player_id") ?? "";
  const tournamentId = searchParams.get("tournament_id") ?? "";
  const dateFrom = searchParams.get("date_from") ?? "";
  const dateTo = searchParams.get("date_to") ?? "";
  const search = searchParams.get("search") ?? "";
  const includeDeleted = searchParams.get("deleted") === "1";
  const filtersDefault =
    !search &&
    !playerId &&
    !tournamentId &&
    !dateFrom &&
    !dateTo &&
    !includeDeleted &&
    (status === "all" || !searchParams.get("status"));

  const queryKey = JSON.stringify({
    page,
    status,
    playerId,
    tournamentId,
    dateFrom,
    dateTo,
    search,
    includeDeleted,
  });

  const players = useAdminQuery("admin-match-players", (token, signal) =>
    getAdminPlayers(token, signal),
  );
  const tournaments = useAdminQuery("admin-match-tournaments", (token, signal) =>
    getAdminTournaments(token, undefined, signal),
  );
  const matches = useAdminQuery(`admin-matches:${queryKey}`, (token, signal) =>
    getAdminMatches(
      token,
      {
        page,
        page_size: PAGE_SIZE,
        status,
        player_id: playerId || undefined,
        tournament_id: tournamentId || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        search: search || undefined,
        include_deleted: includeDeleted,
      },
      signal,
    ),
  );

  function closeRecord() {
    setRecordOpen(false);
    if (wantRecord) update({ record: null });
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-[28px] leading-[34px] font-semibold">Matches</h1>
        <Button
          type="button"
          className={adminPrimaryButtonClass}
          onClick={() => setRecordOpen(true)}
        >
          Record match
        </Button>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <SearchField param="search" label="Player name" placeholder="Search players" />
        <label className={fieldLabelClass}>
          Player
          <select
            className={adminSelectClass}
            value={playerId}
            onChange={(event) =>
              update({ player_id: event.target.value || null, page: null })
            }
          >
            <option value="">Any player</option>
            {players.data?.items.map((player) => (
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
            className={adminSelectClass}
            value={status}
            onChange={(event) =>
              update({
                status: event.target.value === "all" ? null : event.target.value,
                page: null,
              })
            }
          >
            <option value="all">All</option>
            <option value="completed">Completed</option>
            <option value="disputed">Disputed</option>
            <option value="canceled">Canceled</option>
          </select>
        </label>
        <label className={fieldLabelClass}>
          Tournament
          <select
            className={adminSelectClass}
            value={tournamentId}
            onChange={(event) =>
              update({ tournament_id: event.target.value || null, page: null })
            }
          >
            <option value="">Any tournament</option>
            {tournaments.data?.items.map((tournament) => (
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
            className={adminSelectClass}
            value={dateFrom}
            onChange={(event) =>
              update({ date_from: event.target.value || null, page: null })
            }
          />
        </label>
        <label className={fieldLabelClass}>
          To (UTC)
          <input
            type="date"
            className={adminSelectClass}
            value={dateTo}
            onChange={(event) =>
              update({ date_to: event.target.value || null, page: null })
            }
          />
        </label>
        <label className="flex h-11 items-center gap-2 text-sm md:h-10">
          <input
            type="checkbox"
            className="size-4 accent-primary"
            checked={includeDeleted}
            onChange={(event) =>
              update({ deleted: event.target.checked ? "1" : null, page: null })
            }
          />
          Show deleted
        </label>
        <Button
          type="button"
          variant="outline"
          className={adminOutlineButtonClass}
          onClick={() =>
            update({
              search: null,
              player_id: null,
              status: null,
              tournament_id: null,
              date_from: null,
              date_to: null,
              deleted: null,
              page: null,
            })
          }
        >
          Clear
        </Button>
      </div>

      {matches.loading ? (
        <div
          aria-busy="true"
          aria-live="polite"
          className="h-64 animate-pulse rounded-[20px] bg-elevated"
        >
          <span className="sr-only">Loading matches</span>
        </div>
      ) : matches.error ? (
        <AdminQueryError
          thing="matches"
          error={matches.error}
          onRetry={matches.reload}
        />
      ) : matches.data && matches.data.items.length === 0 ? (
        <div className="flex flex-col items-start gap-3">
          <p className="text-sm text-muted-foreground">
            {filtersDefault ? "No matches yet." : "No matches match these filters."}
          </p>
          {filtersDefault ? (
            <Button
              type="button"
              className={adminPrimaryButtonClass}
              onClick={() => setRecordOpen(true)}
            >
              Record match
            </Button>
          ) : null}
        </div>
      ) : (
        <>
          <DataTable>
            <DataTableHeader>
              <DataTableRow>
                <DataTableHead
                  className={`${headClass} sticky left-0 z-10 bg-elevated`}
                >
                  Date
                </DataTableHead>
                <DataTableHead className={headClass}>Player A</DataTableHead>
                <DataTableHead className={headClass}>Player B</DataTableHead>
                <DataTableHead className={headClass}>Winner</DataTableHead>
                <DataTableHead className={headClass}>Status</DataTableHead>
                <DataTableHead className={headClass}>Actions</DataTableHead>
              </DataTableRow>
            </DataTableHeader>
            <DataTableBody>
              {matches.data?.items.map((match) => {
                const deleted = matchDeletedAt(match);
                const winner =
                  match.winner_id === match.player_a.id
                    ? match.player_a.display_name
                    : match.player_b.display_name;
                return (
                  <DataTableRow key={match.id}>
                    <DataTableCell className="sticky left-0 z-10 bg-card whitespace-nowrap">
                      <LocalDateTime value={match.match_date} />
                    </DataTableCell>
                    <DataTableCell>{match.player_a.display_name}</DataTableCell>
                    <DataTableCell>{match.player_b.display_name}</DataTableCell>
                    <DataTableCell>{winner}</DataTableCell>
                    <DataTableCell>
                      <span className="flex flex-wrap items-center gap-1">
                        <StatusBadge status={match.status} />
                        {deleted ? (
                          <span className="inline-flex h-5 items-center rounded-full bg-destructive/15 px-2 text-xs font-medium text-negative">
                            Deleted
                          </span>
                        ) : null}
                        {match.tournament ? (
                          <Link
                            href={`/admin/tournaments/${match.tournament.id}`}
                            className="inline-flex h-5 items-center rounded-full bg-secondary/15 px-2 text-xs font-medium text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          >
                            {match.tournament.name}
                          </Link>
                        ) : null}
                      </span>
                    </DataTableCell>
                    <DataTableCell>
                      {deleted ? null : (
                        <div className="flex flex-wrap gap-2">
                          <RowButton onClick={() => setNotesMatch(match)}>
                            Edit details
                          </RowButton>
                          <RowButton onClick={() => setCorrectMatch(match)}>
                            Correct
                          </RowButton>
                          {match.status !== "canceled" ? (
                            <RowButton onClick={() => setCancelMatch(match)}>
                              Cancel
                            </RowButton>
                          ) : null}
                          <RowButton onClick={() => setDeleteMatch(match)}>
                            Delete
                          </RowButton>
                        </div>
                      )}
                    </DataTableCell>
                  </DataTableRow>
                );
              })}
            </DataTableBody>
          </DataTable>
          {matches.data ? (
            <Pager
              page={matches.data.page}
              pageSize={matches.data.page_size}
              total={matches.data.total}
              pathname={pathname}
              query={{
                search: search || undefined,
                player_id: playerId || undefined,
                status: status === "all" ? undefined : status,
                tournament_id: tournamentId || undefined,
                date_from: dateFrom || undefined,
                date_to: dateTo || undefined,
                deleted: includeDeleted ? "1" : undefined,
              }}
            />
          ) : null}
        </>
      )}

      <RecordMatchDialog
        open={recordOpen}
        onOpenChange={(open) => {
          if (!open) closeRecord();
          else setRecordOpen(true);
        }}
        players={players.data?.items ?? []}
        onDone={() => matches.reload()}
      />
      {notesMatch ? (
        <NotesMatchDialog
          key={notesMatch.id}
          match={notesMatch}
          onOpenChange={(open) => {
            if (!open) setNotesMatch(null);
          }}
          onDone={() => matches.reload()}
        />
      ) : null}
      {correctMatch ? (
        <CorrectMatchDialog
          key={correctMatch.id}
          match={correctMatch}
          players={players.data?.items ?? []}
          onOpenChange={(open) => {
            if (!open) setCorrectMatch(null);
          }}
          onDone={() => matches.reload()}
        />
      ) : null}
      {cancelMatch ? (
        <CancelMatchDialog
          key={cancelMatch.id}
          match={cancelMatch}
          onOpenChange={(open) => {
            if (!open) setCancelMatch(null);
          }}
          onDone={() => matches.reload()}
        />
      ) : null}
      {deleteMatch ? (
        <DeleteMatchDialog
          key={deleteMatch.id}
          match={deleteMatch}
          onOpenChange={(open) => {
            if (!open) setDeleteMatch(null);
          }}
          onDone={() => matches.reload()}
        />
      ) : null}
    </div>
  );
}

function RowButton({ children, onClick }: { children: string; onClick: () => void }) {
  return (
    <button
      type="button"
      className="text-sm underline-offset-4 hover:underline focus-visible:rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      onClick={onClick}
    >
      {children}
    </button>
  );
}
