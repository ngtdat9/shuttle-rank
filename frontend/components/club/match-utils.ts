import type { Match, PlayerSummary } from "@/types/api";

export function playerSide(match: Match, playerId: string): PlayerSummary | null {
  if (match.player_a.id === playerId) return match.player_a;
  if (match.player_b.id === playerId) return match.player_b;
  return null;
}

export function ratingChangeFor(match: Match, playerId: string): number | null {
  if (match.rating_changes.length === 0) return null;
  const row = match.rating_changes.find((change) => change.player_id === playerId);
  return row ? row.rating_change : null;
}

export function isWinner(match: Match, playerId: string): boolean {
  return match.winner_id === playerId;
}
