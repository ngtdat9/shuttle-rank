"use client";

import { useState } from "react";

import { notifyFailure, notifySuccess } from "@/components/admin/feedback";
import { ScoresEditor } from "@/components/admin/scores-editor";
import {
  AdminDialogActions,
  AdminField,
  AdminFormDialog,
  AdminLiveError,
  adminInputClass,
  adminOutlineButtonClass,
  adminPrimaryButtonClass,
  adminSelectClass,
  describedBy,
} from "@/components/admin/ui";
import { useAdminMutation } from "@/components/admin/use-admin-query";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { apiErrorMessage } from "@/lib/admin/errors";
import {
  datetimeLocalToUtc,
  formatLocalWhen,
  isMoreThanOneDayAhead,
  maxMatchDatetimeLocal,
  nowDatetimeLocal,
  optionalText,
  parseScores,
  requiredReason,
  scoresFromApi,
  type ScoreRow,
} from "@/lib/admin/form";
import {
  cancelAdminMatch,
  correctAdminMatch,
  createAdminMatch,
  deleteAdminMatch,
  patchAdminMatch,
  type AdminMatch,
} from "@/lib/api/admin";
import { formatRating } from "@/lib/format";
import type { MatchStatus, PlayerListItem } from "@/types/api";

function playerName(players: PlayerListItem[], id: string): string {
  return players.find((player) => player.id === id)?.display_name ?? "Player";
}

export function RecordMatchDialog({
  open,
  onOpenChange,
  players,
  onDone,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  players: PlayerListItem[];
  onDone: () => void;
}) {
  const mutate = useAdminMutation();
  const active = players.filter((player) => player.is_active);
  const [playerA, setPlayerA] = useState("");
  const [playerB, setPlayerB] = useState("");
  const [winner, setWinner] = useState("");
  const [when, setWhen] = useState(nowDatetimeLocal());
  const [status, setStatus] = useState<"completed" | "disputed">("completed");
  const [scores, setScores] = useState<ScoreRow[]>([]);
  const [notes, setNotes] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const optionsB = active.filter((player) => player.id !== playerA);
  const nameA = playerName(active, playerA);
  const nameB = playerName(active, playerB);
  const winnerName = winner === playerA ? nameA : nameB;
  const loserName = winner === playerA ? nameB : nameA;

  function review() {
    if (!playerA || !playerB || playerA === playerB) {
      setFormError("Choose two different active players.");
      return;
    }
    if (winner !== playerA && winner !== playerB) {
      setFormError("Choose the winner.");
      return;
    }
    if (!when || Number.isNaN(new Date(when).getTime())) {
      setFormError("Choose a date and time.");
      return;
    }
    if (isMoreThanOneDayAhead(when)) {
      setFormError("Match time cannot be more than one day ahead.");
      return;
    }
    const parsedScores = parseScores(scores);
    if (!parsedScores.ok) {
      setFormError(parsedScores.message);
      return;
    }
    const parsedNotes = optionalText(notes, 500);
    if (!parsedNotes.ok) {
      setFormError(parsedNotes.message);
      return;
    }
    setFormError(null);
    setConfirmError(null);
    setConfirmOpen(true);
  }

  async function submit() {
    const parsedScores = parseScores(scores);
    const parsedNotes = optionalText(notes, 500);
    const matchDate = datetimeLocalToUtc(when);
    if (!parsedScores.ok || !parsedNotes.ok || !matchDate) return;
    setPending(true);
    setConfirmError(null);
    try {
      await mutate((token) =>
        createAdminMatch(token, {
          player_a_id: playerA,
          player_b_id: playerB,
          winner_id: winner,
          match_date: matchDate,
          status,
          game_scores: parsedScores.value,
          notes: parsedNotes.value,
        }),
      );
      notifySuccess("Match recorded.");
      setConfirmOpen(false);
      onOpenChange(false);
      onDone();
    } catch (error) {
      const message = notifyFailure(error);
      setConfirmError(message);
      setFormError(message);
    } finally {
      setPending(false);
    }
  }

  const whenLabel = datetimeLocalToUtc(when);
  const summary = whenLabel
    ? `${winnerName} beats ${loserName} on ${formatLocalWhen(whenLabel)}.`
    : `${winnerName} beats ${loserName}.`;

  return (
    <>
      <AdminFormDialog
        open={open}
        onOpenChange={(next) => {
          if (pending) return;
          onOpenChange(next);
        }}
        title="Record match"
        description="Club matches only. Tournament results are recorded from the bracket."
        initialFocusId="record-player-a"
      >
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            review();
          }}
        >
          {formError ? <AdminLiveError>{formError}</AdminLiveError> : null}
          <AdminField label="Player A" htmlFor="record-player-a">
            <select
              id="record-player-a"
              className={adminSelectClass}
              value={playerA}
              onChange={(event) => {
                const next = event.target.value;
                setPlayerA(next);
                if (playerB === next) setPlayerB("");
                if (winner && winner !== next && winner !== playerB) setWinner("");
              }}
            >
              <option value="">Choose player A</option>
              {active.map((player) => (
                <option key={player.id} value={player.id}>
                  {player.display_name} · {formatRating(player.current_rating)}
                </option>
              ))}
            </select>
          </AdminField>
          <AdminField label="Player B" htmlFor="record-player-b">
            <select
              id="record-player-b"
              className={adminSelectClass}
              value={playerB}
              onChange={(event) => {
                const next = event.target.value;
                setPlayerB(next);
                if (winner && winner !== playerA && winner !== next) setWinner("");
              }}
            >
              <option value="">Choose player B</option>
              {optionsB.map((player) => (
                <option key={player.id} value={player.id}>
                  {player.display_name} · {formatRating(player.current_rating)}
                </option>
              ))}
            </select>
          </AdminField>
          <fieldset className="flex flex-col gap-2">
            <legend className="text-xs font-medium text-muted-foreground">
              Winner
            </legend>
            {[playerA, playerB].filter(Boolean).map((id) => (
              <label key={id} className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="record-winner"
                  value={id}
                  checked={winner === id}
                  onChange={() => setWinner(id)}
                />
                {playerName(active, id)}
              </label>
            ))}
          </fieldset>
          <AdminField label="Date and time" htmlFor="record-when">
            <Input
              id="record-when"
              className={adminInputClass}
              type="datetime-local"
              value={when}
              max={maxMatchDatetimeLocal()}
              onChange={(event) => setWhen(event.target.value)}
              required
            />
          </AdminField>
          <AdminField label="Status" htmlFor="record-status">
            <select
              id="record-status"
              className={adminSelectClass}
              value={status}
              onChange={(event) =>
                setStatus(event.target.value as "completed" | "disputed")
              }
            >
              <option value="completed">Completed</option>
              <option value="disputed">Disputed</option>
            </select>
          </AdminField>
          <ScoresEditor
            idPrefix="record-score"
            rows={scores}
            onChange={setScores}
            playerAName={playerA ? nameA : "A"}
            playerBName={playerB ? nameB : "B"}
          />
          <AdminField
            label="Notes"
            htmlFor="record-notes"
            hint="Optional. Up to 500 characters."
          >
            <Textarea
              id="record-notes"
              value={notes}
              maxLength={500}
              onChange={(event) => setNotes(event.target.value)}
              aria-describedby={describedBy("record-notes", true, false)}
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
              Review result
            </Button>
          </AdminDialogActions>
        </form>
      </AdminFormDialog>
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Record this result?"
        description={`${summary}${status === "disputed" ? " A disputed match does not change Elo." : ""}`}
        confirmLabel="Record result"
        pending={pending}
        error={confirmError}
        onConfirm={() => void submit()}
      />
    </>
  );
}

