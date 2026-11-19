"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowUpRight, Crown } from "lucide-react";

import { BracketBoard, bracketHasResults } from "@/components/admin/bracket-board";
import { notifyFailure, notifySuccess } from "@/components/admin/feedback";
import { ScoresEditor } from "@/components/admin/scores-editor";
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
import { ConfirmDialog } from "@/components/confirm-dialog";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { isApiError } from "@/lib/admin/errors";
import {
  datetimeLocalToUtc,
  formatLocalWhen,
  isMoreThanOneDayAhead,
  maxMatchDatetimeLocal,
  nowDatetimeLocal,
  optionalText,
  parseScores,
  type ScoreRow,
} from "@/lib/admin/form";
import { finalPositionLabel } from "@/lib/admin/labels";
import {
  addTournamentParticipants,
  generateTournamentBracket,
  getAdminPlayers,
  recordTournamentMatch,
  removeTournamentParticipant,
  updateAdminTournament,
} from "@/lib/api/admin";
import { getBracket, getTournament } from "@/lib/api/client";
import { formatDate, formatRating } from "@/lib/format";
import type { BracketMatch, TournamentDetail } from "@/types/api";

export function TournamentDetailView() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const detail = useAdminQuery(`admin-tournament:${id}`, async (_token, signal) => {
    const tournament = await getTournament(id, signal);
    const bracket = tournament.bracket_generated ? await getBracket(id, signal) : null;
    return { tournament, bracket };
  });
  const players = useAdminQuery("admin-tournament-players", (token, signal) =>
    getAdminPlayers(token, signal),
  );

  if (!id) return null;
  if (detail.loading) {
    return (
      <div aria-busy="true" className="flex flex-col gap-4">
        <span className="sr-only">Loading tournament</span>
        <div className="h-28 animate-pulse rounded-[20px] bg-elevated" />
        <div className="h-64 animate-pulse rounded-[20px] bg-elevated" />
      </div>
    );
  }
  if (detail.error) {
    if (isApiError(detail.error) && detail.error.status === 404) {
      return (
        <div className="flex flex-col gap-3">
          <p className="text-sm">This tournament isn&apos;t on Shuttle Rank.</p>
          <Link
            href="/admin/tournaments"
            className="text-sm text-primary underline-offset-4 hover:underline"
          >
            Tournaments
          </Link>
        </div>
      );
    }
    return (
      <AdminQueryError
        thing="tournament"
        error={detail.error}
        onRetry={detail.reload}
      />
    );
  }
  if (!detail.data) return null;

  return (
    <TournamentManager
      tournament={detail.data.tournament}
      bracket={detail.data.bracket}
      players={players.data?.items ?? []}
      onChanged={detail.reload}
    />
  );
}

