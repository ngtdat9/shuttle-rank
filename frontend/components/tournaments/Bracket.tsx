"use client";

import { Fragment, useId, useState } from "react";
import Link from "next/link";
import { Check } from "lucide-react";

import { QuietEmpty } from "@/components/club/styles";
import { PlayerAvatar } from "@/components/player-avatar";
import { formatGameScores } from "@/lib/format";
import { cn } from "@/lib/utils";
import type {
  BracketMatch,
  BracketMatchStatus,
  BracketRound,
  PlayerSummary,
} from "@/types/api";

const STATUS_CHIP: Record<BracketMatchStatus, { label: string; className: string }> = {
  pending: { label: "Waiting", className: "bg-foreground/8 text-muted-foreground" },
  ready: { label: "Ready", className: "bg-secondary/15 text-secondary" },
  completed: { label: "Completed", className: "bg-primary/15 text-positive" },
  bye: { label: "BYE", className: "bg-foreground/8 text-muted-foreground" },
};

function orderedRounds(rounds: BracketRound[]): BracketRound[] {
  return [...rounds]
    .sort((a, b) => a.round - b.round)
    .map((round) => ({
      ...round,
      matches: [...round.matches].sort((a, b) => a.position - b.position),
    }))
    .filter((round) => round.matches.length > 0);
}

function rowSpan(
  index: number,
  count: number,
  rowCount: number,
): { start: number; end: number } {
  const start = Math.floor((index * rowCount) / count);
  const end = Math.floor(((index + 1) * rowCount) / count);
  return { start, end: Math.max(end, start + 1) };
}

function StatusChip({ status }: { status: BracketMatchStatus }) {
  const chip = STATUS_CHIP[status];
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded-full px-2 text-xs font-medium",
        chip.className,
      )}
    >
      {chip.label}
    </span>
  );
}

function Slot({
  player,
  seed,
  highlighted,
  muted,
  emptyLabel,
}: {
  player: PlayerSummary | null;
  seed: number | null;
  highlighted: boolean;
  muted: boolean;
  emptyLabel: "BYE" | "TBD";
}) {
  if (!player) {
    return (
      <div className="flex min-h-8 items-center px-1.5 text-sm text-muted-foreground">
        {emptyLabel}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex min-h-8 items-center gap-2 rounded-lg px-1.5 py-1",
        highlighted && "bg-primary/10 text-positive",
        muted && "text-muted-foreground",
      )}
    >
      {seed != null ? (
        <span className="w-5 shrink-0 text-xs tabular-nums text-muted-foreground">
          {seed}
        </span>
      ) : (
        <span className="w-5 shrink-0" />
      )}
      <PlayerAvatar name={player.display_name} imageUrl={player.avatar_url} size="sm" />
      <Link
        href={`/players/${player.id}`}
        className="min-w-0 flex-1 truncate text-sm font-medium underline-offset-2 hover:underline focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {player.display_name}
      </Link>
      {highlighted ? (
        <>
          <Check className="size-3.5 shrink-0 text-positive" aria-hidden />
          <span className="sr-only">Winner</span>
        </>
      ) : null}
    </div>
  );
}

function MatchCard({ match }: { match: BracketMatch }) {
  const scores = formatGameScores(match.game_scores);
  const winnerId = match.winner_id;
  const advancingId =
    winnerId ??
    (match.status === "bye" || match.is_bye
      ? (match.player_a?.id ?? match.player_b?.id ?? null)
      : null);

  return (
    <div className="relative w-full py-1.5">
      <article className="sr-inset rounded-2xl p-2.5">
        <div className="mb-1 flex items-center justify-between gap-2 px-1.5">
          <StatusChip status={match.status} />
          {scores ? (
            <span className="text-xs tabular-nums text-muted-foreground">{scores}</span>
          ) : null}
        </div>
        <Slot
          player={match.player_a}
          seed={match.seed_a}
          highlighted={Boolean(match.player_a && advancingId === match.player_a.id)}
          muted={Boolean(
            match.status === "completed" &&
            winnerId &&
            match.player_a &&
            winnerId !== match.player_a.id,
          )}
          emptyLabel={match.status === "bye" || match.is_bye ? "BYE" : "TBD"}
        />
        <Slot
          player={match.player_b}
          seed={match.seed_b}
          highlighted={Boolean(match.player_b && advancingId === match.player_b.id)}
          muted={Boolean(
            match.status === "completed" &&
            winnerId &&
            match.player_b &&
            winnerId !== match.player_b.id,
          )}
          emptyLabel={match.status === "bye" || match.is_bye ? "BYE" : "TBD"}
        />
        {match.status === "completed" && match.match_id ? (
          <div className="mt-1 flex justify-end px-1.5">
            <Link
              href={`/matches/${match.match_id}`}
              className="inline-flex h-8 items-center text-xs font-medium underline-offset-4 hover:underline focus-visible:rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Match
            </Link>
          </div>
        ) : null}
      </article>
    </div>
  );
}