export function NotesMatchDialog({
  match,
  onOpenChange,
  onDone,
}: {
  match: AdminMatch;
  onOpenChange: (open: boolean) => void;
  onDone: () => void;
}) {
  const mutate = useAdminMutation();
  const [notes, setNotes] = useState(match.notes ?? "");
  const [scores, setScores] = useState<ScoreRow[]>(scoresFromApi(match.game_scores));
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function save() {
    const parsedScores = parseScores(scores);
    if (!parsedScores.ok) {
      setError(parsedScores.message);
      return;
    }
    const parsedNotes = optionalText(notes, 500);
    if (!parsedNotes.ok) {
      setError(parsedNotes.message);
      return;
    }
    setPending(true);
    setError(null);
    try {
      await mutate((token) =>
        patchAdminMatch(token, match.id, {
          notes: parsedNotes.value,
          game_scores: parsedScores.value,
        }),
      );
      notifySuccess("Match details saved.");
      onOpenChange(false);
      onDone();
    } catch (saveError) {
      setError(notifyFailure(saveError));
    } finally {
      setPending(false);
    }
  }

  return (
    <AdminFormDialog
      open
      onOpenChange={onOpenChange}
      title="Edit details"
      description="Notes and scores do not change Elo."
      initialFocusId="notes-field"
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        {error ? <AdminLiveError>{error}</AdminLiveError> : null}
        <ScoresEditor
          idPrefix="notes-score"
          rows={scores}
          onChange={setScores}
          playerAName={match.player_a.display_name}
          playerBName={match.player_b.display_name}
        />
        <AdminField label="Notes" htmlFor="notes-field">
          <Textarea
            id="notes-field"
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
          <Button type="submit" className={adminPrimaryButtonClass} disabled={pending}>
            {pending ? "Saving…" : "Save"}
          </Button>
        </AdminDialogActions>
      </form>
    </AdminFormDialog>
  );
}

