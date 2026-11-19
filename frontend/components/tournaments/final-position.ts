/**
 * Display labels for TournamentParticipant.final_position.
 * Mapping only — the API assigns the place. See R-TN-08.
 */
const NAMED_PLACES: Record<number, string> = {
  1: "Champion",
  2: "Runner-up",
  3: "Semifinals",
  5: "Quarterfinals",
  9: "Round of 16",
};

function ordinal(value: number): string {
  const mod100 = value % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${value}th`;
  switch (value % 10) {
    case 1:
      return `${value}st`;
    case 2:
      return `${value}nd`;
    case 3:
      return `${value}rd`;
    default:
      return `${value}th`;
  }
}

export function finalPositionLabel(position: number | null): string {
  if (position == null) return "—";
  const named = NAMED_PLACES[position];
  if (named) return named;
  if (!Number.isInteger(position) || position < 1) return String(position);
  return `${ordinal(position)} place`;
}
