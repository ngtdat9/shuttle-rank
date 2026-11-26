import Link from "next/link";

import { QuietEmpty } from "@/components/club/styles";
import { LoadError } from "@/components/load-error";
import { PlayerAvatar } from "@/components/player-avatar";
import { StatusBadge } from "@/components/status-badge";
import { isTournamentStatus } from "@/components/tournaments/statuses";
import { getTournaments } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { errorCopy, loadData } from "@/lib/load";
import { readOne, type Query } from "@/lib/query";
import { cn } from "@/lib/utils";

function calendarDate(value: string): string {
  return formatDate(value, undefined, "en-US");
}

export async function TournamentList({
  searchParams,
}: {
  searchParams: Promise<Query>;
}) {
  const params = await searchParams;
  const statusRaw = readOne(params.status);
  const status = statusRaw && isTournamentStatus(statusRaw) ? statusRaw : undefined;
  const result = await loadData(getTournaments(status ? { status } : undefined));

  if (!result.ok) {
    const copy = errorCopy(result.error, "tournaments");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  if (result.data.items.length === 0) {
    return (
      <QuietEmpty>
        {status ? "No tournaments with this status." : "No tournaments yet."}
      </QuietEmpty>
    );
  }

  return (
    <ul className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {result.data.items.map((tournament) => (
        <li key={tournament.id}>
          <Link
            href={`/tournaments/${tournament.id}`}
            className={cn(
              "flex h-full flex-col gap-2 sr-panel sr-lift rounded-[24px] p-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:p-5",
              tournament.status === "in_progress" &&
                "ring-2 ring-primary hover:ring-primary",
            )}
          >
            <StatusBadge status={tournament.status} />
            <span className="text-lg font-semibold">{tournament.name}</span>
            <span className="text-sm text-muted-foreground">
              {tournament.start_date
                ? calendarDate(tournament.start_date)
                : "Date not set"}
              {tournament.end_date ? ` – ${calendarDate(tournament.end_date)}` : ""}
            </span>
            <span className="text-sm">{tournament.participant_count} players</span>
            {tournament.champion ? (
              <span className="inline-flex items-center gap-2 text-sm">
                <PlayerAvatar
                  name={tournament.champion.display_name}
                  imageUrl={tournament.champion.avatar_url}
                  size="sm"
                />
                <span>
                  Champion{" "}
                  <span className="font-medium text-positive">
                    {tournament.champion.display_name}
                  </span>
                </span>
              </span>
            ) : null}
          </Link>
        </li>
      ))}
    </ul>
  );
}
