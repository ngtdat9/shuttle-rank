/** Final-position labels from R-TN-08. Any other number is that place. */
export function finalPositionLabel(position: number | null): string {
  if (position == null) return "—";
  if (position === 1) return "Champion";
  if (position === 2) return "Runner-up";
  if (position === 3) return "Semifinals";
  if (position === 5) return "Quarterfinals";
  if (position === 9) return "Round of 16";
  return String(position);
}

export const ACHIEVEMENT_ICONS = [
  "Trophy",
  "Medal",
  "Crown",
  "Flame",
  "Zap",
  "Target",
  "Star",
  "Award",
  "Shield",
  "Swords",
] as const;

export const AUDIT_ENTITY_TYPES = [
  "player",
  "match",
  "tournament",
  "achievement",
  "rankings",
] as const;

export const AUDIT_ACTIONS = [
  "player.create",
  "player.update",
  "player.deactivate",
  "match.create",
  "match.update",
  "match.correct",
  "match.cancel",
  "match.delete",
  "tournament.create",
  "tournament.update",
  "tournament.participants_add",
  "tournament.participant_remove",
  "tournament.bracket_generate",
  "tournament.match_record",
  "achievement.create",
  "achievement.update",
  "achievement.award",
  "achievement.revoke",
  "rankings.monthly_rebuild",
] as const;
