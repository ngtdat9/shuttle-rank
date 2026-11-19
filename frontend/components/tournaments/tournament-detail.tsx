import Link from "next/link";
import { Crown } from "lucide-react";

import { PlayerProfileLink } from "@/components/club/player-inline";
import { cardClass, QuietEmpty, textActionClass } from "@/components/club/styles";
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHead,
  DataTableHeader,
  DataTableRow,
} from "@/components/data-table";
import { LoadError } from "@/components/load-error";
import { PlayerAvatar } from "@/components/player-avatar";
import { StatusBadge } from "@/components/status-badge";
import { Bracket } from "@/components/tournaments/Bracket";
import { finalPositionLabel } from "@/components/tournaments/final-position";
import { getBracket, getTournament } from "@/lib/api/client";
import { formatDate, formatRating } from "@/lib/format";
import { errorCopy, loadData } from "@/lib/load";
import { cn } from "@/lib/utils";
import type {
  PlayerSummary,
  TournamentDetail as TournamentDetailData,
} from "@/types/api";

function calendarDate(value: string): string {
  return formatDate(value, undefined, "en-US");
}

function dateRange(start: string | null, end: string | null): string {
  if (start && end) return `${calendarDate(start)} – ${calendarDate(end)}`;
  if (start) return calendarDate(start);
  if (end) return `Ends ${calendarDate(end)}`;
  return "Dates not set";
}

function formatName(format: TournamentDetailData["format"]): string {
  if (format === "single_elimination") return "Single elimination";
  return format;
}

function playerCount(count: number): string {
  return `${count} players`;
}

function PodiumPlayer({
  player,
  role,
  champion,
}: {
  player: PlayerSummary;
  role: string;
  champion?: boolean;
}) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      {champion ? (
        <Crown className="size-5 shrink-0 text-positive" aria-hidden />
      ) : null}
      <PlayerAvatar
        name={player.display_name}
        imageUrl={player.avatar_url}
        size={champion ? "lg" : "md"}
      />
      <div className="min-w-0">
        <p
          className={cn(
            "text-xs font-medium",
            champion ? "text-positive" : "text-muted-foreground",
          )}
        >
          {role}
        </p>
        <Link
          href={`/players/${player.id}`}
          className={cn(
            "block truncate rounded-sm font-semibold underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            champion ? "text-lg text-positive" : "text-sm text-muted-foreground",
          )}
        >
          {player.display_name}
        </Link>
      </div>
    </div>
  );
}

export async function TournamentDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [tournamentResult, bracketResult] = await Promise.all([
    loadData(getTournament(id), { notFoundOn404: true }),
    loadData(getBracket(id)),
  ]);

  if (!tournamentResult.ok) {
    const copy = errorCopy(tournamentResult.error, "this tournament");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  const tournament = tournamentResult.data;
  const showPodium =
    tournament.status === "completed" && (tournament.champion || tournament.runner_up);

  return (
    <div className="flex flex-col gap-4 lg:gap-5">
      <header className={cardClass}>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={tournament.status} />
          <span className="text-sm text-muted-foreground">
            {formatName(tournament.format)}
          </span>
        </div>
        <h1 className="mt-2 text-[28px] leading-[34px] font-semibold">
          {tournament.name}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {dateRange(tournament.start_date, tournament.end_date)}
          {" · "}
          {playerCount(tournament.participant_count)}
        </p>
        {tournament.description ? (
          <p className="mt-3 max-w-2xl text-sm whitespace-pre-wrap">
            {tournament.description}
          </p>
        ) : null}
      </header>

      {showPodium ? (
        <section
          className={cn(
            cardClass,
            "flex flex-col gap-4 border-l-[3px] border-l-primary sm:flex-row sm:items-center sm:justify-between",
          )}
        >
          {tournament.champion ? (
            <PodiumPlayer player={tournament.champion} role="Champion" champion />
          ) : null}
          {tournament.runner_up ? (
            <PodiumPlayer player={tournament.runner_up} role="Runner-up" />
          ) : null}
        </section>
      ) : null}

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Participants</h2>
        {tournament.participants.length === 0 ? (
          <QuietEmpty>No participants yet.</QuietEmpty>
        ) : (
          <DataTable>
            <DataTableHeader>
              <DataTableRow>
                <DataTableHead className="w-16">Seed</DataTableHead>
                <DataTableHead>Player</DataTableHead>
                <DataTableHead className="w-24">Rating</DataTableHead>
                <DataTableHead>Final position</DataTableHead>
              </DataTableRow>
            </DataTableHeader>
            <DataTableBody>
              {tournament.participants.map((participant) => (
                <DataTableRow key={participant.player.id}>
                  <DataTableCell className="tabular-nums text-muted-foreground">
                    {participant.seed ?? "—"}
                  </DataTableCell>
                  <DataTableCell>
                    <PlayerProfileLink player={participant.player} />
                  </DataTableCell>
                  <DataTableCell className="tabular-nums">
                    {formatRating(participant.player.current_rating)}
                  </DataTableCell>
                  <DataTableCell
                    className={
                      participant.final_position === 1
                        ? "font-medium text-positive"
                        : undefined
                    }
                  >
                    {finalPositionLabel(participant.final_position)}
                  </DataTableCell>
                </DataTableRow>
              ))}
            </DataTableBody>
          </DataTable>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Bracket</h2>
        {bracketResult.ok ? (
          <Bracket rounds={bracketResult.data.rounds} />
        ) : (
          <LoadError {...errorCopy(bracketResult.error, "the bracket")} />
        )}
        <Link href="/tournaments" className={textActionClass}>
          All tournaments
        </Link>
      </section>
    </div>
  );
}
