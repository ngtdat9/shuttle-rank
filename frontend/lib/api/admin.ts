import { apiFetch } from "@/lib/api/client";
import type {
  Achievement,
  AchievementAward,
  AchievementListResponse,
  AddParticipantsBody,
  AdminMe,
  AdminPlayerAchievement,
  AdminStats,
  AuditLogEntry,
  Bracket,
  CancelMatchBody,
  CorrectMatchBody,
  CreateAchievementBody,
  CreateMatchBody,
  CreatePlayerBody,
  CreateTournamentBody,
  DeletedEntity,
  GenerateBracketBody,
  Match,
  MatchListStatus,
  MonthlyRebuildResponse,
  Paginated,
  PatchMatchBody,
  PlayerListResponse,
  PlayerProfile,
  RecordBracketMatchBody,
  RecordBracketMatchResponse,
  TournamentDetail,
  TournamentListResponse,
  TournamentStatus,
  UpdateAchievementBody,
  UpdatePlayerBody,
  UpdateTournamentBody,
  AwardAchievementBody,
} from "@/types/api";

/**
 * Admin match row. `deleted_at` is read when the payload includes it so deleted
 * rows can be labelled. docs/API.md does not list the field on Match yet.
 */
export type AdminMatch = Match & {
  deleted_at?: string | null;
};

export function matchDeletedAt(match: AdminMatch): string | null {
  return typeof match.deleted_at === "string" && match.deleted_at.length > 0
    ? match.deleted_at
    : null;
}

export type AdminMatchQuery = {
  page?: number;
  page_size?: number;
  player_id?: string;
  status?: MatchListStatus;
  tournament_id?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  include_deleted?: boolean;
};

export type AuditLogQuery = {
  page?: number;
  page_size?: number;
  entity_type?: string;
  action?: string;
};

export function getAdminMe(token: string, signal?: AbortSignal) {
  return apiFetch<AdminMe>("/admin/me", { token, signal });
}

export function getAdminStats(token: string, signal?: AbortSignal) {
  return apiFetch<AdminStats>("/admin/stats", { token, signal });
}

export function getAdminAuditLogs(
  token: string,
  params?: AuditLogQuery,
  signal?: AbortSignal,
) {
  return apiFetch<Paginated<AuditLogEntry>>("/admin/audit-logs", {
    token,
    searchParams: params,
    signal,
  });
}

export function getAdminPlayers(token: string, signal?: AbortSignal) {
  return apiFetch<PlayerListResponse>("/admin/players", { token, signal });
}

export function createAdminPlayer(token: string, body: CreatePlayerBody) {
  return apiFetch<PlayerProfile>("/admin/players", { method: "POST", token, body });
}

export function updateAdminPlayer(token: string, id: string, body: UpdatePlayerBody) {
  return apiFetch<PlayerProfile>(`/admin/players/${encodeURIComponent(id)}`, {
    method: "PATCH",
    token,
    body,
  });
}

export function deactivateAdminPlayer(token: string, id: string) {
  return apiFetch<PlayerProfile>(`/admin/players/${encodeURIComponent(id)}`, {
    method: "DELETE",
    token,
  });
}

export function getAdminMatches(
  token: string,
  params?: AdminMatchQuery,
  signal?: AbortSignal,
) {
  return apiFetch<Paginated<AdminMatch>>("/admin/matches", {
    token,
    searchParams: params,
    signal,
  });
}

export function createAdminMatch(token: string, body: CreateMatchBody) {
  return apiFetch<Match>("/admin/matches", { method: "POST", token, body });
}

export function patchAdminMatch(token: string, id: string, body: PatchMatchBody) {
  return apiFetch<Match>(`/admin/matches/${encodeURIComponent(id)}`, {
    method: "PATCH",
    token,
    body,
  });
}

export function correctAdminMatch(token: string, id: string, body: CorrectMatchBody) {
  return apiFetch<Match>(`/admin/matches/${encodeURIComponent(id)}/correct`, {
    method: "POST",
    token,
    body,
  });
}

