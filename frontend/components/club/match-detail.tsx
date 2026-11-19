import Link from "next/link";

import { isWinner } from "@/components/club/match-utils";
import { PlayerInline } from "@/components/club/player-inline";
import { cardClass, textActionClass } from "@/components/club/styles";
import { InactiveBadge } from "@/components/inactive-badge";
import { LoadError } from "@/components/load-error";
import { LocalDateTime } from "@/components/local-time";
import { RatingDelta } from "@/components/rating-delta";
import { StatusBadge } from "@/components/status-badge";
import { getMatch } from "@/lib/api/client";
import { formatGameScores, formatRating } from "@/lib/format";
import { errorCopy, loadData } from "@/lib/load";
import type { Match, PlayerSummary, RatingChange } from "@/types/api";

function changeFor(match: Match, playerId: string): RatingChange | undefined {
  return match.rating_changes.find((change) => change.player_id === playerId);
}

function PlayerPanel({ match, player }: { match: Match; player: PlayerSummary }) {
  const change = changeFor(match, player.id);
  const winner = isWinner(match, player.id);

  return (
    <div className="rounded-2xl bg-elevated/50 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Link href={`/players/${player.id}`} className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <PlayerInline player={player} size="md" showInactive={false} />
        </Link>
        {winner ? (
          <span className="inline-flex h-5 items-center rounded-full bg-primary/15 px-2 text-xs font-medium text-positive">
            Winner
          </span>
        ) : null}
        {player.is_active ? null : <InactiveBadge />}
      </div>
      {match.rating_changes.length === 0 || !change ? (
        <p className="mt-3 text-sm text-muted-foreground">No rating change</p>
      ) : (
        <p className="mt-3 text-sm tabular-nums">
          {formatRating(change.old_rating)} → {formatRating(change.new_rating)}{" "}
          <RatingDelta value={change.rating_change} />
        </p>
      )}
    </div>
  );
}

export async function MatchDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const result = await loadData(getMatch(id), { notFoundOn404: true });
  if (!result.ok) {
    const copy = errorCopy(result.error, "this match");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  const match = result.data;
  const scores = formatGameScores(match.game_scores);

  return (
    <article className={`${cardClass} mx-auto w-full max-w-[720px]`}>
      <div className="flex flex-wrap items-center gap-2">
        {match.status !== "completed" ? <StatusBadge status={match.status} /> : null}
        <p className="text-sm text-muted-foreground">
          <LocalDateTime value={match.match_date} />
        </p>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">Shown in your local time. Stored in UTC.</p>
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <PlayerPanel match={match} player={match.player_a} />
        <PlayerPanel match={match} player={match.player_b} />
      </div>
      {scores ? (
        <div className="mt-5">
          <p className="text-lg font-semibold tabular-nums">{scores}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Scores are {match.player_a.display_name} first. They do not change Elo.
          </p>
        </div>
      ) : null}
      {match.tournament ? (
        <p className="mt-5 text-sm">
          Tournament:{" "}
          <Link href={`/tournaments/${match.tournament.id}`} className={textActionClass}>
            {match.tournament.name}
          </Link>
        </p>
      ) : null}
      {match.notes ? <p className="mt-4 text-sm">{match.notes}</p> : null}
      <p className="mt-5">
        <Link
          href={`/head-to-head?a=${match.player_a.id}&b=${match.player_b.id}`}
          className={textActionClass}
        >
          Head-to-head
        </Link>
      </p>
    </article>
  );
}
