import Link from "next/link";

import { QuietEmpty } from "@/components/club/styles";
import { LoadError } from "@/components/load-error";
import { StatusBadge } from "@/components/status-badge";
import { getTournaments } from "@/lib/api/client";
import { formatDate } from "@/lib/format";
import { errorCopy, loadData } from "@/lib/load";

function calendarDate(value: string): string {
  return formatDate(value, undefined, "en-US");
}

export async function TournamentList() {
  const result = await loadData(getTournaments());
  if (!result.ok) {
    const copy = errorCopy(result.error, "tournaments");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  if (result.data.items.length === 0) {
    return <QuietEmpty>No tournaments yet.</QuietEmpty>;
  }

  return (
    <ul className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {result.data.items.map((tournament) => (
        <li key={tournament.id}>
          <Link
            href={`/tournaments/${tournament.id}`}
            className="flex h-full flex-col gap-2 rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 transition-colors hover:ring-[#3A403C] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:p-5"
          >
            <StatusBadge status={tournament.status} />
            <span className="text-lg font-semibold">{tournament.name}</span>
            <span className="text-sm text-muted-foreground">
              {tournament.start_date ? calendarDate(tournament.start_date) : "Date not set"}
              {tournament.end_date ? ` – ${calendarDate(tournament.end_date)}` : ""}
            </span>
            <span className="text-sm">{tournament.participant_count} players</span>
            {tournament.champion ? (
              <span className="text-sm">Champion {tournament.champion.display_name}</span>
            ) : null}
          </Link>
        </li>
      ))}
    </ul>
  );
}
