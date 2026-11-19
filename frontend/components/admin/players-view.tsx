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
  describedBy,
} from "@/components/admin/ui";
import { useAdminMutation, useAdminQuery } from "@/components/admin/use-admin-query";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { useQueryUpdate } from "@/components/club/query-controls";
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeader,
  DataTableRow,
} from "@/components/data-table";
import { InactiveBadge } from "@/components/inactive-badge";
import { PlayerAvatar } from "@/components/player-avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fieldError, isApiError } from "@/lib/admin/errors";
import {
  createAdminPlayer,
  deactivateAdminPlayer,
  getAdminPlayers,
  updateAdminPlayer,
} from "@/lib/api/admin";
import { formatRating, formatRecord } from "@/lib/format";
import type { PlayerListItem } from "@/types/api";

const headClass = "normal-case tracking-normal";

export function PlayersView() {
  const { searchParams, update } = useQueryUpdate();
  const wantNew = searchParams.get("new") === "1";
  const players = useAdminQuery("admin-players", (token, signal) =>
    getAdminPlayers(token, signal),
  );
  const mutate = useAdminMutation();
  const [createOpen, setCreateOpen] = useState(false);
  const [seenNew, setSeenNew] = useState(false);
  const [editing, setEditing] = useState<PlayerListItem | null>(null);
  const [deactivateTarget, setDeactivateTarget] = useState<PlayerListItem | null>(null);
  const [reactivateTarget, setReactivateTarget] = useState<PlayerListItem | null>(null);
  const [rowPending, setRowPending] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);

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
        <h1 className="text-[28px] leading-[34px] font-semibold">Players</h1>
        <Button
          type="button"
          className={adminPrimaryButtonClass}
          onClick={() => setCreateOpen(true)}
        >
          New player
        </Button>
      </div>
      {players.loading ? (
        <div
          aria-busy="true"
          aria-live="polite"
          className="h-64 animate-pulse rounded-[20px] bg-elevated"
        >
          <span className="sr-only">Loading players</span>
        </div>
      ) : players.error ? (
        <AdminQueryError
          thing="players"
          error={players.error}
          onRetry={players.reload}
        />
      ) : players.data && players.data.items.length === 0 ? (
        <div className="flex flex-col items-start gap-3">
          <p className="text-sm text-muted-foreground">No players yet.</p>
          <Button
            type="button"
            className={adminPrimaryButtonClass}
            onClick={() => setCreateOpen(true)}
          >
            New player
          </Button>
        </div>
      ) : (
        <DataTable>
          <DataTableHeader>
            <DataTableRow>
              <DataTableHead className={`${headClass} sticky left-0 z-10 bg-elevated`}>
                Name
              </DataTableHead>
              <DataTableHead className={`${headClass} text-right`}>Elo</DataTableHead>
              <DataTableHead className={`${headClass} text-right`}>
                Highest
              </DataTableHead>
              <DataTableHead className={`${headClass} text-right`}>W–L</DataTableHead>
              <DataTableHead className={headClass}>Status</DataTableHead>
              <DataTableHead className={headClass}>Actions</DataTableHead>
            </DataTableRow>
          </DataTableHeader>
          <DataTableBody>
            {players.data?.items.map((player) => (
              <DataTableRow key={player.id}>
                <DataTableCell className="sticky left-0 z-10 min-w-40 bg-card">
                  <span className="flex items-center gap-2">
                    <PlayerAvatar
                      name={player.display_name}
                      imageUrl={player.avatar_url}
                      size="sm"
                    />
                    <span className="font-medium">{player.display_name}</span>
                  </span>
                </DataTableCell>
                <DataTableCell className="text-right tabular-nums">
                  {formatRating(player.current_rating)}
                </DataTableCell>
                <DataTableCell className="text-right tabular-nums">
                  {formatRating(player.highest_rating)}
                </DataTableCell>
                <DataTableCell className="text-right tabular-nums">
                  {formatRecord(player.wins, player.losses)}
                </DataTableCell>
                <DataTableCell>
                  {player.is_active ? (
                    <span className="inline-flex h-5 items-center rounded-full bg-primary/15 px-2 text-xs font-medium text-positive">
                      Active
                    </span>
                  ) : (
                    <InactiveBadge />
                  )}
                </DataTableCell>
                <DataTableCell>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="text-sm underline-offset-4 hover:underline focus-visible:rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      onClick={() => setEditing(player)}
                    >
                      Edit
                    </button>
                    <Link
                      href={`/players/${player.id}`}
                      className="text-sm underline-offset-4 hover:underline focus-visible:rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      View
                    </Link>
                    {player.is_active ? (
                      <button
                        type="button"
                        className="text-sm text-negative underline-offset-4 hover:underline focus-visible:rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        onClick={() => setDeactivateTarget(player)}
                      >
                        Deactivate
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="text-sm underline-offset-4 hover:underline focus-visible:rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        onClick={() => setReactivateTarget(player)}
                      >
                        Reactivate
                      </button>
                    )}
                  </div>
                </DataTableCell>
              </DataTableRow>
            ))}
          </DataTableBody>
        </DataTable>
      )}

      <PlayerFormDialog
        open={createOpen}
        title="New player"
        description="Ratings start at the club default. You cannot type an Elo."
        onOpenChange={(open) => {
          if (!open) closeCreate();
        }}
        onSubmit={async (body) => {
          await mutate((token) => createAdminPlayer(token, body));
          notifySuccess("Player created.");
          players.reload();
          closeCreate();
        }}
      />

      {editing ? (
        <PlayerFormDialog
          key={editing.id}
          open
          title="Edit player"
          description="Elo, highest, and W–L come from the server."
          player={editing}
          onOpenChange={(open) => {
            if (!open) setEditing(null);
          }}
          onSubmit={async (body) => {
            await mutate((token) => updateAdminPlayer(token, editing.id, body));
            notifySuccess("Player updated.");
            players.reload();
            setEditing(null);
          }}
        />
      ) : null}

      <ConfirmDialog
        open={deactivateTarget != null}
        onOpenChange={(open) => {
          if (rowPending) return;
          if (!open) {
            setDeactivateTarget(null);
            setRowError(null);
          }
        }}
        title={
          deactivateTarget
            ? `Deactivate ${deactivateTarget.display_name}?`
            : "Deactivate?"
        }
        description="They leave the leaderboard. Their matches stay."
        confirmLabel="Deactivate"
        destructive
        pending={rowPending}
        error={rowError}
        onConfirm={() => {
          if (!deactivateTarget) return;
          const target = deactivateTarget;
          setRowPending(true);
          setRowError(null);
          void mutate((token) => deactivateAdminPlayer(token, target.id))
            .then(() => {
              notifySuccess("Player deactivated.");
              setDeactivateTarget(null);
              setRowPending(false);
              players.reload();
            })
            .catch((error: unknown) => {
              setRowError(notifyFailure(error));
              setRowPending(false);
            });
        }}
      />

      <ConfirmDialog
        open={reactivateTarget != null}
        onOpenChange={(open) => {
          if (rowPending) return;
          if (!open) {
            setReactivateTarget(null);
            setRowError(null);
          }
        }}
        title={
          reactivateTarget
            ? `Return ${reactivateTarget.display_name} to the board?`
            : "Reactivate?"
        }
        description={
          reactivateTarget
            ? `Their rating stays ${formatRating(reactivateTarget.current_rating)}.`
            : "Their rating stays as recorded."
        }
        confirmLabel="Reactivate"
        destructive
        pending={rowPending}
        error={rowError}
        onConfirm={() => {
          if (!reactivateTarget) return;
          const target = reactivateTarget;
          setRowPending(true);
          setRowError(null);
          void mutate((token) =>
            updateAdminPlayer(token, target.id, { is_active: true }),
          )
            .then(() => {
              notifySuccess("Player reactivated.");
              setReactivateTarget(null);
              setRowPending(false);
              players.reload();
            })
            .catch((error: unknown) => {
              setRowError(notifyFailure(error));
              setRowPending(false);
            });
        }}
      />
    </div>
  );
}

