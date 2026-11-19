"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import type { Bracket, BracketMatch } from "@/types/api";

export function bracketHasResults(bracket: Bracket): boolean {
  return bracket.rounds.some((round) =>
    round.matches.some(
      (match) => match.status === "completed" || match.match_id != null,
    ),
  );
}

export function BracketBoard({
  bracket,
  allowRecord,
  onRecord,
}: {
  bracket: Bracket;
  allowRecord: boolean;
  onRecord: (match: BracketMatch) => void;
}) {
  const rounds = [...bracket.rounds].sort((a, b) => a.round - b.round);
  if (rounds.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        The bracket has not been generated.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4 md:flex-row md:overflow-x-auto">
      {rounds.map((round) => (
        <section
          key={round.round}
          className="flex w-full shrink-0 flex-col gap-3 md:w-64"
        >
          <h3 className="text-sm font-semibold">{round.name}</h3>
          {[...round.matches]
            .sort((a, b) => a.position - b.position)
            .map((slot) => (
              <article
                key={slot.id}
                className="flex flex-col gap-2 rounded-[20px] bg-card p-3 ring-1 ring-foreground/10"
              >
                <SlotSide
                  seed={slot.seed_a}
                  name={slot.player_a?.display_name ?? null}
                  winner={
                    slot.winner_id != null && slot.winner_id === slot.player_a?.id
                  }
                  emptyLabel={slot.is_bye || slot.status === "bye" ? "BYE" : "Waiting"}
                />
                <SlotSide
                  seed={slot.seed_b}
                  name={slot.player_b?.display_name ?? null}
                  winner={
                    slot.winner_id != null && slot.winner_id === slot.player_b?.id
                  }
                  emptyLabel={slot.is_bye || slot.status === "bye" ? "BYE" : "Waiting"}
                />
                <p className="text-xs text-muted-foreground">
                  {slot.status === "completed"
                    ? "Completed"
                    : slot.status === "ready"
                      ? "Ready"
                      : slot.status === "bye"
                        ? "BYE"
                        : "Waiting"}
                </p>
                {slot.status === "completed" && slot.match_id ? (
                  <Link
                    href={`/matches/${slot.match_id}`}
                    className="text-sm text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    Match
                  </Link>
                ) : null}
                {allowRecord && slot.status === "ready" ? (
                  <Button
                    type="button"
                    className="h-11 rounded-full md:h-10"
                    onClick={() => onRecord(slot)}
                  >
                    Record result
                  </Button>
                ) : null}
              </article>
            ))}
        </section>
      ))}
    </div>
  );
}

function SlotSide({
  seed,
  name,
  winner,
  emptyLabel,
}: {
  seed: number | null;
  name: string | null;
  winner: boolean;
  emptyLabel: string;
}) {
  if (!name) {
    return <p className="text-sm text-muted-foreground">{emptyLabel}</p>;
  }
  return (
    <p className={winner ? "text-sm text-positive" : "text-sm"}>
      {seed != null ? (
        <span className="mr-2 text-muted-foreground tabular-nums">{seed}</span>
      ) : null}
      {name}
    </p>
  );
}
