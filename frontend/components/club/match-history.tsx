import Link from "next/link";

import { isWinner, ratingChangeFor } from "@/components/club/match-utils";
import { MatchFilters } from "@/components/club/match-filters";
import { cardClass, QuietEmpty, textActionClass } from "@/components/club/styles";
import { LoadError } from "@/components/load-error";
import { LocalDateTime } from "@/components/local-time";
import { Pager } from "@/components/pager";
import { RatingDelta } from "@/components/rating-delta";
import { StatusBadge } from "@/components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getMatches, getPlayers, getTournaments } from "@/lib/api/client";
import { formatGameScores } from "@/lib/format";
import { errorCopy, loadData } from "@/lib/load";
import { readDateParam, readMatchStatus, readOne, readPage, type Query } from "@/lib/query";
import { cn } from "@/lib/utils";
import type { Match, PlayerListItem, TournamentSummary } from "@/types/api";

const PAGE_SIZE = 20;

function playerClass(winner: boolean) {
  return winner ? "font-medium text-primary" : "text-foreground";
}

function MatchFields({ match, showStatus }: { match: Match; showStatus: boolean }) {
  const scores = formatGameScores(match.game_scores);
  const aChange = ratingChangeFor(match, match.player_a.id);
  const bChange = ratingChangeFor(match, match.player_b.id);
  const unrated = match.rating_changes.length === 0;

  return (
    <>
      <span className="text-xs text-muted-foreground">
        <LocalDateTime value={match.match_date} />
      </span>
      <span className="text-sm">
        <span className={playerClass(isWinner(match, match.player_a.id))}>
          {match.player_a.display_name}
        </span>
        <span className="text-muted-foreground"> vs </span>
        <span className={playerClass(isWinner(match, match.player_b.id))}>
          {match.player_b.display_name}
        </span>
      </span>
      <span className="text-sm text-muted-foreground">
        Winner:{" "}
        <span className="text-primary">
          {isWinner(match, match.player_a.id)
            ? match.player_a.display_name
            : match.player_b.display_name}
        </span>
      </span>
      <span className="text-sm tabular-nums">{scores ?? "—"}</span>
      {unrated ? (
        <span className="text-sm text-muted-foreground">No rating change</span>
      ) : (
        <span className="flex flex-wrap gap-3 text-sm">
          <span>
            {match.player_a.display_name} <RatingDelta value={aChange} />
          </span>
          <span>
            {match.player_b.display_name} <RatingDelta value={bChange} />
          </span>
        </span>
      )}
      {match.tournament ? (
        <span className="text-xs text-muted-foreground">{match.tournament.name}</span>
      ) : null}
      {showStatus ? <StatusBadge status={match.status} /> : null}
    </>
  );
}

export async function MatchHistory({ searchParams }: { searchParams: Promise<Query> }) {
  const params = await searchParams;
  const page = readPage(params.page);
  const status = readMatchStatus(params.status);
  const search = readOne(params.search);
  const playerId = readOne(params.player_id);
  const tournamentId = readOne(params.tournament_id);
  const dateFrom = readDateParam(params.date_from);
  const dateTo = readDateParam(params.date_to);

  const [matchesResult, playersResult, tournamentsResult] = await Promise.all([
    loadData(
      getMatches({
        page,
        page_size: PAGE_SIZE,
        status,
        search,
        player_id: playerId,
        tournament_id: tournamentId,
        date_from: dateFrom,
        date_to: dateTo,
      }),
    ),
    loadData(getPlayers({ include_inactive: true })),
    loadData(getTournaments()),
  ]);

  const players: PlayerListItem[] = playersResult.ok ? playersResult.data.items : [];
  const tournaments: TournamentSummary[] = tournamentsResult.ok ? tournamentsResult.data.items : [];
  const showStatus = status !== "completed";
  const preserved: Record<string, string | undefined> = {
    search,
    player_id: playerId,
    status: status === "completed" ? undefined : status,
    tournament_id: tournamentId,
    date_from: dateFrom,
    date_to: dateTo,
  };

  return (
    <div className="flex flex-col gap-4">
      <MatchFilters players={players} tournaments={tournaments} />
      {!matchesResult.ok ? (
        <LoadError {...errorCopy(matchesResult.error, "matches")} />
      ) : matchesResult.data.items.length === 0 ? (
        <div className="flex flex-col items-start gap-3">
          <QuietEmpty>No matches match these filters.</QuietEmpty>
          <Link href="/matches" className={textActionClass}>
            Clear
          </Link>
        </div>
      ) : (
        <>
          <ul className="flex flex-col gap-3 md:hidden">
            {matchesResult.data.items.map((match) => (
              <li key={match.id}>
                <Link
                  href={`/matches/${match.id}`}
                  className={cn(cardClass, "flex flex-col gap-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring")}
                >
                  <MatchFields match={match} showStatus={showStatus} />
                </Link>
              </li>
            ))}
          </ul>
          <div className={cn(cardClass, "hidden overflow-hidden p-0 md:block")}>
            <Table>
              <caption className="sr-only">Match history, newest first</caption>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Players</TableHead>
                  <TableHead>Winner</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Rating changes</TableHead>
                  <TableHead>Tournament</TableHead>
                  {showStatus ? <TableHead>Status</TableHead> : null}
                </TableRow>
              </TableHeader>
              <TableBody>
                {matchesResult.data.items.map((match) => {
                  const scores = formatGameScores(match.game_scores);
                  const winnerName = isWinner(match, match.player_a.id)
                    ? match.player_a.display_name
                    : match.player_b.display_name;
                  return (
                    <TableRow key={match.id} className="relative">
                      <TableCell>
                        <LocalDateTime value={match.match_date} />
                      </TableCell>
                      <TableCell>
                        <Link
                          href={`/matches/${match.id}`}
                          className="static rounded-full after:absolute after:inset-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <span className={playerClass(isWinner(match, match.player_a.id))}>
                            {match.player_a.display_name}
                          </span>
                          <span className="text-muted-foreground"> vs </span>
                          <span className={playerClass(isWinner(match, match.player_b.id))}>
                            {match.player_b.display_name}
                          </span>
                        </Link>
                      </TableCell>
                      <TableCell className="text-primary">{winnerName}</TableCell>
                      <TableCell className="tabular-nums">{scores ?? "—"}</TableCell>
                      <TableCell>
                        {match.rating_changes.length === 0 ? (
                          <span className="text-muted-foreground">No rating change</span>
                        ) : (
                          <span className="flex flex-col gap-1">
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
                      </TableCell>
                      <TableCell>{match.tournament?.name ?? "—"}</TableCell>
                      {showStatus ? (
                        <TableCell>
                          <StatusBadge status={match.status} />
                        </TableCell>
                      ) : null}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
          <Pager
            page={matchesResult.data.page}
            pageSize={matchesResult.data.page_size}
            total={matchesResult.data.total}
            pathname="/matches"
            query={preserved}
          />
        </>
      )}
    </div>
  );
}