function PlayerFormDialog({
  open,
  title,
  description,
  player,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  title: string;
  description: string;
  player?: PlayerListItem;
  onOpenChange: (open: boolean) => void;
  onSubmit: (body: {
    display_name: string;
    avatar_url?: string | null;
    is_active?: boolean;
  }) => Promise<void>;
}) {
  const [name, setName] = useState(player?.display_name ?? "");
  const [avatar, setAvatar] = useState(player?.avatar_url ?? "");
  const [active, setActive] = useState(player?.is_active ?? true);
  const [nameError, setNameError] = useState<string | null>(null);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [confirm, setConfirm] = useState<"deactivate" | "reactivate" | null>(null);

  async function save() {
    const displayName = name.trim();
    if (displayName.length < 1 || displayName.length > 50) {
      setNameError("Display name must be 1–50 characters.");
      return;
    }
    setNameError(null);
    setAvatarError(null);
    setFormError(null);
    const body = {
      display_name: displayName,
      avatar_url: avatar.trim() ? avatar.trim() : null,
      ...(player ? { is_active: active } : {}),
    };
    setPending(true);
    try {
      await onSubmit(body);
      setConfirm(null);
    } catch (error) {
      const message = notifyFailure(error);
      const nameMessage = fieldError(error, "display_name");
      const avatarMessage = fieldError(error, "avatar_url");
      const onName =
        nameMessage ?? (isApiError(error) && error.status === 409 ? message : null);
      setNameError(onName);
      setAvatarError(avatarMessage);
      setFormError(onName || avatarMessage ? null : message);
    } finally {
      setPending(false);
    }
  }

  function requestSave() {
    if (player && player.is_active && !active) {
      setConfirm("deactivate");
      return;
    }
    if (player && !player.is_active && active) {
      setConfirm("reactivate");
      return;
    }
    void save();
  }

  return (
    <>
      <AdminFormDialog
        open={open}
        onOpenChange={(next) => {
          if (pending) return;
          onOpenChange(next);
        }}
        title={title}
        description={description}
        initialFocusId="player-name"
      >
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            requestSave();
          }}
        >
          {formError ? <AdminLiveError>{formError}</AdminLiveError> : null}
          {player ? (
            <dl className="grid grid-cols-3 gap-2 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Elo</dt>
                <dd className="tabular-nums">{formatRating(player.current_rating)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Highest</dt>
                <dd className="tabular-nums">{formatRating(player.highest_rating)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">W–L</dt>
                <dd className="tabular-nums">
                  {formatRecord(player.wins, player.losses)}
                </dd>
              </div>
            </dl>
          ) : null}
          <AdminField label="Display name" htmlFor="player-name" error={nameError}>
            <Input
              id="player-name"
              className={adminInputClass}
              value={name}
              maxLength={50}
              onChange={(event) => setName(event.target.value)}
              aria-invalid={nameError ? true : undefined}
              aria-describedby={describedBy("player-name", false, Boolean(nameError))}
              required
            />
          </AdminField>
          <AdminField label="Avatar URL" htmlFor="player-avatar" error={avatarError}>
            <Input
              id="player-avatar"
              className={adminInputClass}
              value={avatar}
              onChange={(event) => setAvatar(event.target.value)}
              aria-invalid={avatarError ? true : undefined}
              aria-describedby={describedBy(
                "player-avatar",
                false,
                Boolean(avatarError),
              )}
              placeholder="Optional"
            />
          </AdminField>
          {player ? (
            <label className="flex items-center gap-2 text-sm" htmlFor="player-active">
              <input
                id="player-active"
                type="checkbox"
                className="size-4 accent-primary"
                checked={active}
                onChange={(event) => setActive(event.target.checked)}
              />
              Active
            </label>
          ) : null}
          <AdminDialogActions>
            <Button
              type="button"
              variant="outline"
              className={adminOutlineButtonClass}
              onClick={() => onOpenChange(false)}
              disabled={pending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className={adminPrimaryButtonClass}
              disabled={pending}
            >
              {pending ? "Saving…" : "Save"}
            </Button>
          </AdminDialogActions>
        </form>
      </AdminFormDialog>
      <ConfirmDialog
        open={confirm === "deactivate"}
        onOpenChange={(next) => {
          if (!next) setConfirm(null);
        }}
        title={`Deactivate ${name.trim() || "this player"}?`}
        description="They leave the leaderboard. Their matches stay."
        confirmLabel="Deactivate"
        destructive
        pending={pending}
        error={formError}
        onConfirm={() => void save()}
      />
      <ConfirmDialog
        open={confirm === "reactivate"}
        onOpenChange={(next) => {
          if (!next) setConfirm(null);
        }}
        title={`Return ${name.trim() || "this player"} to the board?`}
        description={`Their rating stays ${player ? formatRating(player.current_rating) : "as recorded"}.`}
        confirmLabel="Reactivate"
        destructive
        pending={pending}
        error={formError}
        onConfirm={() => void save()}
      />
    </>
  );
}