export function CorrectMatchDialog({
  match,
  players,
  onOpenChange,
  onDone,
}: {
  match: AdminMatch;
  players: PlayerListItem[];
  onOpenChange: (open: boolean) => void;
  onDone: () => void;
}) {
  const mutate = useAdminMutation();
  const tournament = match.tournament != null;
  const active = players.filter((player) => player.is_active);
  const currentPlayers = [match.player_a, match.player_b].filter(
    (player) => !active.some((item) => item.id === player.id),
  );
  const [playerA, setPlayerA] = useState(match.player_a.id);
  const [playerB, setPlayerB] = useState(match.player_b.id);
  const [winner, setWinner] = useState(match.winner_id);
  const [when, setWhen] = useState(toLocal(match.match_date));
  const [status, setStatus] = useState<MatchStatus>(match.status);
  const [reason, setReason] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const pool = tournament
    ? [match.player_a, match.player_b]
    : [...active, ...currentPlayers];
  const nameA = tournament ? match.player_a.display_name : playerName(active, playerA);
  const nameB = tournament ? match.player_b.display_name : playerName(active, playerB);

  function review() {
    if (!tournament && (!playerA || !playerB || playerA === playerB)) {
      setFormError("Choose two different players.");
      return;
    }
    const allowed = tournament
      ? [match.player_a.id, match.player_b.id]
      : [playerA, playerB];
    if (!allowed.includes(winner)) {
      setFormError("The winner must be one of the two players.");
      return;
    }
    if (!when || isMoreThanOneDayAhead(when)) {
      setFormError("Match time cannot be more than one day ahead.");
      return;
    }
    const parsedReason = requiredReason(reason);
    if (!parsedReason.ok) {
      setFormError(parsedReason.message);
      return;
    }
    setFormError(null);
    setConfirmError(null);
    setConfirmOpen(true);
  }

  async function submit() {
    const parsedReason = requiredReason(reason);
    const matchDate = datetimeLocalToUtc(when);
    if (!parsedReason.ok || !matchDate) return;
    setPending(true);
    setConfirmError(null);
    try {
      await mutate((token) =>
        correctAdminMatch(token, match.id, {
          ...(tournament ? {} : { player_a_id: playerA, player_b_id: playerB }),
          winner_id: winner,
          match_date: matchDate,
          status,
          reason: parsedReason.value,
        }),
      );
      notifySuccess("Match corrected. Ratings were replayed.");
      setConfirmOpen(false);
      onOpenChange(false);
      onDone();
    } catch (error) {
      const message = notifyFailure(error);
      setConfirmError(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <AdminFormDialog
        open
        onOpenChange={(next) => {
          if (pending) return;
          onOpenChange(next);
        }}
        title="Correct match"
        description="This replays ratings from the earlier of the old and new dates."
        initialFocusId={tournament ? "correct-winner-note" : "correct-player-a"}
      >
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            review();
          }}
        >
          {formError ? <AdminLiveError>{formError}</AdminLiveError> : null}
          {tournament ? (
            <p id="correct-winner-note" className="text-sm text-muted-foreground">
              Tournament players come from the bracket.
            </p>
          ) : (
            <>
              <AdminField label="Player A" htmlFor="correct-player-a">
                <select
                  id="correct-player-a"
                  className={adminSelectClass}
                  value={playerA}
                  onChange={(event) => setPlayerA(event.target.value)}
                >
                  {pool.map((player) => (
                    <option key={player.id} value={player.id}>
                      {player.display_name} · {formatRating(player.current_rating)}
                    </option>
                  ))}
                </select>
              </AdminField>
              <AdminField label="Player B" htmlFor="correct-player-b">
                <select
                  id="correct-player-b"
                  className={adminSelectClass}
                  value={playerB}
                  onChange={(event) => setPlayerB(event.target.value)}
                >
                  {pool
                    .filter((player) => player.id !== playerA)
                    .map((player) => (
                      <option key={player.id} value={player.id}>
                        {player.display_name} · {formatRating(player.current_rating)}
                      </option>
                    ))}
                </select>
              </AdminField>
            </>
          )}
          <fieldset className="flex flex-col gap-2">
            <legend className="text-xs font-medium text-muted-foreground">
              Winner
            </legend>
            {(tournament ? [match.player_a.id, match.player_b.id] : [playerA, playerB])
              .filter(Boolean)
              .map((id) => (
                <label key={id} className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="correct-winner"
                    checked={winner === id}
                    onChange={() => setWinner(id)}
                  />
                  {id === match.player_a.id
                    ? match.player_a.display_name
                    : id === match.player_b.id
                      ? match.player_b.display_name
                      : playerName(active, id)}
                </label>
              ))}
          </fieldset>
          <AdminField label="Date and time" htmlFor="correct-when">
            <Input
              id="correct-when"
              className={adminInputClass}
              type="datetime-local"
              value={when}
              max={maxMatchDatetimeLocal()}
              onChange={(event) => setWhen(event.target.value)}
            />
          </AdminField>
          <AdminField label="Status" htmlFor="correct-status">
            <select
              id="correct-status"
              className={adminSelectClass}
              value={status}
              onChange={(event) => setStatus(event.target.value as MatchStatus)}
            >
              <option value="completed">Completed</option>
              <option value="disputed">Disputed</option>
              <option value="canceled">Canceled</option>
            </select>
          </AdminField>
          <AdminField
            label="Reason"
            htmlFor="correct-reason"
            hint="Required. 1–500 characters."
          >
            <Textarea
              id="correct-reason"
              value={reason}
              maxLength={500}
              onChange={(event) => setReason(event.target.value)}
              aria-describedby={describedBy("correct-reason", true, false)}
              required
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
              Review correction
            </Button>
          </AdminDialogActions>
        </form>
      </AdminFormDialog>
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Replay ratings?"
        description={`${nameA} and ${nameB}. Every later match is recalculated.`}
        confirmLabel="Replay ratings"
        destructive
        pending={pending}
        error={confirmError}
        onConfirm={() => void submit()}
      />
    </>
  );
}