function RoundColumns({ rounds }: { rounds: BracketRound[] }) {
  const rowCount = Math.max(...rounds.map((round) => round.matches.length));

  return (
    <div>
      <p className="mb-2 text-xs text-muted-foreground xl:hidden">
        Scroll sideways to see later rounds.
      </p>
      <div className="overflow-x-auto pb-2">
        <div
          className="grid w-max gap-x-8"
          style={{
            gridTemplateColumns: `repeat(${rounds.length}, minmax(15rem, 16rem))`,
            gridTemplateRows: `auto repeat(${rowCount}, minmax(0, auto))`,
          }}
        >
          {rounds.map((round, roundIndex) => {
            const count = round.matches.length;
            const showConnector = roundIndex < rounds.length - 1;
            return (
              <Fragment key={round.round}>
                <h3
                  className="self-end pb-2 text-xs font-medium tracking-[0.14em] text-muted-foreground uppercase"
                  style={{ gridColumn: roundIndex + 1, gridRow: 1 }}
                >
                  {round.name}
                </h3>
                {round.matches.map((match, index) => {
                  const { start, end } = rowSpan(index, count, rowCount);
                  return (
                    <div
                      key={match.id}
                      className="relative flex items-center"
                      style={{
                        gridColumn: roundIndex + 1,
                        gridRow: `${start + 2} / ${end + 2}`,
                      }}
                    >
                      <MatchCard match={match} />
                      {showConnector ? (
                        <span
                          aria-hidden
                          className="pointer-events-none absolute top-1/2 left-full z-10 h-px w-8 bg-border"
                        />
                      ) : null}
                      {showConnector && index % 2 === 0 && index + 1 < count ? (
                        <span
                          aria-hidden
                          className="pointer-events-none absolute top-1/2 left-[calc(100%+2rem-1px)] z-10 h-full w-px bg-border"
                        />
                      ) : null}
                    </div>
                  );
                })}
              </Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function RoundTabs({ rounds }: { rounds: BracketRound[] }) {
  const baseId = useId();
  const [index, setIndex] = useState(0);
  const selectedIndex = index >= 0 && index < rounds.length ? index : 0;
  const selected = rounds[selectedIndex] ?? rounds[0];

  if (!selected) return null;

  return (
    <div>
      <div
        role="tablist"
        aria-label="Bracket rounds"
        className="flex gap-2 overflow-x-auto pb-3"
      >
        {rounds.map((round, roundIndex) => {
          const selectedTab = roundIndex === selectedIndex;
          return (
            <button
              key={round.round}
              type="button"
              role="tab"
              id={`${baseId}-tab-${round.round}`}
              aria-selected={selectedTab}
              aria-controls={`${baseId}-panel`}
              className={cn(
                "h-11 shrink-0 rounded-full px-4 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                selectedTab ? "bg-elevated text-positive" : "text-muted-foreground",
              )}
              onClick={() => setIndex(roundIndex)}
            >
              {round.name}
            </button>
          );
        })}
      </div>
      <div
        role="tabpanel"
        id={`${baseId}-panel`}
        aria-labelledby={`${baseId}-tab-${selected.round}`}
        className="flex flex-col gap-3"
      >
        {selected.matches.map((match) => (
          <MatchCard key={match.id} match={match} />
        ))}
      </div>
    </div>
  );
}

export function Bracket({ rounds }: { rounds: BracketRound[] }) {
  const ordered = orderedRounds(rounds);

  if (ordered.length === 0) {
    return (
      <div className="flex flex-col gap-1">
        <QuietEmpty>The bracket has not been generated.</QuietEmpty>
        <QuietEmpty>Bracket will appear once the admin generates it.</QuietEmpty>
      </div>
    );
  }

  return (
    <div>
      <div className="md:hidden">
        <RoundTabs rounds={ordered} />
      </div>
      <div className="hidden md:block">
        <RoundColumns rounds={ordered} />
      </div>
    </div>
  );
}