export function cancelAdminMatch(token: string, id: string, body: CancelMatchBody) {
  return apiFetch<Match>(`/admin/matches/${encodeURIComponent(id)}/cancel`, {
    method: "POST",
    token,
    body,
  });
}

export function deleteAdminMatch(token: string, id: string, reason: string) {
  return apiFetch<DeletedEntity>(`/admin/matches/${encodeURIComponent(id)}`, {
    method: "DELETE",
    token,
    searchParams: { reason },
  });
}

export function getAdminTournaments(
  token: string,
  params?: { status?: TournamentStatus },
  signal?: AbortSignal,
) {
  return apiFetch<TournamentListResponse>("/admin/tournaments", {
    token,
    searchParams: params,
    signal,
  });
}

export function createAdminTournament(token: string, body: CreateTournamentBody) {
  return apiFetch<TournamentDetail>("/admin/tournaments", {
    method: "POST",
    token,
    body,
  });
}

export function updateAdminTournament(
  token: string,
  id: string,
  body: UpdateTournamentBody,
) {
  return apiFetch<TournamentDetail>(`/admin/tournaments/${encodeURIComponent(id)}`, {
    method: "PATCH",
    token,
    body,
  });
}

export function addTournamentParticipants(
  token: string,
  id: string,
  body: AddParticipantsBody,
) {
  return apiFetch<TournamentDetail>(
    `/admin/tournaments/${encodeURIComponent(id)}/participants`,
    {
      method: "POST",
      token,
      body,
    },
  );
}

export function removeTournamentParticipant(
  token: string,
  id: string,
  playerId: string,
) {
  return apiFetch<TournamentDetail>(
    `/admin/tournaments/${encodeURIComponent(id)}/participants/${encodeURIComponent(playerId)}`,
    { method: "DELETE", token },
  );
}

export function generateTournamentBracket(
  token: string,
  id: string,
  body: GenerateBracketBody,
) {
  return apiFetch<Bracket>(
    `/admin/tournaments/${encodeURIComponent(id)}/generate-bracket`,
    {
      method: "POST",
      token,
      body,
    },
  );
}

export function recordTournamentMatch(
  token: string,
  id: string,
  body: RecordBracketMatchBody,
) {
  return apiFetch<RecordBracketMatchResponse>(
    `/admin/tournaments/${encodeURIComponent(id)}/matches`,
    { method: "POST", token, body },
  );
}

export function getAdminAchievements(token: string, signal?: AbortSignal) {
  return apiFetch<AchievementListResponse>("/admin/achievements", { token, signal });
}

export function createAdminAchievement(token: string, body: CreateAchievementBody) {
  return apiFetch<Achievement>("/admin/achievements", { method: "POST", token, body });
}

export function updateAdminAchievement(
  token: string,
  id: string,
  body: UpdateAchievementBody,
) {
  return apiFetch<Achievement>(`/admin/achievements/${encodeURIComponent(id)}`, {
    method: "PATCH",
    token,
    body,
  });
}

export function getAdminPlayerAchievements(
  token: string,
  params?: { page?: number; page_size?: number },
  signal?: AbortSignal,
) {
  return apiFetch<Paginated<AdminPlayerAchievement>>("/admin/player-achievements", {
    token,
    searchParams: params,
    signal,
  });
}

export function awardPlayerAchievement(
  token: string,
  playerId: string,
  body: AwardAchievementBody,
) {
  return apiFetch<AchievementAward>(
    `/admin/players/${encodeURIComponent(playerId)}/achievements`,
    {
      method: "POST",
      token,
      body,
    },
  );
}

export function revokePlayerAchievement(token: string, id: string) {
  return apiFetch<DeletedEntity>(
    `/admin/player-achievements/${encodeURIComponent(id)}`,
    {
      method: "DELETE",
      token,
    },
  );
}

export function rebuildMonthlyRankings(token: string) {
  return apiFetch<MonthlyRebuildResponse>("/admin/rankings/monthly/rebuild", {
    method: "POST",
    token,
  });
}
