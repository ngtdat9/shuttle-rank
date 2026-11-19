import type { TournamentStatus } from "@/types/api";

export const TOURNAMENT_STATUSES: { value: TournamentStatus; label: string }[] = [
  { value: "in_progress", label: "In progress" },
  { value: "draft", label: "Draft" },
  { value: "completed", label: "Completed" },
  { value: "canceled", label: "Canceled" },
];

export function isTournamentStatus(value: string): value is TournamentStatus {
  return TOURNAMENT_STATUSES.some((item) => item.value === value);
}
