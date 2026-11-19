"use client";

import { useState } from "react";

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
  adminSelectClass,
} from "@/components/admin/ui";
import { useAdminMutation, useAdminQuery } from "@/components/admin/use-admin-query";
import { AchievementIcon } from "@/components/achievement-icon";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { useQueryUpdate } from "@/components/club/query-controls";
import { InactiveBadge } from "@/components/inactive-badge";
import { LocalDateTime } from "@/components/local-time";
import { Pager } from "@/components/pager";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { fieldError } from "@/lib/admin/errors";
import { ACHIEVEMENT_ICONS } from "@/lib/admin/labels";
import {
  awardPlayerAchievement,
  createAdminAchievement,
  getAdminAchievements,
  getAdminPlayerAchievements,
  getAdminPlayers,
  revokePlayerAchievement,
  updateAdminAchievement,
} from "@/lib/api/admin";
import type { Achievement, AdminPlayerAchievement } from "@/types/api";

const PAGE_SIZE = 20;

export function AchievementsView() {
  const { searchParams, pathname } = useQueryUpdate();
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const definitions = useAdminQuery("admin-achievements", (token, signal) =>
    getAdminAchievements(token, signal),
  );
  const awards = useAdminQuery(`admin-awards:${page}`, (token, signal) =>
    getAdminPlayerAchievements(token, { page, page_size: PAGE_SIZE }, signal),
  );
  const players = useAdminQuery("admin-award-players", (token, signal) =>
    getAdminPlayers(token, signal),
  );
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Achievement | null>(null);
  const [awardOpen, setAwardOpen] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<AdminPlayerAchievement | null>(null);

  const activePlayers = players.data?.items.filter((player) => player.is_active) ?? [];
  const activeBadges = definitions.data?.items.filter((item) => item.is_active) ?? [];

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-[28px] leading-[34px] font-semibold">Achievements</h1>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 md:p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Definitions</h2>
            <Button
              type="button"
              className={adminPrimaryButtonClass}
              onClick={() => setCreateOpen(true)}
            >
              New definition
            </Button>
          </div>
          {definitions.loading ? (
            <div
              aria-busy="true"
              className="mt-4 h-40 animate-pulse rounded-xl bg-elevated"
            >
              <span className="sr-only">Loading definitions</span>
            </div>
          ) : definitions.error ? (
            <div className="mt-4">
              <AdminQueryError
                thing="achievements"
                error={definitions.error}
                onRetry={definitions.reload}
              />
            </div>
          ) : definitions.data && definitions.data.items.length === 0 ? (
            <p className="mt-4 text-sm text-muted-foreground">No badges yet.</p>
          ) : (
            <ul className="mt-3 divide-y divide-border">
              {definitions.data?.items.map((item) => (
                <li
                  key={item.id}
                  className="flex items-start justify-between gap-3 py-3"
                >
                  <div className="flex min-w-0 gap-3">
                    <span className="grid size-9 place-items-center rounded-full bg-elevated">
                      <AchievementIcon name={item.icon} />
                    </span>
                    <div className="min-w-0">
                      <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                        {item.name}
                        {item.is_active ? null : <InactiveBadge />}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {item.description}
                      </p>
                      <p className="text-xs text-muted-foreground tabular-nums">
                        {item.awarded_count} awarded
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="text-sm underline-offset-4 hover:underline focus-visible:rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    onClick={() => setEditing(item)}
                  >
                    Edit
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 md:p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Awards</h2>
            <Button
              type="button"
              className={adminPrimaryButtonClass}
              onClick={() => setAwardOpen(true)}
            >
              Award
            </Button>
          </div>
          {awards.loading ? (
            <div
              aria-busy="true"
              className="mt-4 h-40 animate-pulse rounded-xl bg-elevated"
            >
              <span className="sr-only">Loading awards</span>
            </div>
          ) : awards.error ? (
            <div className="mt-4">
              <AdminQueryError
                thing="awards"
                error={awards.error}
                onRetry={awards.reload}
              />
            </div>
          ) : awards.data && awards.data.items.length === 0 ? (
            <p className="mt-4 text-sm text-muted-foreground">No awards yet.</p>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">Player</th>
                    <th className="py-2 pr-3 font-medium">Badge</th>
                    <th className="py-2 pr-3 font-medium">Date</th>
                    <th className="py-2 pr-3 font-medium">Notes</th>
                    <th className="py-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {awards.data?.items.map((award) => (
                    <tr key={award.id} className="border-t border-border">
                      <td className="py-3 pr-3">{award.player.display_name}</td>
                      <td className="py-3 pr-3">
                        <span className="inline-flex items-center gap-2">
                          <AchievementIcon name={award.achievement.icon} />
                          {award.achievement.name}
                        </span>
                      </td>
                      <td className="py-3 pr-3 whitespace-nowrap">
                        <LocalDateTime value={award.awarded_at} withTime={false} />
                      </td>
                      <td className="py-3 pr-3 text-muted-foreground">
                        {award.notes ?? "—"}
                      </td>
                      <td className="py-3">
                        <button
                          type="button"
                          className="text-sm text-negative underline-offset-4 hover:underline focus-visible:rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          onClick={() => setRevokeTarget(award)}
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {awards.data ? (
                <div className="mt-3">
                  <Pager
                    page={awards.data.page}
                    pageSize={awards.data.page_size}
                    total={awards.data.total}
                    pathname={pathname}
                    query={{}}
                  />
                </div>
              ) : null}
            </div>
          )}
        </section>
      </div>

      {createOpen ? (
        <DefinitionDialog
          onOpenChange={setCreateOpen}
          onSaved={() => {
            notifySuccess("Badge created.");
            setCreateOpen(false);
            definitions.reload();
          }}
        />
      ) : null}
      {editing ? (
        <DefinitionDialog
          key={editing.id}
          achievement={editing}
          onOpenChange={(open) => {
            if (!open) setEditing(null);
          }}
          onSaved={() => {
            notifySuccess("Badge updated.");
            setEditing(null);
            definitions.reload();
          }}
        />
      ) : null}
      {awardOpen ? (
        <AwardDialog
          players={activePlayers}
          achievements={activeBadges}
          onOpenChange={setAwardOpen}
          onSaved={() => {
            notifySuccess("Badge awarded.");
            setAwardOpen(false);
            awards.reload();
            definitions.reload();
          }}
        />
      ) : null}
      <RevokeDialog
        award={revokeTarget}
        onOpenChange={(open) => {
          if (!open) setRevokeTarget(null);
        }}
        onDone={() => {
          setRevokeTarget(null);
          awards.reload();
          definitions.reload();
        }}
      />
    </div>
  );
}

function DefinitionDialog({
  achievement,
  onOpenChange,
  onSaved,
}: {
  achievement?: Achievement;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}) {
  const mutate = useAdminMutation();
  const [name, setName] = useState(achievement?.name ?? "");
  const [description, setDescription] = useState(achievement?.description ?? "");
  const [icon, setIcon] = useState(achievement?.icon ?? "Trophy");
  const [criteriaType, setCriteriaType] = useState(
    achievement?.criteria_type ?? "manual",
  );
  const [criteriaValue, setCriteriaValue] = useState(
    achievement?.criteria_value == null ? "" : String(achievement.criteria_value),
  );
  const [active, setActive] = useState(achievement?.is_active ?? true);
  const [nameError, setNameError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const knownIcons: readonly string[] = ACHIEVEMENT_ICONS;
  const iconOptions = knownIcons.includes(icon)
    ? ACHIEVEMENT_ICONS
    : [icon, ...ACHIEVEMENT_ICONS];

  async function save() {
    const trimmedName = name.trim();
    const trimmedDescription = description.trim();
    if (trimmedName.length < 1 || trimmedName.length > 80) {
      setNameError("Name must be 1–80 characters.");
      return;
    }
    if (trimmedDescription.length < 1 || trimmedDescription.length > 300) {
      setError("Description must be 1–300 characters.");
      return;
    }
    let parsedValue: number | null = null;
    if (criteriaValue.trim()) {
      const numeric = Number(criteriaValue);
      if (!Number.isFinite(numeric)) {
        setError("Criteria value must be a number.");
        return;
      }
      parsedValue = numeric;
    }
    setPending(true);
    setError(null);
    setNameError(null);
    try {
      if (achievement) {
        await mutate((token) =>
          updateAdminAchievement(token, achievement.id, {
            name: trimmedName,
            description: trimmedDescription,
            icon,
            criteria_type: criteriaType.trim() || "manual",
            criteria_value: parsedValue,
            is_active: active,
          }),
        );
      } else {
        const created = await mutate((token) =>
          createAdminAchievement(token, {
            name: trimmedName,
            description: trimmedDescription,
            icon,
            criteria_type: criteriaType.trim() || "manual",
            criteria_value: parsedValue,
          }),
        );
        if (!active) {
          await mutate((token) =>
            updateAdminAchievement(token, created.id, { is_active: false }),
          );
        }
      }
      onSaved();
    } catch (saveError) {
      const message = notifyFailure(saveError);
      setNameError(fieldError(saveError, "name") ?? message);
      setError(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <AdminFormDialog
      open
      onOpenChange={onOpenChange}
      title={achievement ? "Edit definition" : "New definition"}
      description="Badges are awarded by hand."
      initialFocusId="badge-name"
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        {error ? <AdminLiveError>{error}</AdminLiveError> : null}
        <AdminField label="Name" htmlFor="badge-name" error={nameError}>
          <Input
            id="badge-name"
            className={adminInputClass}
            value={name}
            maxLength={80}
            onChange={(event) => setName(event.target.value)}
            required
          />
        </AdminField>
        <AdminField label="Description" htmlFor="badge-description">
          <Textarea
            id="badge-description"
            value={description}
            maxLength={300}
            onChange={(event) => setDescription(event.target.value)}
            required
          />
        </AdminField>
        <AdminField label="Icon" htmlFor="badge-icon">
          <div className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-full bg-elevated">
              <AchievementIcon name={icon} />
            </span>
            <select
              id="badge-icon"
              className={adminSelectClass}
              value={icon}
              onChange={(event) => setIcon(event.target.value)}
            >
              {iconOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        </AdminField>
        <AdminField
          label="Criteria type"
          htmlFor="badge-criteria-type"
          hint="Stored as a note. Shuttle Rank does not award this automatically."
        >
          <Input
            id="badge-criteria-type"
            className={adminInputClass}
            value={criteriaType}
            onChange={(event) => setCriteriaType(event.target.value)}
          />
        </AdminField>
        <AdminField label="Criteria value" htmlFor="badge-criteria-value">
          <Input
            id="badge-criteria-value"
            className={adminInputClass}
            inputMode="decimal"
            value={criteriaValue}
            onChange={(event) => setCriteriaValue(event.target.value)}
          />
        </AdminField>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="size-4 accent-primary"
            checked={active}
            onChange={(event) => setActive(event.target.checked)}
          />
          Active
        </label>
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
            {pending ? "Saving…" : "Save"}
          </Button>
        </AdminDialogActions>
      </form>
    </AdminFormDialog>
  );
}

function AwardDialog({
  players,
  achievements,
  onOpenChange,
  onSaved,
}: {
  players: { id: string; display_name: string }[];
  achievements: Achievement[];
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}) {
  const mutate = useAdminMutation();
  const [playerId, setPlayerId] = useState("");
  const [achievementId, setAchievementId] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const player = players.find((item) => item.id === playerId);
  const badge = achievements.find((item) => item.id === achievementId);

  function review() {
    if (!playerId || !achievementId) {
      setError("Choose a player and an active badge.");
      return;
    }
    setError(null);
    setConfirmError(null);
    setConfirmOpen(true);
  }

  async function submit() {
    setPending(true);
    setConfirmError(null);
    try {
      await mutate((token) =>
        awardPlayerAchievement(token, playerId, {
          achievement_id: achievementId,
          notes: notes.trim() ? notes.trim() : null,
        }),
      );
      onSaved();
    } catch (saveError) {
      setConfirmError(notifyFailure(saveError));
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <AdminFormDialog
        open
        onOpenChange={onOpenChange}
        title="Award"
        description="A player can hold each badge once."
        initialFocusId="award-player"
      >
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            review();
          }}
        >
          {error ? <AdminLiveError>{error}</AdminLiveError> : null}
          <AdminField label="Player" htmlFor="award-player">
            <select
              id="award-player"
              className={adminSelectClass}
              value={playerId}
              onChange={(event) => setPlayerId(event.target.value)}
            >
              <option value="">Choose a player</option>
              {players.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.display_name}
                </option>
              ))}
            </select>
          </AdminField>
          <AdminField label="Badge" htmlFor="award-badge">
            <select
              id="award-badge"
              className={adminSelectClass}
              value={achievementId}
              onChange={(event) => setAchievementId(event.target.value)}
            >
              <option value="">Choose a badge</option>
              {achievements.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </AdminField>
          <AdminField label="Notes" htmlFor="award-notes">
            <Textarea
              id="award-notes"
              value={notes}
              maxLength={500}
              onChange={(event) => setNotes(event.target.value)}
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
            <Button type="submit" className={adminPrimaryButtonClass}>
              Review award
            </Button>
          </AdminDialogActions>
        </form>
      </AdminFormDialog>
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={`Award ${badge?.name ?? "badge"} to ${player?.display_name ?? "player"}?`}
        description={
          notes.trim() ? `Notes: ${notes.trim()}` : "This adds the badge to the player."
        }
        confirmLabel="Award"
        pending={pending}
        error={confirmError}
        onConfirm={() => void submit()}
      />
    </>
  );
}

function RevokeDialog({
  award,
  onOpenChange,
  onDone,
}: {
  award: AdminPlayerAchievement | null;
  onOpenChange: (open: boolean) => void;
  onDone: () => void;
}) {
  const mutate = useAdminMutation();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function revoke() {
    if (!award) return;
    setPending(true);
    setError(null);
    try {
      await mutate((token) => revokePlayerAchievement(token, award.id));
      notifySuccess("Award revoked.");
      onDone();
    } catch (revokeError) {
      setError(notifyFailure(revokeError));
    } finally {
      setPending(false);
    }
  }

  return (
    <ConfirmDialog
      open={award != null}
      onOpenChange={onOpenChange}
      title={
        award
          ? `Revoke ${award.achievement.name} from ${award.player.display_name}?`
          : "Revoke?"
      }
      description="The badge leaves this player's profile."
      confirmLabel="Revoke"
      destructive
      pending={pending}
      error={error}
      onConfirm={() => void revoke()}
    />
  );
}