function TournamentManager({
  tournament,
  bracket,
  players,
  onChanged,
}: {
  tournament: TournamentDetail;
  bracket: Awaited<ReturnType<typeof getBracket>> | null;
  players: {
    id: string;
    display_name: string;
    current_rating: number;
    is_active: boolean;
  }[];
  onChanged: () => void;
}) {
  const mutate = useAdminMutation();
  const [editOpen, setEditOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [cancelPending, setCancelPending] = useState(false);
  const [seeding, setSeeding] = useState<"rating" | "manual">("rating");
  const [generateOpen, setGenerateOpen] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [generatePending, setGeneratePending] = useState(false);
  const [picked, setPicked] = useState<Record<string, string>>({});
  const [participantError, setParticipantError] = useState<string | null>(null);
  const [participantPending, setParticipantPending] = useState(false);
  const [slot, setSlot] = useState<BracketMatch | null>(null);

  const draft = tournament.status === "draft";
  const live = tournament.status === "draft" || tournament.status === "in_progress";
  const hasResults = bracket ? bracketHasResults(bracket) : false;
  const canGenerate =
    tournament.participant_count >= 2 &&
    (draft || (tournament.status === "in_progress" && !hasResults));
  const replacing =
    tournament.status === "in_progress" && !hasResults && tournament.bracket_generated;
  const memberIds = new Set(tournament.participants.map((entry) => entry.player.id));
  const available = players.filter(
    (player) => player.is_active && !memberIds.has(player.id),
  );

  async function cancelTournament() {
    setCancelPending(true);
    setCancelError(null);
    try {
      await mutate((token) =>
        updateAdminTournament(token, tournament.id, { status: "canceled" }),
      );
      notifySuccess("Tournament canceled.");
      setCancelOpen(false);
      onChanged();
    } catch (error) {
      setCancelError(notifyFailure(error));
    } finally {
      setCancelPending(false);
    }
  }

  async function generate() {
    setGeneratePending(true);
    setGenerateError(null);
    try {
      await mutate((token) =>
        generateTournamentBracket(token, tournament.id, { seeding }),
      );
      notifySuccess(replacing ? "Bracket replaced." : "Bracket generated.");
      setGenerateOpen(false);
      onChanged();
    } catch (error) {
      setGenerateError(notifyFailure(error));
    } finally {
      setGeneratePending(false);
    }
  }

  async function addPlayers() {
    const participants = Object.entries(picked).map(([playerId, seed]) => {
      const trimmed = seed.trim();
      return {
        player_id: playerId,
        seed: trimmed === "" ? null : Number(trimmed),
      };
    });
    if (participants.length === 0) {
      setParticipantError("Select at least one player.");
      return;
    }
    if (
      participants.some(
        (entry) =>
          entry.seed != null && (!Number.isInteger(entry.seed) || entry.seed < 1),
      )
    ) {
      setParticipantError("Seeds are whole numbers, or leave them blank.");
      return;
    }
    setParticipantPending(true);
    setParticipantError(null);
    try {
      await mutate((token) =>
        addTournamentParticipants(token, tournament.id, { participants }),
      );
      notifySuccess("Players added.");
      setPicked({});
      onChanged();
    } catch (error) {
      setParticipantError(notifyFailure(error));
    } finally {
      setParticipantPending(false);
    }
  }

  async function removePlayer(playerId: string) {
    setParticipantError(null);
    try {
      await mutate((token) =>
        removeTournamentParticipant(token, tournament.id, playerId),
      );
      notifySuccess("Player removed.");
      onChanged();
    } catch (error) {
      setParticipantError(notifyFailure(error));
    }
  }

  const seedingLabel = seeding === "rating" ? "By current Elo" : "Use assigned seeds";

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 md:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-2">
            <StatusBadge status={tournament.status} />
            <h1 className="text-[28px] leading-[34px] font-semibold">
              {tournament.name}
            </h1>
            <p className="text-sm text-muted-foreground">
              {tournament.start_date
                ? formatDate(tournament.start_date, undefined, "en-US")
                : "Start not set"}
              {tournament.end_date
                ? ` – ${formatDate(tournament.end_date, undefined, "en-US")}`
                : ""}
            </p>
            {tournament.description ? (
              <p className="text-sm">{tournament.description}</p>
            ) : null}
            {tournament.champion ? (
              <p className="flex items-center gap-2 text-sm">
                <Crown
                  className="size-4 text-positive"
                  strokeWidth={1.75}
                  aria-hidden
                />
                Champion {tournament.champion.display_name}
              </p>
            ) : null}
            {tournament.runner_up ? (
              <p className="text-sm text-muted-foreground">
                Runner-up {tournament.runner_up.display_name}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href={`/tournaments/${tournament.id}`}
              className="inline-flex h-11 items-center gap-1 rounded-full border border-border px-4 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:h-10"
            >
              View public page
              <ArrowUpRight className="size-4" aria-hidden />
            </Link>
            {live ? (
              <Button
                type="button"
                variant="outline"
                className={adminOutlineButtonClass}
                onClick={() => setEditOpen(true)}
              >
                Edit
              </Button>
            ) : null}
            {live ? (
              <Button
                type="button"
                className="h-11 rounded-full bg-destructive px-4 text-primary-foreground hover:bg-destructive/90 md:h-10"
                onClick={() => {
                  setCancelError(null);
                  setCancelOpen(true);
                }}
              >
                Cancel tournament
              </Button>
            ) : null}
          </div>
        </div>
      </section>

      <section className="rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 md:p-5">
        <h2 className="text-lg font-semibold">Participants</h2>
        {participantError ? (
          <div className="mt-3">
            <AdminLiveError>{participantError}</AdminLiveError>
          </div>
        ) : null}
        {tournament.participants.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">No players yet.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="py-2 pr-3 font-medium">Seed</th>
                  <th className="py-2 pr-3 font-medium">Player</th>
                  <th className="py-2 pr-3 font-medium">Place</th>
                  {draft ? <th className="py-2 font-medium">Actions</th> : null}
                </tr>
              </thead>
              <tbody>
                {tournament.participants.map((entry) => (
                  <tr key={entry.player.id} className="border-t border-border">
                    <td className="py-3 pr-3 tabular-nums">{entry.seed ?? "—"}</td>
                    <td className="py-3 pr-3">
                      <Link
                        href={`/players/${entry.player.id}`}
                        className="underline-offset-4 hover:underline"
                      >
                        {entry.player.display_name}
                      </Link>
                    </td>
                    <td className="py-3 pr-3">
                      {finalPositionLabel(entry.final_position)}
                    </td>
                    {draft ? (
                      <td className="py-3">
                        <button
                          type="button"
                          className="text-sm text-negative underline-offset-4 hover:underline focus-visible:rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          onClick={() => void removePlayer(entry.player.id)}
                        >
                          Remove
                        </button>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {draft ? (
          <div className="mt-4 flex flex-col gap-3">
            <p className="text-xs font-medium text-muted-foreground">
              Add active players
            </p>
            {available.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Every active player is already in.
              </p>
            ) : (
              <ul className="flex max-h-64 flex-col gap-2 overflow-y-auto">
                {available.map((player) => {
                  const checked = player.id in picked;
                  return (
                    <li key={player.id} className="flex flex-wrap items-center gap-3">
                      <label className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          className="size-4 accent-primary"
                          checked={checked}
                          onChange={(event) => {
                            setPicked((current) => {
                              const next = { ...current };
                              if (event.target.checked)
                                next[player.id] = current[player.id] ?? "";
                              else delete next[player.id];
                              return next;
                            });
                          }}
                        />
                        {player.display_name} · {formatRating(player.current_rating)}
                      </label>
                      {checked ? (
                        <label className="flex items-center gap-2 text-xs text-muted-foreground">
                          Seed
                          <input
                            className="h-10 w-20 rounded-xl border border-input bg-transparent px-2 text-sm"
                            inputMode="numeric"
                            value={picked[player.id] ?? ""}
                            onChange={(event) =>
                              setPicked((current) => ({
                                ...current,
                                [player.id]: event.target.value,
                              }))
                            }
                            aria-label={`Seed for ${player.display_name}`}
                          />
                        </label>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            )}
            <Button
              type="button"
              className={adminPrimaryButtonClass}
              disabled={participantPending}
              onClick={() => void addPlayers()}
            >
              {participantPending ? "Adding…" : "Add"}
            </Button>
          </div>
        ) : (
          <p className="mt-3 text-sm text-muted-foreground">
            Participants can change only while the tournament is a draft.
          </p>
        )}
      </section>

      <section className="rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 md:p-5">
        <h2 className="text-lg font-semibold">Bracket</h2>
        {tournament.status === "completed" ||
        tournament.status === "canceled" ? null : (
          <div className="mt-3 flex flex-col gap-3">
            <fieldset className="flex flex-col gap-2">
              <legend className="text-xs font-medium text-muted-foreground">
                Seeding
              </legend>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="seeding"
                  checked={seeding === "rating"}
                  onChange={() => setSeeding("rating")}
                />
                By current Elo
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="seeding"
                  checked={seeding === "manual"}
                  onChange={() => setSeeding("manual")}
                />
                Use assigned seeds
              </label>
            </fieldset>
            {tournament.participant_count < 2 ? (
              <p className="text-sm text-muted-foreground">
                Add at least two players to generate a bracket.
              </p>
            ) : null}
            {canGenerate ? (
              <Button
                type="button"
                className={adminPrimaryButtonClass}
                onClick={() => setGenerateOpen(true)}
              >
                {replacing ? "Replace bracket" : "Generate bracket"}
              </Button>
            ) : null}
          </div>
        )}
        <div className="mt-4">
          {bracket && bracket.rounds.length > 0 ? (
            <BracketBoard
              bracket={bracket}
              allowRecord={tournament.status === "in_progress"}
              onRecord={setSlot}
            />
          ) : (
            <p className="text-sm text-muted-foreground">
              The bracket has not been generated.
            </p>
          )}
        </div>
      </section>

      {editOpen ? (
        <EditTournamentDialog
          tournament={tournament}
          onOpenChange={setEditOpen}
          onSaved={() => {
            notifySuccess("Tournament updated.");
            setEditOpen(false);
            onChanged();
          }}
        />
      ) : null}
      <ConfirmDialog
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        title="Cancel this tournament?"
        description="Matches already played keep their ratings."
        confirmLabel="Cancel tournament"
        destructive
        pending={cancelPending}
        error={cancelError}
        onConfirm={() => void cancelTournament()}
      />
      <ConfirmDialog
        open={generateOpen}
        onOpenChange={setGenerateOpen}
        title={replacing ? "Replace the bracket?" : "Generate the bracket?"}
        description={
          replacing
            ? `${tournament.participant_count} players. ${seedingLabel}. Only available because no result has been recorded.`
            : `${tournament.participant_count} players. ${seedingLabel}. Byes advance with no Elo change.`
        }
        confirmLabel={replacing ? "Replace bracket" : "Generate"}
        destructive={replacing}
        pending={generatePending}
        error={generateError}
        onConfirm={() => void generate()}
      />
      {slot ? (
        <RecordSlotDialog
          key={slot.id}
          tournamentId={tournament.id}
          slot={slot}
          onOpenChange={(open) => {
            if (!open) setSlot(null);
          }}
          onDone={() => {
            setSlot(null);
            onChanged();
          }}
        />
      ) : null}
    </div>
  );
}

function EditTournamentDialog({
  tournament,
  onOpenChange,
  onSaved,
}: {
  tournament: TournamentDetail;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}) {
  const mutate = useAdminMutation();
  const [name, setName] = useState(tournament.name);
  const [description, setDescription] = useState(tournament.description ?? "");
  const [start, setStart] = useState(tournament.start_date ?? "");
  const [end, setEnd] = useState(tournament.end_date ?? "");
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
        updateAdminTournament(token, tournament.id, {
          name: trimmed,
          description: description.trim() ? description.trim() : null,
          start_date: start || null,
          end_date: end || null,
        }),
      );
      onSaved();
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
      title="Edit tournament"
      description="Cancel is a separate confirmation."
      initialFocusId="edit-tournament-name"
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        {error ? <AdminLiveError>{error}</AdminLiveError> : null}
        <AdminField label="Name" htmlFor="edit-tournament-name">
          <Input
            id="edit-tournament-name"
            className={adminInputClass}
            value={name}
            maxLength={100}
            onChange={(event) => setName(event.target.value)}
            required
          />
        </AdminField>
        <AdminField label="Description" htmlFor="edit-tournament-description">
          <Textarea
            id="edit-tournament-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </AdminField>
        <AdminField label="Start date" htmlFor="edit-tournament-start">
          <Input
            id="edit-tournament-start"
            className={adminInputClass}
            type="date"
            value={start}
            onChange={(event) => setStart(event.target.value)}
          />
        </AdminField>
        <AdminField label="End date" htmlFor="edit-tournament-end">
          <Input
            id="edit-tournament-end"
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
            {pending ? "Saving…" : "Save"}
          </Button>
        </AdminDialogActions>
      </form>
    </AdminFormDialog>
  );
}

function RecordSlotDialog({
  tournamentId,
  slot,
  onOpenChange,
  onDone,
}: {
  tournamentId: string;
  slot: BracketMatch;
  onOpenChange: (open: boolean) => void;
  onDone: () => void;
}) {
  const mutate = useAdminMutation();
  const playerA = slot.player_a;
  const playerB = slot.player_b;
  const [winner, setWinner] = useState("");
  const [when, setWhen] = useState(nowDatetimeLocal());
  const [scores, setScores] = useState<ScoreRow[]>([]);
  const [notes, setNotes] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  if (!playerA || !playerB) return null;
  const winnerName =
    winner === playerA.id ? playerA.display_name : playerB.display_name;
  const loserName = winner === playerA.id ? playerB.display_name : playerA.display_name;

  function review() {
    if (winner !== playerA?.id && winner !== playerB?.id) {
      setFormError("Choose the winner.");
      return;
    }
    if (!when || isMoreThanOneDayAhead(when)) {
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
    if (!playerA || !playerB || !parsedScores.ok || !parsedNotes.ok || !matchDate)
      return;
    setPending(true);
    setConfirmError(null);
    try {
      await mutate((token) =>
        recordTournamentMatch(token, tournamentId, {
          bracket_match_id: slot.id,
          winner_id: winner,
          match_date: matchDate,
          game_scores: parsedScores.value,
          notes: parsedNotes.value,
        }),
      );
      notifySuccess("Result recorded.");
      onDone();
    } catch (error) {
      setConfirmError(notifyFailure(error));
    } finally {
      setPending(false);
    }
  }

  const whenLabel = datetimeLocalToUtc(when);

  return (
    <>
      <AdminFormDialog
        open
        onOpenChange={onOpenChange}
        title="Record result"
        description="Players come from this bracket slot."
        initialFocusId="slot-winner-a"
      >
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            review();
          }}
        >
          {formError ? <AdminLiveError>{formError}</AdminLiveError> : null}
          <fieldset className="flex flex-col gap-2">
            <legend className="text-xs font-medium text-muted-foreground">
              Winner
            </legend>
            <label className="flex items-center gap-2 text-sm">
              <input
                id="slot-winner-a"
                type="radio"
                name="slot-winner"
                checked={winner === playerA.id}
                onChange={() => setWinner(playerA.id)}
              />
              {playerA.display_name}
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="slot-winner"
                checked={winner === playerB.id}
                onChange={() => setWinner(playerB.id)}
              />
              {playerB.display_name}
            </label>
          </fieldset>
          <AdminField label="Date and time" htmlFor="slot-when">
            <Input
              id="slot-when"
              className={adminInputClass}
              type="datetime-local"
              value={when}
              max={maxMatchDatetimeLocal()}
              onChange={(event) => setWhen(event.target.value)}
            />
          </AdminField>
          <ScoresEditor
            idPrefix="slot-score"
            rows={scores}
            onChange={setScores}
            playerAName={playerA.display_name}
            playerBName={playerB.display_name}
          />
          <AdminField label="Notes" htmlFor="slot-notes">
            <Textarea
              id="slot-notes"
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
              Review result
            </Button>
          </AdminDialogActions>
        </form>
      </AdminFormDialog>
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Record this result?"
        description={
          whenLabel
            ? `${winnerName} beats ${loserName} on ${formatLocalWhen(whenLabel)}.`
            : `${winnerName} beats ${loserName}.`
        }
        confirmLabel="Record result"
        pending={pending}
        error={confirmError}
        onConfirm={() => void submit()}
      />
    </>
  );
}
