import Link from "next/link";

import { HeadToHeadChooser } from "@/components/club/h2h-chooser";
import { isWinner, ratingChangeFor } from "@/components/club/match-utils";
import { cardClass, QuietEmpty } from "@/components/club/styles";
import { LoadError } from "@/components/load-error";
import { LocalDateTime } from "@/components/local-time";
import { RatingDelta } from "@/components/rating-delta";
import { getHeadToHead, getPlayers } from "@/lib/api/client";
import { formatGameScores, formatWinRate } from "@/lib/format";
import { errorCopy, loadData } from "@/lib/load";
import { readOne, type Query } from "@/lib/query";
import type { HeadToHead, Match } from "@/types/api";

export async function HeadToHeadChooserSection() {
  const result = await loadData(getPlayers({ include_inactive: true }));
  if (!result.ok) {
    const copy = errorCopy(result.error, "players");
    return <LoadError title={copy.title} message={copy.message} />;
  }
  return <HeadToHeadChooser players={result.data.items} />;
}

function Encounter({ match }: { match: Match }) {
  const scores = formatGameScores(match.game_scores);
  return (
    <Link
      href={`/matches/${match.id}`}
      className="flex flex-col gap-1 rounded-xl py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className="text-xs text-muted-foreground">
        <LocalDateTime value={match.match_date} />
        {match.tournament ? ` · ${match.tournament.name}` : ""}
      </span>
      <span className="text-sm">
        <span className={isWinner(match, match.player_a.id) ? "text-primary" : undefined}>
          {match.player_a.display_name}
        </span>
        <span className="text-muted-foreground"> vs </span>
        <span className={isWinner(match, match.player_b.id) ? "text-primary" : undefined}>
          {match.player_b.display_name}
        </span>
      </span>
      <span className="text-sm tabular-nums text-muted-foreground">{scores ?? "—"}</span>
      {match.rating_changes.length === 0 ? (
        <span className="text-sm text-muted-foreground">No rating change</span>
      ) : (
        <span className="flex flex-wrap gap-3 text-sm">
          <span>
            {match.player_a.display_name}{" "}
            <RatingDelta value={ratingChangeFor(match, match.player_a.id)} />
          </span>
          <span>
            {match.player_b.display_name}{" "}
            <RatingDelta value={ratingChangeFor(match, match.player_b.id)} />
          </span>
        </span>
      )}
    </Link>
  );
}

function EncounterList({ matches }: { matches: Match[] }) {
  const recent = matches.slice(0, 5);
  const earlier = matches.slice(5);
  return (
    <div>
      <h2 className="text-lg font-semibold">Recent</h2>
      <ul className="divide-y divide-border">
        {recent.map((match) => (
          <li key={match.id}>
            <Encounter match={match} />
          </li>
        ))}
      </ul>
      {earlier.length > 0 ? (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm font-medium">Earlier</summary>
          <ul className="divide-y divide-border">
            {earlier.map((match) => (
              <li key={match.id}>
                <Encounter match={match} />
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}

function Summary({ data }: { data: HeadToHead }) {
  const total = data.player_a_wins + data.player_b_wins;
  const aShare = total === 0 ? 50 : (data.player_a_wins / total) * 100;
  const streakPlayer =
    data.current_streak == null
      ? null
      : data.current_streak.player_id === data.player_a.id
        ? data.player_a
        : data.player_b;

  return (
    <section className={cardClass}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="text-xs text-muted-foreground">Matches</p>
          <p className="text-[28px] leading-none font-semibold tabular-nums">{data.total_matches}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{data.player_a.display_name} wins</p>
          <p className="text-[28px] leading-none font-semibold tabular-nums">{data.player_a_wins}</p>
          <p className="mt-1 text-sm tabular-nums">{formatWinRate(data.player_a_win_rate)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{data.player_b.display_name} wins</p>
          <p className="text-[28px] leading-none font-semibold tabular-nums">{data.player_b_wins}</p>
          <p className="mt-1 text-sm tabular-nums">{formatWinRate(data.player_b_win_rate)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Net Elo for {data.player_a.display_name}</p>
          <p className="mt-2">
            <RatingDelta value={data.player_a_net_rating_change} />
          </p>
        </div>
      </div>
      <div
        className="mt-4 flex h-2 overflow-hidden rounded-full"
        role="img"
        aria-label={`${data.player_a.display_name} ${data.player_a_wins}, ${data.player_b.display_name} ${data.player_b_wins}`}
      >
        <span className="bg-primary" style={{ width: `${aShare}%` }} />
        <span className="bg-secondary" style={{ width: `${100 - aShare}%` }} />
      </div>
      {streakPlayer && data.current_streak ? (
        <p className="mt-3 text-sm">
          {streakPlayer.display_name} has won the last {data.current_streak.count}.
        </p>
      ) : null}
    </section>
  );
}

export async function HeadToHeadResult({ searchParams }: { searchParams: Promise<Query> }) {
  const params = await searchParams;
  const a = readOne(params.a);
  const b = readOne(params.b);

  if (!a || !b) {
    return <QuietEmpty>Choose two players.</QuietEmpty>;
  }
  if (a === b) {
    return <p className="text-sm text-foreground">Pick two different players.</p>;
  }

  const result = await loadData(getHeadToHead(a, b), { notFoundOn404: true });
  if (!result.ok) {
    const copy = errorCopy(result.error, "this head-to-head");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  const data = result.data;
  if (data.total_matches === 0) {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium">
          {data.player_a.display_name} and {data.player_b.display_name}
        </p>
        <QuietEmpty>No completed matches between these two.</QuietEmpty>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Summary data={data} />
      <EncounterList matches={data.matches} />
    </div>
  );
}
