"use client";

import { useState } from "react";
import Link from "next/link";

import { notifyFailure, notifySuccess } from "@/components/admin/feedback";
import {
  AdminDialogActions,
  AdminField,
  AdminFormDialog,
  AdminLiveError,
  AdminQueryError,
  adminInputClass,
  adminOutlineButtonClass,
  adminPrimaryButtonClass,
} from "@/components/admin/ui";
import { useAdminMutation, useAdminQuery } from "@/components/admin/use-admin-query";
import { useQueryUpdate } from "@/components/club/query-controls";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { createAdminTournament, getAdminTournaments } from "@/lib/api/admin";
import { formatDate } from "@/lib/format";

export function TournamentsView() {
  const { searchParams, update } = useQueryUpdate();
  const wantNew = searchParams.get("new") === "1";
  const [createOpen, setCreateOpen] = useState(false);
  const [seenNew, setSeenNew] = useState(false);
  const tournaments = useAdminQuery("admin-tournaments", (token, signal) =>
    getAdminTournaments(token, undefined, signal),
  );

  if (wantNew && !seenNew) {
    setSeenNew(true);
    setCreateOpen(true);
  }
  if (!wantNew && seenNew) setSeenNew(false);

  function closeCreate() {
    setCreateOpen(false);
    if (wantNew) update({ new: null });
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-[28px] leading-[34px] font-semibold">Tournaments</h1>
        <Button
          type="button"
          className="h-11 rounded-full px-4 md:h-10"
          onClick={() => setCreateOpen(true)}
        >
          New tournament
        </Button>
      </div>
      {tournaments.loading ? (
        <div aria-busy="true" className="grid gap-4 lg:grid-cols-2">
          <span className="sr-only">Loading tournaments</span>
          <div className="h-36 animate-pulse rounded-[20px] bg-elevated" />
          <div className="h-36 animate-pulse rounded-[20px] bg-elevated" />
        </div>
      ) : tournaments.error ? (
        <AdminQueryError
          thing="tournaments"
          error={tournaments.error}
          onRetry={tournaments.reload}
        />
      ) : tournaments.data && tournaments.data.items.length === 0 ? (
        <div className="flex flex-col items-start gap-3">
          <p className="text-sm text-muted-foreground">No tournaments yet.</p>
          <Button
            type="button"
            className="h-11 rounded-full px-4 md:h-10"
            onClick={() => setCreateOpen(true)}
          >
            New tournament
          </Button>
        </div>
      ) : (
        <ul className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {tournaments.data?.items.map((tournament) => (
            <li key={tournament.id}>
              <Link
                href={`/admin/tournaments/${tournament.id}`}
                className="flex h-full flex-col gap-2 rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 transition-colors hover:ring-[#3A403C] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:p-5"
              >
                <StatusBadge status={tournament.status} />
                <span className="text-lg font-semibold">{tournament.name}</span>
                <span className="text-sm text-muted-foreground">
                  {tournament.start_date
                    ? formatDate(tournament.start_date, undefined, "en-US")
                    : "Date not set"}
                  {tournament.end_date
                    ? ` – ${formatDate(tournament.end_date, undefined, "en-US")}`
                    : ""}
                </span>
                <span className="text-sm">{tournament.participant_count} players</span>
                {tournament.champion ? (
                  <span className="text-sm">
                    Champion {tournament.champion.display_name}
                  </span>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
      <CreateTournamentDialog
        open={createOpen}
        onOpenChange={(open) => {
          if (!open) closeCreate();
        }}
        onCreated={() => {
          notifySuccess("Tournament created.");
          tournaments.reload();
          closeCreate();
        }}
      />
    </div>
  );
}

function CreateTournamentDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}) {
  const mutate = useAdminMutation();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function save() {
    const trimmed = name.trim();
    if (trimmed.length < 1 || trimmed.length > 100) {
      setError("Name must be 1–100 characters.");
      return;
    }
    if (start && end && end < start) {
      setError("End date is before the start date.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      await mutate((token) =>
        createAdminTournament(token, {
          name: trimmed,
          description: description.trim() ? description.trim() : null,
          start_date: start || null,
          end_date: end || null,
        }),
      );
      onCreated();
    } catch (saveError) {
      setError(notifyFailure(saveError));
    } finally {
      setPending(false);
    }
  }

  return (
    <AdminFormDialog
      open={open}
      onOpenChange={onOpenChange}
      title="New tournament"
      description="Starts as a draft. Add players before generating a bracket."
      initialFocusId="tournament-name"
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        {error ? <AdminLiveError>{error}</AdminLiveError> : null}
        <AdminField label="Name" htmlFor="tournament-name">
          <Input
            id="tournament-name"
            className={adminInputClass}
            value={name}
            maxLength={100}
            onChange={(event) => setName(event.target.value)}
            required
          />
        </AdminField>
        <AdminField label="Description" htmlFor="tournament-description">
          <Textarea
            id="tournament-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </AdminField>
        <AdminField label="Start date" htmlFor="tournament-start">
          <Input
            id="tournament-start"
            className={adminInputClass}
            type="date"
            value={start}
            onChange={(event) => setStart(event.target.value)}
          />
        </AdminField>
        <AdminField label="End date" htmlFor="tournament-end">
          <Input
            id="tournament-end"
            className={adminInputClass}
            type="date"
            value={end}
            onChange={(event) => setEnd(event.target.value)}
          />
        </AdminField>
        <AdminDialogActions>
          <Button
            type="button"
            variant="outline"
            className={adminOutlineButtonClass}
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button type="submit" className={adminPrimaryButtonClass} disabled={pending}>
            {pending ? "Saving…" : "Create"}
          </Button>
        </AdminDialogActions>
      </form>
    </AdminFormDialog>
  );
}
