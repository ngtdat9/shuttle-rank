import Link from "next/link";

import { PlayerAvatar } from "@/components/player-avatar";
import { RankBadge } from "@/components/rank-badge";
import { LoadError } from "@/components/load-error";
import { QuietEmpty } from "@/components/club/styles";
import { getPlayers } from "@/lib/api/client";
import { formatRating, formatRecord, formatWinRate } from "@/lib/format";
import { errorCopy, loadData } from "@/lib/load";
import { readOne, type Query } from "@/lib/query";

export async function PlayerDirectory({ searchParams }: { searchParams: Promise<Query> }) {
  const params = await searchParams;
  const search = readOne(params.search);
  const result = await loadData(getPlayers(search ? { search } : undefined));

  if (!result.ok) {
    const copy = errorCopy(result.error, "players");
    return <LoadError title={copy.title} message={copy.message} />;
  }

  if (result.data.items.length === 0) {
    return (
      <QuietEmpty>
        {search ? `No players match “${search}”.` : "No active players yet."}
      </QuietEmpty>
    );
  }

  return (
    <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {result.data.items.map((player) => (
        <li key={player.id}>
          <Link
            href={`/players/${player.id}`}
            className="flex h-full flex-col gap-3 rounded-[20px] bg-card p-4 ring-1 ring-foreground/10 transition-colors hover:ring-[#3A403C] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:p-5"
          >
            <span className="flex items-center justify-between gap-3">
              <PlayerAvatar name={player.display_name} imageUrl={player.avatar_url} size="lg" />
              {player.rank == null ? (
                <span className="text-xs text-muted-foreground">Inactive</span>
              ) : (
                <RankBadge rank={player.rank} />
              )}
            </span>
            <span className="font-medium">{player.display_name}</span>
            <span className="text-[28px] leading-none font-semibold tabular-nums">
              {formatRating(player.current_rating)}
            </span>
            <span className="text-sm text-muted-foreground tabular-nums">
              {formatRecord(player.wins, player.losses)} · {formatWinRate(player.win_rate)}
            </span>
            <span className="text-xs text-muted-foreground">
              Highest {formatRating(player.highest_rating)}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