export function CancelMatchDialog({
  match,
  onOpenChange,
  onDone,
}: {
  match: AdminMatch;
  onOpenChange: (open: boolean) => void;
  onDone: () => void;
}) {
  return (
    <ReasonActionDialog
      match={match}
      title="Cancel match"
      description="It stops affecting Elo. Later matches are recalculated."
      confirmTitle="Cancel this match?"
      confirmLabel="Cancel match"
      success="Match canceled."
      onOpenChange={onOpenChange}
      onDone={onDone}
      run={(token, reason) => cancelAdminMatch(token, match.id, { reason })}
    />
  );
}

export function DeleteMatchDialog({
  match,
  onOpenChange,
  onDone,
}: {
  match: AdminMatch;
  onOpenChange: (open: boolean) => void;
  onDone: () => void;
}) {
  return (
    <ReasonActionDialog
      match={match}
      title="Delete match"
      description="It leaves the public site. Ratings are recalculated. The audit log keeps the old result. This cannot be undone here."
      confirmTitle="Delete this match?"
      confirmLabel="Delete match"
      success="Match deleted."
      onOpenChange={onOpenChange}
      onDone={onDone}
      run={(token, reason) => deleteAdminMatch(token, match.id, reason)}
    />
  );
}

function ReasonActionDialog({
  match,
  title,
  description,
  confirmTitle,
  confirmLabel,
  success,
  onOpenChange,
  onDone,
  run,
}: {
  match: AdminMatch;
  title: string;
  description: string;
  confirmTitle: string;
  confirmLabel: string;
  success: string;
  onOpenChange: (open: boolean) => void;
  onDone: () => void;
  run: (token: string, reason: string) => Promise<unknown>;
}) {
  const mutate = useAdminMutation();
  const [reason, setReason] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const names = `${match.player_a.display_name} and ${match.player_b.display_name}`;

  function review() {
    const parsed = requiredReason(reason);
    if (!parsed.ok) {
      setFormError(parsed.message);
      return;
    }
    setFormError(null);
    setConfirmError(null);
    setConfirmOpen(true);
  }

  async function submit() {
    const parsed = requiredReason(reason);
    if (!parsed.ok) return;
    setPending(true);
    setConfirmError(null);
    try {
      await mutate((token) => run(token, parsed.value));
      notifySuccess(success);
      setConfirmOpen(false);
      onOpenChange(false);
      onDone();
    } catch (error) {
      setConfirmError(apiErrorMessage(error));
      notifyFailure(error);
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <AdminFormDialog
        open
        onOpenChange={(next) => {
          if (pending) return;
          onOpenChange(next);
        }}
        title={title}
        description={description}
        initialFocusId="match-reason"
      >
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            review();
          }}
        >
          {formError ? <AdminLiveError>{formError}</AdminLiveError> : null}
          <AdminField
            label="Reason"
            htmlFor="match-reason"
            hint="Required. 1–500 characters."
          >
            <Textarea
              id="match-reason"
              value={reason}
              maxLength={500}
              onChange={(event) => setReason(event.target.value)}
              required
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
              Review
            </Button>
          </AdminDialogActions>
        </form>
      </AdminFormDialog>
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={confirmTitle}
        description={`${names}. ${description}`}
        confirmLabel={confirmLabel}
        destructive
        pending={pending}
        error={confirmError}
        onConfirm={() => void submit()}
      />
    </>
  );
}

function toLocal(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return nowDatetimeLocal();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
