import Link from "next/link";

import { InactiveBadge } from "@/components/inactive-badge";
import { PlayerAvatar } from "@/components/player-avatar";
import { cn } from "@/lib/utils";
import type { PlayerSummary } from "@/types/api";

type PlayerBits = Pick<PlayerSummary, "id" | "display_name" | "avatar_url" | "is_active">;

export function PlayerInline({
  player,
  size = "sm",
  showInactive = true,
  className,
}: {
  player: PlayerBits;
  size?: "sm" | "md" | "lg";
  showInactive?: boolean;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex min-w-0 items-center gap-2", className)}>
      <PlayerAvatar name={player.display_name} imageUrl={player.avatar_url} size={size} />
      <span className="truncate">{player.display_name}</span>
      {showInactive && !player.is_active ? <InactiveBadge /> : null}
    </span>
  );
}

export function PlayerProfileLink({
  player,
  className,
  stretch = false,
}: {
  player: PlayerBits;
  className?: string;
  stretch?: boolean;
}) {
  return (
    <Link
      href={`/players/${player.id}`}
      className={cn(
        "inline-flex min-w-0 items-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        stretch && "static after:absolute after:inset-0",
        className,
      )}
    >
      <PlayerInline player={player} />
    </Link>
  );
}
