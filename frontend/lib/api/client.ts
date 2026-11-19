import { config } from "@/lib/config";
import type {
  AchievementListResponse,
  Bracket,
  Dashboard,
  HeadToHead,
  HealthResponse,
  Match,
  MatchListStatus,
  MonthlyRankingsResponse,
  Paginated,
  PlayerAchievementListResponse,
  PlayerListResponse,
  PlayerMatch,
  PlayerMonthlyResponse,
  PlayerProfile,
  RankingSort,
  RankingsResponse,
  RatingHistoryResponse,
  SortOrder,
  TournamentDetail,
  TournamentListResponse,
  TournamentStatus,
} from "@/types/api";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

type SearchParams = Record<string, string | number | boolean | null | undefined>;

export type ApiFetchOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  token?: string;
  searchParams?: SearchParams;
  signal?: AbortSignal;
};

function buildUrl(path: string, searchParams?: SearchParams): string {
  const base = config.apiBaseUrl.replace(/\/$/, "");
  const suffix = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${base}${suffix}`);

  if (searchParams) {
    for (const [key, value] of Object.entries(searchParams)) {
      if (value === undefined || value === null || value === "") continue;
      url.searchParams.set(key, String(value));
    }
  }

  return url.toString();
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const url = buildUrl(path, options.searchParams);
  const headers = new Headers({ Accept: "application/json" });

  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      cache: "no-store",
      signal: options.signal,
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "network_error", "Couldn't reach Shuttle Rank. Try again.", null);
  }

  if (!response.ok) {
    let code = "request_failed";
    let message = response.statusText || "Request failed";
    let details: unknown = null;

    try {
      const payload: unknown = await response.json();
      if (payload && typeof payload === "object" && "error" in payload) {
        const errorBody = (payload as { error?: unknown }).error;
        if (errorBody && typeof errorBody === "object") {
          const record = errorBody as { code?: unknown; message?: unknown; details?: unknown };
          if (typeof record.code === "string" && record.code) code = record.code;
          if (typeof record.message === "string" && record.message) message = record.message;
          details = record.details ?? null;
        }
      }
    } catch {
      details = null;
    }

    throw new ApiError(response.status, code, message, details);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(response.status, "invalid_response", "The server returned an unreadable response.", null);
  }
}

export function getHealth(signal?: AbortSignal) {
  return apiFetch<HealthResponse>("/health", { signal });
}

export function getDashboard(signal?: AbortSignal) {
  return apiFetch<Dashboard>("/dashboard", { signal });
}

export function getRankings(
  params?: {
    include_inactive?: boolean;
    sort?: RankingSort;
    order?: SortOrder;
  },
  signal?: AbortSignal,
) {
  return apiFetch<RankingsResponse>("/rankings", { searchParams: params, signal });
}

export function getMonthlyRankings(year?: number, month?: number, signal?: AbortSignal) {
  return apiFetch<MonthlyRankingsResponse>("/rankings/monthly", {
    searchParams: { year, month },
    signal,
  });
}

export function getPlayers(
  params?: { include_inactive?: boolean; search?: string },
  signal?: AbortSignal,
) {
  return apiFetch<PlayerListResponse>("/players", { searchParams: params, signal });
}

export function getPlayer(id: string, signal?: AbortSignal) {
  return apiFetch<PlayerProfile>(`/players/${encodeURIComponent(id)}`, { signal });
}

export function getPlayerMatches(
  id: string,
  params?: { page?: number; page_size?: number; status?: MatchListStatus },
  signal?: AbortSignal,
) {
  return apiFetch<Paginated<PlayerMatch>>(`/players/${encodeURIComponent(id)}/matches`, {
    searchParams: params,
    signal,
  });
}

export function getPlayerRatingHistory(id: string, signal?: AbortSignal) {
  return apiFetch<RatingHistoryResponse>(`/players/${encodeURIComponent(id)}/rating-history`, { signal });
}

export function getPlayerMonthly(id: string, signal?: AbortSignal) {
  return apiFetch<PlayerMonthlyResponse>(`/players/${encodeURIComponent(id)}/monthly`, { signal });
}

export function getPlayerAchievements(id: string, signal?: AbortSignal) {
  return apiFetch<PlayerAchievementListResponse>(`/players/${encodeURIComponent(id)}/achievements`, { signal });
}

export function getMatches(
  params?: {
    page?: number;
    page_size?: number;
    player_id?: string;
    status?: MatchListStatus;
    tournament_id?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
  },
  signal?: AbortSignal,
) {
  return apiFetch<Paginated<Match>>("/matches", { searchParams: params, signal });
}

export function getMatch(id: string, signal?: AbortSignal) {
  return apiFetch<Match>(`/matches/${encodeURIComponent(id)}`, { signal });
}

export function getHeadToHead(playerA: string, playerB: string, signal?: AbortSignal) {
  return apiFetch<HeadToHead>(
    `/head-to-head/${encodeURIComponent(playerA)}/${encodeURIComponent(playerB)}`,
    { signal },
  );
}

export function getTournaments(params?: { status?: TournamentStatus }, signal?: AbortSignal) {
  return apiFetch<TournamentListResponse>("/tournaments", { searchParams: params, signal });
}

export function getTournament(id: string, signal?: AbortSignal) {
  return apiFetch<TournamentDetail>(`/tournaments/${encodeURIComponent(id)}`, { signal });
}

export function getBracket(id: string, signal?: AbortSignal) {
  return apiFetch<Bracket>(`/tournaments/${encodeURIComponent(id)}/bracket`, { signal });
}

export function getAchievements(params?: { include_inactive?: boolean }, signal?: AbortSignal) {
  return apiFetch<AchievementListResponse>("/achievements", { searchParams: params, signal });
}
